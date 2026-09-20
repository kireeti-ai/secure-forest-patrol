#pragma once
// DS3231 real-time clock over I2C (address 0x68). Own register-level driver: timekeeping registers
// 0x00-0x06 in packed BCD, status register 0x0F (OSF = oscillator stopped, time not trustworthy),
// temperature registers 0x11-0x12. Uses only the Arduino-ESP32 Wire (I2C HAL), no DS3231 library.
//
//   application -> ForestSensors::DS3231 -> Wire (ESP32 I2C HAL) -> DS3231

#include <cstdint>

namespace ForestSensors {

struct DateTime {
    uint16_t year = 2000;   // 2000..2099
    uint8_t month = 1, day = 1, hour = 0, minute = 0, second = 0;
};

class DS3231 {
public:
    bool begin(int sdaPin, int sclPin);          // probes the device; false if it does not ACK
    bool readDateTime(DateTime& out);            // false on I2C error
    bool setDateTime(const DateTime& in);        // also clears the OSF flag
    bool lostPower();                            // OSF set: the time was lost, set it before use
    bool readTemperatureCentiC(int16_t& centiC); // 0.25 C resolution
    uint32_t unixTime(const DateTime& t) const;  // seconds since 1970-01-01 (UTC as stored)

private:
    bool readRegs(uint8_t reg, uint8_t* out, uint8_t n);
    bool writeRegs(uint8_t reg, const uint8_t* data, uint8_t n);
    bool ready_ = false;
};

}  // namespace ForestSensors
