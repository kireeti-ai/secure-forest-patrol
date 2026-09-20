#include "AcousticPipeline.h"
#include <algorithm>

#include <Arduino.h>
#include <new>
#include <esp_heap_caps.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>

#include "AcousticClassifier.h"
#include "AcousticConfig.h"
#include "AcousticModelData.h"
#include "AcousticTables.h"
#include "AcousticTestVectors.h"
#include "AcousticTrigger.h"
#include "AudioCapture.h"
#include "AudioPreprocessor.h"

namespace forest::acoustic {
namespace {

enum class State : uint8_t { Monitoring, Triggered, Capture, Inference, Result, Cooldown };
const char* stateName(State s) {
    switch (s) {
        case State::Monitoring: return "MONITORING";
        case State::Triggered: return "TRIGGERED";
        case State::Capture: return "CAPTURE";
        case State::Inference: return "INFERENCE";
        case State::Result: return "RESULT";
        case State::Cooldown: return "COOLDOWN";
    }
    return "?";
}

constexpr size_t kPreSamples = ACOUSTIC_PRE_MS * (ACOUSTIC_SAMPLE_RATE / 1000);
constexpr size_t kPostSamples = ACOUSTIC_POST_MS * (ACOUSTIC_SAMPLE_RATE / 1000);
static_assert(ACOUSTIC_PRE_MS + ACOUSTIC_POST_MS == 1000, "PRE + POST must be the 1 s window the model was trained on");
static_assert(kPreSamples + kPostSamples == ACOUSTIC_WINDOW_SAMPLES, "window length mismatch");
static_assert(ACOUSTIC_WINDOW_SAMPLES == tables::kWindowSamples, "config disagrees with generated tables");
static_assert(ACOUSTIC_SAMPLE_RATE == tables::kSampleRate, "config disagrees with generated tables");
static_assert(MAX4466_TRIGGER_HIGH > MAX4466_TRIGGER_LOW, "TRIGGER_HIGH must exceed TRIGGER_LOW");
static_assert(ACOUSTIC_RING_SAMPLES >= ACOUSTIC_WINDOW_SAMPLES + 4000, "ring must hold a window plus latency margin");

// ---- shared state (allocated once in begin(); nothing is allocated per event) -----------------
SampleRing* g_ring = nullptr;
int16_t* g_window = nullptr;           // 1 s copy for preprocessing
AudioPreprocessor* g_pre = nullptr;
float* g_filterScratch = nullptr;      // only when the (optional) high-pass is enabled
AcousticClassifier g_classifier;
Inmp441Capture g_capture;
Max4466Sampler g_sampler;
QueueHandle_t g_events = nullptr;
TaskHandle_t g_inferTask = nullptr;
volatile State g_state = State::Monitoring;
volatile uint32_t g_cooldownEndMs = 0;
volatile uint16_t g_lastTriggerRms = 0;

EnergyDetectorConfig detectorConfig() {
    EnergyDetectorConfig c;
    c.high = MAX4466_TRIGGER_HIGH;
    c.low = MAX4466_TRIGGER_LOW;
    c.adaptive = ACOUSTIC_ADAPTIVE != 0;
    c.noiseAlpha = ACOUSTIC_NOISE_FLOOR_ALPHA;
    c.noiseFactor = ACOUSTIC_NOISE_FLOOR_FACTOR;
    c.noiseDelta = ACOUSTIC_NOISE_FLOOR_DELTA;
    c.relative = ACOUSTIC_RELATIVE_TRIGGER != 0;
    c.highDb = ACOUSTIC_TRIGGER_HIGH_DB;
    c.lowDb = ACOUSTIC_TRIGGER_LOW_DB;
    c.sustainBlocks = ACOUSTIC_SUSTAIN_BLOCKS;
    c.maxFloor = ACOUSTIC_MAX_NOISE_FLOOR_RMS;
    c.warmupBlocks = ACOUSTIC_NOISE_WARMUP_MS * MAX4466_SAMPLE_RATE / 1000 / MAX4466_BLOCK_SIZE;
    return c;
}

void setState(State s) {
    g_state = s;
#if ACOUSTIC_DEBUG_LOG
    Serial.printf("[ACOUSTIC] state=%s\n", stateName(s));
#endif
}

void* psramOrInternal(size_t bytes) {
    void* p = heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    return p ? p : heap_caps_malloc(bytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
}

// ---- tasks ------------------------------------------------------------------------------------
void captureTask(void*) {
    for (;;) {
        if (g_capture.pump(100) < 0) vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void triggerTask(void*) {
    EnergyDetector detector(detectorConfig());
    BlockStats st;
    uint32_t lastDebugMs = 0;
    Serial.printf("[ACOUSTIC] Trigger monitor started (HIGH=%.0f LOW=%.0f, %d Hz, %d-sample blocks%s)\n",
                  MAX4466_TRIGGER_HIGH, MAX4466_TRIGGER_LOW, MAX4466_SAMPLE_RATE, MAX4466_BLOCK_SIZE,
                  ACOUSTIC_RELATIVE_TRIGGER ? ", relative-dB" : (ACOUSTIC_ADAPTIVE ? ", adaptive" : ", fixed"));
    // The ADC DMA delivers a start-up transient (seen as RMS ~230 in the first blocks); ignore the first
    // ~0.5 s so it can neither trigger nor pollute the noise-floor warm-up.
    constexpr int kSettleBlocks = 500 * MAX4466_SAMPLE_RATE / 1000 / MAX4466_BLOCK_SIZE;
    int settleLeft = kSettleBlocks;
    bool reported = !detectorConfig().relative;   // the health report only applies to relative mode
    double dcSum = 0.0;
    uint32_t dcBlocks = 0;
    for (;;) {
        if (!g_sampler.readBlock(st, 100)) continue;
        if (settleLeft > 0) { --settleLeft; continue; }
        const uint32_t now = millis();
        const auto edge = detector.update(st.rms);
        if (!reported) {
            dcSum += st.mean;
            ++dcBlocks;
            if (detector.warmedUp()) {
                reported = true;
                Serial.printf("[ACOUSTIC] DC mean = %.0f ADC counts (logged only, not used)\n", dcSum / dcBlocks);
                Serial.printf("[ACOUSTIC] Noise floor = %.1f RMS (median of %d blocks, %d ms)\n", detector.noiseFloor(),
                              static_cast<int>(dcBlocks), ACOUSTIC_NOISE_WARMUP_MS);
                if (detector.sensorFault()) {
                    if (detector.noiseFloor() < 1.0f)
                        Serial.println("[ACOUSTIC] SENSOR FAULT: input is flat/stuck (no signal variation at all)");
                    else
                        Serial.printf("[ACOUSTIC] SENSOR FAULT: background noise too high (%.1f > %.1f RMS)\n",
                                      detector.noiseFloor(), static_cast<float>(ACOUSTIC_MAX_NOISE_FLOOR_RMS));
                    const double dc = dcSum / dcBlocks;
                    if (dc > 4000.0) Serial.println("[ACOUSTIC] DC is at the top of the ADC range: OUT looks tied/pulled to 3V3");
                    else if (dc < 100.0) Serial.println("[ACOUSTIC] DC is near 0: OUT looks grounded or unpowered");
                    Serial.println("[ACOUSTIC] ML trigger disabled (check MAX4466 wiring/power/gain, then reset)");
                } else {
                    Serial.println("[ACOUSTIC] Sensor status = OK");
                    Serial.printf("[ACOUSTIC] HIGH = %.1f  LOW = %.1f\n", detector.highThreshold(), detector.lowThreshold());
                }
            }
        }
#if ACOUSTIC_DEBUG_LOG
        if (now - lastDebugMs >= ACOUSTIC_DEBUG_INTERVAL_MS) {
            lastDebugMs = now;
            const float peak = std::max(static_cast<float>(st.max) - st.mean, st.mean - static_cast<float>(st.min));
            Serial.printf("[ACOUSTIC] RMS=%.1f peak=%.0f crest=%.1f floor=%.1f dB=%+.1f%s state=%s\n", st.rms, peak,
                          crestFactor(peak, st.rms), detector.noiseFloor(), detector.lastDeltaDb(),
                          detector.warmedUp() ? "" : " (warming up)", stateName(g_state));
        }
#else
        (void)lastDebugMs;
#endif
        if (g_state == State::Cooldown && static_cast<int32_t>(now - g_cooldownEndMs) >= 0) {
            setState(State::Monitoring);
            Serial.println("[ACOUSTIC] Monitoring");
            // If the sound is still loud the detector stays active: a new trigger then needs the
            // level to fall below LOW and rise again (no Rising edge without a Falling one).
        }
        if (edge == EnergyDetector::Edge::Rising && g_state == State::Monitoring) {
            const uint32_t triggerIndex = g_ring->total();   // ring position at the trigger
            Serial.printf("[ACOUSTIC] Trigger detected (RMS=%.1f >= %.1f)\n", st.rms, detector.highThreshold());
            setState(State::Triggered);
            g_lastTriggerRms = static_cast<uint16_t>(st.rms > 65535.0f ? 65535.0f : st.rms);
            xTaskNotify(g_inferTask, triggerIndex, eSetValueWithOverwrite);
        }
    }
}

void inferenceTask(void*) {
    for (;;) {
        uint32_t triggerIndex = 0;
        xTaskNotifyWait(0, 0xFFFFFFFFu, &triggerIndex, portMAX_DELAY);
        setState(State::Capture);
        Serial.println("[ACOUSTIC] Capturing audio");
        // Wait for the post-trigger audio (the pre-trigger part is already in the ring).
        const uint32_t deadline = millis() + 3000;
        while (static_cast<uint32_t>(g_ring->total() - triggerIndex) < kPostSamples && millis() < deadline) vTaskDelay(pdMS_TO_TICKS(10));
        const uint32_t start = triggerIndex - static_cast<uint32_t>(kPreSamples);
        if (!g_ring->copyWindow(start, ACOUSTIC_WINDOW_SAMPLES, g_window)) {
            Serial.println("[ACOUSTIC] audio window unavailable (capture stalled?) - skipping");
        } else {
            setState(State::Inference);
            Serial.println("[ACOUSTIC] Running inference");
            PreprocessOptions opt;
            opt.highPass = ACOUSTIC_FILTER_ENABLED != 0;
            opt.peakNormalize = ACOUSTIC_PEAK_NORMALIZE != 0;
            opt.peakTarget = ACOUSTIC_PEAK_TARGET;
            const uint32_t t0 = millis();
            const bool okPre = g_pre->process(g_window, g_classifier.inputBuffer(), opt, g_filterScratch);
            const uint32_t t1 = millis();
            ClassifierResult r;
            if (okPre && g_classifier.invoke(r)) {
                Serial.printf("[ML] class=%s confidence=%.3f (background %.2f chainsaw %.2f gunshot %.2f) features=%lums invoke=%.1fms\n",
                              tables::kClassNames[r.classIndex], r.confidence, r.probs[0], r.probs[1], r.probs[2],
                              (unsigned long)(t1 - t0), r.invokeUs / 1000.0f);
                setState(State::Result);
                if (r.classIndex != 0 && r.confidence >= ACOUSTIC_MIN_CONFIDENCE) {
                    AcousticEvent ev{static_cast<uint8_t>(r.classIndex), r.confidence, g_lastTriggerRms};
                    if (xQueueSend(g_events, &ev, 0) == pdTRUE) Serial.println("[ACOUSTIC] Event generated");
                    else Serial.println("[ACOUSTIC] Event queue full - event dropped");
                }
            } else {
                Serial.println("[ML] preprocessing/inference failed");
            }
        }
        g_cooldownEndMs = millis() + ACOUSTIC_COOLDOWN_MS;
        setState(State::Cooldown);
        Serial.printf("[ACOUSTIC] Cooldown (%d ms)\n", ACOUSTIC_COOLDOWN_MS);
    }
}

// ---- test modes -------------------------------------------------------------------------------
void testMode1Task(void*) {   // MAX4466: print RMS / DC / threshold decisions
    EnergyDetector detector(detectorConfig());
    BlockStats st, acc;
    int n = 0;
    float rmsMax = 0, rmsSum = 0;
    uint32_t last = millis();
    Serial.printf("[TEST1] MAX4466 on GPIO%d: printing RMS (AC counts, DC removed). HIGH=%.0f LOW=%.0f\n",
                  FOREST_MAX4466_PIN, MAX4466_TRIGGER_HIGH, MAX4466_TRIGGER_LOW);
    for (;;) {
        if (!g_sampler.readBlock(st, 200)) { Serial.println("[TEST1] no ADC data"); continue; }
        const auto e = detector.update(st.rms);
        if (e == EnergyDetector::Edge::Rising) Serial.printf("[TEST1] >>> TRIGGER  RMS=%.1f\n", st.rms);
        if (e == EnergyDetector::Edge::Falling) Serial.printf("[TEST1] <<< release  RMS=%.1f\n", st.rms);
        rmsMax = st.rms > rmsMax ? st.rms : rmsMax; rmsSum += st.rms; ++n; acc = st;
        if (millis() - last >= 500) {
            Serial.printf("[TEST1] rms avg=%.1f max=%.1f | dc=%.0f min=%d max=%d | %s\n", rmsSum / n, rmsMax, acc.mean,
                          acc.min, acc.max, detector.active() ? "ACTIVE" : "quiet");
            last = millis(); n = 0; rmsMax = 0; rmsSum = 0;
        }
    }
}

void testMode2Task(void*) {   // INMP441: sample statistics from the ring buffer
    static int16_t snap[4000];
    Serial.printf("[TEST2] INMP441 I2S (BCLK=%d WS=%d SD=%d, %d Hz, shift %d): 0.25 s statistics\n",
                  FOREST_I2S_BCLK_PIN, FOREST_I2S_WS_PIN, FOREST_I2S_DATA_PIN, ACOUSTIC_SAMPLE_RATE, ACOUSTIC_I2S_SHIFT);
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(500));
        const uint32_t end = g_ring->total();
        if (end < 4000 || !g_ring->copyWindow(end - 4000, 4000, snap)) { Serial.println("[TEST2] waiting for audio..."); continue; }
        const PcmStats s = computePcmStats(snap, 4000);
        Serial.printf("[TEST2] min=%d max=%d mean=%.1f rms=%.1f %s\n", s.min, s.max, s.mean, s.rms,
                      (s.min == 0 && s.max == 0) ? "<- all zero: check SD/BCLK/WS wiring and 3.3 V" :
                      (s.max >= 32767 || s.min <= -32768) ? "<- clipping: raise ACOUSTIC_I2S_SHIFT" : "");
    }
}

// Mode 3: needs no microphone. Runs the embedded known vectors through TFLite Micro on the device
// and compares with what the real INT8 model produced in Python; then runs the on-device
// preprocessing on a real PCM window and compares the tensor with the librosa/ml one.
constexpr int kMaxOutputDiff = 8;   // INT8 output steps of 1/256 vs the Python TFLite reference

bool runKnownVectorTest() {
    bool allOk = true;
    Serial.println("[TEST3] --- TFLite Micro vs Python INT8 reference ---");
    for (const KnownVector& v : kKnownVectors) {
        memcpy(g_classifier.inputBuffer(), v.tensor, AudioPreprocessor::kTensorSize);
        ClassifierResult r;
        if (!g_classifier.invoke(r)) { allOk = false; continue; }
        int maxDiff = 0;
        for (int i = 0; i < 3; ++i) maxDiff = max(maxDiff, abs(int(r.raw[i]) - int(v.expectedOutput[i])));
        // TFLM and full TFLite differ slightly in conv/softmax rounding: measured worst case on 343 real
        // windows was 8/256 (docs/ACOUSTIC_NODE.md). The predicted class must always agree.
        const bool ok = r.classIndex == v.expectedClass && maxDiff <= kMaxOutputDiff;
        allOk &= ok;
        Serial.printf("[TEST3] %-44s expected=%s got=%s conf=%.3f raw=[%d %d %d] ref=[%d %d %d] maxdiff=%d invoke=%.1fms %s\n",
                      v.name, tables::kClassNames[v.expectedClass], tables::kClassNames[r.classIndex], r.confidence,
                      r.raw[0], r.raw[1], r.raw[2], v.expectedOutput[0], v.expectedOutput[1], v.expectedOutput[2], maxDiff,
                      r.invokeUs / 1000.0f, ok ? "PASS" : "FAIL");
    }
    Serial.println("[TEST3] --- on-device preprocessing vs ml/ features (real gunshot window, no mic) ---");
    PreprocessOptions opt;
    opt.peakNormalize = false;   // the reference tensor was computed on the raw window
    static int8_t tensor[AudioPreprocessor::kTensorSize];
    const uint32_t t0 = micros();
    g_pre->process(kKnownPcmGunshot, tensor, opt);
    const uint32_t us = micros() - t0;
    int exact = 0, big = 0;
    for (int i = 0; i < AudioPreprocessor::kTensorSize; ++i) {
        const int d = abs(int(tensor[i]) - int(kVec_gunshot[i]));
        exact += d == 0; big += d > 1;
    }
    const bool preOk = big == 0 && exact >= AudioPreprocessor::kTensorSize * 999 / 1000;
    allOk &= preOk;
    Serial.printf("[TEST3] preprocessing: %d/%d exact, %d off by >1 LSB, %.1f ms %s\n", exact,
                  AudioPreprocessor::kTensorSize, big, us / 1000.0f, preOk ? "PASS" : "FAIL");
    memcpy(g_classifier.inputBuffer(), tensor, AudioPreprocessor::kTensorSize);
    ClassifierResult r;
    if (g_classifier.invoke(r)) {
        const bool ok = r.classIndex == 2;
        allOk &= ok;
        Serial.printf("[TEST3] end-to-end (device features -> device model): class=%s conf=%.3f %s\n",
                      tables::kClassNames[r.classIndex], r.confidence, ok ? "PASS" : "FAIL");
    }
    Serial.printf("[TEST3] arena used %u / %u bytes, model %u bytes, free heap %u, free PSRAM %u\n",
                  (unsigned)g_classifier.arenaUsedBytes(), (unsigned)g_classifier.arenaSizeBytes(), (unsigned)kModelDataLen,
                  (unsigned)ESP.getFreeHeap(), (unsigned)ESP.getFreePsram());
    Serial.println(allOk ? "[TEST3] RESULT: PASS" : "[TEST3] RESULT: FAIL");
    return allOk;
}

// Mode 4: BENCH DEMO. Both microphones live, no MAX4466 gate: every ACOUSTIC_DEMO_INTERVAL_MS the newest
// 1 s of real INMP441 audio goes through the real preprocessing + model and the result is logged next to the
// MAX4466 readings. Nothing is simulated. It is continuous inference (power hungry) and its predictions are
// unvalidated on real microphones, so it is a bench/showcase mode, not the field configuration.
volatile float g_maxRms = 0.0f, g_maxDc = 0.0f;
volatile int g_maxMin = 0, g_maxMax = 0;
volatile bool g_maxSeen = false;

void maxMonitorTask(void*) {   // keeps the MAX4466 DMA drained and publishes its latest block statistics
    BlockStats st;
    for (;;) {
        if (!g_sampler.readBlock(st, 200)) continue;
        g_maxRms = st.rms; g_maxDc = st.mean; g_maxMin = st.min; g_maxMax = st.max; g_maxSeen = true;
    }
}

void demoTask(void*) {
    uint32_t n = 0;
    Serial.printf("[DEMO] bench demo: classifying live INMP441 audio every %d ms (events over LoRa: %s)\n",
                  ACOUSTIC_DEMO_INTERVAL_MS, ACOUSTIC_DEMO_SEND_EVENTS ? "ON" : "off, log only");
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(ACOUSTIC_DEMO_INTERVAL_MS));
        const uint32_t end = g_ring->total();
        if (end < ACOUSTIC_WINDOW_SAMPLES || !g_ring->copyWindow(end - ACOUSTIC_WINDOW_SAMPLES, ACOUSTIC_WINDOW_SAMPLES, g_window)) {
            Serial.println("[DEMO] waiting for INMP441 audio...");
            continue;
        }
        const PcmStats ps = computePcmStats(g_window, ACOUSTIC_WINDOW_SAMPLES);
        PreprocessOptions opt;
        opt.highPass = ACOUSTIC_FILTER_ENABLED != 0;
        opt.peakNormalize = ACOUSTIC_PEAK_NORMALIZE != 0;
        opt.peakTarget = ACOUSTIC_PEAK_TARGET;
        const uint32_t t0 = millis();
        const bool okPre = g_pre->process(g_window, g_classifier.inputBuffer(), opt, g_filterScratch);
        const uint32_t t1 = millis();
        ClassifierResult r;
        if (!okPre || !g_classifier.invoke(r)) { Serial.println("[DEMO] preprocessing/inference failed"); continue; }
        ++n;
        Serial.printf("[DEMO #%lu] INMP441 rms=%.0f min=%d max=%d%s | MAX4466 ", (unsigned long)n, ps.rms, ps.min, ps.max,
                      (ps.max >= 32767 || ps.min <= -32768) ? " CLIP" : "");
        if (g_maxSeen) Serial.printf("rms=%.1f dc=%.0f range=%d..%d", g_maxRms, g_maxDc, g_maxMin, g_maxMax);
        else Serial.print("no data");
        Serial.printf(" | class=%s conf=%.2f [bg %.2f chainsaw %.2f gunshot %.2f] features=%lums invoke=%.0fms\n",
                      tables::kClassNames[r.classIndex], r.confidence, r.probs[0], r.probs[1], r.probs[2],
                      (unsigned long)(t1 - t0), r.invokeUs / 1000.0f);
#if ACOUSTIC_DEMO_SEND_EVENTS
        if (r.classIndex != 0 && r.confidence >= ACOUSTIC_MIN_CONFIDENCE) {
            AcousticEvent ev{static_cast<uint8_t>(r.classIndex), r.confidence, static_cast<uint16_t>(g_maxRms)};
            if (xQueueSend(g_events, &ev, 0) == pdTRUE) Serial.println("[DEMO] event queued for LoRa");
        }
#endif
    }
}

bool initCommon(bool needClassifier) {
    g_pre = new (psramOrInternal(sizeof(AudioPreprocessor))) AudioPreprocessor();
    if (g_pre == nullptr) return false;
    if (needClassifier && !g_classifier.begin(ACOUSTIC_TENSOR_ARENA_BYTES)) return false;
    return true;
}

bool initAudioIn() {
    int16_t* storage = static_cast<int16_t*>(psramOrInternal(sizeof(int16_t) * ACOUSTIC_RING_SAMPLES));
    g_ring = new SampleRing(storage, ACOUSTIC_RING_SAMPLES);
    g_window = static_cast<int16_t*>(psramOrInternal(sizeof(int16_t) * ACOUSTIC_WINDOW_SAMPLES));
    if (ACOUSTIC_FILTER_ENABLED) g_filterScratch = static_cast<float*>(psramOrInternal(sizeof(float) * ACOUSTIC_WINDOW_SAMPLES));
    if (storage == nullptr || g_window == nullptr) return false;
    return g_capture.begin(FOREST_I2S_BCLK_PIN, FOREST_I2S_WS_PIN, FOREST_I2S_DATA_PIN, ACOUSTIC_SAMPLE_RATE,
                           ACOUSTIC_I2S_SHIFT, g_ring);
}

bool initTrigger() { return g_sampler.begin(FOREST_MAX4466_PIN, MAX4466_SAMPLE_RATE, MAX4466_BLOCK_SIZE); }

}  // namespace

