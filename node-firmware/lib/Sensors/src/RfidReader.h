#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace forest::sensors
{
    class RfidReader final
    {
    public:
        bool begin(int sckPin, int misoPin, int mosiPin, int chipSelectPin, int resetPin);
        bool readUid(std::array<std::uint8_t, 10> &uid, std::size_t &uidSize);
        bool isInitialized() const { return initialized_; }

    private:
        bool initialized_ = false;
        int chipSelectPin_ = -1;
        int resetPin_ = -1;
        std::array<std::uint8_t, 10> lastUid_{};
        std::size_t lastUidSize_ = 0U;
    };
} // namespace forest::sensors
