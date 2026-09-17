#pragma once
#include "ISpiBus.h"
namespace forest::hal
{
    class Esp32SpiBus final : public ISpiBus { public: void begin(const config::RadioConfig &config) override; };
} // namespace forest::hal
