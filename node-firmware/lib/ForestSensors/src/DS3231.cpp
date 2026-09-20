#include "DS3231.h"

#include <Arduino.h>
#include <Wire.h>

#include "SensorMath.h"

namespace ForestSensors {
namespace {
constexpr uint8_t kAddr = 0x68;
constexpr uint8_t kRegTime = 0x00, kRegStatus = 0x0F, kRegTemp = 0x11;
}  // namespace

bool DS3231::readRegs(uint8_t reg, uint8_t* out, uint8_t n) {
    Wire.beginTransmission(kAddr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(static_cast<int>(kAddr), static_cast<int>(n)) != n) return false;
    for (uint8_t i = 0; i < n; ++i) out[i] = static_cast<uint8_t>(Wire.read());
    return true;
}

bool DS3231::writeRegs(uint8_t reg, const uint8_t* data, uint8_t n) {
    Wire.beginTransmission(kAddr);
    Wire.write(reg);
    for (uint8_t i = 0; i < n; ++i) Wire.write(data[i]);
    return Wire.endTransmission(true) == 0;
}

bool DS3231::begin(int sdaPin, int sclPin) {
    if (!Wire.begin(sdaPin, sclPin)) return false;
    Wire.setTimeOut(100);   // never hang on a missing device
    Wire.beginTransmission(kAddr);
    ready_ = Wire.endTransmission(true) == 0;
    return ready_;
}

bool DS3231::readDateTime(DateTime& out) {
    uint8_t r[7];
    if (!ready_ || !readRegs(kRegTime, r, 7)) return false;
    out.second = bcdToBin(r[0] & 0x7F);
    out.minute = bcdToBin(r[1] & 0x7F);
    out.hour = bcdToBin(r[2] & 0x3F);            // 24-hour mode
    out.day = bcdToBin(r[4] & 0x3F);
    out.month = bcdToBin(r[5] & 0x1F);           // bit 7 = century
    out.year = static_cast<uint16_t>(2000 + bcdToBin(r[6]));
    return true;
}

bool DS3231::setDateTime(const DateTime& in) {
    if (!ready_) return false;
    uint8_t r[7] = {binToBcd(in.second), binToBcd(in.minute), binToBcd(in.hour), 1 /* weekday unused */,
                    binToBcd(in.day), binToBcd(in.month), binToBcd(static_cast<uint8_t>(in.year - 2000))};
    if (!writeRegs(kRegTime, r, 7)) return false;
    uint8_t st = 0;
    if (!readRegs(kRegStatus, &st, 1)) return false;
    st = static_cast<uint8_t>(st & ~0x80);       // clear OSF
    return writeRegs(kRegStatus, &st, 1);
}

bool DS3231::lostPower() {
    uint8_t st = 0;
    return ready_ && readRegs(kRegStatus, &st, 1) && (st & 0x80);
}

bool DS3231::readTemperatureCentiC(int16_t& centiC) {
    uint8_t r[2];
    if (!ready_ || !readRegs(kRegTemp, r, 2)) return false;
    centiC = static_cast<int16_t>(static_cast<int8_t>(r[0]) * 100 + (r[1] >> 6) * 25);
    return true;
}

uint32_t DS3231::unixTime(const DateTime& t) const {
    static const uint16_t kDaysBeforeMonth[12] = {0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};
    uint32_t days = 365UL * (t.year - 1970) + (t.year - 1969) / 4 + kDaysBeforeMonth[t.month - 1] + (t.day - 1);
    if (t.month > 2 && (t.year % 4) == 0) ++days;
    return ((days * 24UL + t.hour) * 60UL + t.minute) * 60UL + t.second;
}

}  // namespace ForestSensors
