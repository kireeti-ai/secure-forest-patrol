#pragma once
// Fixed-size (48 byte) on-flash record of one Forest node event. Portable (host-tested).
//
//  off  size  field
//   0    1    magic 0xE7
//   1    1    format version (1)
//   2    1    event type      (1 RFID, 2 ACOUSTIC, 3 TEST)
//   3    1    sync status     (1 PENDING_SYNC, 2 SYNCED)
//   4    4    local id        (monotonic, little endian)
//   8    1    node id
//   9    1    payload length  (<= 24)
//  10    1    transmit attempts
//  11    1    reserved (0)
//  12    4    boot counter    (which power-up created the record)
//  16    4    uptime ms       (since that boot; the node has no wall clock without an RTC)
//  20   24    payload         (exactly the bytes handed to the LoRa packet: 'R'... or 'A'...)
//  44    2    reserved (0)
//  46    2    CRC-16/CCITT-FALSE over bytes 0..45 (forest::utils::Crc16, the same routine the LoRa protocol uses)

#include <cstddef>
#include <cstdint>

namespace forest::storage {

constexpr size_t kRecordSize = 48;
constexpr size_t kMaxPayload = 24;
constexpr uint8_t kRecordMagic = 0xE7;
constexpr uint8_t kRecordVersion = 1;

enum class EventType : uint8_t { Rfid = 1, Acoustic = 2, Test = 3 };
enum class SyncStatus : uint8_t { PendingSync = 1, Synced = 2 };

struct EventRecord {
    uint32_t localId = 0;
    EventType type = EventType::Test;
    SyncStatus status = SyncStatus::PendingSync;
    uint8_t nodeId = 0;
    uint8_t payloadLen = 0;
    uint8_t attempts = 0;
    uint32_t bootCount = 0;
    uint32_t uptimeMs = 0;
    uint8_t payload[kMaxPayload] = {0};
};

enum class DecodeResult { Ok, BadMagic, BadVersion, BadCrc, BadField };

void encodeRecord(const EventRecord& r, uint8_t out[kRecordSize]);
DecodeResult decodeRecord(const uint8_t in[kRecordSize], EventRecord& out);
// Human readable id, e.g. "N01-RFID-000012" or "TEST-012".
void formatEventId(const EventRecord& r, char* out, size_t outLen);
const char* typeName(EventType t);
const char* statusName(SyncStatus s);

}  // namespace forest::storage
