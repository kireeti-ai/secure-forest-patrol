#pragma once
// Persists the per-node (sequence, previous_hash) state the signed-patrol-event hash chain
// needs across reboots, in NVS. Mirrors how LocalEventStore persists nextId_/lastChainHash_,
// but this chain is the one the BACKEND verifies (PatrolEvent.previous_hash/record_hash via
// backend/app/services/forest_chain.py), not the local tamper-evidence chain from Phase 1 -
// two different chains, deliberately: Phase 1 protects the flash log before it's ever sent;
// this one is what an outside verifier (backend) checks once it IS sent.

#include <cstddef>
#include <cstdint>

namespace forest::crypto {

class PatrolChainState {
public:
    bool begin(const char* nvsNamespace = "forest_pchain");

    // Sequence number to use for the NEXT signed patrol event, and the previous record's hash
    // hex string (empty "" for the very first event - the backend's GENESIS convention).
    // Call this, build+sign the record with these values, THEN call commit() once the record is
    // built (not only once it's confirmed sent - consistent with how LocalEventStore persists
    // nextId_ before transmission, so a crash mid-send skips a sequence number rather than
    // reusing one, which would look like a replay).
    uint32_t nextSequence() const { return sequence_; }
    const char* previousHashHex() const { return previousHash_; }

    // Persists newRecordHashHex as the chain's new previous_hash and advances the sequence.
    void commit(const char* newRecordHashHex);

private:
    char previousHash_[65] = {0};   // "" until the first commit()
    uint32_t sequence_ = 1;
};

}  // namespace forest::crypto
