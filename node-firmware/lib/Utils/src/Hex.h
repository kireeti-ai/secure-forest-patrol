#pragma once
// Tiny, portable (host-testable) hex <-> bytes helpers.

#include <cstddef>
#include <cstdint>

namespace forest::utils {

// Writes len*2 lowercase hex chars + NUL into out (out must have room for len*2+1).
void bytesToHex(const uint8_t* in, size_t len, char* out);

// Parses exactly len*2 hex chars from `hex` into out[len]. Returns false on any non-hex
// character or if hex is shorter than len*2 (checked via strlen internally is avoided - caller
// guarantees hex is NUL-terminated and at least len*2 chars, as every caller here does).
bool hexToBytes(const char* hex, size_t len, uint8_t* out);

}  // namespace forest::utils
