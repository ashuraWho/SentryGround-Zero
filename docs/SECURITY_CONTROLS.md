# Sentry-Ground Zero Security Controls Documentation

## System Overview

**Sentry-Ground Zero** is an End-to-End Secure Earth Observation Ecosystem that integrates:

- **Space Segment (Sentry-Sat)**: On-Board Computer (OBC) with AI-based anomaly detection, PUF-based cryptographic signing, and 28×28 sensor frame acquisition
- **Ground Segment (Secure EO Pipeline)**: Telemetry ingestion, signature verification, encryption-at-rest, IDS correlation, and resilient backup/recovery

## Data Flow: Space-to-Vault

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SPACE SEGMENT (Sentry-Sat OBC)                       │
│  ┌──────────┐    ┌──────────────────┐    ┌─────────────────┐              │
│  │ Sensor   │───▶│ InferenceEngine  │───▶│ CryptoSigner    │              │
│  │ 28×28    │    │ (Autoencoder)    │    │ (PUF + HMAC)    │              │
│  └──────────┘    └──────────────────┘    └────────┬────────┘              │
│                                                   │                         │
│                    Telemetry JSON ─────────────────┘                         │
│                    {cycle_id, anomaly, signature_hex, reconstruction_mse}  │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │ X-Band Downlink
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GROUND SEGMENT (Secure EO Pipeline)                   │
│  ┌────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐ │
│  │ TelemetryBridge│───▶│ SignatureVerification│───▶│ EnhancedIDS         │ │
│  │ (Landing Zone) │    │ Engine (HMAC)     │    │ (AI Correlation)      │ │
│  └────────────────┘    └──────────────────┘    └──────────┬──────────────┘ │
│  ┌────────────────┐    ┌──────────────────┐               │                │
│  │ ArchiveManager │◀───│ ResilienceManager│◀──────────────┘                │
│  │ (Fernet AES)   │    │ (Backup/Restore) │                                 │
│  └────────────────┘    └──────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ISO 27001:2013 Controls Mapping

| Control ID | Control Name | Implementation | Location |
|------------|--------------|----------------|----------|
| **A.8.1.1** | Asset Inventory | `config.py`: `directories`, `USERS_DB` | `ground_segment/` |
| **A.9.1.1** | Access Control Policy | `AccessController`: RBAC with roles (admin/analyst/user) | `ground_segment/secure_eo_pipeline/components/access_control.py` |
| **A.9.2.1** | User Registration | `create_user()`, `delete_user()` in AccessController | `ground_segment/secure_eo_pipeline/components/access_control.py:52-76` |
| **A.9.2.2** | Privilege Management | RBAC permissions: `["read", "write", "delete", "manage_keys", "process"]` | `ground_segment/secure_eo_pipeline/config.py:86-102` |
| **A.9.4.1** | Information Access Restriction | `check_auth()` enforces RBAC before actions | `main.py:253-274` |
| **A.9.4.2** | Secure Logon Procedures | `authenticate()` with bcrypt password verification | `ground_segment/secure_eo_pipeline/components/access_control.py:78-109` |
| **A.10.1.1** | Policy on Use of Cryptographic Controls | PUF + HMAC-SHA256 for space segment, Fernet (AES-128-CBC) for ground | `space_segment/`, `ground_segment/secure_eo_pipeline/utils/security.py` |
| **A.10.1.2** | Key Management | `rotate_keys()` with historical key preservation | `ground_segment/secure_eo_pipeline/utils/security.py:210-293` |
| **A.12.4.1** | Event Logging | `audit_log` with structured logging | `ground_segment/secure_eo_pipeline/utils/logger.py` |
| **A.12.4.2** | Protection of Log Information | Audit log with tamper detection | `ground_segment/secure_eo_pipeline/utils/logger.py` |
| **A.12.4.3** | Administrator Logs | Role-based action logging | `main.py` command handlers |
| **A.12.4.4** | Clock Synchronization | `datetime.utcnow()` for consistent timestamps | Throughout codebase |
| **A.13.1.1** | Network Controls | TelemetryBridge with secure handoff protocol | `ground_segment/secure_eo_pipeline/telemetry_bridge.py` |
| **A.13.2.1** | Information Transfer Policy | JSON schema validation, signature verification | `ground_segment/secure_eo_pipeline/components/ingestion.py` |
| **A.14.2.1** | Secure Development Policy | C++ OBC with release guard, Python with type hints | `space_segment/`, `ground_segment/` |
| **A.16.1.1** | Incident Management | IDS alerts, audit log incident detection | `ground_segment/secure_eo_pipeline/components/ids.py` |
| **A.16.1.2** | Reporting Security Events | `IntrusionDetectionSystem.analyze_audit_log()` | `ground_segment/secure_eo_pipeline/components/ids.py:16-39` |
| **A.17.1.1** | Business Continuity | `ResilienceManager.verify_and_restore()` | `ground_segment/secure_eo_pipeline/resilience/backup_system.py` |
| **A.17.1.2** | Disaster Recovery | Backup/restore with SHA-256 verification | `ground_segment/secure_eo_pipeline/resilience/backup_system.py:69-132` |

