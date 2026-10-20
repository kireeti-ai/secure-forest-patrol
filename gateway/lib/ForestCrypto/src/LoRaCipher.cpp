#include "LoRaCipher.h"

#include <cstring>

#include <mbedtls/ctr_drbg.h>
#include <mbedtls/entropy.h>
#include <mbedtls/gcm.h>

namespace forest::crypto {

namespace {

struct Rng {
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;
    bool ready = false;

    Rng() {
        mbedtls_entropy_init(&entropy);
        mbedtls_ctr_drbg_init(&drbg);
        static const unsigned char kPersonalization[] = "forest-lora-gcm";
        ready = mbedtls_ctr_drbg_seed(&drbg, mbedtls_entropy_func, &entropy, kPersonalization,
                                      sizeof(kPersonalization) - 1) == 0;
    }
};

Rng& rng() {
    static Rng instance;
    return instance;
}

void encodeAad(const PacketAad& aad, std::uint8_t out[5]) {
    out[0] = aad.type;
    out[1] = aad.sourceId;
    out[2] = aad.destinationId;
    out[3] = static_cast<std::uint8_t>(aad.sequenceNumber & 0xFFU);
    out[4] = static_cast<std::uint8_t>((aad.sequenceNumber >> 8U) & 0xFFU);
}

}  // namespace

bool loRaEncrypt(const std::uint8_t key[kGcmKeyBytes], const PacketAad& aad, const std::uint8_t* plaintext,
                 std::size_t ptLen, std::uint8_t* out, std::size_t outCapacity, std::size_t& outLen) {
    if (plaintext == nullptr || out == nullptr || outCapacity < ptLen + kGcmOverheadBytes) {
        return false;
    }
    if (!rng().ready) {
        return false;
    }
    std::uint8_t nonce[kGcmNonceBytes];
    if (mbedtls_ctr_drbg_random(&rng().drbg, nonce, sizeof(nonce)) != 0) {
        return false;
    }

    std::uint8_t aadBytes[5];
    encodeAad(aad, aadBytes);

    mbedtls_gcm_context gcm;
    mbedtls_gcm_init(&gcm);
    bool ok = mbedtls_gcm_setkey(&gcm, MBEDTLS_CIPHER_ID_AES, key, kGcmKeyBytes * 8U) == 0;
    std::uint8_t tag[kGcmTagBytes];
    if (ok) {
        ok = mbedtls_gcm_crypt_and_tag(&gcm, MBEDTLS_GCM_ENCRYPT, ptLen, nonce, sizeof(nonce), aadBytes,
                                       sizeof(aadBytes), plaintext, out + kGcmNonceBytes, sizeof(tag), tag) == 0;
    }
    mbedtls_gcm_free(&gcm);
    if (!ok) {
        return false;
    }

    std::memcpy(out, nonce, kGcmNonceBytes);
    std::memcpy(out + kGcmNonceBytes + ptLen, tag, kGcmTagBytes);
    outLen = ptLen + kGcmOverheadBytes;
    return true;
}

bool loRaDecrypt(const std::uint8_t key[kGcmKeyBytes], const PacketAad& aad, const std::uint8_t* wrapped,
                 std::size_t wrappedLen, std::uint8_t* out, std::size_t outCapacity, std::size_t& outLen) {
    if (wrapped == nullptr || out == nullptr || wrappedLen < kGcmOverheadBytes) {
        return false;
    }
    const std::size_t ctLen = wrappedLen - kGcmOverheadBytes;
    if (outCapacity < ctLen) {
        return false;
    }

    std::uint8_t aadBytes[5];
    encodeAad(aad, aadBytes);

    mbedtls_gcm_context gcm;
    mbedtls_gcm_init(&gcm);
    bool ok = mbedtls_gcm_setkey(&gcm, MBEDTLS_CIPHER_ID_AES, key, kGcmKeyBytes * 8U) == 0;
    if (ok) {
        ok = mbedtls_gcm_auth_decrypt(&gcm, ctLen, wrapped, kGcmNonceBytes, aadBytes, sizeof(aadBytes),
                                      wrapped + kGcmNonceBytes + ctLen, kGcmTagBytes,
                                      wrapped + kGcmNonceBytes, out) == 0;
    }
    mbedtls_gcm_free(&gcm);
    if (!ok) {
        return false;
    }
    outLen = ctLen;
    return true;
}

}  // namespace forest::crypto
