#include "CivilTime.h"

namespace forest::time {
namespace {

// days since civil 1970-01-01 for the given proleptic-Gregorian civil date.
int64_t daysFromCivil(int64_t y, uint8_t m, uint8_t d) {
    y -= m <= 2;
    const int64_t era = (y >= 0 ? y : y - 399) / 400;
    const int64_t yoe = y - era * 400;                                    // [0, 399]
    const int64_t doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;    // [0, 365]
    const int64_t doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;             // [0, 146096]
    return era * 146097 + doe - 719468;
}

// inverse of daysFromCivil.
void civilFromDays(int64_t z, int64_t& y, uint8_t& m, uint8_t& d) {
    z += 719468;
    const int64_t era = (z >= 0 ? z : z - 146096) / 146097;
    const int64_t doe = z - era * 146097;                                          // [0, 146096]
    const int64_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;      // [0, 399]
    y = yoe + era * 400;
    const int64_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);                    // [0, 365]
    const int64_t mp = (5 * doy + 2) / 153;                                          // [0, 11]
    d = static_cast<uint8_t>(doy - (153 * mp + 2) / 5 + 1);                          // [1, 31]
    m = static_cast<uint8_t>(mp + (mp < 10 ? 3 : -9));                               // [1, 12]
    y += (m <= 2);
}

}  // namespace

CivilUtc epochToCivilUtc(int64_t epochSeconds) {
    int64_t days = epochSeconds / 86400;
    int64_t secOfDay = epochSeconds % 86400;
    if (secOfDay < 0) { secOfDay += 86400; days -= 1; }
    CivilUtc c{};
    civilFromDays(days, c.year, c.month, c.day);
    c.hour = static_cast<uint8_t>(secOfDay / 3600);
    c.minute = static_cast<uint8_t>((secOfDay % 3600) / 60);
    c.second = static_cast<uint8_t>(secOfDay % 60);
    return c;
}

int64_t civilUtcToEpoch(int64_t year, uint8_t month, uint8_t day, uint8_t hour, uint8_t minute, uint8_t second) {
    return daysFromCivil(year, month, day) * 86400 + hour * 3600 + minute * 60 + second;
}

}  // namespace forest::time
