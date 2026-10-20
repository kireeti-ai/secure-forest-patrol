#include <cstdio>
#include <cstring>

#include "Hex.h"

using namespace forest::utils;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); ++failures; } } while (0)

int main() {
    const uint8_t bytes[4] = {0xDE, 0xAD, 0xBE, 0xEF};
    char hex[9];
    bytesToHex(bytes, 4, hex);
    CHECK(!strcmp(hex, "deadbeef"), "bytesToHex lowercase");

    uint8_t decoded[4];
    CHECK(hexToBytes(hex, 4, decoded) && !memcmp(decoded, bytes, 4), "hexToBytes round trip");
    CHECK(hexToBytes("DEADBEEF", 4, decoded) && !memcmp(decoded, bytes, 4), "hexToBytes accepts uppercase");
    CHECK(!hexToBytes("zzadbeef", 4, decoded), "hexToBytes rejects non-hex chars");

    printf(failures ? "\nHEX TESTS FAIL (%d)\n" : "\nHEX TESTS PASS\n", failures);
    return failures ? 1 : 0;
}