---

## NIST Cybersecurity Framework (CSF) v1.1 Mapping

### IDENTIFY (ID)

| Function | Category | Implementation |
|----------|----------|----------------|
| **ID.AM** | Asset Management | `config.py`: Directory structure, user database |
| **ID.BE** | Business Environment | Space-to-Vault mission critical data flow |
| **ID.GV** | Governance | ISO 27001 aligned, audit logging |
| **ID.RA** | Risk Assessment | IDS pattern detection, attack simulation |

### PROTECT (PR)

| Category | Implementation | NIST Mapping |
|----------|----------------|--------------|
| **PR.AC** | Access Control | RBAC, bcrypt passwords, file permissions (0o600) |
| **PR.AT** | Awareness Training | Documentation, inline comments |
| **PR.DS** | Data Security | |
| PR.DS-1 | Data-at-rest protected | Fernet AES-128-CBC encryption |
| PR.DS-2 | Data-in-transit protected | HMAC-SHA256 signed telemetry |
| PR.DS-6 | Integrity checking | SHA-256 hash verification |
| **PR.IP** | Information Protection | |
| PR.IP-1 | Baseline policy | IngestionManager schema validation |
| PR.IP-3 | Change control | Key rotation with re-encryption |
| **PR.MA** | Maintenance | Backup system, integrity verification |
| **PR.PT** | Protective Technology | |
| PT.ER-1 | Endpoint detection | IDS log analysis |
| PT.RB-1 | Recovery planning | ResilienceManager backup/restore |

### DETECT (DE)

| Category | Implementation |
|----------|----------------|
| **DE.AE** | Anomaly Detection |
| DE.AE-1 | Network baselining | Telemetry baseline comparison |
| DE.AE-2 | Analysis of detected events | IDS correlation engine |
| DE.AE-3 | Event correlation | `EnhancedIDS.correlate_attack_patterns()` |
| **DE.CM** | Continuous Monitoring |
| DE.CM-1 | Network monitoring | TelemetryBridge receiving logs |
| DE.CM-7 | Anomaly detection monitoring | IDS with reconstruction_mse correlation |

### RESPOND (RS)

| Category | Implementation |
|----------|----------------|
| **RS.AN** | Analysis |
| RS.AN-1 | Incident analysis | IDS alert generation |
| RS.AN-2 | Incident categorization | Severity levels (CRITICAL/HIGH/MEDIUM/LOW) |
| **RS.MI** | Mitigation |
| RS.MI-1 | Incident containment | Tamper detection, custody isolation |
| RS.MI-2 | Incident mitigation | Recovery from encrypted backup |
| **RS.RP** | Response Planning | `full_mission_attack` command for incident response testing |

### RECOVER (RC)

| Category | Implementation |
|----------|----------------|
| **RC.RP** | Recovery Planning |
| RC.RP-1 | Recovery plan execution | `recover_mission()` command |
| **RC.IM** | Improvements |
| RC.IM-1 | Incorporate lessons learned | IDS correlation analysis |
| **RC.CO** | Communications |
| RC.CO-1 | Public relations | Audit log incident reporting |

---

## Security Architecture Details

### 1. Chain of Custody

**Implementation**: `TelemetryBridge._establish_custody()` and `MissionControl._establish_custody()`

```
Chain of Custody Record:
{
    "cycle_id": "T+001",
    "received_at": "2026-03-27T12:00:00",
    "source": "SENTRY_SAT_OBC",
    "device_id": "SAT_KEY_0x8F9A2B",
    "original_signature": "...",
    "reconstruction_mse": 0.001234,
    "status": "CUSTODY_ESTABLISHED",
    "tamper_detected": false
}
```

**ISO 27001**: A.12.4.1 (Event Logging), A.12.4.2 (Log Protection)
**NIST CSF**: DE.CM-1 (Network Monitoring)

### 2. Cryptographic Signing (Space Segment)

**Implementation**: `CryptoSigner` in C++ with HMAC-SHA256

```cpp
std::string sign_payload(bool is_anomalous, const std::string& timestamp) {
    std::string key = puf_ref.get_device_key();
    std::string payload = (is_anomalous ? "ANOMALY_TRUE" : "ANOMALY_FALSE") + timestamp;
    return hmac_sha256_hex(key, payload);
}
```

**ISO 27001**: A.10.1.1 (Cryptographic Policy)
**NIST CSF**: PR.DS-2 (Data-in-transit Protection)

### 3. Signature Verification (Ground Segment)

**Implementation**: `SignatureVerificationEngine.verify_signature()`

- Matches OBC payload construction
- Supports historical key verification after rotation
- Logs verification results to audit trail

**ISO 27001**: A.10.1.2 (Key Management)
**NIST CSF**: PR.DS-6 (Integrity Checking)

### 4. Key Rotation with Historical Preservation

**Implementation**: `SignatureVerificationEngine.rotate_puf_key()`

