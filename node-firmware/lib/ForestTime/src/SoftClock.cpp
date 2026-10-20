#include "SoftClock.h"

#include <cstdio>

#include <Arduino.h>
#include <Preferences.h>

#include "CivilTime.h"

namespace forest::time {
namespace {
constexpr const char* kKey = "sync_epoch";
}  // namespace

bool SoftClock::begin(const char* nvsNamespace) {
    Preferences prefs;
    if (!prefs.begin(nvsNamespace, false)) return false;
    const bool have = prefs.getBytesLength(kKey) == sizeof(uint32_t);
    uint32_t stored = 0;
    if (have) prefs.getBytes(kKey, &stored, sizeof(stored));
    prefs.end();
    if (have) {
        // Treat the persisted epoch as valid "as of this boot" (millis() resets to 0 every
        // boot, so there is no way to know how long the device was powered off for - the
        // clock effectively pauses across a power cycle and resumes counting from the last
        // known value, until the next gateway sync corrects it).
        syncEpoch_ = stored;
        syncMillis_ = millis();
        synced_ = true;
    }
    return true;
}

void SoftClock::onSync(uint32_t utcEpochSeconds) {
    syncEpoch_ = utcEpochSeconds;
    syncMillis_ = millis();
    synced_ = true;
    Preferences prefs;
    if (prefs.begin("forest_clk", false)) {
        prefs.putBytes(kKey, &syncEpoch_, sizeof(syncEpoch_));
        prefs.end();
    }
}

uint32_t SoftClock::secondsSinceSync() const {
    return (millis() - syncMillis_) / 1000U;   // unsigned subtraction: safe even across millis() wraparound
}

bool SoftClock::nowEpoch(uint32_t& outEpoch) const {
    if (!synced_) return false;
    outEpoch = syncEpoch_ + secondsSinceSync();
    return true;
}

bool SoftClock::nowIso8601Utc(char* out, size_t outLen) const {
    uint32_t epoch = 0;
    if (!nowEpoch(epoch)) return false;
    const CivilUtc c = epochToCivilUtc(static_cast<int64_t>(epoch));
    const int n = std::snprintf(out, outLen, "%04lld-%02u-%02uT%02u:%02u:%02u+00:00",
                                static_cast<long long>(c.year), c.month, c.day, c.hour, c.minute, c.second);
    return n > 0 && static_cast<size_t>(n) < outLen;
}

}  // namespace forest::time
