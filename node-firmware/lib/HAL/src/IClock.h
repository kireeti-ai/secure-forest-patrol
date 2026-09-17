#pragma once

#include <cstdint>

namespace forest::hal
{
    class IClock { public: virtual ~IClock() = default; virtual std::uint32_t millis() const = 0; };
} // namespace forest::hal
