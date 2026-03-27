# Secure and Resilient Earth Observation (EO) Data Pipeline
## Official Technical and Operational Manual

This repository is a high‑fidelity educational prototype of a secure ground‑segment pipeline for Earth Observation (EO) missions. The goal is not only to show **what** the system does, but to explain **why** every control exists and **how** it is implemented in code. The manual therefore includes both operational guidance and the underlying security theory that motivates each design decision.

Two audiences are assumed simultaneously:
1. Newcomers who need explicit definitions and a guided explanation.
2. Engineers and security practitioners who expect precise terminology, rationale, and architectural intent.

If you want a quick start, see "Quick Start". If you want the full conceptual and code‑level explanation, read from the top.

---

## 1. Mission Context and Strategic Objectives
Earth Observation data is not just scientific; it is strategic. It supports environmental monitoring, infrastructure planning, disaster response, and national security. The ground segment is responsible for protecting this data from the instant it is received to the moment it is delivered to an authorized user.

The system is engineered to satisfy the **CIA Triad**:
1. **Confidentiality**: unauthorized actors must not read or infer sensitive data.
2. **Integrity**: any modification, accidental or malicious, must be detectable.
3. **Availability**: data must remain recoverable and serviceable over time.

This repository implements these objectives explicitly and teaches how they map to concrete mechanisms: authenticated encryption, hashing, access control, redundancy, and audit logging.

---

## 2. What This Project Is
This project is:
1. A functional prototype of a secure EO data lifecycle.
2. A teaching system for security design patterns and operational safeguards.
3. A demonstration of how to align code with security goals and threat assumptions.

## 3. What This Project Is Not
This project is not:
1. A production‑grade ground segment.
2. A complete scientific processing chain.
3. A substitute for enterprise IAM (Identity and Access Management), key management, or HSM (Hardware Security Module) solutions.
4. A performance or scalability benchmark.

These exclusions are intentional. The prototype focuses on correctness of security logic and clarity of architecture.

---

## 4. Quick Start
### 4.1. Requirements
1. Python 3.8+.
2. A terminal shell.

### 4.2. Create a Virtual Environment (recommended)

To avoid conflicts with the system Python (for example on macOS with Homebrew and PEP 668), it is strongly recommended to use a virtual environment inside this repository:

```bash
cd EO_DataSecurity
python3 -m venv .venv
source .venv/bin/activate
```

Once the virtual environment is active your shell prompt will typically show `(.venv)` at the beginning.

### 4.3. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 4.4. Run the Interactive Console
```bash
python main.py
```

### 4.5. Suggested Demo Flow
1. `scan`
2. `login`
3. `ingest`
4. `process`
5. `archive`
6. `hack`
7. `recover`

This sequence walks through acquisition → validation → processing → encryption → corruption → recovery.

---

## 4.6. Hardening Guide (SECURE MODE)

By default the system now starts in **SECURE** mode, which enforces stricter IAM rules.

- **Operating modes**
  - `EO_PIPELINE_MODE=SECURE` (default): password policy and login lockout enabled.
  - `EO_PIPELINE_MODE=DEMO`: more relaxed behaviour, useful only for quick demos.

- **Key environment variables**
  - `EO_PIPELINE_MODE`: `SECURE` / `DEMO`.
  - `EO_MAX_FAILED_LOGINS`: maximum number of failed login attempts before temporary lockout (default: `5`).
  - `EO_LOCKOUT_SECONDS`: lockout duration in seconds after too many failed attempts (default: `60`).

- **Recommendations for “serious” use of the demo**
  1. Keep `EO_PIPELINE_MODE=SECURE` (or set it explicitly).
  2. Use `user_add` with strong passwords (minimum 8 characters, with upper/lowercase letters, digits, and symbols).
  3. Keep `USE_SQLITE = True` so that users and the audit trail are persisted in the SQLite database instead of only in memory / flat files.
  4. Enable `USE_ML = True` if you want to see anomaly scores on EO data and logs (advanced configuration).

