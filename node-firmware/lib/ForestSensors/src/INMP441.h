#pragma once
// INMP441 I2S MEMS microphone. The sensor streams 24-bit samples in a 32-bit I2S slot; this driver configures
// the ESP32-S3 I2S peripheral in RX/master mode (Philips standard, left slot because L/R is tied to GND) and
// converts to signed 16-bit PCM.
//
//   application -> ForestSensors::INMP441 -> ESP32 I2S0 + DMA (legacy driver/i2s.h) -> INMP441

#include <cstddef>
#include <cstdint>

namespace ForestSensors {

class INMP441 {
public:
    // bclk / ws / data pins, sample rate in Hz (16000 for the model), `shift`: right shift applied to the
    // 32-bit sample to reach 16 bit (16 = keep the top 16 bits of the 24-bit data).
    bool begin(int bclkPin, int wsPin, int dataPin, int sampleRate, int shift);
    // Reads up to maxSamples PCM16 samples (blocks up to timeoutMs for the DMA). Returns the number read,
    // or -1 on a driver error.
    int readSamples(int16_t* out, size_t maxSamples, uint32_t timeoutMs);
    bool started() const { return started_; }

private:
    int shift_ = 16;
    bool started_ = false;
};

}  // namespace ForestSensors
