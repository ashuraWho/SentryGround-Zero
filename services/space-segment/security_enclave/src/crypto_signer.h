// Include guard start.
#ifndef CRYPTO_SIGNER_H
// Unique macro definition for this header file.
#define CRYPTO_SIGNER_H

// Forward dependency: signer reads device identity through PUF interface.
#include "puf_simulator.h"
// Payload metadata strings use std::string for convenience in simulation.
#include <string>

// Signs a minimal telemetry tuple (anomaly flag + timestamp string).
// When built with SENTRY_HAVE_OPENSSL + OpenSSL::Crypto, uses HMAC-SHA256 hex;
// otherwise uses an educational dummy digest (not suitable for operations).
class CryptoSigner {
public:
  // Capture a const reference to an existing PUF instance for key lookups.
  CryptoSigner(const PUFSimulator &puf);

  // Returns hex-encoded authentication tag (HMAC-SHA256 when OpenSSL is
  // linked).
  std::string sign_payload(bool is_anomalous, const std::string &timestamp);

private:
  // Immutable back-reference to simulator-provided root key material.
  const PUFSimulator &puf_ref;

  // Last-resort hash substitute when OpenSSL is absent from the build graph.
  std::string dummy_hash(const std::string &input);
};

#endif
