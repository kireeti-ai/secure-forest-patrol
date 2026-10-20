#include "Hex.h"

#include <cstdio>

namespace forest::utils {

void bytesToHex(const uint8_t* in, size_t len, char* out) {
    for (size_t i = 0; i < len; ++i) std::snprintf(out + i * 2, 3, "%02x", in[i]);
}

namespace {
int hexNibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}
}  // namespace

bool hexToBytes(const char* hex, size_t len, uint8_t* out) {
    for (size_t i = 0; i < len; ++i) {
        const int hi = hexNibble(hex[i * 2]);
        const int lo = hexNibble(hex[i * 2 + 1]);
        if (hi < 0 || lo < 0) return false;
        out[i] = static_cast<uint8_t>((hi << 4) | lo);
    }
    return true;
}

}  // namespace forest::utils
