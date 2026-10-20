#include "Lcd1602.h"

#include <Arduino.h>
#include <cstring>
#include <driver/gpio.h>

namespace ForestSensors {

namespace {
constexpr uint8_t kRowAddr[2] = {0x00U, 0x40U};  // DDRAM base address per row, 16x2 part
constexpr uint8_t kCols = 16U;
}  // namespace

bool Lcd1602::begin(int rsPin, int enPin, int d4Pin, int d5Pin, int d6Pin, int d7Pin) {
    rsPin_ = rsPin;
    enPin_ = enPin;
    dataPins_[0] = d4Pin;
    dataPins_[1] = d5Pin;
    dataPins_[2] = d6Pin;
    dataPins_[3] = d7Pin;

    pinMode(rsPin_, OUTPUT);
    pinMode(enPin_, OUTPUT);
    digitalWrite(rsPin_, LOW);
    digitalWrite(enPin_, LOW);
    // Default drive strength on the ESP32-S3 is GPIO_DRIVE_CAP_2 (medium), not the
    // chip's maximum. A breadboard jumper adds real contact resistance; driving at
    // the strongest available level gives the cleanest possible logic transitions
    // into that resistance instead of a borderline one.
    gpio_set_drive_capability(static_cast<gpio_num_t>(rsPin_), GPIO_DRIVE_CAP_3);
    gpio_set_drive_capability(static_cast<gpio_num_t>(enPin_), GPIO_DRIVE_CAP_3);
    for (int pin : dataPins_) {
        pinMode(pin, OUTPUT);
        digitalWrite(pin, LOW);
        gpio_set_drive_capability(static_cast<gpio_num_t>(pin), GPIO_DRIVE_CAP_3);
    }

    // HD44780 power-on init: wait for internal reset, then force the controller
    // into 8-bit mode three times (it may have powered up in either mode), then
    // switch to 4-bit. These are the datasheet's mandated delays, not tuning.
    delay(45);
    writeNibble_(0x03U);
    delayMicroseconds(4500);
    writeNibble_(0x03U);
    delayMicroseconds(150);
    writeNibble_(0x03U);
    delayMicroseconds(150);
    writeNibble_(0x02U);  // now in 4-bit mode
    delayMicroseconds(150);

    command_(0x28U);  // function set: 4-bit, 2 line, 5x8 font
    command_(0x08U);  // display off
    command_(0x01U);  // clear (also returns home); needs the long delay inside command_
    command_(0x06U);  // entry mode: increment cursor, no display shift
    command_(0x0CU);  // display on, cursor off, blink off

    ready_ = true;
    return true;
}

void Lcd1602::clear() {
    if (!ready_) return;
    command_(0x01U);
}

void Lcd1602::setLine(uint8_t row, const char* text) {
    if (!ready_ || row > 1U) return;
    command_(static_cast<uint8_t>(0x80U | kRowAddr[row]));
    const std::size_t len = text ? strnlen(text, kCols) : 0U;
    for (std::size_t i = 0; i < kCols; ++i) {
        writeChar_(i < len ? text[i] : ' ');
    }
}

void Lcd1602::pulseEnable_() {
    digitalWrite(enPin_, HIGH);
    delayMicroseconds(1);  // EN pulse width, datasheet minimum is ~450ns
    digitalWrite(enPin_, LOW);
    delayMicroseconds(1);  // EN cycle time before the controller latches data
}

void Lcd1602::writeNibble_(uint8_t nibble) {
    for (int i = 0; i < 4; ++i) {
        digitalWrite(dataPins_[i], (nibble >> i) & 0x01U ? HIGH : LOW);
    }
    pulseEnable_();
}

void Lcd1602::send_(uint8_t value, bool isCommand) {
    digitalWrite(rsPin_, isCommand ? LOW : HIGH);
    writeNibble_((value >> 4U) & 0x0FU);
    writeNibble_(value & 0x0FU);
    // Every instruction needs >=37us to complete except clear/home, which need
    // >=1.52ms; there is no busy-flag read-back (R/W tied to GND), so we just
    // wait the worst case for the slow ones and move on for everything else.
    delayMicroseconds(isCommand && (value == 0x01U || value == 0x02U) ? 1600U : 40U);
}

}  // namespace ForestSensors
