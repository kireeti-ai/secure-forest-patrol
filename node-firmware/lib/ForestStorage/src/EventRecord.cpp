#include "EventRecord.h"

#include <cstdio>
#include <cstring>

#include "Crc16.h"

namespace forest::storage {
namespace {
void put32(uint8_t* p, uint32_t v) {
    p[0] = static_cast<uint8_t>(v);
    p[1] = static_cast<uint8_t>(v >> 8);
    p[2] = static_cast<uint8_t>(v >> 16);
    p[3] = static_cast<uint8_t>(v >> 24);
}
uint32_t get32(const uint8_t* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) | (static_cast<uint32_t>(p[2]) << 16) |
           (static_cast<uint32_t>(p[3]) << 24);
}
}  // namespace

void encodeRecord(const EventRecord& r, uint8_t out[kRecordSize]) {
    std::memset(out, 0, kRecordSize);
    out[0] = kRecordMagic;
    out[1] = kRecordVersion;
    out[2] = static_cast<uint8_t>(r.type);
    out[3] = static_cast<uint8_t>(r.status);
    put32(out + 4, r.localId);
    out[8] = r.nodeId;
    out[9] = r.payloadLen;
    out[10] = r.attempts;
    put32(out + 12, r.bootCount);
    put32(out + 16, r.uptimeMs);
    std::memcpy(out + 20, r.payload, kMaxPayload);
    const uint16_t crc = forest::utils::Crc16::computeCcitt(out, 46);
    out[46] = static_cast<uint8_t>(crc & 0xFF);
    out[47] = static_cast<uint8_t>(crc >> 8);
}

DecodeResult decodeRecord(const uint8_t in[kRecordSize], EventRecord& out) {
    if (in[0] != kRecordMagic) return DecodeResult::BadMagic;
    if (in[1] != kRecordVersion) return DecodeResult::BadVersion;
    const uint16_t crc = forest::utils::Crc16::computeCcitt(in, 46);
    if (in[46] != (crc & 0xFF) || in[47] != (crc >> 8)) return DecodeResult::BadCrc;
    if (in[2] < 1 || in[2] > 3 || in[3] < 1 || in[3] > 2 || in[9] > kMaxPayload) return DecodeResult::BadField;
    out.type = static_cast<EventType>(in[2]);
    out.status = static_cast<SyncStatus>(in[3]);
    out.localId = get32(in + 4);
    out.nodeId = in[8];
    out.payloadLen = in[9];
    out.attempts = in[10];
    out.bootCount = get32(in + 12);
    out.uptimeMs = get32(in + 16);
    std::memcpy(out.payload, in + 20, kMaxPayload);
    return DecodeResult::Ok;
}

const char* typeName(EventType t) {
    switch (t) {
        case EventType::Rfid: return "RFID";
        case EventType::Acoustic: return "ACOUSTIC";
        case EventType::Test: return "TEST";
    }
    return "?";
}

const char* statusName(SyncStatus s) { return s == SyncStatus::Synced ? "SYNCED" : "PENDING_SYNC"; }

void formatEventId(const EventRecord& r, char* out, size_t outLen) {
    if (r.type == EventType::Test) std::snprintf(out, outLen, "TEST-%03u", static_cast<unsigned>(r.localId));
    else std::snprintf(out, outLen, "N%02X-%s-%06u", r.nodeId, typeName(r.type), static_cast<unsigned>(r.localId));
}

}  // namespace forest::storage
