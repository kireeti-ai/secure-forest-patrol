#pragma once
// Compile-time configuration for the acoustic pipeline. Every value can be
// overridden with a PlatformIO build flag (-D NAME=value), matching the RFID
// pin convention in src/main.cpp. Nothing here is a hidden magic number: each
// value says what it is and why it has that default.

// ---- Pins -------------------------------------------------------------------
// MAX4466 analog mic OUT -> ADC1 (works while radios are on; ADC2 would not).
#ifndef FOREST_MAX4466_PIN
#define FOREST_MAX4466_PIN 1  // GPIO1 = ADC1_CH0
#endif
// INMP441 I2S microphone (L/R tied to GND -> left channel).
#ifndef FOREST_I2S_BCLK_PIN
#define FOREST_I2S_BCLK_PIN 6  // SCK / BCLK
#endif
#ifndef FOREST_I2S_WS_PIN
#define FOREST_I2S_WS_PIN 7    // WS / LRCLK
#endif
#ifndef FOREST_I2S_DATA_PIN
#define FOREST_I2S_DATA_PIN 8  // SD
#endif

// ---- MAX4466 wake-up trigger ------------------------------------------------
// Sample rate of the trigger ADC. 8 kHz is plenty for an energy detector and
// keeps DMA traffic low.
#ifndef MAX4466_SAMPLE_RATE
#define MAX4466_SAMPLE_RATE 8000
#endif
// Samples per RMS block. 128 @ 8 kHz = 16 ms, short enough not to average a
// gunshot impulse away, long enough to be a stable energy estimate.
#ifndef MAX4466_BLOCK_SIZE
#define MAX4466_BLOCK_SIZE 128
#endif
// Hysteresis, in raw 12-bit ADC counts of AC RMS (DC removed per block).
// **UNCALIBRATED DEFAULTS**: they depend on the MAX4466 gain trimmer and the
// site. Use FOREST_ACOUSTIC_TEST_MODE=1 to read the quiet RMS and set them to
// roughly 3-4x quiet RMS (HIGH) and 2x (LOW). Requirement: HIGH > LOW.
#ifndef MAX4466_TRIGGER_HIGH
#define MAX4466_TRIGGER_HIGH 120.0f
#endif
#ifndef MAX4466_TRIGGER_LOW
#define MAX4466_TRIGGER_LOW 60.0f
#endif
// Optional adaptive threshold (off by default; fixed thresholds first).
// When on: trigger if rms > noise_floor * FACTOR + DELTA, where noise_floor is
// a slow EMA of RMS taken only while quiet. HIGH/LOW then act as lower bounds.
#ifndef ACOUSTIC_ADAPTIVE
#define ACOUSTIC_ADAPTIVE 0
#endif
#ifndef ACOUSTIC_NOISE_FLOOR_ALPHA
#define ACOUSTIC_NOISE_FLOOR_ALPHA 0.01f
#endif
#ifndef ACOUSTIC_NOISE_FLOOR_FACTOR
#define ACOUSTIC_NOISE_FLOOR_FACTOR 3.0f
#endif
#ifndef ACOUSTIC_NOISE_FLOOR_DELTA
#define ACOUSTIC_NOISE_FLOOR_DELTA 20.0f
#endif

// ---- Event cycle ------------------------------------------------------------
// After an inference the trigger is ignored for this long, so one chainsaw or
// gunshot burst does not cause dozens of inferences.
#ifndef ACOUSTIC_COOLDOWN_MS
#define ACOUSTIC_COOLDOWN_MS 5000
#endif
// Send an event only if confidence >= this (0 = every gunshot/chainsaw
// prediction, as specified). The shipped model has low precision (see docs);
// raise this once field data exists.
#ifndef ACOUSTIC_MIN_CONFIDENCE
#define ACOUSTIC_MIN_CONFIDENCE 0.0f
#endif

// ---- INMP441 capture / ML window --------------------------------------------
// Must equal the training pipeline (16 kHz, 1.0 s window). Do not change
// without regenerating tables from ml/.
#define ACOUSTIC_SAMPLE_RATE 16000
#define ACOUSTIC_WINDOW_SAMPLES 16000
// Audio kept before the trigger (so the event onset is not lost) and audio
// captured after it. PRE + POST must equal 1000 ms.
#ifndef ACOUSTIC_PRE_MS
#define ACOUSTIC_PRE_MS 250
#endif
#ifndef ACOUSTIC_POST_MS
#define ACOUSTIC_POST_MS 750
#endif
// The INMP441 delivers 24-bit samples left-justified in a 32-bit slot;
// >> 16 keeps the top 16 bits. Lower this (e.g. 14) to add digital gain.
#ifndef ACOUSTIC_I2S_SHIFT
#define ACOUSTIC_I2S_SHIFT 16
#endif
// Circular buffer length in samples (2 s), allocated once in PSRAM.
#ifndef ACOUSTIC_RING_SAMPLES
#define ACOUSTIC_RING_SAMPLES 32000
#endif

// ---- Preprocessing ----------------------------------------------------------
// 80 Hz high-pass (2nd-order Butterworth). OFF: the shipped model was trained
// without it and the A/B experiment showed no consistent benefit
// (ml/reports/FILTER_REPORT.md). Do not enable unless the model is retrained.
#ifndef ACOUSTIC_FILTER_ENABLED
#define ACOUSTIC_FILTER_ENABLED 0
#endif
// Training peak-normalised each *recording* to -3 dBFS. A device has no whole
// recording, so each 1 s window is peak-normalised to the same level instead.
#ifndef ACOUSTIC_PEAK_NORMALIZE
#define ACOUSTIC_PEAK_NORMALIZE 1
#endif
#define ACOUSTIC_PEAK_TARGET 0.70794578f  // 10^(-3/20)

// ---- TFLite Micro -----------------------------------------------------------
// Start value; the classifier logs the bytes actually used so it can be trimmed.
#ifndef ACOUSTIC_TENSOR_ARENA_BYTES
#define ACOUSTIC_TENSOR_ARENA_BYTES 65536
#endif

// ---- Test modes (FOREST_ACOUSTIC_TEST_MODE) ---------------------------------
// 0 = full pipeline (default)      1 = MAX4466 RMS/threshold monitor
// 2 = INMP441 sample statistics    3 = ML on the embedded known test vectors
#ifndef FOREST_ACOUSTIC_TEST_MODE
#define FOREST_ACOUSTIC_TEST_MODE 0
#endif

// Verbose per-block RMS logging (high frequency; keep 0 outside bring-up).
#ifndef ACOUSTIC_DEBUG_LOG
#define ACOUSTIC_DEBUG_LOG 0
#endif

// Model identity sent with events.
#define ACOUSTIC_MODEL_VERSION "forest-acoustic-v1"
