#pragma once
// RG1602A (HD44780-compatible 16x2 character LCD), 4-bit parallel mode, write-only
// (R/W tied to GND -- no busy-flag polling, timing is delay-based per the HD44780
// datasheet). Own driver: no LiquidCrystal, matches the rest of ForestSensors.
//
//   application -> ForestSensors::Lcd1602 -> 6 GPIOs (RS, EN, D4-D7) -> HD44780
//
// Caller discipline: only call clear()/setLine() on a state change, never every
// loop() pass. Each command/char write blocks for 40us-1.5ms (the clear command
// is the slow one); that is fine on a state change but would compete with LoRa
// RX/TX and RFID polling if called unconditionally.

#include <cstdint>

namespace ForestSensors {

class Lcd1602 {
public:
    // rsPin/enPin/d4..d7Pin are the six GPIOs wired to the LCD. Contrast (VO) is
    // set by an on-board trim pot, not driven by the MCU.
    bool begin(int rsPin, int enPin, int d4Pin, int d5Pin, int d6Pin, int d7Pin);
    void clear();
    // row: 0 or 1. Clears just that row's 16 cells first, then writes text
    // left-aligned, truncated to 16 characters -- the caller never needs to
    // pad or truncate itself.
    void setLine(uint8_t row, const char* text);

private:
    void pulseEnable_();
    void writeNibble_(uint8_t nibble);
    void send_(uint8_t value, bool isCommand);
    void command_(uint8_t value) { send_(value, true); }
    void writeChar_(char c) { send_(static_cast<uint8_t>(c), false); }

    int rsPin_ = -1, enPin_ = -1;
    int dataPins_[4] = {-1, -1, -1, -1};
    bool ready_ = false;
};

}  // namespace ForestSensors