In SECURE mode, accounts are temporarily locked after too many failed login attempts and lockout events are recorded in the audit trail.

## 5. Repository Structure
1. `main.py` Interactive operator console (CLI) and orchestration.
2. `secure_eo_pipeline/` Core pipeline package.
3. `secure_eo_pipeline/components/` Data source, ingestion, processing, storage, RBAC, and IDS.
4. `secure_eo_pipeline/resilience/` Backup and self‑healing logic.
5. `secure_eo_pipeline/utils/` Cryptography and logging utilities.
6. `secure_eo_pipeline/db/` SQLite adapter for users and structured audit events.
7. `secure_eo_pipeline/ml/` Lightweight feature extraction and anomaly scoring helpers.
8. `secure_eo_pipeline/config.py` Central configuration and policy definitions.
9. `simulation_data/` Runtime artifacts (generated).
10. `secret.key` Symmetric encryption key for the simulation.

---

## 6. Architectural Model (Zones of Trust)
The pipeline is designed around **trust zones**. Each zone is a security boundary with a specific risk profile:

1. **Landing Zone (Ingest)**: untrusted entry point. Data is treated as hostile until verified.
2. **Processing Staging**: trusted internal zone for validation and scientific transformation.
3. **Secure Archive**: encrypted long‑term storage. Data here must be unreadable without a key.
4. **Backup Storage**: redundant encrypted copy, isolated for recovery.
5. **Access Gateway**: controlled retrieval enforcing authentication and authorization.

This mirrors operational ground segments, where physical and logical separation reduces attack surface and limits blast radius.

---

## 7. Security Theory and Design Rationale
This section explains the **theory** behind the controls, not just the controls themselves.

### 7.1. Confidentiality
Confidentiality protects against disclosure. In storage systems, the most common disclosure risks are:
1. Physical loss or theft of a disk.
2. Misconfigured access controls.
3. Insider misuse.

**Strategy:** Use encryption at rest with authenticated encryption to prevent exposure even when storage is compromised.

### 7.2. Integrity
Integrity means data is trustworthy. EO data is often used for critical decisions, so corruption must be detectable.

**Strategy:** Use cryptographic hashes as immutable fingerprints. Any modification, even a single bit flip, changes the hash (the avalanche effect). By storing hashes in metadata, we maintain a chain of custody across transformations.

### 7.3. Availability
Availability ensures data is recoverable in the face of failures or attacks.

**Strategy:** Maintain redundant copies in isolated zones and verify integrity before restoration.

### 7.4. Least Privilege and Role-Based Access Control (RBAC)
Least privilege reduces the potential damage of compromised accounts. RBAC formalizes this by assigning permissions to roles, not to individuals. This is more scalable and reduces policy drift.

### 7.5. Defense in Depth
Security is not a single mechanism but a layered system. If one control fails, another should still prevent catastrophic impact. This pipeline applies that principle by combining RBAC, encryption, hashing, and redundancy.

---

## 8. Cryptographic Model
### 8.1. Encryption
**Library:** `cryptography` (Fernet).

**Fernet properties:**
1. AES‑128 (Advanced Encryption Standard) in CBC (Cipher Block Chaining) mode for confidentiality.
2. HMAC‑SHA256 for integrity and authenticity.
3. Random IV (Initialization Vector) generation for semantic security.

**Why Fernet:** It is safe by default and reduces configuration errors in educational contexts. For production, AES‑GCM (Advanced Encryption Standard - Galois/Counter Mode) or envelope encryption would be preferred, but Fernet is sufficient to demonstrate authenticated encryption principles.

### 8.2. Key Management
1. Key stored in `secret.key`.
2. Generated automatically if missing.
3. File permissions restricted to owner where supported.

### 8.3. Hashing
**Algorithm:** SHA‑256 (Secure Hash Algorithm 256-bit).

**Rationale:** SHA‑256 is a widely accepted standard for integrity verification. Hashes are computed in chunks to allow processing of large data files without excessive memory use.

