#pragma once
// MAX4466-triggered TinyML acoustic pipeline (ESP32-S3, FreeRTOS, all tasks on core 0 so the
// Arduino loop() - RFID + LoRa on core 1 - is never blocked by DSP or inference).
//
//   MONITORING --RMS>=HIGH--> TRIGGERED --> CAPTURE --> INFERENCE --> RESULT --> COOLDOWN --> MONITORING
//
//   captureTask   INMP441 I2S -> 2 s ring buffer (always running, cheap DMA)
//   triggerTask   MAX4466 ADC DMA -> RMS -> hysteresis; on a rising edge, marks the ring position
//   inferenceTask waits for the post-trigger audio, then features + TFLite Micro (only when triggered)
//
// Only loop() touches SPI/LoRa: this class hands finished events over through a queue (pollEvent).

#include <cstdint>

namespace forest::acoustic {

struct AcousticEvent {
    uint8_t classIndex;     // 1 = chainsaw, 2 = gunshot (never 0/background)
    float confidence;       // 0..1
    uint16_t triggerRms;    // MAX4466 AC RMS (ADC counts) that woke the pipeline
};

class AcousticPipeline {
public:
    // Starts whatever FOREST_ACOUSTIC_TEST_MODE selects. Returns false if hardware/model init failed
    // (the RFID node keeps running either way).
    static bool begin();
    // Non-blocking; call from loop().
    static bool pollEvent(AcousticEvent& event);
};

}  // namespace forest::acoustic
