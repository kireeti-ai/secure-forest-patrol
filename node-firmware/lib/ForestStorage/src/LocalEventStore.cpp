#include "LocalEventStore.h"

#include <cstring>

#include "Crc16.h"

namespace forest::storage {
namespace {
constexpr uint16_t kMetaMagic = 0xB007;
constexpr size_t kMetaSize = 12;   // magic(2) boot(4) overflow(4) crc(2)

void put32(uint8_t* p, uint32_t v) {
    p[0] = static_cast<uint8_t>(v); p[1] = static_cast<uint8_t>(v >> 8);
    p[2] = static_cast<uint8_t>(v >> 16); p[3] = static_cast<uint8_t>(v >> 24);
}
uint32_t get32(const uint8_t* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) | (static_cast<uint32_t>(p[2]) << 16) |
           (static_cast<uint32_t>(p[3]) << 24);
}
}  // namespace

bool LocalEventStore::loadMeta() {
    uint8_t m[kMetaSize];
    stats_.bootCount = 0;
    stats_.overflowDropped = 0;
    if (be_.size(kMetaFile) != static_cast<int64_t>(kMetaSize) || !be_.read(kMetaFile, 0, m, kMetaSize)) return false;
    const uint16_t crc = forest::utils::Crc16::computeCcitt(m, 10);
    if ((m[0] | (m[1] << 8)) != kMetaMagic || m[10] != (crc & 0xFF) || m[11] != (crc >> 8)) return false;
    stats_.bootCount = get32(m + 2);
    stats_.overflowDropped = get32(m + 6);
    return true;
}

bool LocalEventStore::saveMeta() {
    uint8_t m[kMetaSize] = {0};
    m[0] = kMetaMagic & 0xFF;
    m[1] = kMetaMagic >> 8;
    put32(m + 2, stats_.bootCount);
    put32(m + 6, stats_.overflowDropped);
    const uint16_t crc = forest::utils::Crc16::computeCcitt(m, 10);
    m[10] = static_cast<uint8_t>(crc & 0xFF);
    m[11] = static_cast<uint8_t>(crc >> 8);
    return be_.write(kMetaFile, 0, m, kMetaSize);
}

size_t LocalEventStore::slotCount() {
    const int64_t sz = be_.size(kLogFile);
    return sz <= 0 ? 0 : static_cast<size_t>(sz) / kRecordSize;
}

// Walks the log once: fills record/pending/synced counts and nextId_, returns corrupt + duplicate counts.
bool LocalEventStore::scan(bool) {
    stats_.records = stats_.pending = stats_.synced = 0;
    uint32_t lastId = 0, corrupt = 0, dup = 0;
    const size_t n = slotCount();
    uint8_t buf[kRecordSize];
    for (size_t i = 0; i < n; ++i) {
        EventRecord r;
        if (!be_.read(kLogFile, i * kRecordSize, buf, kRecordSize) || decodeRecord(buf, r) != DecodeResult::Ok) {
            ++corrupt;
            continue;
        }
        if (r.localId <= lastId) {   // ids only ever increase: anything else is a leftover duplicate
            ++dup;
            continue;
        }
        lastId = r.localId;
        ++stats_.records;
        (r.status == SyncStatus::Synced ? stats_.synced : stats_.pending)++;
    }
    nextId_ = lastId + 1;
    stats_.corruptSkipped = corrupt;
    stats_.duplicatesSkipped = dup;
    return corrupt != 0 || dup != 0;
}

bool LocalEventStore::begin() {
    ready_ = false;
    if (!be_.begin()) return false;
    loadMeta();
    ++stats_.bootCount;
    saveMeta();
    stats_.tornTailBytes = 0;
    const int64_t sz = be_.size(kLogFile);
    if (sz > 0 && static_cast<size_t>(sz) % kRecordSize != 0) {   // a power loss cut an append short
        stats_.tornTailBytes = static_cast<uint32_t>(static_cast<size_t>(sz) % kRecordSize);
        be_.truncate(kLogFile, static_cast<size_t>(sz) - stats_.tornTailBytes);
    }
    if (scan(true)) {
        const uint32_t corrupt = stats_.corruptSkipped, dup = stats_.duplicatesSkipped;
        // Rewrite without the bad records but keep the SYNCED history.
        uint8_t buf[kRecordSize];
        size_t j = 0;
        uint32_t lastId = 0;
        const size_t n = slotCount();
        for (size_t i = 0; i < n; ++i) {
            EventRecord r;
            if (!be_.read(kLogFile, i * kRecordSize, buf, kRecordSize) || decodeRecord(buf, r) != DecodeResult::Ok || r.localId <= lastId) continue;
            lastId = r.localId;
            if (j != i) be_.write(kLogFile, j * kRecordSize, buf, kRecordSize);
            ++j;
        }
        be_.truncate(kLogFile, j * kRecordSize);
        scan(true);
        stats_.corruptSkipped = corrupt;
        stats_.duplicatesSkipped = dup;
    }
    ready_ = true;
    return true;
}

