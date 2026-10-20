#include <cstdio>
#include <cstring>

#include "SignedAcousticPayload.h"

using namespace forest::crypto;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); ++failures; } } while (0)

int main() {
    uint8_t prevHash[32], recHash[32];
    for (int i = 0; i < 32; ++i) { prevHash[i] = static_cast<uint8_t>(i); recHash[i] = static_cast<uint8_t>(0xB0 + i); }
    const uint8_t sig[6] = {0x30, 0x04, 0x02, 0x01, 0x01, 0x02};
    const char* cp = "CP-01";   // 5 chars
    const char* zone = "Z1";    // 2 chars

    uint8_t buf[256];
    const size_t n = encodeSignedAcousticPayload(3, 1700000000U, 1, 166, cp, 5, zone, 2, prevHash, recHash, sig, 6, buf, sizeof buf);
    // fixed 15 + cp(5) + zone(2) + hashes(64) + sig(6) = 92
    CHECK(n == 92, "encoded length matches the documented layout");

    CHECK(buf[0] == kSignedAcousticPayloadType, "type byte");
    CHECK(buf[1] == kSignedAcousticPayloadVersion, "version byte (2, distinct from legacy unsigned v1)");
    CHECK(buf[2] == 3 && buf[3] == 0 && buf[4] == 0 && buf[5] == 0, "sequence LE");
    CHECK(buf[6] == 0x00 && buf[7] == 0xF1 && buf[8] == 0x53 && buf[9] == 0x65, "epoch LE (1700000000)");
    CHECK(buf[10] == 1, "class index");
    CHECK(buf[11] == 166, "confidence byte (table index, not a reformatted value)");
    CHECK(buf[12] == 5, "checkpoint_id length byte");
    CHECK(!memcmp(buf + 13, "CP-01", 5), "checkpoint_id bytes");
    CHECK(buf[18] == 2, "zone_id length byte");
    CHECK(!memcmp(buf + 19, "Z1", 2), "zone_id bytes");
    CHECK(!memcmp(buf + 21, prevHash, 32), "previous hash bytes");
    CHECK(!memcmp(buf + 53, recHash, 32), "record hash bytes");
    CHECK(buf[85] == 6, "signature length byte");
    CHECK(!memcmp(buf + 86, sig, 6), "signature bytes");

    // zero-length zone_id is valid (optional field)
    const size_t n2 = encodeSignedAcousticPayload(1, 0, 2, 0, cp, 5, nullptr, 0, prevHash, recHash, sig, 6, buf, sizeof buf);
    CHECK(n2 == 15 + 5 + 0 + 64 + 6, "zero-length zone_id encodes correctly");
    CHECK(buf[18] == 0, "zone_id length byte is 0");

    uint8_t tiny[10];
    CHECK(encodeSignedAcousticPayload(1, 0, 1, 0, cp, 5, zone, 2, prevHash, recHash, sig, 6, tiny, sizeof tiny) == 0,
          "rejects output buffer too small");

    printf(failures ? "\nSIGNED ACOUSTIC PAYLOAD TESTS FAIL (%d)\n" : "\nSIGNED ACOUSTIC PAYLOAD TESTS PASS\n", failures);
    return failures ? 1 : 0;
}
