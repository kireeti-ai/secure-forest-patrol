#include "SignedPatrolPayload.h"

#include <cstring>

namespace forest::crypto {
namespace {
void put32(uint8_t* p, uint32_t v) {
    p[0] = static_cast<uint8_t>(v); p[1] = static_cast<uint8_t>(v >> 8);
    p[2] = static_cast<uint8_t>(v >> 16); p[3] = static_cast<uint8_t>(v >> 24);
}
}  // namespace

size_t encodeSignedPatrolPayload(uint32_t sequence, uint32_t eventCreatedAtEpoch,
                                 uint8_t rfidResultCode, uint8_t fingerprintResultCode,
                                 const char* checkpointId, size_t checkpointIdLen,
                                 const uint8_t* officerUid, size_t officerUidLen,
                                 const uint8_t previousHash[kPatrolHashBytes],
                                 const uint8_t recordHash[kPatrolHashBytes],
                                 const uint8_t* signatureDer, size_t signatureLen,
                                 uint8_t* out, size_t outCap) {
    if (checkpointIdLen > kMaxCheckpointIdLen || officerUidLen > kMaxOfficerUidLen || signatureLen > 255) return 0;
    // fixed bytes: type(1) version(1) sequence(4) epoch(4) rfidResult(1) fingerprintResult(1)
    // checkpointIdLen(1) officerUidLen(1) = 15, plus the two 32-byte hashes and the variable parts.
    const size_t total = 15 + checkpointIdLen + officerUidLen + kPatrolHashBytes * 2 + signatureLen;
    if (total > outCap) return 0;

    size_t off = 0;
    out[off++] = kSignedPatrolPayloadType;
    out[off++] = kSignedPatrolPayloadVersion;
    put32(out + off, sequence); off += 4;
    put32(out + off, eventCreatedAtEpoch); off += 4;
    out[off++] = rfidResultCode;
    out[off++] = fingerprintResultCode;
    out[off++] = static_cast<uint8_t>(checkpointIdLen);
    if (checkpointIdLen) { std::memcpy(out + off, checkpointId, checkpointIdLen); off += checkpointIdLen; }
    out[off++] = static_cast<uint8_t>(officerUidLen);
    if (officerUidLen) { std::memcpy(out + off, officerUid, officerUidLen); off += officerUidLen; }
    std::memcpy(out + off, previousHash, kPatrolHashBytes); off += kPatrolHashBytes;
    std::memcpy(out + off, recordHash, kPatrolHashBytes); off += kPatrolHashBytes;
    out[off++] = static_cast<uint8_t>(signatureLen);
    if (signatureLen) { std::memcpy(out + off, signatureDer, signatureLen); off += signatureLen; }
    return off;
}

}  // namespace forest::crypto