---

## 9. Data Lifecycle and Control Flow
### 9.1. Generation (Data Source)
The `EOSimulator` produces a synthetic Level‑0 product consisting of:
1. A `.npy` NumPy array (synthetic sensor data).
2. A `.json` metadata file (timestamp, sensor ID, orbit, cloud cover).

**Control intent:** Even simulated data is treated as untrusted to enforce correct pipeline logic.

### 9.2. Ingestion
The `IngestionManager`:
1. Validates metadata schema.
2. Computes SHA‑256 hash of the raw data.
3. Copies data into the trusted staging zone.

**Control intent:** Establishes the first chain‑of‑custody anchor and isolates untrusted inputs.

### 9.3. Processing and Quality Control
The `ProcessingEngine`:
1. Verifies integrity by comparing hashes.
2. Performs QC (Quality Control) (rejects NaN values).
3. Normalizes values into 0.0–1.0 reflectance range.
4. Writes a new hash for the processed data.

**Control intent:** Ensures only verified data is processed and provenance is updated after transformation.

### 9.4. Archiving
The `ArchiveManager`:
1. Copies processed data into the archive.
2. Encrypts the archive copy in place.
3. Writes final metadata into the archive.
4. Optionally removes cleartext staging files.

**Control intent:** Protects confidentiality and minimizes exposure of cleartext data.

### 9.5. Backup and Recovery
The `ResilienceManager`:
1. Creates an encrypted backup copy.
2. Verifies integrity during recovery.
3. Restores from backup if mismatch is detected.

**Control intent:** Guarantees availability even if the primary archive is corrupted.

---

## 10. Codebase Walkthrough
This section explains each module and its role in the system. It is a conceptual walkthrough of the entire codebase.

### 10.1. `main.py`
Purpose: interactive CLI (Command Line Interface) that orchestrates all pipeline stages.

Key responsibilities:
1. Maintains session state and user identity.
2. Enforces pipeline order and authorization checks.
3. Provides operator commands (`scan`, `ingest`, `process`, `archive`, `hack`, `recover`).
4. Surfaces status and results in a user‑friendly interface.

Design rationale:
- Centralizing orchestration in a CLI mirrors mission control workflows, where operators progress data through controlled stages.

### 10.2. `secure_eo_pipeline/config.py`
Purpose: centralized configuration and policy definition.

Key responsibilities:
1. Defines filesystem layout for trust zones.
2. Defines RBAC roles and permissions.
3. Defines user‑to‑role mappings and IAM security parameters (e.g. lockout thresholds, mode).
4. Enables or disables optional subsystems (SQLite, ML) and sets the default operating mode (`SECURE` by default).

Design rationale:
- Central configuration prevents hardcoding and allows policy changes without modifying core logic.

### 10.3. `secure_eo_pipeline/components/data_source.py`
Purpose: data generation simulation.

Key responsibilities:
1. Creates synthetic data arrays.
2. Writes metadata with acquisition details.
3. Logs the creation for auditability.

Design rationale:
- Simulated data allows security logic to be tested without real mission datasets.

### 10.4. `secure_eo_pipeline/components/ingestion.py`
Purpose: secure entry point into the pipeline.

Key responsibilities:
1. Validates metadata schema.
2. Computes and stores SHA‑256 hash.
3. Moves data into trusted staging.

Design rationale:
- Establishes chain of custody and prevents malformed data from entering processing.

### 10.5. `secure_eo_pipeline/components/processing.py`
Purpose: data transformation with integrity protection.

Key responsibilities:
1. Verifies ingestion hash.
2. Performs QC (NaN rejection).
3. Normalizes data values.
4. Optionally computes a simple anomaly/quality score over the EO data when ML is enabled.
5. Updates metadata and hash.

Design rationale:
- Prevents processing of tampered data and maintains provenance through transformation while exposing hooks for quality analytics.

### 10.6. `secure_eo_pipeline/components/storage.py`
Purpose: secure archiving and retrieval.

