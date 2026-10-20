#pragma once
// Separate hash-chain state for signed acoustic events (own NVS namespace/sequence, independent
// of PatrolChainState's): the backend tracks (node_id, sequence) uniqueness per event TABLE
// (AcousticEvent vs PatrolEvent are different tables with independent sequence spaces), so
// sharing one counter between patrol and acoustic events would make the acoustic chain look
// broken relative to its own prior record on the first mismatch. See PatrolChainState.h for why
// this chain is distinct from Phase 1's local tamper-evidence chain too.

#include <cstddef>
#include <cstdint>

namespace forest::crypto {

class AcousticChainState {
public:
    bool begin(const char* nvsNamespace = "forest_achain");
    uint32_t nextSequence() const { return sequence_; }
    const char* previousHashHex() const { return previousHash_; }
    void commit(const char* newRecordHashHex);

private:
    char previousHash_[65] = {0};
    uint32_t sequence_ = 1;
};

}  // namespace forest::crypto
