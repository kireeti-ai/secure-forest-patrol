#include "SignedAcousticPayload.h"

#include <cstring>

#include "SignedPatrolPayload.h"  // kMaxCheckpointIdLen (shared cap, same semantics)

namespace forest::crypto {
namespace {
void put32(uint8_t* p, uint32_t v) {
    p[0] = static_cast<uint8_t>(v); p[1] = static_cast<uint8_t>(v >> 8);
    p[2] = static_cast<uint8_t>(v >> 16); p[3] = static_cast<uint8_t>(v >> 24);
}
}  // namespace

size_t encodeSignedAcousticPayload(uint32_t sequence, uint32_t eventCreatedAtEpoch,
                                   uint8_t classIndex, uint8_t confidenceByte,
                                   const char* checkpointId, size_t checkpointIdLen,
                                   const char* zoneId, size_t zoneIdLen,
                                   const uint8_t previousHash[32], const uint8_t recordHash[32],
                                   const uint8_t* signatureDer, size_t signatureLen,
                                   uint8_t* out, size_t outCap) {
    if (checkpointIdLen > kMaxCheckpointIdLen || zoneIdLen > kMaxZoneIdLen || signatureLen > 255) return 0;
    // fixed bytes: type(1) version(1) sequence(4) epoch(4) classIndex(1) confidence(1)
    // checkpointIdLen(1) zoneIdLen(1) sigLen(1) = 15, plus 2*32-byte hashes, plus the variable parts.
    const size_t total = 15 + checkpointIdLen + zoneIdLen + 64 + signatureLen;
    if (total > outCap) return 0;

    size_t off = 0;
    out[off++] = kSignedAcousticPayloadType;
    out[off++] = kSignedAcousticPayloadVersion;
    put32(out + off, sequence); off += 4;
    put32(out + off, eventCreatedAtEpoch); off += 4;
    out[off++] = classIndex;
    out[off++] = confidenceByte;
    out[off++] = static_cast<uint8_t>(checkpointIdLen);
    if (checkpointIdLen) { std::memcpy(out + off, checkpointId, checkpointIdLen); off += checkpointIdLen; }
    out[off++] = static_cast<uint8_t>(zoneIdLen);
    if (zoneIdLen) { std::memcpy(out + off, zoneId, zoneIdLen); off += zoneIdLen; }
    std::memcpy(out + off, previousHash, 32); off += 32;
    std::memcpy(out + off, recordHash, 32); off += 32;
    out[off++] = static_cast<uint8_t>(signatureLen);
    if (signatureLen) { std::memcpy(out + off, signatureDer, signatureLen); off += signatureLen; }
    return off;
}

}  // namespace forest::crypto
