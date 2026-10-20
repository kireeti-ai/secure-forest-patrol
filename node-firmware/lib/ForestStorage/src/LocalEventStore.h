#pragma once
// Local (on-node) event store: an append-only log of fixed-size CRC-protected records plus a tiny metadata
// file. Nothing but the record being handled is held in RAM. Events are written BEFORE they are sent, marked
// SYNCED once the radio reports the transmission complete, and survive reset and power loss.
//
//   sensor event -> append() [PENDING_SYNC] -> LoRa transmit -> markSynced() [SYNCED]
//                                 |
//                                 +-> still PENDING after a failed/interrupted send -> oldestPending() retries it

#include <cstddef>
#include <cstdint>

#include "EventRecord.h"
#include "StorageBackend.h"

namespace forest::storage {

struct StoreStats {
    uint32_t records = 0;          // valid records in the log
    uint32_t pending = 0;
    uint32_t synced = 0;
    uint32_t corruptSkipped = 0;   // failed magic/CRC/field checks at recovery
    uint32_t duplicatesSkipped = 0;
    uint32_t tornTailBytes = 0;    // partial record left by a power loss during an append
    uint32_t overflowDropped = 0;  // pending events overwritten because the log was full (lifetime, persisted)
    uint32_t bootCount = 0;
};

// Result of walking the currently-stored log and recomputing each record's chain hash.
// See LocalEventStore::verifyChain() for what this can and cannot detect.
struct ChainVerifyResult {
    bool ok = true;
    size_t recordsChecked = 0;
    size_t breakAtSlot = static_cast<size_t>(-1);   // first slot whose stored hash didn't match, if !ok
    uint32_t breakAtLocalId = 0;
};

class LocalEventStore {
public:
    static constexpr const char* kLogFile = "/events.log";
    static constexpr const char* kMetaFile = "/meta.bin";

    explicit LocalEventStore(StorageBackend& backend, size_t maxRecords = 512) : be_(backend), maxRecords_(maxRecords) {}

    // Mount the backend, recover the log (drops torn tails / corrupt / duplicate records), bump the boot counter.
    bool begin();

    // Persist a new event as PENDING_SYNC. `out` (optional) receives the stored record.
    bool append(EventType type, uint8_t nodeId, const uint8_t* payload, size_t len, uint32_t uptimeMs, EventRecord* out = nullptr);

    bool readAt(size_t index, EventRecord& out);                 // index = record slot, false if unreadable/corrupt
    // Oldest PENDING_SYNC record; TEST events are skipped unless includeTest.
    bool oldestPending(EventRecord& out, bool includeTest = false);
    bool markSynced(uint32_t localId);
    bool markAttempt(uint32_t localId);                           // ++attempts (saturating)
    bool clear();                                                 // wipe the log (test / maintenance)
    bool compact();                                               // drop SYNCED / corrupt / duplicate records

    size_t slotCount();                                           // raw slots in the file
    const StoreStats& stats() const { return stats_; }
    size_t capacity() const { return maxRecords_; }

    // Recomputes each currently-stored record's chain hash from the previous one and compares
    // against what's on flash. Detects reordering, deletion of a record from the middle, or a
    // forged record inserted by someone with physical flash access (the Phase 1 tamper-evidence
    // primitive from docs/TAMPER_EVIDENCE_SECURITY_PLAN.md).
    // Known limitations (by design, not a bug):
    //  - Does not detect truncation of the newest record(s) - nothing comes after them to break.
    //    Closing this gap needs an external anchor (e.g. the gateway/backend remembering the
    //    last hash it accepted), which is Phase 2/3 territory, not on-device.
    //  - This call verifies the log as currently stored. compact()/dropOldest() legitimately
    //    remove old records and will make the *first* remaining record's declared previous-hash
    //    unverifiable against history that's gone on purpose; that first record is treated as
    //    the trusted root of what's currently on flash, not a break. Anything after it must
    //    still chain correctly.
    ChainVerifyResult verifyChain();

private:
    bool scan(bool rebuildStats);
    bool writeSlot(size_t index, const EventRecord& r);
    bool findSlot(uint32_t localId, size_t& index, EventRecord& rec);
    bool loadMeta();
    bool saveMeta();
    bool dropOldest();

    StorageBackend& be_;
    size_t maxRecords_;
    StoreStats stats_;
    uint32_t nextId_ = 1;
    uint8_t lastChainHash_[kChainHashSize] = {0};   // chain hash of the last record written/recovered
    bool ready_ = false;
};

}  // namespace forest::storage
