#pragma once
// Per-node ECDSA P-256 identity: Phase 2 of docs/TAMPER_EVIDENCE_SECURITY_PLAN.md.
//
// On first boot, generates a secp256r1 keypair (mbedtls, hardware-accelerated on the ESP32-S3)
// and stores only the private scalar `d` (32 bytes) in NVS via Preferences, under a dedicated
// namespace. The public key is derived fresh each boot (cheap: one scalar multiply) rather than
// also stored, so there is exactly one secret at rest. NVS is the project's documented baseline
// ("store it in NVS, not plaintext flash" - see the plan); enabling full flash encryption is a
// board-provisioning step (efuse burn) outside what firmware code should do unattended, and is
// noted as a deployment hardening step, not done here.
//
// publicKeyHex() is what an operator exports once, at commissioning, to register against this
// node's ForestNode.public_key row in the backend (ForestCrypto never transmits the private key).
//
// signSha256(canonical_bytes) signs with ECDSA-SHA256, DER-encoded output - byte-for-byte what
// Python's `cryptography` package (`key.verify(sig, message, ec.ECDSA(hashes.SHA256()))`,
// backend/app/services/crypto.py::verify_signature) expects. See tools/verify_node_signature.py
// for the authoritative cross-check against that exact backend code.

#include <cstddef>
#include <cstdint>

namespace forest::crypto {

constexpr size_t kPublicKeyBytes = 65;    // uncompressed SEC1 point: 0x04 || X(32) || Y(32)
constexpr size_t kMaxSignatureBytes = 72; // DER ECDSA over P-256: at most 2*32 + 9 per mbedtls docs

class NodeIdentity {
public:
    // Loads the stored key, or generates and persists a new one if none exists. Call once at boot.
    bool begin(const char* nvsNamespace = "forest_id");

    bool ready() const { return ready_; }

    // Uncompressed SEC1 public key point, 65 bytes (0x04 || X || Y).
    const uint8_t* publicKey() const { return publicKey_; }
    // Same, as a 130-char hex string (null-terminated); outLen must be >= 131.
    void publicKeyHex(char* out, size_t outLen) const;

    // SHA-256-hashes `data` internally, then ECDSA-signs the digest. Writes a DER-encoded
    // signature to `sigOut` (must have room for kMaxSignatureBytes) and sets sigLen.
    // Returns false if not ready() or on an underlying mbedtls failure.
    bool signSha256(const uint8_t* data, size_t len, uint8_t* sigOut, size_t& sigLen);

private:
    uint8_t publicKey_[kPublicKeyBytes] = {0};
    bool ready_ = false;
    void* impl_ = nullptr;   // mbedtls ecdsa/entropy/drbg state (mbedtls types stay out of this header)
};

}  // namespace forest::crypto
