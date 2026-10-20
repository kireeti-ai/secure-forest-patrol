#pragma once

#include <cstddef>
#include <cstdint>

namespace forest::crypto {

// Phase 4 (docs/TAMPER_EVIDENCE_SECURITY_PLAN.md): AES-128-GCM confidentiality layer wrapped
// around the LoRa application payload. Signing (NodeIdentity/PatrolChainHash) already proves a
// payload is authentic and unmodified; it does nothing to stop a passive RF eavesdropper from
// simply reading the plaintext off the air. This is a separate, narrower concern: hide the
// payload bytes in transit. The outer packet header (source/dest/sequence/type - see
// Protocol/src/Serializer.cpp) stays in clear so the gateway can route and ACK before it even
// knows which packet this is; only the application payload is encrypted.
//
// Wire format of the wrapped payload: nonce(12) || ciphertext(N) || tag(16), where N is the
// plaintext length. The nonce is fresh random bytes from the hardware RNG on every call, not
// derived from the sequence number or anything persisted: GCM's one unforgivable mistake is
// reusing a (key, nonce) pair, and a random 96-bit nonce makes that collision probability
// negligible for any realistic lifetime message volume, with no counter/NVS bookkeeping to get
// wrong. The AAD binds the ciphertext to this specific packet's source/destination/sequence/type
// header fields, so a ciphertext captured off one packet cannot be replayed into another header
// context even though the header itself is unencrypted.
constexpr std::size_t kGcmNonceBytes = 12;
constexpr std::size_t kGcmTagBytes = 16;
constexpr std::size_t kGcmKeyBytes = 16;  // AES-128
constexpr std::size_t kGcmOverheadBytes = kGcmNonceBytes + kGcmTagBytes;

struct PacketAad {
    std::uint8_t type;
    std::uint8_t sourceId;
    std::uint8_t destinationId;
    std::uint16_t sequenceNumber;
};

// outLen on success is ptLen + kGcmOverheadBytes. outCapacity must be at least that; returns
// false (and leaves out untouched) if it isn't, or if the underlying GCM operation fails.
bool loRaEncrypt(const std::uint8_t key[kGcmKeyBytes], const PacketAad& aad, const std::uint8_t* plaintext,
                 std::size_t ptLen, std::uint8_t* out, std::size_t outCapacity, std::size_t& outLen);

// wrapped is nonce||ciphertext||tag as produced by loRaEncrypt. Returns false (authentication
// failure, truncated input, or output buffer too small) without writing any plaintext bytes -
// callers must treat a false return as "drop this packet", never fall back to treating
// `wrapped` itself as plaintext.
bool loRaDecrypt(const std::uint8_t key[kGcmKeyBytes], const PacketAad& aad, const std::uint8_t* wrapped,
                 std::size_t wrappedLen, std::uint8_t* out, std::size_t outCapacity, std::size_t& outLen);

}  // namespace forest::crypto
