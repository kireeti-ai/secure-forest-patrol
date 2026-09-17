#pragma once

#include "IClock.h"

namespace forest::hal
{
    class Esp32Clock final : public IClock { public: std::uint32_t millis() const override; };
} // namespace forest::hal
