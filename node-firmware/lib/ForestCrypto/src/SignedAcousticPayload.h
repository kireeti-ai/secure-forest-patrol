#pragma once
// Wire format for a signed acoustic event (Phase 2 extension, docs/TAMPER_EVIDENCE_SECURITY_PLAN.md).
// Distinct version byte (0x02, not 0x01) from the existing unsigned 'A' payload so the gateway
// can tell them apart unambiguously by (type, version) alone, same as it already does for the
// legacy fixed 6-byte v1 format.
//
//  off  size  field
//   0    1    0x41 ('A')
//   1    1    version (2) - signed, as opposed to the legacy unsigned v1 (still 6 bytes, unchanged)
//   2    4    sequence (uint32 LE)
//   6    4    event_created_at, UTC unix epoch second (uint32 LE)
//  10    1    class index: 1=chainsaw, 2=gunshot (background is never sent, same as today)
//  11    1    confidence byte (0-255): index into AcousticConfidenceTable.h's verified
//             Python-repr lookup table - NOT a linear confidence*255 value to be reformatted
//             downstream; the gateway must look up the same table entry, not reformat this byte.
//  12    1    checkpoint_id length (<= kMaxCheckpointIdLen)
//  13    C    checkpoint_id bytes
// 13+C    1    zone_id length (<= kMaxZoneIdLen; 0 if unset)
// 14+C    Z    zone_id bytes
// 14+C+Z 32    previous_hash (raw SHA-256; all-zero means GENESIS/first record)
// 46+C+Z 32    record_hash (raw SHA-256)
// 78+C+Z  1    signature length (DER ECDSA)
// 79+C+Z  M    signature bytes

#include <cstddef>
#include <cstdint>

namespace forest::crypto {

constexpr uint8_t kSignedAcousticPayloadType = 0x41;
constexpr uint8_t kSignedAcousticPayloadVersion = 2;
constexpr size_t kMaxZoneIdLen = 16;

size_t encodeSignedAcousticPayload(uint32_t sequence, uint32_t eventCreatedAtEpoch,
                                   uint8_t classIndex, uint8_t confidenceByte,
                                   const char* checkpointId, size_t checkpointIdLen,
                                   const char* zoneId, size_t zoneIdLen,
                                   const uint8_t previousHash[32], const uint8_t recordHash[32],
                                   const uint8_t* signatureDer, size_t signatureLen,
                                   uint8_t* out, size_t outCap);

}  // namespace forest::crypto
