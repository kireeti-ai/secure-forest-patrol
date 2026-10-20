#pragma once
// Pure, portable (host-testable) Unix-epoch <-> UTC civil date/time conversion. No calendar
// library, no timezone database - UTC only, which is all a Unix epoch second ever needs.
// Algorithm: Howard Hinnant's "chrono-Compatible Low-Level Date Algorithms"
// (http://howardhinnant.github.io/date_algorithms.html), public domain, proleptic Gregorian,
// correct for the full int64 range (way beyond any date this project will ever see).

#include <cstdint>

namespace forest::time {

struct CivilUtc {
    int64_t year;
    uint8_t month;   // 1-12
    uint8_t day;     // 1-31
    uint8_t hour;    // 0-23
    uint8_t minute;  // 0-59
    uint8_t second;  // 0-59
};

CivilUtc epochToCivilUtc(int64_t epochSeconds);
int64_t civilUtcToEpoch(int64_t year, uint8_t month, uint8_t day, uint8_t hour, uint8_t minute, uint8_t second);

}  // namespace forest::time
