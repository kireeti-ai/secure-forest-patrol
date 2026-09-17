#pragma once
#include "IDelay.h"
namespace forest::hal { class Esp32Delay final : public IDelay { public: void milliseconds(unsigned long duration) const override; }; }
