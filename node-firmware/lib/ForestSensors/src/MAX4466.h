#pragma once
// MAX4466 electret microphone amplifier on an ESP32-S3 ADC1 pin, sampled by the ADC digital controller
// through DMA (no per-sample CPU work). The MAX4466 output rides on a ~VCC/2 bias, so the raw ADC value is
// never used directly: each block has its DC (mean) removed and its RMS computed.
//
//   application -> ForestSensors::MAX4466 -> ESP32 ADC1 digital controller + DMA -> MAX4466 OUT

#include <cstdint>

namespace ForestSensors {

struct BlockStats {
    float rms = 0.0f;    // AC RMS of the block (DC removed), in ADC counts
    float mean = 0.0f;   // DC level in ADC counts (a healthy MAX4466 idles near 2000 at 3.3 V)
    int16_t min = 0;
    int16_t max = 0;
};

class MAX4466 {
public:
    // gpio must be an ADC1 pin (GPIO1..10 on the ESP32-S3); GPIO1 = ADC1_CH0.
    bool begin(int gpio, int sampleRateHz, int blockSize);
    // Waits up to timeoutMs for one full block. False on timeout / driver error.
    bool readBlock(BlockStats& stats, uint32_t timeoutMs);
    // Convenience: RMS of the next block.
    bool readRms(float& rms, uint32_t timeoutMs);

    // Two-threshold trigger with hysteresis on the block RMS: rises at >= high, falls at < low.
    void setThresholds(float high, float low) { high_ = high; low_ = low; }
    bool getTriggerState() const { return triggered_; }

    int blockSize() const { return blockSize_; }

private:
    int blockSize_ = 0;
    int filled_ = 0;
    int16_t* block_ = nullptr;   // allocated once in begin()
    bool started_ = false;
    float high_ = 50.0f, low_ = 30.0f;
    bool triggered_ = false;
};

}  // namespace ForestSensors
