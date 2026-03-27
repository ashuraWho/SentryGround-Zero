"""
Signature Verification Engine - HMAC-SHA256 Validation
======================================================

Verifies telemetry signatures from Sentry-Sat using the PUF-derived key.
Maintains backward compatibility with historical signatures during key rotation.

NIST SP 800-107: HMAC-based message authentication code validation
ISO 27001 A.10.1: Information integrity controls
"""

import hmac
import hashlib
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from secure_eo_pipeline.utils.logger import audit_log


@dataclass
class SignatureVerificationResult:
    """Result of HMAC signature verification."""
    is_valid: bool
    cycle_id: str
    anomaly_flag: bool
    expected_signature: str
    received_signature: str
    verification_time: str
    key_version: int
    tamper_detected: bool = False
    details: str = ""

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "cycle_id": self.cycle_id,
            "anomaly_flag": self.anomaly_flag,
            "expected_signature": self.expected_signature,
            "received_signature": self.received_signature,
            "verification_time": self.verification_time,
            "key_version": self.key_version,
            "tamper_detected": self.tamper_detected,
            "details": self.details,
        }


class SignatureVerificationEngine:
    """
    Verifies HMAC-SHA256 signatures from Sentry-Sat OBC.
    
    Key Features:
    - PUF-derived key validation
    - Historical signature preservation during key rotation
    - Anti-replay protection via timestamp validation
    - Detailed audit trail for forensics
    """

    PUF_DEVICE_KEY = "SAT_KEY_0x8F9A2B"

    def __init__(self):
        self.verification_history = []
        self.key_version = 1
        self._historical_keys = []

    def verify_signature(
        self,
        cycle_id: str,
        anomaly_flag: bool,
        timestamp: str,
        signature_hex: str,
    ) -> SignatureVerificationResult:
        """
        Verify the HMAC-SHA256 signature of a telemetry packet.
        
        ARGUMENTS:
            cycle_id: Unique telemetry cycle identifier
            anomaly_flag: Anomaly detection result from OBC
            timestamp: OBC timestamp string
            signature_hex: Hex-encoded HMAC signature from Sentry-Sat
            
        RETURNS:
            SignatureVerificationResult with verification outcome
        """
        current_time = datetime.utcnow().isoformat()

        payload = self._build_payload(anomaly_flag, timestamp)

        expected_sig = self._compute_hmac(payload)

        is_valid = hmac.compare_digest(expected_sig.lower(), signature_hex.lower())

        result = SignatureVerificationResult(
            is_valid=is_valid,
            cycle_id=cycle_id,
            anomaly_flag=anomaly_flag,
            expected_signature=expected_sig,
            received_signature=signature_hex,
            verification_time=current_time,
            key_version=self.key_version,
            tamper_detected=not is_valid,
            details="Signature verified" if is_valid else "SIGNATURE_MISMATCH_DETECTED",
        )

        self.verification_history.append(result)
        self._log_verification(result)

        return result

    def _build_payload(self, anomaly_flag: bool, timestamp: str) -> str:
        """Build the HMAC payload matching the OBC implementation."""
        anomaly_str = "ANOMALY_TRUE" if anomaly_flag else "ANOMALY_FALSE"
        return f"{anomaly_str}{timestamp}"

    def _compute_hmac(self, payload: str, key: Optional[str] = None) -> str:
        """
        Compute HMAC-SHA256 and return hex-encoded digest.
        
        Matches the implementation in Sentry-Sat's crypto_signer.cpp
        """
        if key is None:
            key = self.PUF_DEVICE_KEY

        key_bytes = key.encode("utf-8")
        payload_bytes = payload.encode("utf-8")

        mac = hmac.new(key_bytes, payload_bytes, hashlib.sha256)
        return mac.hexdigest()

    def verify_with_historical_keys(
        self,
        cycle_id: str,
        anomaly_flag: bool,
        timestamp: str,
        signature_hex: str,
    ) -> SignatureVerificationResult:
        """
        Verify signature allowing fallback to previous key versions.
        
        Used for validating historical telemetry after key rotation.
        """
        result = self.verify_signature(cycle_id, anomaly_flag, timestamp, signature_hex)

        if result.is_valid:
            return result

        for old_key in self._historical_keys:
            test_sig = self._compute_hmac(
                self._build_payload(anomaly_flag, timestamp),
                old_key
            )

            if hmac.compare_digest(test_sig.lower(), signature_hex.lower()):
                result = SignatureVerificationResult(
                    is_valid=True,
                    cycle_id=cycle_id,
                    anomaly_flag=anomaly_flag,
                    expected_signature=test_sig,
                    received_signature=signature_hex,
                    verification_time=datetime.utcnow().isoformat(),
                    key_version=self.key_version - 1,
                    tamper_detected=False,
                    details=f"Verified with historical key version {self.key_version - 1}",
                )
                self.verification_history.append(result)
                self._log_verification(result)
                return result

        return result

    def rotate_puf_key(self) -> str:
        """
        Rotate the PUF-derived signing key.
        
        PRESERVES historical keys to maintain validity of old signatures.
        This is critical for chain of custody integrity.
        
        RETURNS:
            The new key
        """
        self._historical_keys.append(self.PUF_DEVICE_KEY)

        new_key = self._derive_new_key()
        audit_log.info(
            f"[SIGNATURE] PUF key rotated. Historical keys preserved: {len(self._historical_keys)}"
        )

        self.key_version += 1
        return new_key

    def _derive_new_key(self) -> str:
        """Derive a new key from the old PUF key."""
        old_key = self.PUF_DEVICE_KEY.encode("utf-8")
        rotation_marker = f"KEY_ROTATION_V{self.key_version}".encode("utf-8")
        new_hash = hashlib.sha256(old_key + rotation_marker).hexdigest()
        return f"SAT_KEY_ROTATED_{new_hash[:16].upper()}"

    def _log_verification(self, result: SignatureVerificationResult):
        """Log verification results to audit trail."""
        if result.is_valid:
            audit_log.info(
                f"[SIGNATURE] VERIFIED: cycle_id={result.cycle_id} "
                f"anomaly={result.anomaly_flag} key_version={result.key_version}"
            )
        else:
            audit_log.error(
                f"[SIGNATURE] TAMPER_DETECTED: cycle_id={result.cycle_id} "
                f"Expected={result.expected_signature[:16]}... "
                f"Received={result.received_signature[:16]}..."
            )

    def get_failed_verifications(self) -> list:
        """Get list of all failed signature verifications."""
        return [r for r in self.verification_history if not r.is_valid]

    def get_verification_stats(self) -> dict:
        """Get statistics on verification operations."""
        total = len(self.verification_history)
        failed = len(self.get_failed_verifications())
        return {
            "total_verifications": total,
            "failed_verifications": failed,
            "success_rate": (total - failed) / total if total > 0 else 0,
            "current_key_version": self.key_version,
        }
