// Class declaration for CryptoSigner member implementations.
#include "crypto_signer.h"
// Operator logs to stdout / stderr for mission console visibility.
#include <iostream>
// stringstream retained only for dummy fallback path formatting.
#include <sstream>
// Hex width fill used when printing OpenSSL HMAC digests.
#include <iomanip>

// ── Release-mode safety guard ─────────────────────────────────────────────────
// The dummy_hash fallback is intentionally weak (additive byte sum, not
// collision-resistant).  Allowing it to silently slip into a release binary
// would undermine the integrity guarantee of the telemetry MAC.
//
// If you are building without OpenSSL AND this is not a debug/dev build,
// the compilation is aborted with a meaningful message rather than producing
// an executable that appears secure but isn't.
//
// To suppress this error deliberately (e.g. CI environments without OpenSSL):
//   cmake ... -DSENTRY_ALLOW_DUMMY_MAC=ON
// or define SENTRY_ALLOW_DUMMY_MAC=1 in your build system.
#if !defined(SENTRY_HAVE_OPENSSL) && !defined(NDEBUG) == 0  \
    && !defined(SENTRY_ALLOW_DUMMY_MAC)
// NDEBUG is set by CMake in Release/RelWithDebInfo configurations.
// This fires only when: no OpenSSL AND it IS a release build AND the override
// flag is absent.
#error "CryptoSigner: OpenSSL is required for release builds.  " \
       "Either install libssl-dev and re-run CMake, or set " \
       "-DSENTRY_ALLOW_DUMMY_MAC=ON to acknowledge the dummy MAC."
#endif

#ifdef SENTRY_HAVE_OPENSSL
// OpenSSL HMAC-SHA256 (link OpenSSL::Crypto when enabled).
#include <openssl/hmac.h>
#include <openssl/sha.h>
#endif

// Store the PUF reference for later key retrieval during signing.
CryptoSigner::CryptoSigner(const PUFSimulator& puf) : puf_ref(puf) {
    std::cout << "[TrustZone] Initializing Crypto Signer Enclave..." << std::endl;
#ifndef SENTRY_HAVE_OPENSSL
    // Warn once at construction time so the notice is visible in every run's log,
    // not buried inside sign_payload() calls.
    std::cerr << "[TrustZone] WARNING: OpenSSL not linked.  "
                 "dummy_hash MAC is in use — development only.\n";
#endif
}

// Non-cryptographic fallback used only when OpenSSL is unavailable at link time.
std::string CryptoSigner::dummy_hash(const std::string& input) {
    unsigned long sum = 0;
    for (char c : input) {
        sum += static_cast<unsigned char>(c);
    }
    std::stringstream ss;
    ss << std::hex << sum;
    return ss.str();
}

#ifdef SENTRY_HAVE_OPENSSL
// Compute HMAC-SHA256(key, msg) and return a fixed-width lowercase hex string.
static std::string hmac_sha256_hex(const std::string& key, const std::string& msg) {
    unsigned char out[SHA256_DIGEST_LENGTH];
    unsigned int out_len = 0;
    const unsigned char* ok = HMAC(
        EVP_sha256(),
        reinterpret_cast<const unsigned char*>(key.data()),
        static_cast<int>(key.size()),
        reinterpret_cast<const unsigned char*>(msg.data()),
        msg.size(),
        out,
        &out_len);
    if (!ok || out_len == 0) return "HMAC_FAIL";

    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (unsigned int i = 0; i < out_len; ++i) {
        oss << std::setw(2) << static_cast<unsigned int>(out[i]);
    }
    return oss.str();
}
#endif

// Compose domain-specific payload, mix secrets, and emit MAC / hex digest.
std::string CryptoSigner::sign_payload(bool is_anomalous, const std::string& timestamp) {
    std::string key     = puf_ref.get_device_key();
    std::string payload = (is_anomalous ? "ANOMALY_TRUE" : "ANOMALY_FALSE") + timestamp;

    std::cout << "[TrustZone] Cryptographically Signing Telemetry Payload..." << std::endl;

#ifdef SENTRY_HAVE_OPENSSL
    return hmac_sha256_hex(key, payload);
#else
    // Warning already emitted once in the constructor; no need to repeat here.
    return dummy_hash(key + payload);
#endif
}
