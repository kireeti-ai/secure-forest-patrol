#include "PatrolChainHash.h"

#include <cstdio>
#include <cstring>

#include "Sha256.h"

namespace forest::crypto {
namespace {

const char* orEmpty(const char* s) { return s ? s : ""; }

void toHex(const uint8_t* in, size_t len, char* out) {
    for (size_t i = 0; i < len; ++i) std::snprintf(out + i * 2, 3, "%02x", in[i]);
}

void sha256Hex(const char* data, size_t len, char outHex[65]) {
    uint8_t digest[forest::utils::kSha256DigestSize];
    forest::utils::sha256(reinterpret_cast<const uint8_t*>(data), len, digest);
    toHex(digest, sizeof(digest), outHex);
    outHex[64] = '\0';
}

}  // namespace

void patrolPayloadDigestHex(const char* checkpointId, const char* officerId, const char* rfidResult,
                            const char* fingerprintResult, char outHex[65]) {
    char buf[512];
    const int n = std::snprintf(buf, sizeof buf, "%s|%s|%s|%s", orEmpty(checkpointId), orEmpty(officerId),
                                orEmpty(rfidResult), orEmpty(fingerprintResult));
    sha256Hex(buf, static_cast<size_t>(n), outHex);
}

void computeRecordHashHex(const char* nodeId, uint32_t sequence, const char* eventCreatedAtIso,
                          const char* payloadDigestHex, const char* previousHashHex, char outHex[65]) {
    const char* prev = (previousHashHex && previousHashHex[0]) ? previousHashHex : "GENESIS";
    char buf[512];
    const int n = std::snprintf(buf, sizeof buf, "%s|%lu|%s|%s|%s", orEmpty(nodeId),
                                static_cast<unsigned long>(sequence), orEmpty(eventCreatedAtIso),
                                orEmpty(payloadDigestHex), prev);
    sha256Hex(buf, static_cast<size_t>(n), outHex);
}

}  // namespace forest::crypto
