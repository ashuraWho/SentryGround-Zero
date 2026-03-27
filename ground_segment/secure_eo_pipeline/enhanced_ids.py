"""
Enhanced Intrusion Detection System (IDS)
==========================================

Correlates HMAC signature verification failures with AI anomaly scores
(reconstruction_mse) to detect cross-segment attack patterns.

NIST CSF PR.DS-2: Data-in-transit is protected
NIST CSF DE.CM-7: Network and environment monitoring
ISO 27001 A.12.4.1: Event logging
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from secure_eo_pipeline.components.ids import IntrusionDetectionSystem as BaseIDS
from secure_eo_pipeline.utils.logger import audit_log


@dataclass
class CrossSegmentAlert:
    """Alert generated from cross-segment correlation analysis."""
    severity: str
    alert_type: str
    cycle_id: str
    anomaly_score: float
    hmac_failures: int
    correlation_factor: float
    attack_probability: float
    details: str
    recommended_action: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "alert_type": self.alert_type,
            "cycle_id": self.cycle_id,
            "anomaly_score": self.anomaly_score,
            "hmac_failures": self.hmac_failures,
            "correlation_factor": self.correlation_factor,
            "attack_probability": self.attack_probability,
            "details": self.details,
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp,
        }


class EnhancedIDS(BaseIDS):
    """
    Enhanced IDS with cross-segment correlation capabilities.
    
    Detects attack patterns that span both Space and Ground segments:
    1. Data injection attempts (high MSE + signature mismatch)
    2. Man-in-the-Middle attacks (signature tampered during downlink)
    3. Replay attacks (duplicate cycle_id + invalid signature)
    4. False anomaly injection (low MSE but anomaly=True)
    """

    MSE_ANOMALY_THRESHOLD = 0.005
    CORRELATION_WEIGHT_MSE = 0.4
    CORRELATION_WEIGHT_HMAC = 0.6

    def __init__(self, log_path: str = "audit.log"):
        super().__init__(log_path)
        self.telemetry_verification_log: List[Dict[str, Any]] = []
        self.ai_anomaly_log: List[Dict[str, Any]] = []
        self.correlation_alerts: List[CrossSegmentAlert] = []

    def log_signature_verification(
        self,
        cycle_id: str,
        is_valid: bool,
        signature_hex: str,
        timestamp: str,
    ):
        """Log HMAC signature verification result for correlation."""
        self.telemetry_verification_log.append({
            "cycle_id": cycle_id,
            "is_valid": is_valid,
            "signature_hex": signature_hex,
            "timestamp": timestamp,
            "logged_at": datetime.utcnow().isoformat(),
        })

    def log_ai_anomaly_score(
        self,
        cycle_id: str,
        reconstruction_mse: float,
        anomaly_detected: bool,
        threshold: float,
    ):
        """Log AI anomaly detection result for correlation."""
        self.ai_anomaly_log.append({
            "cycle_id": cycle_id,
            "reconstruction_mse": reconstruction_mse,
            "anomaly_detected": anomaly_detected,
            "threshold": threshold,
            "logged_at": datetime.utcnow().isoformat(),
        })

    def correlate_attack_patterns(self) -> List[CrossSegmentAlert]:
        """
        Correlate HMAC failures with AI anomaly scores to detect:
        - False data injection
        - Man-in-the-middle attacks
        - Replay attacks
        """
        alerts: List[CrossSegmentAlert] = []
        current_time = datetime.utcnow().isoformat()

        verification_map = {
            v["cycle_id"]: v for v in self.telemetry_verification_log
        }
        anomaly_map = {
            a["cycle_id"]: a for a in self.ai_anomaly_log
        }

        all_cycle_ids = set(verification_map.keys()) | set(anomaly_map.keys())

        for cycle_id in all_cycle_ids:
            verification = verification_map.get(cycle_id, {})
            anomaly = anomaly_map.get(cycle_id, {})

            hmac_failed = not verification.get("is_valid", True)
            mse = anomaly.get("reconstruction_mse", 0.0)
            anomaly_detected = anomaly.get("anomaly_detected", False)

            if hmac_failed:
                alert = self._detect_data_injection_attack(
                    cycle_id, mse, anomaly_detected, current_time
                )
                if alert:
                    alerts.append(alert)

            elif mse < self.MSE_ANOMALY_THRESHOLD and anomaly_detected:
                alert = self._detect_false_anomaly_injection(
                    cycle_id, mse, current_time
                )
                if alert:
                    alerts.append(alert)

            elif cycle_id in verification_map and cycle_id in anomaly_map:
                cycle_count = sum(
                    1 for v in self.telemetry_verification_log
                    if v["cycle_id"] == cycle_id
                )
                if cycle_count > 1:
                    alert = self._detect_replay_attack(
                        cycle_id, cycle_count, current_time
                    )
                    if alert:
                        alerts.append(alert)

        self.correlation_alerts.extend(alerts)
        return alerts

    def _detect_data_injection_attack(
        self,
        cycle_id: str,
        mse: float,
        anomaly_detected: bool,
        timestamp: str,
    ) -> Optional[CrossSegmentAlert]:
        """Detect potential data injection attack."""
        correlation = self._calculate_correlation(mse, True)

        attack_prob = correlation * (1.0 + mse * 10)

        alert = CrossSegmentAlert(
            severity="CRITICAL" if attack_prob > 0.7 else "HIGH",
            alert_type="DATA_INJECTION_SUSPECTED",
            cycle_id=cycle_id,
            anomaly_score=mse,
            hmac_failures=1,
            correlation_factor=correlation,
            attack_probability=min(attack_prob, 1.0),
            details=(
                f"HMAC verification failed with MSE={mse:.6f}. "
                f"Possible malicious data injection or MITM attack on cycle {cycle_id}."
            ),
            recommended_action=(
                "ISOLATE telemetry from this cycle. "
                "Check downlink channel for interference. "
                "Verify PUF key integrity."
            ),
            timestamp=timestamp,
        )

        audit_log.error(
            f"[IDS-CROSS] CRITICAL: Data injection suspected on cycle {cycle_id}. "
            f"MSE={mse:.6f}, Attack probability={attack_prob:.2%}"
        )

        return alert

    def _detect_false_anomaly_injection(
        self,
        cycle_id: str,
        mse: float,
        timestamp: str,
    ) -> Optional[CrossSegmentAlert]:
        """Detect false anomaly flag injection."""
        alert = CrossSegmentAlert(
            severity="MEDIUM",
            alert_type="FALSE_ANOMALY_FLAG",
            cycle_id=cycle_id,
            anomaly_score=mse,
            hmac_failures=0,
            correlation_factor=0.0,
            attack_probability=0.3,
            details=(
                f"Anomaly flag set but MSE={mse:.6f} below threshold "
                f"({self.MSE_ANOMALY_THRESHOLD}). Possible spoofing attempt."
            ),
            recommended_action="Verify sensor calibration and OBC firmware integrity.",
            timestamp=timestamp,
        )

        audit_log.warning(
            f"[IDS-CROSS] Anomaly flag inconsistency on cycle {cycle_id}. "
            f"MSE={mse:.6f} below threshold."
        )

        return alert

    def _detect_replay_attack(
        self,
        cycle_id: str,
        occurrence_count: int,
        timestamp: str,
    ) -> Optional[CrossSegmentAlert]:
        """Detect replay attack via duplicate cycle_id."""
        alert = CrossSegmentAlert(
            severity="HIGH",
            alert_type="REPLAY_ATTACK",
            cycle_id=cycle_id,
            anomaly_score=0.0,
            hmac_failures=occurrence_count - 1,
            correlation_factor=1.0,
            attack_probability=0.9,
            details=(
                f"Cycle ID {cycle_id} received {occurrence_count} times. "
                f"Possible replay attack or downlink malfunction."
            ),
            recommended_action=(
                "Verify sequence integrity. "
                "Check for network replay attack. "
                "Implement cycle_id nonce validation."
            ),
            timestamp=timestamp,
        )

        audit_log.error(
            f"[IDS-CROSS] Replay attack detected: cycle_id={cycle_id} "
            f"seen {occurrence_count} times"
        )

        return alert

    def _calculate_correlation(self, mse: float, hmac_failed: bool) -> float:
        """Calculate correlation factor between MSE and HMAC failures."""
        mse_factor = min(mse / self.MSE_ANOMALY_THRESHOLD, 1.0) * self.CORRELATION_WEIGHT_MSE
        hmac_factor = self.CORRELATION_WEIGHT_HMAC if hmac_failed else 0.0
        return min(mse_factor + hmac_factor, 1.0)

    def analyze_audit_log(self) -> List[Dict[str, str]]:
        """Extended analysis including cross-segment correlation."""
        base_incidents = super().analyze_audit_log()

        cross_segment_alerts = self.correlate_attack_patterns()

        for alert in cross_segment_alerts:
            base_incidents.append({
                "severity": alert.severity,
                "type": f"CROSS-SEGMENT: {alert.alert_type}",
                "details": alert.details,
            })

        return base_incidents

    def get_cross_segment_report(self) -> Dict[str, Any]:
        """Generate comprehensive cross-segment security report."""
        return {
            "report_time": datetime.utcnow().isoformat(),
            "total_hmac_verifications": len(self.telemetry_verification_log),
            "failed_hmac_verifications": sum(
                1 for v in self.telemetry_verification_log if not v["is_valid"]
            ),
            "total_ai_anomalies": len(self.ai_anomaly_log),
            "correlation_alerts": len(self.correlation_alerts),
            "alerts_by_type": self._count_alerts_by_type(),
            "attack_probability_summary": self._get_attack_probability_summary(),
        }

    def _count_alerts_by_type(self) -> Dict[str, int]:
        counts = {}
        for alert in self.correlation_alerts:
            counts[alert.alert_type] = counts.get(alert.alert_type, 0) + 1
        return counts

    def _get_attack_probability_summary(self) -> Dict[str, float]:
        if not self.correlation_alerts:
            return {"max": 0.0, "average": 0.0, "critical_count": 0}

        probs = [a.attack_probability for a in self.correlation_alerts]
        return {
            "max": max(probs),
            "average": sum(probs) / len(probs),
            "critical_count": sum(1 for p in probs if p > 0.7),
        }

    def reset_logs(self):
        """Clear all correlation logs."""
        self.telemetry_verification_log.clear()
        self.ai_anomaly_log.clear()
        self.correlation_alerts.clear()
