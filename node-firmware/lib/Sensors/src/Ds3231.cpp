#include "Ds3231.h"

namespace forest::sensors
{
    namespace
    {
        constexpr std::uint8_t kAddress = 0x68U;
        std::uint8_t bcdToBinary(std::uint8_t value) { return static_cast<std::uint8_t>((value >> 4U) * 10U + (value & 0x0FU)); }
        bool validBcd(std::uint8_t value, std::uint8_t maximum)
        {
            return (value & 0x0FU) <= 9U && ((value >> 4U) <= 9U) && bcdToBinary(value) <= maximum;
        }
        std::uint8_t binaryToBcd(std::uint8_t value) { return static_cast<std::uint8_t>(((value / 10U) << 4U) | (value % 10U)); }
    }

    bool Ds3231::begin(int sdaPin, int sclPin)
    {
        initialized_ = bus_.begin(sdaPin, sclPin);
        return initialized_;
    }

    bool Ds3231::read(RtcSample &sample)
    {
        sample = {};
        if (!initialized_) return false;

        // Read 7 time registers (0x00 to 0x06)
        const std::uint8_t timeReg = 0x00U;
        std::uint8_t timeBuf[7]{};
        if (!bus_.writeRead(kAddress, &timeReg, 1U, timeBuf, sizeof(timeBuf))) return false;

        const std::uint8_t seconds = timeBuf[0] & 0x7FU;
        const std::uint8_t minutes = timeBuf[1] & 0x7FU;
        const std::uint8_t hours = timeBuf[2] & 0x3FU;
        const std::uint8_t day = timeBuf[4] & 0x3FU;
        const std::uint8_t month = timeBuf[5] & 0x1FU;
        const std::uint8_t year = timeBuf[6];

        const bool timeOk = validBcd(seconds, 59U) && validBcd(minutes, 59U) && validBcd(hours, 23U) &&
                            validBcd(day, 31U) && validBcd(month, 12U) && validBcd(year, 99U) && day != 0U && month != 0U;

        if (timeOk)
        {
            sample.timeValid = true;
            sample.year = static_cast<std::uint16_t>(2000U + bcdToBinary(year));
            sample.month = bcdToBinary(month);
            sample.day = bcdToBinary(day);
            sample.hour = bcdToBinary(hours);
            sample.minute = bcdToBinary(minutes);
            sample.second = bcdToBinary(seconds);
        }

        // Read 2 temperature registers (0x11 to 0x12)
        const std::uint8_t tempReg = 0x11U;
        std::uint8_t tempBuf[2]{};
        if (bus_.writeRead(kAddress, &tempReg, 1U, tempBuf, sizeof(tempBuf)))
        {
            const std::int16_t whole = static_cast<std::int8_t>(tempBuf[0]);
            const std::uint8_t fraction = tempBuf[1] >> 6U;
            sample.temperatureCentiC = static_cast<std::int16_t>(whole * 100 + fraction * 25);
            sample.temperatureValid = sample.temperatureCentiC >= -4000 && sample.temperatureCentiC <= 8500;
        }

        return sample.timeValid || sample.temperatureValid;
    }

    bool Ds3231::setDateTime(const RtcSample &sample)
    {
        if (!initialized_ || !sample.timeValid || sample.year < 2000U || sample.year > 2099U ||
            sample.month < 1U || sample.month > 12U || sample.day < 1U || sample.day > 31U ||
            sample.hour > 23U || sample.minute > 59U || sample.second > 59U) return false;
        const std::uint8_t registers[] = {
            0x00U, binaryToBcd(sample.second), binaryToBcd(sample.minute), binaryToBcd(sample.hour),
            0x01U, binaryToBcd(sample.day), binaryToBcd(sample.month), binaryToBcd(static_cast<std::uint8_t>(sample.year - 2000U))};
        return bus_.write(kAddress, registers, sizeof(registers));
    }
} // namespace forest::sensors