Key responsibilities:
1. Encrypts processed products.
2. Writes archive metadata.
3. Optionally removes cleartext staging files.
4. Decrypts only cloned copies for delivery.

Design rationale:
- Protects confidentiality and ensures the archive remains immutable and trustworthy.

### 10.7. `secure_eo_pipeline/components/access_control.py`
Purpose: RBAC enforcement.

Key responsibilities:
1. Authenticate users against either the in‑memory mock DB (`USERS_DB`) or the SQLite `users` table.
2. Authorize actions based on role permissions defined in `config.ROLES`.
3. Enforce password policy and temporary account lockout in SECURE mode.
4. Provide admin‑level user management primitives (create/update/delete users, change roles, enable/disable accounts).
5. Log security events (auth successes/failures, role changes, lockouts) to the unified audit logger.

Design rationale:
- Prevents unauthorized operations and supports auditability.

### 10.8. `secure_eo_pipeline/resilience/backup_system.py`
Purpose: redundancy and recovery.

Key responsibilities:
1. Copies encrypted data to backup zone.
2. Verifies integrity against a known good hash.
3. Restores corrupted data from backup.

Design rationale:
- Ensures availability and reduces operational risk.

### 10.9. `secure_eo_pipeline/db/sqlite_adapter.py`
Purpose: SQLite database access layer.

Key responsibilities:
1. Manage a singleton SQLite connection and ensure the schema exists.
2. Provide CRUD functions for the `users` table (used by the access control layer).
3. Provide an insertion helper for the `audit_events` table (used by the logging subsystem).

Design rationale:
- Centralizes all SQL details in one place and keeps the rest of the codebase database‑agnostic. Makes it easy to replace SQLite with another backend in the future.

### 10.10. `secure_eo_pipeline/ml/`
Purpose: lightweight ML-inspired scoring.

Key responsibilities:
1. `features.py` extracts simple numerical features from EO arrays and log windows.
2. `models.py` computes threshold-based anomaly scores (no heavy dependencies required).

Design rationale:
- Provides realistic hooks for anomaly detection without complicating the stack. Can later be replaced with full ML models.

### 10.11. `secure_eo_pipeline/utils/security.py`
Purpose: cryptographic utilities.

Key responsibilities:
1. Generate and load symmetric keys.
2. Encrypt and decrypt files.
3. Compute SHA‑256 hashes.

Design rationale:
- Centralizing cryptographic primitives reduces code duplication and mistakes.

### 10.12. `secure_eo_pipeline/utils/logger.py`
Purpose: unified audit logging.

Key responsibilities:
1. Configures a shared logger.
2. Enforces consistent format and severity.
3. Provides a system‑wide audit trail.

Design rationale:
- Auditability is a foundational security requirement for mission systems.

---

## 11. Step-by-Step Operational Flow (Mission Control Walkthrough)

This section describes **exactly what happens under the hood** when the operator launches the program (`main.py`) and how to interact with the system as a Mission Control operator.

It is intended to provide full operational transparency and reproducibility.

---

### 11.1. Program Startup and Initial Sanitization

When the operator runs:

```bash
python main.py
```

the system immediately performs a set of automated initialization tasks:

1. **Environment Reset**
	- The system checks for the existence of the `simulation_data/` directory.
	- If found, it is completely deleted.
	- This guarantees a clean, deterministic starting state (tabula rasa) for every execution, with no residual data from previous runs.

2. **Component Initialization**
    All core subsystems are instantiated:
	- EO Data Simulator
	- Secure Ingestion Module
	- Processing Engine
	- Secure Archive Manager
	- Access Control Engine
	- Backup & Resilience Manager

    This mirrors the initialization of services in a real EO Ground Segment.

3. **Operator Interface**
    - The terminal is cleared.
    - The system banner is displayed: ```SECURE EARTH OBSERVATION PIPELINE```
    - The system then enters Mission Control mode.

