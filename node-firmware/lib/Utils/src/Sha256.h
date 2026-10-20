#pragma once
// Minimal, portable (host- and ESP32-buildable) SHA-256, one-shot only. No streaming state,
// no dynamic allocation - fits the same "no RAM beyond what's being processed" rule the rest
// of ForestStorage follows. Used for the local event-store hash chain (tamper evidence).

#include <cstddef>
#include <cstdint>

namespace forest::utils {

constexpr size_t kSha256DigestSize = 32;

// out must have room for 32 bytes.
void sha256(const uint8_t* data, size_t len, uint8_t out[kSha256DigestSize]);

}  // namespace forest::utils
