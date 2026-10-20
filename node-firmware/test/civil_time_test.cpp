// Host test: epochToCivilUtc/civilUtcToEpoch checked against real Python output
// (datetime.fromtimestamp(epoch, tz=timezone.utc)), not hand-derived.
#include <cstdio>

#include "CivilTime.h"

using namespace forest::time;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); ++failures; } } while (0)

static bool eq(const CivilUtc& c, int64_t y, int mo, int d, int h, int mi, int s) {
    return c.year == y && c.month == mo && c.day == d && c.hour == h && c.minute == mi && c.second == s;
}

int main() {
    // captured via: python3 -c "from datetime import datetime, timezone; ..." (see git history / PR)
    CHECK(eq(epochToCivilUtc(0), 1970, 1, 1, 0, 0, 0), "epoch 0");
    CHECK(eq(epochToCivilUtc(1), 1970, 1, 1, 0, 0, 1), "epoch 1");
    CHECK(eq(epochToCivilUtc(86399), 1970, 1, 1, 23, 59, 59), "epoch 86399 (end of day 1)");
    CHECK(eq(epochToCivilUtc(86400), 1970, 1, 2, 0, 0, 0), "epoch 86400 (start of day 2)");
    CHECK(eq(epochToCivilUtc(1700000000), 2023, 11, 14, 22, 13, 20), "epoch 1700000000");
    CHECK(eq(epochToCivilUtc(1577836800), 2020, 1, 1, 0, 0, 0), "epoch 1577836800 (2020-01-01)");
    CHECK(eq(epochToCivilUtc(951782400), 2000, 2, 29, 0, 0, 0), "epoch 951782400 (leap day)");
    CHECK(eq(epochToCivilUtc(-1), 1969, 12, 31, 23, 59, 59), "epoch -1 (before Unix epoch)");
    CHECK(eq(epochToCivilUtc(1735689599), 2024, 12, 31, 23, 59, 59), "epoch 1735689599 (end of leap year)");

    // round-trip: civilUtcToEpoch must invert epochToCivilUtc for every case above
    const int64_t cases[] = {0, 1, 86399, 86400, 1700000000, 1577836800, 951782400, -1, 1735689599};
    for (int64_t e : cases) {
        const CivilUtc c = epochToCivilUtc(e);
        CHECK(civilUtcToEpoch(c.year, c.month, c.day, c.hour, c.minute, c.second) == e, "round trip");
    }

    printf(failures ? "\nCIVIL TIME TESTS FAIL (%d)\n" : "\nCIVIL TIME TESTS PASS\n", failures);
    return failures ? 1 : 0;
}