### 11.2.  Mission Control Console
The operator is presented with an interactive prompt: ```MISSION_CONTROL> _```

At this stage:
- The program is running inside an event loop, waiting for operator commands.
- No processing occurs until an explicit command is issued.
- The system is initially in anonymous mode, with no active identity.

### 11.3. Authentication (login)
Sensitive operations are protected by access control.
1. **Operator Action**: `login`
2. **System Behavior**:
    - In **DEMO** mode the system can display the list of predefined identities (configured in `config.py` and seeded into SQLite):


        | **User** | **Role** | **Password (Demo)** | **Description** |
        | :--- | :--- | :--- | :--- |
        | **admin** | Admin | `admin123` | Full privileges, including disaster recovery |
        | **analyst** | Analyst | `analyst123` | Processing and archiving permissions |
        | **user** | User | `user123` | Read-only access |

      In **SECURE** mode the directory is not enumerated on screen, to avoid leaking usernames to a potential attacker watching the console.

    - The operator selects a username and enters the password (hidden input).
	- Authentication and role assignment are enforced.
	- **Note:** Passwords are hashed using `bcrypt` for security.
	- All subsequent actions are authorized based on the assigned role.

### 11.4. EO Data Generation (scan)
This step simulates the arrival of EO data from the Space Segment.
1. **Operator Action**: `scan`
2. **System Behavior**:
    - Simulates a short downlink delay: ```Listening for satellite downlink...```
    - Generates a unique EO product identifier (e.g. Sentinel_2_XXXX).
    - Creates synthetic Level-0 raw data products in the `ingest_landing_zone/`.
    - The product lifecycle state becomes: ```GENERATED```

At this point, data exists but is **untrusted**.

### 11.5. Secure Ingestion (ingest)
The raw product must be validated before further processing.
1. **Operator Action**: `ingest`
2. **System Behavior**:
    - Verifies that the operator has processing privileges.
    - Validates metadata and file structure.
    - Computes a SHA-256 cryptographic hash, establishing the integrity baseline.
    - Registers the hash as part of the product’s chain of custody.
    - Lifecycle state transitions to: ```INGESTED```

### 11.6. Processing (process)
Raw EO data is transformed into a scientific product.
1. **Operator Action**: `process`
2. **System Behavior**:
    - Simulates computation latency (~1.5 seconds).
    - Symbolically converts data from Level-0 → Level-1C.
    - Executes quality control checks (e.g. NaN detection).
    - Moves the product to the processing staging area.
    - Generates a new integrity hash reflecting the modified content.
    - Lifecycle state transitions to: ```PROCESSED```

### 11.7. Secure Archiving (archive)
The finalized product is secured for long-term storage.
1. **Operator Action**: `archive`
2. **System Behavior**:
    - **Encryption**:
        - The product is encrypted using the Fernet scheme.
        - The encrypted file is unreadable without the secret key.
    - **Backup Creation**:
        - An identical encrypted copy is immediately stored in the backup zone.
    - **Vaulting**:
        - The encrypted product is transferred to the secure archive.
    - Lifecycle state transitions to: ```ARCHIVED```

At this point, confidentiality, integrity, and availability guarantees are enforced.

### 11.8. Attack and Defense Simulation (Optional)
The operator can simulate security incidents and recovery actions.

#### 11.8.1. Simulated Attack (hack)
```hack```
- The system intentionally corrupts the encrypted file in the primary archive.
- The product lifecycle state becomes:
```CORRUPTED```

This represents a disk-level or malicious tampering scenario.

#### 11.8.2. Recovery (recover) — Admin Only
```recover```
- The system compares the corrupted file against the trusted backup.
- Integrity mismatch is detected.
- The corrupted archive is automatically replaced with the clean backup copy.
- The product is restored to a secure state.

This demonstrates automated resilience and self-healing behavior.

