#include "PatrolChainState.h"

#include <cstring>

#include <Preferences.h>

namespace forest::crypto {
namespace {
constexpr const char* kNs = "forest_pchain";
constexpr const char* kSeqKey = "seq";
constexpr const char* kHashKey = "prev_hash";
}  // namespace

bool PatrolChainState::begin(const char* nvsNamespace) {
    const char* ns = nvsNamespace ? nvsNamespace : kNs;
    Preferences prefs;
    if (!prefs.begin(ns, false)) return false;
    sequence_ = prefs.getULong(kSeqKey, 1);
    const size_t len = prefs.getBytesLength(kHashKey);
    if (len > 0 && len < sizeof(previousHash_)) {
        prefs.getBytes(kHashKey, previousHash_, len);
        previousHash_[len] = '\0';
    } else {
        previousHash_[0] = '\0';
    }
    prefs.end();
    return true;
}

void PatrolChainState::commit(const char* newRecordHashHex) {
    if (newRecordHashHex) {
        std::strncpy(previousHash_, newRecordHashHex, sizeof(previousHash_) - 1);
        previousHash_[sizeof(previousHash_) - 1] = '\0';
    }
    ++sequence_;
    Preferences prefs;
    if (prefs.begin(kNs, false)) {
        prefs.putULong(kSeqKey, sequence_);
        prefs.putBytes(kHashKey, previousHash_, std::strlen(previousHash_));
        prefs.end();
    }
}

}  // namespace forest::crypto