- Old keys stored in `_historical_keys` list
- `verify_with_historical_keys()` allows backward verification
- Maintains chain of custody integrity for historical telemetry

**ISO 27001**: A.10.1.2 (Key Management)
**NIST CSF**: PR.DS-6 (Integrity Checking)

### 5. Enhanced IDS Correlation

**Implementation**: `EnhancedIDS.correlate_attack_patterns()`

**Detects**:
1. **Data Injection**: HMAC failure + high MSE correlation
2. **MITM Attacks**: Signature mismatch during downlink
3. **False Anomaly Injection**: Anomaly flag with low MSE
4. **Replay Attacks**: Duplicate cycle_id detection

**Correlation Formula**:
```
correlation = (mse_factor * 0.4) + (hmac_failure_factor * 0.6)
attack_probability = correlation * (1.0 + mse * 10)
```

**ISO 27001**: A.12.4.1 (Event Logging), A.16.1.1 (Incident Management)
**NIST CSF**: DE.AE-3 (Event Correlation), DE.CM-7 (Anomaly Monitoring)

### 6. Resilience and Recovery

**Implementation**: `ResilienceManager.verify_and_restore()`

```
Flow:
1. Calculate SHA-256 hash of primary file
2. Compare with known-good hash from ingestion
3. If mismatch → copy from encrypted backup
4. If backup missing → CRITICAL data loss alert
```

**ISO 27001**: A.17.1.1 (Business Continuity), A.17.1.2 (Disaster Recovery)
**NIST CSF**: RC.RP-1 (Recovery Plan Execution)

---

## Attack Simulation Scenarios

### Cross-Segment Attack: `full_mission_attack`

| Phase | Attack | Detection Mechanism |
|-------|--------|---------------------|
| 1 | Sensor Sabotage | Elevated MSE, anomaly flag |
| 2 | MITM Attack | Signature verification failure |
| 3 | False Data Injection | HMAC mismatch |
| 4 | IDS Correlation | Cross-segment pattern detection |
| 5 | Recovery | Backup verification |

### MITM Attack Detection

**Command**: `mitm_attack`

- Intercepts telemetry during downlink
- Replaces authentic signature with forged MAC
- Ground segment detects via `SignatureVerificationEngine`

### Data Injection Detection

**Correlation**:
```python
if hmac_failed and mse > threshold:
    alert("DATA_INJECTION_SUSPECTED")
```

---

## Threat Matrix

| Threat | Vector | Mitigation | Controls |
|--------|--------|------------|----------|
| Data Tampering | MITM during downlink | HMAC-SHA256 signatures | ISO A.10.1.1, NIST PR.DS-2 |
| Unauthorized Access | Credential brute-force | RBAC, bcrypt, lockout | ISO A.9.2.1, NIST PR.AC |
| Data Loss | Storage corruption | Encrypted backups, SHA-256 verification | ISO A.17.1.2, NIST RC.RP-1 |
|Replay Attack | Duplicate telemetry | Cycle ID tracking, timestamp validation | ISO A.12.4.4, NIST DE.AE |
| Insider Threat | Malicious actor | Audit logging, IDS pattern detection | ISO A.16.1.1, NIST DE.AE-2 |
| Key Compromise | PUF key exposure | Key rotation, historical preservation | ISO A.10.1.2, NIST PR.DS-6 |

---

## Compliance Verification

### ISO 27001:2013 Compliance Checklist

- [x] A.8.1.1: Asset inventory maintained
- [x] A.9.1.1: Access control policy documented
- [x] A.9.4.1: Information access restriction enforced
- [x] A.10.1.1: Cryptographic controls implemented
- [x] A.10.1.2: Key management procedures established
- [x] A.12.4.1: Event logging implemented
- [x] A.16.1.1: Incident management procedures defined
- [x] A.17.1.2: Disaster recovery procedures documented

### NIST CSF v1.1 Compliance Checklist

- [x] ID.GV: Governance structure established
- [x] PR.AC: Access controls implemented
- [x] PR.DS-1: Data-at-rest protection (Fernet)
- [x] PR.DS-2: Data-in-transit protection (HMAC)
- [x] PR.DS-6: Integrity checking (SHA-256)
- [x] DE.AE-1: Network baselining (telemetry baseline)
- [x] DE.AE-3: Event correlation (EnhancedIDS)
- [x] DE.CM-7: Anomaly detection monitoring (ML correlation)
- [x] RC.RP-1: Recovery plan execution (ResilienceManager)
- [x] RS.AN-1: Incident analysis (IDS alerts)

---

## Security Testing

### Penetration Testing Commands

```bash
# Full attack simulation
python main.py
> full_mission_attack

# MITM attack
> obc_init
> obc_cycle
> mitm_attack
> ground_receive

# Brute force detection
> obc_init
> obc_mission 10
> ids_correlation

# Recovery verification
> ground_recover
> custody_status
```

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-03-27 | Initial security controls documentation | Sentry-Ground Zero Team |

---

**Document Classification**: UNCLASSIFIED
**Document Owner**: Security Architecture Team
**Review Cycle**: Annual
