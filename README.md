# ✨ Sentry-Ground Zero V5: The Web Dashboard

**Sentry-Ground Zero** is an interconnected, end-to-end Deep Space mission architecture. It represents the ultimate synthesis of **Physics, Astrophysics, Machine Learning, and Cybersecurity**.

V4 evolves the project into a **Distributed Constellation Swarm** of microservices, transforming a standard satellite simulation into a multi-domain fleet composed of:
- **Sentry-Astro:** A Precision Astrophysics Probe hunting for Dark Matter.
- **Sentry-Exo:** A Stellar Observatory analyzing Exoplanetary Transits (Keplerian lightcurves).
- **Sentry-EO:** An Earth Observation sentinel tracking atmospheric and surface anomalies.

## 🌌 The Scientific Objective (Nature & Astrophysics)
The Space Segment is containerized in a modular C++ engine that dynamically generates different mathematical and physical realities depending on its mission profile:
1. **Navarro-Frenk-White (NFW)** density profiles for Dark Matter subhalos.
2. **U-shaped Keplerian Flux Dips** representing transiting Exoplanets.
3. **Multi-spectral Albedo Tracking** for Earth terrain simulations.

All physical models are mathematically superimposed onto natural **Poisson photon noise**. The Edge-AI Machine Learning engine hunts for Cosmic Ray strikes or anomalous transit interruptions on the edge.

## 🛡️ The Defense Architecture (Cybersecurity & ML)
Because astronomical discoveries are priceless, the data is constantly under threat by Advanced Persistent Threats (APTs) seeking to steal, forge, or censor the discovery prior to publication.
1. **Space-to-Ground CCSDS Telemetry:** Data is downlinked using authentic binary Space Packets.
2. **Post-Quantum Cryptography (PQC):** The data archives are encrypted using a simulated FIPS 203 ML-KEM (Kyber-768) hybrid protocol against *Harvest Now, Decrypt Later* attacks.
3. **Machine Learning IDS (Isolation Forest):** An Unsupervised ML model actively profiles the behaviors of Mission Control operators to detect insider threats.

## ⚛️ The Physical Firewall 
What if quantum hackers steal the PQC keys and forge a fake image without breaking the cryptography?
Sentry-Ground Zero employs a **Physical-Layer Cybersecurity** defense. 
Upon ingestion, the Ground Segment routes the Numpy payload to a specific **Scientific Validator** based on the sender's Mission Profile. By computing the **Laplacian gradients** of the data matrices, the Firewall enforces:
1. **Virial Theorem & Density Laws** on Dark Matter payloads.
2. **Smooth Keplerian Transitions** to prevent impossible square-wave forgery on Exoplanet transits.
3. **Albedo Maximum Constraints** on Earth observation products.

Malformed data triggers massive non-physical gradient spikes, immediately dropping the payload—**The laws of Physics act as the ultimate cryptographic hash.**

---

## 🚀 Getting Started (The Constellation Swarm + Dashboard)

The architecture is fully containerized with `docker-compose`:
1. **`db`**: A PostgreSQL 15 audit and telemetry log.
2. **`sentry-astro-1`**: SentrySat executing the Dark Matter C++ profile.
3. **`sentry-exo-1`**: SentrySat executing the Exoplanet C++ profile.
4. **`sentry-eo-1`**: SentrySat executing the Earth Observation C++ profile.
5. **`ground-segment`**: The interactive Python Async Mission Control Gateway.
6. **`web-dashboard`**: A LIVE Streamlit UI rendering scientific telemetry in the browser.

### Boot the Constellation
> **IMPORTANT:** Ensure Docker Desktop is running on your machine before executing.
```bash
docker-compose up --build -d
```

### View Live Scientific Telemetry
Open your browser and navigate to the Mission Control Monitor:
```
http://localhost:8501
```

### Trigger Subsystem Downlinks
Attach to the interactive Mission Control terminal:
```bash
docker attach sentryground-zero-ground-segment-1
```

Inside the console, run:
- `scan` -> Randomly assigns the downlink task to one of the satellites in the swarm. Watch the Dashboard instantly render the NFW Halo or Keplerian lightcurve!
- `ingest` -> Validates the PQC signature **AND the laws of Physics**.
- `archive` -> Securely encrypts the scientific data.
- `ids` -> Scans the logs using the Scikit-Learn Isolation Forest.

