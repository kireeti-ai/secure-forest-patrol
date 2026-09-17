#pragma once

#include <cstdint>

namespace forest::hal {

class ISystemClock {
public:
    virtual ~ISystemClock() = default;

    virtual std::uint32_t millis() const = 0;
};

}  // namespace forest::hal

