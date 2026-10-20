#pragma once
// Software UTC clock for a node with no RTC chip. There is no battery-backed timekeeping
// hardware here, so wall-clock time can only ever be an *estimate*: the last UTC second the
// gateway told us about, plus however much millis() has advanced since. Persisted in NVS so a
// reboot keeps the last known time (still drifting forward via millis() since boot) rather than
// resetting to "unknown" - though millis() itself resets to 0 every boot, so the stored sync
// point's millis() reference is only valid until the next reboot; see onSync()/begin().
//
// Accuracy: good right after a sync, drifts with the ESP32's crystal tolerance between syncs
// (typically tens of ppm - a few seconds per day). This is what docs/TAMPER_EVIDENCE_SECURITY_PLAN.md
// Phase 2 chose over a physical RTC chip: works with zero added hardware, self-corrects whenever
// a gateway round-trip succeeds, degrades gracefully (by drifting, not failing) when offline for
// a long stretch.

#include <cstddef>
#include <cstdint>

namespace forest::time {

class SoftClock {
public:
    bool begin(const char* nvsNamespace = "forest_clk");

    // Call whenever a trusted time source is available (e.g. the gateway's ACK payload carries
    // its current UTC epoch second). Persists the sync point to NVS.
    void onSync(uint32_t utcEpochSeconds);

    bool hasSynced() const { return synced_; }
    // Seconds since the last onSync() call (this boot only - see class comment).
    uint32_t secondsSinceSync() const;
    // Best current estimate of UTC unix time. Returns false if never synced (this boot or NVS).
    bool nowEpoch(uint32_t& outEpoch) const;
    // "YYYY-MM-DDTHH:MM:SS+00:00" - matches Python's datetime.isoformat(). Returns false if
    // never synced; `out` is left untouched in that case (caller should not sign/send a record
    // with no real timestamp available).
    bool nowIso8601Utc(char* out, size_t outLen) const;

private:
    uint32_t syncEpoch_ = 0;    // UTC epoch second at the moment of the last sync
    uint32_t syncMillis_ = 0;   // millis() at that same moment (this boot's millis(), see above)
    bool synced_ = false;
};

}  // namespace forest::time
