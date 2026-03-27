import os
from typing import List, Dict

from secure_eo_pipeline import config
from secure_eo_pipeline.db import sqlite_adapter

class IntrusionDetectionSystem:
    """
    Analyzes system logs to detect suspicious patterns and potential security breaches.
    Acts as a "Log Hunter" or SIEM (Security Information and Event Management) lite.
    """

    def __init__(self, log_path: str = "audit.log"):
        self.log_path = log_path

    def analyze_audit_log(self) -> List[Dict[str, str]]:
        """
        Scans the audit log for predefined threat signatures.
        
        RETURNS:
            List[Dict]: A list of detected incidents, each with 'severity', 'type', and 'details'.
        """
        incidents: List[Dict[str, str]] = []

        # If a custom log_path was provided and the file exists, always honor it
        # and use file-based analysis. This is important for tests and for
        # running IDS over archived log snapshots.
        if self.log_path != "audit.log" and os.path.exists(self.log_path):
            incidents.extend(self._analyze_events_from_file())
            return incidents

        # Otherwise, prefer structured events from SQLite when enabled,
        # falling back to the default file-based audit.log.
        if getattr(config, "USE_SQLITE", False):
            incidents.extend(self._analyze_events_from_db())
        else:
            incidents.extend(self._analyze_events_from_file())

        return incidents

    # ------------------------------------------------------------------
    # File-based analysis (backward compatible)
    # ------------------------------------------------------------------

    def _analyze_events_from_file(self) -> List[Dict[str, str]]:
        if not os.path.exists(self.log_path):
            return [
                {
                    "severity": "LOW",
                    "type": "System Check",
                    "details": "Audit log not found. System may be fresh.",
                }
            ]

        try:
            with open(self.log_path, "r") as f:
                lines = [line.strip() for line in f.readlines()]
        except Exception as e:
            return [
                {
                    "severity": "CRITICAL",
                    "type": "IDS Failure",
                    "details": f"Could not read audit log: {e}",
                }
            ]

        return self._run_signature_rules(lines)

    # ------------------------------------------------------------------
    # DB-based analysis (structured events)
    # ------------------------------------------------------------------

    def _analyze_events_from_db(self) -> List[Dict[str, str]]:
        # Pull recent events ordered by timestamp. For now, analyze everything.
        conn = sqlite_adapter.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT ts, level, component, user, action, details FROM audit_events ORDER BY ts ASC"
            )
            rows = cur.fetchall()
        except Exception as e:
            return [
                {
                    "severity": "CRITICAL",
                    "type": "IDS Failure",
                    "details": f"Could not query audit_events: {e}",
                }
            ]

        # Build a simple line-like representation reused by the existing rules.
        lines = []
        for r in rows:
            base = f"{r['ts']} {r['level']} {r['component']} {r['details']}"
            if r["user"]:
                base += f" user={r['user']}"
            if r["action"]:
                base += f" action={r['action']}"
            lines.append(base)

        return self._run_signature_rules(lines)

    # ------------------------------------------------------------------
    # Rule engine (shared between file and DB modes)
    # ------------------------------------------------------------------

    def _run_signature_rules(self, lines) -> List[Dict[str, str]]:
        incidents: List[Dict[str, str]] = []
        consecutive_failures = 0

        failed_logins = 0
        critical_events = 0

        for line in lines:
            # Signature 1: Known Malicious Actor
            if "hacker" in line:
                incidents.append(
                    {
                        "severity": "HIGH",
                        "type": "Insider Threat",
                        "details": f"Activity detected from banned user 'hacker': {line}",
                    }
                )

            # Signature 2: Brute Force Detection (Simple Pattern)
            if "Access Denied" in line or "FAILURE" in line:
                consecutive_failures += 1
                failed_logins += 1
            else:
                if "SUCCESS" in line:
                    consecutive_failures = 0

            if consecutive_failures >= 3:
                incidents.append(
                    {
                        "severity": "CRITICAL",
                        "type": "Brute Force Attack",
                        "details": "Multiple consecutive authentication failures detected.",
                    }
                )
                consecutive_failures = 0

            # Signature 3: Data Tampering
            if "Attack successful" in line or "INTEGRITY FAILURE" in line:
                incidents.append(
                    {
                        "severity": "CRITICAL",
                        "type": "Data Integrity Breach",
                        "details": f"CONFIRMED: Storage integrity issue. Context: {line}",
                    }
                )
                critical_events += 1

            # Signature 4: Unauthorized Resource Access
            if "Unauthorized" in line and "lacks" in line:
                incidents.append(
                    {
                        "severity": "MEDIUM",
                        "type": "Privilege Escalation Attempt",
                        "details": f"User attempted action without permission: {line}",
                    }
                )

            # Signature 5: Backup sabotage
            if "[BACKUP] FAILED" in line or "Backup also missing" in line:
                incidents.append(
                    {
                        "severity": "HIGH",
                        "type": "Backup Tampering",
                        "details": f"Backup or redundancy failure detected: {line}",
                    }
                )
                critical_events += 1

        # Optional: basic ML-style scoring over the whole window of events.
        if getattr(config, "USE_ML", False):
            from secure_eo_pipeline.ml import features as ml_features
            from secure_eo_pipeline.ml import models as ml_models

            feats = ml_features.extract_log_window_features(
                events_count=len(lines),
                failed_logins=failed_logins,
                critical_events=critical_events,
            )
            score, reason = ml_models.log_window_anomaly_score(feats)
            if score > 0.0:
                incidents.append(
                    {
                        "severity": "HIGH" if score > 0.5 else "MEDIUM",
                        "type": "ML Log Anomaly",
                        "details": f"Anomaly score={score:.3f}, reason={reason}",
                    }
                )

        return incidents
