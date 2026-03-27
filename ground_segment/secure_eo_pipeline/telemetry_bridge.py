"""
Telemetry Bridge Module - Space-to-Ground Communication
=======================================================

Handles the secure transmission and reception of telemetry from Sentry-Sat OBC
to the Ground Segment's Secure EO Pipeline.

Chain of Custody: Each telemetry packet is bound to a unique cycle_id that
serves as the anchor for tracking data provenance through the entire pipeline.
"""

import json
import os
import time
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

from secure_eo_pipeline.utils.logger import audit_log


class TelemetryStatus(Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    CORRUPTED = "CORRUPTED"


@dataclass
class TelemetryPacket:
    """Represents a complete telemetry packet from Sentry-Sat."""
    telemetry_schema: str
    cycle_id: str
    anomaly: bool
    signature_hex: str
    reconstruction_mse: float
    inference_backend: str
    timestamp_utc: str
    puf_device_id: str = "SAT_KEY_0x8F9A2B"
    received_at: Optional[str] = None
    verification_status: TelemetryStatus = TelemetryStatus.PENDING
    tamper_detected: bool = False

    @classmethod
    def from_json(cls, json_str: str) -> Optional["TelemetryPacket"]:
        try:
            data = json.loads(json_str)
            return cls(
                telemetry_schema=data.get("telemetry_schema", "unknown"),
                cycle_id=data.get("cycle_id", ""),
                anomaly=bool(data.get("anomaly", False)),
                signature_hex=data.get("signature_hex", ""),
                reconstruction_mse=float(data.get("reconstruction_mse", 0.0)),
                inference_backend=data.get("inference_backend", "unknown"),
                timestamp_utc=data.get("timestamp", datetime.utcnow().isoformat()),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            audit_log.error(f"[BRIDGE] Failed to parse telemetry JSON: {e}")
            return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "telemetry_schema": self.telemetry_schema,
            "cycle_id": self.cycle_id,
            "anomaly": self.anomaly,
            "signature_hex": self.signature_hex,
            "reconstruction_mse": self.reconstruction_mse,
            "inference_backend": self.inference_backend,
            "timestamp_utc": self.timestamp_utc,
            "puf_device_id": self.puf_device_id,
            "received_at": self.received_at,
            "verification_status": self.verification_status.value,
            "tamper_detected": self.tamper_detected,
        }


class TelemetryBridge:
    """
    Manages the downlink path from Sentry-Sat to Ground Segment.
    
    Responsibilities:
    1. Simulate X-band downlink reception
    2. Parse and validate telemetry JSON
    3. Establish chain of custody via cycle_id
    4. Hand off verified packets to IngestionManager
    """

    LANDING_ZONE = "simulation_data/telemetry_landing_zone"

    def __init__(self, ground_ingestion_manager):
        self.ingestion = ground_ingestion_manager
        self.received_packets: List[TelemetryPacket] = []
        self.custody_chain: Dict[str, Dict[str, Any]] = {}
        self._ensure_landing_zone()

    def _ensure_landing_zone(self):
        """Create the telemetry landing zone directory."""
        os.makedirs(self.LANDING_ZONE, exist_ok=True)

    def receive_downlink(self, telemetry_json: str) -> Optional[TelemetryPacket]:
        """
        Simulate receiving telemetry from Sentry-Sat via X-band downlink.
        
        ARGUMENTS:
            telemetry_json: Raw JSON string from OBC telemetry emission
            
        RETURNS:
            TelemetryPacket if parsing succeeds, None otherwise
        """
        audit_log.info("[BRIDGE] Receiving telemetry downlink...")

        packet = TelemetryPacket.from_json(telemetry_json)
        if not packet:
            return None

        packet.received_at = datetime.utcnow().isoformat()
        self.received_packets.append(packet)

        self._establish_custody(packet)

        audit_log.info(
            f"[BRIDGE] Telemetry received: cycle_id={packet.cycle_id}, "
            f"anomaly={packet.anomaly}, mse={packet.reconstruction_mse:.6f}"
        )

        return packet

    def _establish_custody(self, packet: TelemetryPacket):
        """Establish chain of custody for a telemetry packet."""
        custody_record = {
            "cycle_id": packet.cycle_id,
            "received_at": packet.received_at,
            "source": "SENTRY_SAT_OBC",
            "device_id": packet.puf_device_id,
            "original_signature": packet.signature_hex,
            "reconstruction_mse": packet.reconstruction_mse,
            "handoff_to_ground": None,
            "status": "CUSTODY_ESTABLISHED",
        }
        self.custody_chain[packet.cycle_id] = custody_record

    def handoff_to_ground_segment(self, packet: TelemetryPacket) -> bool:
        """
        Transfer verified telemetry to the Ground Segment ingestion pipeline.
        
        ARGUMENTS:
            packet: Verified TelemetryPacket
            
        RETURNS:
            True if handoff succeeds
        """
        custody = self.custody_chain.get(packet.cycle_id, {})
        custody["handoff_to_ground"] = datetime.utcnow().isoformat()
        custody["status"] = "HANDOFF_COMPLETE"

        telemetry_path = os.path.join(self.LANDING_ZONE, f"{packet.cycle_id}.json")
        with open(telemetry_path, "w") as f:
            json.dump(packet.to_dict(), f, indent=2)

        audit_log.info(
            f"[BRIDGE] Handoff complete for cycle_id={packet.cycle_id} "
            f"to Ground Segment at {telemetry_path}"
        )
        return True

    def get_custody_record(self, cycle_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve chain of custody record for a cycle."""
        return self.custody_chain.get(cycle_id)

    def list_received_packets(self) -> List[TelemetryPacket]:
        """List all received telemetry packets."""
        return self.received_packets.copy()
