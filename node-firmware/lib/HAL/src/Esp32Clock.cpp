#include "Esp32Clock.h"
#include <Arduino.h>
namespace forest::hal { std::uint32_t Esp32Clock::millis() const { return ::millis(); } }
