// Host tests for the local event store (record codec, recovery, sync state, corruption, capacity)
// and the portable ForestSensors helpers. An in-memory backend stands in for LittleFS; "restart" is simulated
// by building a new LocalEventStore on the same backend (the backend keeps the "flash" contents).
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>

#include "LocalEventStore.h"
#include "SensorMath.h"

using namespace forest::storage;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); ++failures; } } while (0)

class MemBackend : public StorageBackend {
public:
    std::map<std::string, std::vector<uint8_t>> files;
    bool begin() override { return true; }
    int64_t size(const char* n) override { auto it = files.find(n); return it == files.end() ? -1 : (int64_t)it->second.size(); }
    bool read(const char* n, size_t off, uint8_t* b, size_t len) override {
        auto it = files.find(n); if (it == files.end() || off + len > it->second.size()) return false;
        memcpy(b, it->second.data() + off, len); return true; }
    bool write(const char* n, size_t off, const uint8_t* b, size_t len) override {
        auto& f = files[n]; if (f.size() < off + len) f.resize(off + len); memcpy(f.data() + off, b, len); return true; }
    bool truncate(const char* n, size_t s) override { files[n].resize(s); return true; }
    bool remove(const char* n) override { files.erase(n); return true; }
};

static const uint8_t kRfid[7] = {'R', 1, 4, 0xCD, 0x4E, 0x32, 0x40};
static const uint8_t kAc[6] = {'A', 1, 2, 244, 99, 0};