bool AcousticPipeline::begin() {
    Serial.printf("[ACOUSTIC] init (test mode %d). Pins: MAX4466=GPIO%d I2S BCLK=%d WS=%d SD=%d\n", FOREST_ACOUSTIC_TEST_MODE,
                  FOREST_MAX4466_PIN, FOREST_I2S_BCLK_PIN, FOREST_I2S_WS_PIN, FOREST_I2S_DATA_PIN);
#if FOREST_ACOUSTIC_TEST_MODE == 1
    if (!initTrigger()) return false;
    xTaskCreatePinnedToCore(testMode1Task, "ac-test1", 8192, nullptr, 2, nullptr, 0);
    return true;
#elif FOREST_ACOUSTIC_TEST_MODE == 2
    if (!initAudioIn()) return false;
    xTaskCreatePinnedToCore(captureTask, "ac-capture", 4096, nullptr, 3, nullptr, 0);
    xTaskCreatePinnedToCore(testMode2Task, "ac-test2", 4096, nullptr, 1, nullptr, 0);
    return true;
#elif FOREST_ACOUSTIC_TEST_MODE == 3
    if (!initCommon(true)) return false;
    return runKnownVectorTest();
#elif FOREST_ACOUSTIC_TEST_MODE == 4
    if (!initCommon(true) || !initAudioIn()) { Serial.println("[DEMO] init failed"); return false; }
    g_events = xQueueCreate(4, sizeof(AcousticEvent));
    xTaskCreatePinnedToCore(captureTask, "ac-capture", 4096, nullptr, 3, nullptr, 0);
    if (initTrigger()) xTaskCreatePinnedToCore(maxMonitorTask, "ac-max", 4096, nullptr, 2, nullptr, 0);
    else Serial.println("[DEMO] MAX4466 sampler unavailable - continuing with INMP441 only");
    xTaskCreatePinnedToCore(demoTask, "ac-demo", 16384, nullptr, 1, nullptr, 0);
    return true;
#else
    if (!initCommon(true) || !initAudioIn() || !initTrigger()) {
        Serial.println("[ACOUSTIC] init failed - acoustic pipeline disabled, RFID node continues");
        return false;
    }
    g_events = xQueueCreate(4, sizeof(AcousticEvent));
    xTaskCreatePinnedToCore(inferenceTask, "ac-infer", 16384, nullptr, 1, &g_inferTask, 0);
    xTaskCreatePinnedToCore(captureTask, "ac-capture", 4096, nullptr, 3, nullptr, 0);
    xTaskCreatePinnedToCore(triggerTask, "ac-trigger", 8192, nullptr, 2, nullptr, 0);
    Serial.printf("[ACOUSTIC] pipeline running: ring %u samples, window %d ms (pre %d + post %d), cooldown %d ms\n",
                  (unsigned)ACOUSTIC_RING_SAMPLES, ACOUSTIC_PRE_MS + ACOUSTIC_POST_MS, ACOUSTIC_PRE_MS, ACOUSTIC_POST_MS, ACOUSTIC_COOLDOWN_MS);
    return true;
#endif
}

bool AcousticPipeline::pollEvent(AcousticEvent& event) {
    return g_events != nullptr && xQueueReceive(g_events, &event, 0) == pdTRUE;
}

}  // namespace forest::acoustic
