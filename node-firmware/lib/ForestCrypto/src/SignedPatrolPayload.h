#pragma once
// Wire format for a signed patrol event (Phase 2, docs/TAMPER_EVIDENCE_SECURITY_PLAN.md).
// Larger than the legacy 'R'/'V' payloads because it carries a full DER signature and both
// hash-chain links; see Constants.h::kMaxPayloadSize (bumped to fit this).
//
//  off  size  field
//   0    1    0x50 ('P')
//   1    1    version (1)
//   2    4    sequence (uint32 LE) - the (node_id, sequence) key the backend de-dupes on
//   6    4    event_created_at, UTC unix epoch second (uint32 LE) - see ForestTime/SoftClock
//  10    1    rfid_result code (1=VALID, 2=INVALID)
//  11    1    fingerprint_result code (1=MATCH, 2=NO_MATCH)
//  12    1    checkpoint_id length (<= kMaxCheckpointIdLen)
//  13    C    checkpoint_id bytes (ASCII) - transmitted, not just locally configured: the
//             signature covers whatever value the gateway forwards, so it must be exactly what
//             the node signed, not a value the gateway guesses or looks up separately.
// 13+C    1    officer UID length (<= kMaxOfficerUidLen)
// 14+C    N    officer UID bytes
// 14+C+N 32    previous_hash (raw SHA-256; all-zero means GENESIS/first record)
// 46+C+N 32    record_hash (raw SHA-256)
// 78+C+N  1    signature length (DER ECDSA, <= kMaxSignatureBytes)
// 79+C+N  M    signature bytes
//
// The gateway (a separate firmware/codebase) decodes this directly - there is no shared library
// between the two repos for it, so this layout is the actual contract; changing it means
// updating gateway/src/Gateway/GatewayService.cpp's decoder to match, in lockstep.

#include <cstddef>
#include <cstdint>

namespace forest::crypto {

constexpr uint8_t kSignedPatrolPayloadType = 0x50;
constexpr uint8_t kSignedPatrolPayloadVersion = 1;
constexpr size_t kMaxCheckpointIdLen = 16;
constexpr size_t kMaxOfficerUidLen = 10;
constexpr size_t kPatrolHashBytes = 32;

// Returns the encoded length, or 0 if it wouldn't fit in outCap (caller's buffer too small, or
// checkpointIdLen/officerUidLen/signatureLen exceed their limits).
size_t encodeSignedPatrolPayload(uint32_t sequence, uint32_t eventCreatedAtEpoch,
                                 uint8_t rfidResultCode, uint8_t fingerprintResultCode,
                                 const char* checkpointId, size_t checkpointIdLen,
                                 const uint8_t* officerUid, size_t officerUidLen,
                                 const uint8_t previousHash[kPatrolHashBytes],
                                 const uint8_t recordHash[kPatrolHashBytes],
                                 const uint8_t* signatureDer, size_t signatureLen,
                                 uint8_t* out, size_t outCap);

}  // namespace forest::crypto
