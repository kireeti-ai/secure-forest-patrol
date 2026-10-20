#include <cstdio>
#include <cstring>

#include "SignedPatrolPayload.h"

using namespace forest::crypto;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); ++failures; } } while (0)

int main() {
    uint8_t prevHash[32], recHash[32];
    for (int i = 0; i < 32; ++i) { prevHash[i] = static_cast<uint8_t>(i); recHash[i] = static_cast<uint8_t>(0xA0 + i); }
    const uint8_t uid[6] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF};
    const uint8_t sig[8] = {0x30, 0x06, 0x02, 0x01, 0x01, 0x02, 0x01, 0x02};  // fake DER-ish bytes for layout testing
    const char* cp = "CP1";

    uint8_t buf[256];
    const size_t n = encodeSignedPatrolPayload(7, 1700000000U, 1, 1, cp, 3, uid, 6, prevHash, recHash, sig, 8, buf, sizeof buf);
    CHECK(n == 15 + 3 + 6 + 32 + 32 + 8, "encoded length matches the documented layout");

    CHECK(buf[0] == kSignedPatrolPayloadType, "type byte");
    CHECK(buf[1] == kSignedPatrolPayloadVersion, "version byte");
    CHECK(buf[2] == 7 && buf[3] == 0 && buf[4] == 0 && buf[5] == 0, "sequence LE");
    // 1700000000 = 0x6553F100
    CHECK(buf[6] == 0x00 && buf[7] == 0xF1 && buf[8] == 0x53 && buf[9] == 0x65, "epoch LE");
    CHECK(buf[10] == 1 && buf[11] == 1, "rfid/fingerprint result codes");
    CHECK(buf[12] == 3, "checkpoint_id length byte");
    CHECK(!memcmp(buf + 13, "CP1", 3), "checkpoint_id bytes");
    CHECK(buf[16] == 6, "officer UID length byte");
    CHECK(!memcmp(buf + 17, uid, 6), "officer UID bytes");
    CHECK(!memcmp(buf + 23, prevHash, 32), "previous hash bytes");
    CHECK(!memcmp(buf + 55, recHash, 32), "record hash bytes");
    CHECK(buf[87] == 8, "signature length byte");
    CHECK(!memcmp(buf + 88, sig, 8), "signature bytes");

    // rejects oversized inputs rather than silently truncating
    CHECK(encodeSignedPatrolPayload(1, 0, 1, 1, cp, 3, uid, kMaxOfficerUidLen + 1, prevHash, recHash, sig, 8, buf, sizeof buf) == 0,
          "rejects officer UID longer than kMaxOfficerUidLen");
    CHECK(encodeSignedPatrolPayload(1, 0, 1, 1, "0123456789ABCDEFX", kMaxCheckpointIdLen + 1, uid, 6, prevHash, recHash, sig, 8, buf, sizeof buf) == 0,
          "rejects checkpoint_id longer than kMaxCheckpointIdLen");
    uint8_t tiny[10];
    CHECK(encodeSignedPatrolPayload(1, 0, 1, 1, cp, 3, uid, 6, prevHash, recHash, sig, 8, tiny, sizeof tiny) == 0,
          "rejects output buffer too small");

    printf(failures ? "\nSIGNED PATROL PAYLOAD TESTS FAIL (%d)\n" : "\nSIGNED PATROL PAYLOAD TESTS PASS\n", failures);
    return failures ? 1 : 0;
}
