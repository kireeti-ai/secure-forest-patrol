#pragma once

namespace forest::hal {

enum class PinLevel {
    low,
    high,
};

class IGpioPin {
public:
    virtual ~IGpioPin() = default;

    virtual void write(PinLevel level) = 0;
    virtual PinLevel read() const = 0;
};

}  // namespace forest::hal

