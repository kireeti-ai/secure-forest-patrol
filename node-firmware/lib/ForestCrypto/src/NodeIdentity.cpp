#include "NodeIdentity.h"

#include <cstdio>
#include <cstring>

#include <Preferences.h>
#include <mbedtls/ecdsa.h>
#include <mbedtls/entropy.h>
#include <mbedtls/ctr_drbg.h>

#include "Sha256.h"

namespace forest::crypto {
namespace {

constexpr size_t kScalarBytes = 32;   // P-256 private scalar d
constexpr const char* kKeyName = "ecdsa_d";

struct Impl {
    mbedtls_ecdsa_context ctx;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context drbg;
};

int rngFn(void* p, unsigned char* out, size_t len) {
    return mbedtls_ctr_drbg_random(static_cast<mbedtls_ctr_drbg_context*>(p), out, len);
}

void toHex(const uint8_t* in, size_t len, char* out) {
    for (size_t i = 0; i < len; ++i) std::snprintf(out + i * 2, 3, "%02x", in[i]);
}

}  // namespace

bool NodeIdentity::begin(const char* nvsNamespace) {
    ready_ = false;
    auto* impl = new Impl();
    mbedtls_ecdsa_init(&impl->ctx);
    mbedtls_entropy_init(&impl->entropy);
    mbedtls_ctr_drbg_init(&impl->drbg);

    static const char kPers[] = "forest_node_identity";
    if (mbedtls_ctr_drbg_seed(&impl->drbg, mbedtls_entropy_func, &impl->entropy,
                               reinterpret_cast<const unsigned char*>(kPers), sizeof(kPers) - 1) != 0) {
        delete impl;
        return false;
    }

    Preferences prefs;
    if (!prefs.begin(nvsNamespace, false)) {
        delete impl;
        return false;
    }

    uint8_t scalar[kScalarBytes];
    bool haveKey = prefs.getBytesLength(kKeyName) == kScalarBytes &&
                   prefs.getBytes(kKeyName, scalar, kScalarBytes) == kScalarBytes;

    int rc = mbedtls_ecp_group_load(&impl->ctx.grp, MBEDTLS_ECP_DP_SECP256R1);
    if (rc == 0 && haveKey) {
        rc = mbedtls_mpi_read_binary(&impl->ctx.d, scalar, kScalarBytes);
        if (rc == 0) {
            rc = mbedtls_ecp_mul(&impl->ctx.grp, &impl->ctx.Q,
                                 &impl->ctx.d, &impl->ctx.grp.G,
                                 rngFn, &impl->drbg);
        }
    } else if (rc == 0) {
        rc = mbedtls_ecdsa_genkey(&impl->ctx, MBEDTLS_ECP_DP_SECP256R1, rngFn, &impl->drbg);
        if (rc == 0) {
            rc = mbedtls_mpi_write_binary(&impl->ctx.d, scalar, kScalarBytes);
        }
        if (rc == 0) {
            const size_t written = prefs.putBytes(kKeyName, scalar, kScalarBytes);
            if (written != kScalarBytes) rc = -1;   // persistence failed - do not report ready with an unsaved key
        }
    }
    prefs.end();
    // Scrub the scalar from our own stack regardless of outcome; mbedtls keeps its own copy in impl->ctx.d.
    std::memset(scalar, 0, sizeof(scalar));

    if (rc != 0) {
        mbedtls_ecdsa_free(&impl->ctx);
        delete impl;
        return false;
    }

    size_t pubLen = 0;
    rc = mbedtls_ecp_point_write_binary(&impl->ctx.grp, &impl->ctx.Q,
                                        MBEDTLS_ECP_PF_UNCOMPRESSED, &pubLen, publicKey_, kPublicKeyBytes);
    if (rc != 0 || pubLen != kPublicKeyBytes) {
        mbedtls_ecdsa_free(&impl->ctx);
        delete impl;
        return false;
    }

    impl_ = impl;
    ready_ = true;
    return true;
}

void NodeIdentity::publicKeyHex(char* out, size_t outLen) const {
    if (outLen < kPublicKeyBytes * 2 + 1) { if (outLen) out[0] = '\0'; return; }
    toHex(publicKey_, kPublicKeyBytes, out);
}

bool NodeIdentity::signSha256(const uint8_t* data, size_t len, uint8_t* sigOut, size_t& sigLen) {
    if (!ready_ || impl_ == nullptr) return false;
    auto* impl = static_cast<Impl*>(impl_);
    uint8_t digest[forest::utils::kSha256DigestSize];
    forest::utils::sha256(data, len, digest);
    return mbedtls_ecdsa_write_signature(&impl->ctx, MBEDTLS_MD_SHA256, digest, sizeof(digest),
                                         sigOut, &sigLen, rngFn, &impl->drbg) == 0;
}

}  // namespace forest::crypto
