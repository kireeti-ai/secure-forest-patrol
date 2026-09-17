#pragma once

#include "Config.h"

namespace forest::hal
{
    class ISpiBus { public: virtual ~ISpiBus() = default; virtual void begin(const config::RadioConfig &config) = 0; };
} // namespace forest::hal