bool LocalEventStore::compact() {
    if (!ready_) return false;
    uint8_t buf[kRecordSize];
    size_t j = 0;
    uint32_t lastId = 0;
    const size_t n = slotCount();
    for (size_t i = 0; i < n; ++i) {   // in place: the write index never passes the read index
        EventRecord r;
        if (!be_.read(kLogFile, i * kRecordSize, buf, kRecordSize) || decodeRecord(buf, r) != DecodeResult::Ok) continue;
        if (r.localId <= lastId || r.status == SyncStatus::Synced) continue;
        lastId = r.localId;
        if (j != i && !be_.write(kLogFile, j * kRecordSize, buf, kRecordSize)) return false;
        ++j;
    }
    if (!be_.truncate(kLogFile, j * kRecordSize)) return false;
    const uint32_t c = stats_.corruptSkipped, d = stats_.duplicatesSkipped;
    scan(true);
    stats_.corruptSkipped = c;
    stats_.duplicatesSkipped = d;
    return true;
}

bool LocalEventStore::dropOldest() {
    uint8_t buf[kRecordSize];
    size_t j = 0;
    bool skipped = false;
    const size_t n = slotCount();
    for (size_t i = 0; i < n; ++i) {
        EventRecord r;
        if (!be_.read(kLogFile, i * kRecordSize, buf, kRecordSize) || decodeRecord(buf, r) != DecodeResult::Ok) continue;
        if (!skipped) { skipped = true; continue; }
        if (j != i && !be_.write(kLogFile, j * kRecordSize, buf, kRecordSize)) return false;
        ++j;
    }
    if (!be_.truncate(kLogFile, j * kRecordSize)) return false;
    ++stats_.overflowDropped;
    saveMeta();
    scan(true);
    return true;
}

bool LocalEventStore::append(EventType type, uint8_t nodeId, const uint8_t* payload, size_t len, uint32_t uptimeMs, EventRecord* out) {
    if (!ready_ || len > kMaxPayload || (len > 0 && payload == nullptr)) return false;
    if (slotCount() >= maxRecords_) {
        compact();                                       // 1) reclaim SYNCED records
        if (slotCount() >= maxRecords_ && !dropOldest()) return false;   // 2) last resort: overwrite the oldest, counted
    }
    EventRecord r;
    r.localId = nextId_;
    r.type = type;
    r.status = SyncStatus::PendingSync;
    r.nodeId = nodeId;
    r.payloadLen = static_cast<uint8_t>(len);
    r.bootCount = stats_.bootCount;
    r.uptimeMs = uptimeMs;
    if (len) std::memcpy(r.payload, payload, len);
    uint8_t buf[kRecordSize];
    encodeRecord(r, buf);
    if (!be_.write(kLogFile, slotCount() * kRecordSize, buf, kRecordSize)) return false;
    ++nextId_;
    ++stats_.records;
    ++stats_.pending;
    if (out) *out = r;
    return true;
}

bool LocalEventStore::readAt(size_t index, EventRecord& out) {
    uint8_t buf[kRecordSize];
    return ready_ && index < slotCount() && be_.read(kLogFile, index * kRecordSize, buf, kRecordSize) &&
           decodeRecord(buf, out) == DecodeResult::Ok;
}

bool LocalEventStore::oldestPending(EventRecord& out, bool includeTest) {
    const size_t n = slotCount();
    for (size_t i = 0; i < n; ++i) {
        EventRecord r;
        if (!readAt(i, r) || r.status != SyncStatus::PendingSync) continue;
        if (r.type == EventType::Test && !includeTest) continue;
        out = r;
        return true;
    }
    return false;
}

bool LocalEventStore::writeSlot(size_t index, const EventRecord& r) {
    uint8_t buf[kRecordSize];
    encodeRecord(r, buf);
    return be_.write(kLogFile, index * kRecordSize, buf, kRecordSize);
}

bool LocalEventStore::findSlot(uint32_t localId, size_t& index, EventRecord& rec) {
    const size_t n = slotCount();
    for (size_t i = 0; i < n; ++i) {
        if (readAt(i, rec) && rec.localId == localId) { index = i; return true; }
    }
    return false;
}

bool LocalEventStore::markSynced(uint32_t localId) {
    size_t idx;
    EventRecord r;
    if (!ready_ || !findSlot(localId, idx, r)) return false;
    if (r.status == SyncStatus::Synced) return true;
    r.status = SyncStatus::Synced;
    if (!writeSlot(idx, r)) return false;
    --stats_.pending;
    ++stats_.synced;
    return true;
}

bool LocalEventStore::markAttempt(uint32_t localId) {
    size_t idx;
    EventRecord r;
    if (!ready_ || !findSlot(localId, idx, r)) return false;
    if (r.attempts < 255) ++r.attempts;
    return writeSlot(idx, r);
}

bool LocalEventStore::clear() {
    if (!ready_) return false;
    be_.remove(kLogFile);
    scan(true);
    return true;
}

}  // namespace forest::storage
