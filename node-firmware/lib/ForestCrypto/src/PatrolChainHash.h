#pragma once
// Reimplements backend/app/services/crypto.py's patrol_payload_digest() and
// compute_record_hash() in C++, so the node can compute the exact same hash-chain values the
// backend will independently verify. Each hex-string output is lowercase, 64 chars + NUL (65
// bytes), matching Python's hashlib.sha256(...).hexdigest().

#include <cstddef>
#include <cstdint>

namespace forest::crypto {

// "|".join([checkpoint_id or "", officer_id or "", rfid_result or "", fingerprint_result or ""])
// -> SHA-256 hex. Any null pointer renders as "" (Python's `x or ""`).
void patrolPayloadDigestHex(const char* checkpointId, const char* officerId, const char* rfidResult,
                            const char* fingerprintResult, char outHex[65]);

// "|".join([node_id, str(sequence), event_created_at_iso, payload_digest_hex,
// previous_hash_hex or "GENESIS"]) -> SHA-256 hex. previousHashHex may be nullptr/"" for the
// first record in the chain (Python's `previous_hash or GENESIS_HASH`).
void computeRecordHashHex(const char* nodeId, uint32_t sequence, const char* eventCreatedAtIso,
                          const char* payloadDigestHex, const char* previousHashHex, char outHex[65]);

// "|".join([classification, confidenceRepr, model_version or ""]) -> SHA-256 hex. Matches
// backend/app/services/crypto.py::acoustic_payload_digest. confidenceRepr must already be
// Python's exact repr(float(confidence)) string - see AcousticConfidenceTable.h for why that
// can't just be "%.2f"-formatted here.
void acousticPayloadDigestHex(const char* classification, const char* confidenceRepr,
                              const char* modelVersion, char outHex[65]);

}  // namespace forest::crypto