#### 11.8.3. Intrusion Detection and Log Analytics (ids)
```ids```
- The operator scans the `audit.log` or the structured DB (`audit_events`) for suspicious patterns.
- If an attack (like the `hack` above), brute force attempt, privilege escalation or backup sabotage occurred, it is flagged.
- When `USE_ML` is enabled, an additional anomaly score over the full log window is computed and surfaced as a `ML Log Anomaly` incident.
- A color-coded threat report is displayed on the console.

#### 11.8.5. Attack simulations (scenario commands)

The system includes dedicated commands that orchestrate end‑to‑end attack narratives for educational purposes:

- `bruteforce_login`  
  Replays repeated login failures against a chosen username to generate a brute‑force pattern in the logs, later detected by the IDS.

- `tamper_metadata`  
  Modifies processing metadata (QC status and integrity fields) without touching the underlying data to demonstrate integrity and provenance checks.

- `delete_backup`  
  Deletes the encrypted backup copy of a product, simulating sabotage of resilience mechanisms.

- `full_attack`  
  Chains together a complete “kill chain”: generate and ingest a product, process and archive it, perform brute‑force attempts, tamper with metadata, sabotage the backup, corrupt the archive, and finally run the IDS. This is the recommended scenario for showing the full defense‑in‑depth story.

#### 11.8.4. Key Rotation (rotate_keys) — Admin Only
```rotate_keys```
- Start the key rotation process.
- All encrypted files are re-encrypted with a new `secret.key`.
- Essential for post-incident recovery.

### 11.9. Utility Commands

- `status` : Displays a summary table showing which lifecycle stages have been completed.
- `help` : Displays the full list of available commands.

### 11.10. Typical Operational Flow
A standard secure EO workflow follows this sequence:

`login` → `scan` → `ingest` → `process` → `archive`

Security testing can then be performed using:

`login` → `scan` → `ingest` → `process` → `archive`

Security testing can then be performed using:

`hack` → `ids` → `recover` → `rotate_keys`

---

## 12. Operational Threat Model
### 12.1. Threats Addressed
1. Unauthorized access → blocked via RBAC.
2. Data corruption or tampering → detected by hashing.
3. Hardware failure → mitigated with backup and recovery.

### 12.2. Threats Not Addressed
1. Network transport security.
2. Multi‑tenant isolation.
3. Key rotation policies.
4. External SIEM (Security Information and Event Management) integration.

Professional security design explicitly states both covered and uncovered risks.

---

## 13. Runtime Data Layout
All runtime artifacts live under `simulation_data/`:
1. `ingest_landing_zone/` untrusted input.
2. `processing_staging/` trusted processing workspace.
3. `secure_archive/` encrypted vault.
4. `backup_storage/` redundant encrypted copy.

---

## 14. File Formats
1. `.npy` NumPy binary arrays for synthetic sensor data.
2. `.json` metadata for validation and provenance.
3. `.enc` encrypted archive outputs.

---

## 15. CLI Command Reference

### 15.1. Core pipeline
1. `login`  
   Authenticate as an operator using the access control component.
2. `logout`  
   End the current session and clear identity.
3. `scan`  
   Generate a new synthetic EO product in the ingest landing zone.
4. `ingest`  
   Validate metadata, compute the initial hash, and move data into the processing zone.
5. `process`  
   Verify integrity, run QC, normalize data, and update metadata (including optional ML scores).
6. `archive`  
   Encrypt the processed product, move it into the secure archive, and create a backup copy.
7. `status`  
   Show the lifecycle state (generated/ingested/processed/archived/hacked) for the active product.

### 15.2. Security operations
8. `hack`  
   Simulate a disk‑level corruption of the encrypted archive file for the active product.
9. `recover`  
   Verify archive integrity against the backup and restore from the backup if corruption is detected (admin only).
10. `ids`  
    Run the intrusion detection logic over audit logs and/or the SQLite `audit_events` table.
11. `rotate_keys`  
    Rotate cryptographic keys across all encrypted archive and backup files (admin only).
12. `health`  
    Run basic health checks on configuration, required directories, and the SQLite database.

