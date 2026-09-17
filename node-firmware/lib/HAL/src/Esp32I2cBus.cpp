#include "Esp32I2cBus.h"

#include <Arduino.h>
#include <Wire.h>

namespace jalari::hal
{
    bool Esp32I2cBus::begin(int sdaPin, int sclPin)
    {
        pinMode(sdaPin, INPUT_PULLUP);
        pinMode(sclPin, INPUT_PULLUP);
        bool ok = Wire.begin(sdaPin, sclPin);
        Wire.setTimeOut(100); // Set 100ms timeout to prevent hanging on missing I2C devices
        return ok;
    }

    bool Esp32I2cBus::writeRead(std::uint8_t address, const std::uint8_t *writeData, std::size_t writeSize,
                                std::uint8_t *readData, std::size_t readSize)
    {
        Wire.beginTransmission(address);
        for (std::size_t i = 0; i < writeSize; ++i) Wire.write(writeData[i]);
        // Send STOP condition on error to clear bus state
        if (Wire.endTransmission(true) != 0) return false;
        if (Wire.requestFrom(static_cast<int>(address), static_cast<int>(readSize)) != readSize) return false;
        for (std::size_t i = 0; i < readSize; ++i) readData[i] = static_cast<std::uint8_t>(Wire.read());
        return true;
    }

    bool Esp32I2cBus::write(std::uint8_t address, const std::uint8_t *data, std::size_t size)
    {
        Wire.beginTransmission(address);
        for (std::size_t i = 0; i < size; ++i) Wire.write(data[i]);
        return Wire.endTransmission(true) == 0;
    }
} // namespace jalari::hal
