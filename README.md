# Sentry-Ground Zero

## End-to-End Secure Earth Observation Ecosystem (Space-to-Vault)

### Overview

**Sentry-Ground Zero** is a unified mission control system that integrates:

- **Space Segment (Sentry-Sat)**: On-Board Computer with AI-based anomaly detection, PUF-based cryptographic signing, and 28×28 sensor frame acquisition
- **Ground Segment (Secure EO Pipeline)**: Telemetry ingestion, HMAC-SHA256 signature verification, AES-128 encryption, IDS correlation, and resilient backup/recovery

### Quick Start

```bash
# Install dependencies
pip install rich

# Run unified mission control
python main.py

# Available commands:
# - obc_init        : Initialize Sentry-Sat OBC
# - obc_cycle       : Run single sensor acquisition
# - obc_mission     : Run full mission loop
# - full_mission_attack : Execute cross-segment attack simulation
# - ground_receive  : Receive and verify telemetry
# - ids_correlation : Run IDS correlation analysis
# - recover_mission : Recover from attack
```

### Architecture

```
┌─────────────────────────────────────────────┐
│           SPACE SEGMENT (Sentry-Sat)         │
│  Sensor → InferenceEngine → CryptoSigner    │
│           (Autoencoder)    (PUF+HMAC)       │
└────────────────────┬────────────────────────┘
                     │ X-Band Downlink
                     ▼
┌─────────────────────────────────────────────┐
│          GROUND SEGMENT (Secure EO)          │
│  TelemetryBridge → SignatureVerification    │
│                   ↓                         │
│  EnhancedIDS ← Correlation Analysis          │
│                   ↓                         │
│  ResilienceManager ← Backup/Restore          │
└─────────────────────────────────────────────┘
```

### Security Controls

Mapped to **ISO 27001:2013** and **NIST CSF v1.1**:

| Control | Implementation |
|---------|---------------|
| HMAC-SHA256 Signing | `crypto_signer.cpp`, `signature_verification.py` |
| Chain of Custody | `telemetry_bridge.py`, `mission_control.py` |
| Key Rotation | `security.py:rotate_keys()` |
| IDS Correlation | `enhanced_ids.py` |
| Backup/Restore | `backup_system.py` |

See [docs/SECURITY_CONTROLS.md](docs/SECURITY_CONTROLS.md) for full documentation.

### Directory Structure

```
SentryGround-Zero/
├── main.py                    # Unified Mission Control
├── docs/
│   └── SECURITY_CONTROLS.md   # ISO 27001/NIST CSF mapping
├── space_segment/             # Sentry-Sat OBC (C++)
│   ├── sentry_sat/
│   └── security_enclave/
└── ground_segment/            # Secure EO Pipeline (Python)
    └── secure_eo_pipeline/
        ├── telemetry_bridge.py
        ├── signature_verification.py
        └── enhanced_ids.py
```

### Attack Simulation

The system includes comprehensive attack simulation:

```bash
# Execute full attack kill chain
> full_mission_attack

# Or run individual phases:
> inject_anomaly      # Sensor sabotage
> mitm_attack         # Man-in-the-Middle
> ids_correlation     # Detection by IDS
> recover_mission     # Recovery via backup
```

### Security Compliance

- **ISO 27001:2013**: 17 control objectives implemented
- **NIST CSF v1.1**: All 5 functions (Identify, Protect, Detect, Respond, Recover)

See [docs/SECURITY_CONTROLS.md](docs/SECURITY_CONTROLS.md) for complete control mapping.
