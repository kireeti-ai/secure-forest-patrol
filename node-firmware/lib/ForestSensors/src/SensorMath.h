#pragma once
// Portable helpers used by the ForestSensors drivers (no Arduino dependency, host-tested).

#include <cstddef>
#include <cstdint>

namespace ForestSensors {

// CRC_A of ISO/IEC 14443-3 (poly 0x8408 reflected, init 0x6363). Appended to RC522 select / halt frames.
inline uint16_t crcA(const uint8_t* data, size_t len) {
    uint16_t crc = 0x6363;
    for (size_t i = 0; i < len; ++i) {
        uint8_t b = data[i] ^ static_cast<uint8_t>(crc & 0xFF);
        b = static_cast<uint8_t>(b ^ (b << 4));
        crc = static_cast<uint16_t>((crc >> 8) ^ (static_cast<uint16_t>(b) << 8) ^ (static_cast<uint16_t>(b) << 3) ^ (b >> 4));
    }
    return crc;
}

// DS3231 stores every time field as packed BCD.
inline uint8_t bcdToBin(uint8_t v) { return static_cast<uint8_t>((v >> 4) * 10 + (v & 0x0F)); }
inline uint8_t binToBcd(uint8_t v) { return static_cast<uint8_t>(((v / 10) << 4) | (v % 10)); }

// AC RMS of a block of ADC samples: subtract the block mean, then sqrt(mean(x^2)).
float blockRms(const int16_t* samples, size_t count, float* meanOut = nullptr);

}  // namespace ForestSensors