### 15.3. Attack scenarios (simulation)
13. `bruteforce_login`  
    Simulate a brute‑force login attack with repeated failed attempts against a target username.
14. `tamper_metadata`  
    Simulate tampering with processing metadata to show integrity and provenance protections.
15. `delete_backup`  
    Simulate backup sabotage by deleting the redundant encrypted copy.
16. `full_attack`  
    Run a full multi‑step attack story (brute‑force, metadata tampering, backup sabotage, archive corruption, IDS).

### 15.4. User & IAM management (admin)
17. `add`  
    Create or update a user account with a given role (enforces password policy in SECURE mode).
18. `list`  
    List all user accounts, roles, status (enabled/disabled), and creation timestamps.
19. `remove`  
    Permanently delete a user account.
20. `change_role`  
    Change the role assigned to an existing user.
21. `disable`  
    Disable or re‑enable a user account.

### 15.5. Utility
22. `help`  
    Display the command list with grouped descriptions.
23. `exit`  
    Quit the console.

---

## 16. Operational Notes and Caveats
1. `secret.key` is a sensitive asset. Do not commit real keys in production.
2. Deleting `secret.key` makes archive data unrecoverable.
3. Verbose logging is intentional for traceability and auditability.

---

## 17. Extensibility Guidelines
1. Maintain trust zone separation for new data flows.
2. Extend metadata schema in a backward‑compatible way.
3. Add new permissions only through `config.py`.
4. Add integrity checks after any new transformation.

---

## 18. Troubleshooting
**Q: Where is data stored?**  
A: Under `simulation_data/` in the zone directories.

**Q: I lost `secret.key`. Can I recover?**  
A: No. The encryption is symmetric; the key is mandatory.

**Q: Processing fails with QC errors. Why?**  
A: The data contains NaN values and is rejected to maintain data quality.

---

## 19. Versioning and Status
This repository is an educational prototype. Version numbers reflect feature maturity, not operational readiness.

---

## 20. Developer Guide (New Features)
This project now includes industry-standard development tools.

### 20.1. Running Automated Tests
We use `pytest` for unit testing the Ingestion and Security modules.
```bash
make test
```
Or manually:
```bash
python -m pytest tests/ -v
```

### 20.2. Running with Docker
You can run the entire pipeline inside a container to ensure environment consistency.
1. **Build the image**:
    ```bash
    docker build -t eo-pipeline .
    ```
2. **Run the container**:
    ```bash
    docker run -it eo-pipeline
    ```

### 20.3. Project Management (Makefile)
- `make install`: Install all dependencies (including dev).
- `make test`: Run the test suite.
- `make run`: Launch the interactive console.
- `make clean`: Remove all simulation data and logs.



### 20.4. Code Quality (Linting)
To ensure the code adheres to PEP 8 standards and best practices, we use `flake8`.
```bash
make lint
```
This command checks for syntax errors, undefined names, and standard formatting issues.

### 20.5. Audit Logging
A persistent audit trail is now saved to `audit.log` in the project root. This file records all security-critical events (login, ingestion, errors) for forensic analysis.

---

## 21. Feature Showcase

### 21.1. Dynamic User Interface
The console now uses **rich** progress bars and animations to simulate realistic satellite operations.
- **Acquisition**: Visualizes X-Band downlink progress.
- **Processing**: Visualizes radiometric calibration steps.

### 21.2. Cryptographic Key Rotation
A critical enterprise security feature. The `rotate_keys` command:
1. Generates a fresh AES-256 key.
2. Decrypts every `.enc` file in the archive and backup zones using the *old* key.
3. Re-encrypts them with the *new* key.
4. Securely overwrites `secret.key`.

This allows the system to recover from potential key compromise without losing data.

This allows the system to recover from potential key compromise without losing data.

### 21.3. Intrusion Detection System (IDS)
Actively hunts for threats in the `audit.log`. The `ids` command uses pattern matching to detect:
- **Brute Force Attacks**: Multiple failed login attempts.
- **Insider / External Threats**: Suspicious activity such as repeated attempts with non-existent or blocked usernames (e.g. an external attacker guessing `hacker`), or access denials for legitimate users.
- **Data Tampering**: Confirmed corruption events on the archive.