int main() {
    // --- codec ---
    {
        EventRecord r; r.localId = 7; r.type = EventType::Acoustic; r.nodeId = 1; r.payloadLen = 6; r.bootCount = 3; r.uptimeMs = 123456;
        memcpy(r.payload, kAc, 6);
        uint8_t b[kRecordSize]; encodeRecord(r, b);
        EventRecord d; CHECK(decodeRecord(b, d) == DecodeResult::Ok, "round trip decodes");
        CHECK(d.localId == 7 && d.type == EventType::Acoustic && d.payloadLen == 6 && d.bootCount == 3 && d.uptimeMs == 123456 && !memcmp(d.payload, kAc, 6), "round trip fields");
        b[25] ^= 0x01; CHECK(decodeRecord(b, d) == DecodeResult::BadCrc, "1-bit flip caught by CRC");
        encodeRecord(r, b); b[0] = 0; CHECK(decodeRecord(b, d) == DecodeResult::BadMagic, "bad magic");
        char id[24]; formatEventId(r, id, sizeof id); CHECK(!strcmp(id, "N01-ACOUSTIC-000007"), "event id format");
    }
    // --- empty store, write, list ---
    MemBackend flash;
    {
        LocalEventStore s(flash, 16);
        CHECK(s.begin(), "begin on empty flash");
        CHECK(s.stats().records == 0 && s.stats().bootCount == 1, "empty store, boot 1");
        EventRecord r;
        CHECK(s.append(EventType::Rfid, 1, kRfid, 7, 1000, &r) && r.localId == 1 && r.status == SyncStatus::PendingSync, "append RFID -> PENDING_SYNC");
        CHECK(s.append(EventType::Acoustic, 1, kAc, 6, 2000, &r) && r.localId == 2, "append acoustic");
        CHECK(s.append(EventType::Test, 1, nullptr, 0, 3000, &r) && r.localId == 3, "append test event");
        CHECK(!s.append(EventType::Rfid, 1, kRfid, 25, 0), "payload > 24 rejected");
        CHECK(s.stats().records == 3 && s.stats().pending == 3, "3 pending");
        CHECK(flash.size("/events.log") == 3 * (int64_t)kRecordSize, "fixed 48-byte records on flash");
        CHECK(s.markSynced(1), "mark synced");
        CHECK(s.stats().pending == 2 && s.stats().synced == 1, "counts after sync");
        EventRecord p; CHECK(s.oldestPending(p) && p.localId == 2, "oldest pending skips synced");
        CHECK(s.markSynced(2) && s.oldestPending(p) == false, "TEST events are not retried");
        CHECK(s.oldestPending(p, true) && p.localId == 3, "...unless requested");
        CHECK(!s.markSynced(99), "unknown id");
        CHECK(s.markAttempt(3) && s.readAt(2, p) && p.attempts == 1, "attempt counter persisted");
    }
    // --- recovery after "reboot": data survives, boot counter increments, ids continue ---
    {
        LocalEventStore s(flash, 16);
        CHECK(s.begin(), "begin after restart");
        CHECK(s.stats().records == 3 && s.stats().synced == 2 && s.stats().pending == 1, "recovered 3 records with sync state");
        CHECK(s.stats().bootCount == 2, "boot counter persisted and incremented");
        EventRecord r; CHECK(s.append(EventType::Rfid, 1, kRfid, 7, 10, &r) && r.localId == 4 && r.bootCount == 2, "ids continue after restart");
    }
    // --- corrupted record + duplicate + torn tail ---
    {
        auto& log = flash.files["/events.log"];
        log[48 * 1 + 30] ^= 0xFF;                                     // corrupt record #2
        std::vector<uint8_t> dup(log.begin(), log.begin() + 48);      // duplicate of record #1 appended
        log.insert(log.end(), dup.begin(), dup.end());
        log.push_back(0xAB); log.push_back(0xCD);                     // half-written append
        LocalEventStore s(flash, 16);
        CHECK(s.begin(), "begin with damaged log");
        CHECK(s.stats().tornTailBytes == 2, "torn tail detected");
        CHECK(s.stats().corruptSkipped == 1, "corrupt record skipped");
        CHECK(s.stats().duplicatesSkipped == 1, "duplicate id skipped");
        CHECK(s.stats().records == 3, "3 valid records remain (1,3,4)");
        CHECK(flash.size("/events.log") == 3 * (int64_t)kRecordSize, "log rewritten clean");
        LocalEventStore again(flash, 16);
        again.begin();
        CHECK(again.stats().corruptSkipped == 0 && again.stats().records == 3, "clean on next restart");
    }
    // --- capacity: compaction reclaims SYNCED, overflow drops the oldest PENDING and counts it ---
    {
        MemBackend f2;
        LocalEventStore s(f2, 4);
        s.begin();
        for (int i = 0; i < 4; ++i) s.append(EventType::Rfid, 1, kRfid, 7, i);
        CHECK(s.stats().records == 4, "full");
        s.markSynced(1); s.markSynced(2);
        CHECK(s.append(EventType::Rfid, 1, kRfid, 7, 99), "append when full compacts SYNCED");
        CHECK(s.stats().records == 3 && s.stats().pending == 3 && s.stats().overflowDropped == 0, "synced reclaimed, nothing lost");
        s.append(EventType::Rfid, 1, kRfid, 7, 100);   // now 4 pending, full
        CHECK(s.append(EventType::Rfid, 1, kRfid, 7, 101), "append when full of PENDING overwrites the oldest");
        CHECK(s.stats().overflowDropped == 1 && s.stats().records == 4, "overflow counted");
        EventRecord p; s.oldestPending(p);
        CHECK(p.localId == 4, "oldest pending is now #4 (#3 dropped)");
        LocalEventStore r2(f2, 4); r2.begin();
        CHECK(r2.stats().overflowDropped == 1, "overflow counter persisted");
    }
    // --- sensor helpers ---
    {
        const uint8_t halt[2] = {0x50, 0x00};
        CHECK(ForestSensors::crcA(halt, 2) == 0xCD57, "CRC_A of HLTA = 57 CD (ISO 14443-3 known value)");
        CHECK(ForestSensors::bcdToBin(0x59) == 59 && ForestSensors::binToBcd(37) == 0x37, "BCD conversion");
        int16_t x[4] = {2050, 2048, 2046, 2048};
        float mean; const float rms = ForestSensors::blockRms(x, 4, &mean);
        CHECK(mean == 2048.0f && rms > 1.0f && rms < 2.0f, "block RMS removes the DC level");
    }
    printf(failures ? "\nLOCAL STORE TESTS FAIL (%d)\n" : "\nLOCAL STORE TESTS PASS\n", failures);
    return failures ? 1 : 0;
}
