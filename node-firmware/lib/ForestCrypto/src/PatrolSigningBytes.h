#pragma once
// Canonical patrol-event signing bytes, byte-for-byte matching
// backend/app/services/crypto.py::patrol_signing_bytes:
//
//   node_id | sequence | event_created_at(iso) | checkpoint_id |
//   officer_id | rfid_result | fingerprint_result | previous_hash | record_hash
//
// Any field passed as nullptr or "" renders as "" (Python's `x or ""`), except previous_hash,
// which renders as "GENESIS" when empty (Python's `previous_hash or GENESIS_HASH`) - the
// genesis-record convention already used by the backend's hash chain.
//
// event_created_at must already be formatted exactly as Python's datetime.isoformat() would
// render it server-side after parsing (e.g. "2026-01-15T10:30:00+00:00" - no "Z", no fractional
// seconds when there are none), since the backend reconstructs and re-signs-checks this same
// string from its own parsed datetime, not from whatever string the node originally sent.
// formatIso8601Utc() below produces exactly that form from a DS3231-resolution (1s) timestamp.

#include <cstddef>
#include <cstdint>

namespace forest::crypto {

// Writes "YYYY-MM-DDTHH:MM:SS+00:00" (26 chars + NUL) - matches Python's isoformat() for a
// timezone-aware UTC datetime with zero microseconds, which is all a DS3231 can provide.
void formatIso8601Utc(uint16_t year, uint8_t month, uint8_t day, uint8_t hour, uint8_t minute,
                       uint8_t second, char* out, size_t outLen);

// Returns the number of bytes written (excluding the NUL), or 0 if outLen was too small.
size_t buildPatrolSigningBytes(const char* nodeId, uint32_t sequence, const char* eventCreatedAtIso,
                               const char* checkpointId, const char* officerId, const char* rfidResult,
                               const char* fingerprintResult, const char* previousHash,
                               const char* recordHash, char* out, size_t outLen);

}  // namespace forest::crypto