It produces a color-coded threat report, simulating a Security Operations Center (SOC) dashboard.

---

## 22. Security Competency Matrix (Project Rationale)
This project is engineered as a **"Vertical Slice"** of a real-world secure system. It is not just a collection of scripts, but a holistic demonstration of how abstract cybersecurity competencies translate into working code.

It provides concrete evidence of proficiency in the following areas:

### 22.1. Risk Management (ISO 27005, EBIOS)
**The Concept**: Identifying risks and implementing proportionate controls.
**In This Project**: The architecture is built on a specific Threat Model (see §12). Every line of code answers a specific risk:
- Risk: Confidentiality Loss $\rightarrow$ Mitigation: **Encryption Agnostic** (`security.py`).
- Risk: Integrity Loss $\rightarrow$ Mitigation: **Hashing SHA-256** (`ingestion.py`).
- Risk: Availability Loss $\rightarrow$ Mitigation: **Backup & Restore Logic** (`resilience`).

### 22.2. ISMS Governance (ISO 27001)
**The Concept**: Governing security through policies and controls.
**In This Project**: The code implements key controls from **ISO 27001 Annex A**:
- **A.9 Access Control**: Implemented via the RBAC system in `config.py`.
- **A.10 Cryptography**: Managed via the `rotate_keys` command and secure key storage.
- **A.12 Operations Security**: Demonstrated through the comprehensive `audit.log`.
- **A.14 System Acquisition**: Enforced by input validation in `ingestion.py`.

### 22.3. Security Architecture
**The Concept**: Designing systems that are secure by design.
**In This Project**:
- **Defense in Depth**: Multiple layers of security (Authentication $\rightarrow$ Authorization $\rightarrow$ Encryption $\rightarrow$ Hashing $\rightarrow$ Backup).
- **Network Segmentation**: Simulated by the "Trust Zones" (Ingest, Staging, Archive), which mimic physical network segregation.
- **Intrusion Detection**: The `ids.py` component acts as a host-based IDS, analyzing logs for patterns.

### 22.4. Verification & Testing
**The Concept**: Proving that security controls work.
**In This Project**:
- **SAST (Static Analysis)**: `flake8` integration ensures code quality and adherence to standards.
- **DAST (Dynamic Analysis)**: `pytest` suites verify security logic at runtime.
- **Penetration Testing**: The `hack` command simulates an active exploit (Data Tampering), and `recover` validates the incident response.

### 22.5. Threat Intelligence (MITRE ATT&CK)
**The Concept**: Understanding adversary tactics.
**In This Project**: The IDS is explicitly designed to detect specific MITRE techniques:
- **T1110 (Brute Force)**: Detected by monitoring consecutive login failures.
- **T1078 (Valid Accounts)**: Detected by identifying activity from known compromised accounts (`hacker`).
- **T1485 (Data Destruction)**: Mitigated by the automated interactions between the Archive and Backup systems.

---

| **Competency Area** | **Framework / Standard** | **Project Implementation** |
| :--- | :--- | :--- |
| **Risk Management** | **ISO 27005, EBIOS** | • Threat Modeling & Risk-based controls |
| **ISMS Governance** | **ISO 27001 (Annex A)** | • A.9, A.10, A.12, A.14 controls |
| **Security Architecture** | **NIST CSF, TOGAF** | • Defense in Depth, Segmentation, IDS |
| **Verification & Testing** | **SAST / DAST / Pentest** | • Linting, Unit Tests, Attack Simulation |
| **Threat Intelligence** | **MITRE ATT&CK / ATLAS** | • Detection of T1110, T1078, T1485 |

---

## 23. Attribution
- **Author**: Emanuele Anzellotti 
- **Type**: Educational / Concept Validation Prototype 
- **Target Domain**: EO Ground Segment Security