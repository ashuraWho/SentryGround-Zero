# Sentry-Sat — Developer Manual

**Sentry-Sat** is an educational reference implementation of a simulated satellite
On-Board Computer (OBC) pipeline.  It covers the full lifecycle from raw sensor
acquisition through embedded inference, cryptographic telemetry signing, and
ground-station visualization — all without any external hardware, cloud services,
or proprietary datasets.

---

## Table of Contents

1. [What Sentry-Sat Is (and Is Not)](#1-what-sentry-sat-is-and-is-not)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Repository Layout](#3-repository-layout)
4. [Component Deep-Dives](#4-component-deep-dives)
   - 4.1 [core\_engine — C++ OBC Simulator](#41-core_engine--c-obc-simulator)
   - 4.2 [security\_enclave — PUF & Crypto](#42-security_enclave--puf--crypto)
   - 4.3 [ai\_training — Python / TensorFlow Pipeline](#43-ai_training--python--tensorflow-pipeline)
   - 4.4 [console — Mission Control TUI](#44-console--mission-control-tui)
5. [Design Decisions and Motivations](#5-design-decisions-and-motivations)
6. [Known Limitations](#6-known-limitations)
7. [Strengths](#7-strengths)
8. [Prerequisites](#8-prerequisites)
9. [Quick Start](#9-quick-start)
10. [Simulating a Sensor Acquisition](#10-simulating-a-sensor-acquisition)
11. [Building the C++ Simulator](#11-building-the-c-simulator)
12. [Training and Exporting the AI Model](#12-training-and-exporting-the-ai-model)
13. [Linking Real TensorFlow Lite in C++](#13-linking-real-tensorflow-lite-in-c)
14. [Configuration Reference](#14-configuration-reference)
15. [Telemetry Schema Reference](#15-telemetry-schema-reference)
16. [Testing](#16-testing)
17. [Bug Fixes and Design Notes (v1.1)](#17-bug-fixes-and-design-notes-v11)
18. [Extending Sentry-Sat](#18-extending-sentry-sat)
19. [Outputs and Artifacts](#19-outputs-and-artifacts)
20. [License](#20-license)

---

## 1. What Sentry-Sat Is (and Is Not)

### What it IS

- A **self-contained educational stack** that demonstrates how an edge-AI anomaly
  detector would be integrated into a space-grade OBC.
- A **complete CI-friendly project** with CMake, CTest, and Python byte-compilation
  checks that pass without TensorFlow or OpenSSL installed.
- A **reference architecture** connecting Python training → TFLite export → C++
  runtime inference in a single coherent codebase.
- A **teaching tool** for topics including: bump allocators, sensor noise modelling,
  convolutional autoencoders, quantization, HMAC-SHA256, Physical Unclonable
  Functions, and terminal UI design.

### What it IS NOT

- A production flight computer.  No RTOS, no actual satellite bus protocol, no
  radiation-hardened execution model.
- A real machine-learning benchmark.  The synthetic dataset is intentionally simple
  and the model is tiny (< 10 K parameters).
- A security product.  The PUF simulator returns a hard-coded string.  The
  `dummy_hash` fallback is a byte-sum, not a MAC.

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Ground / Development                                         │
│                                                               │
│  ┌───────────────┐   ┌────────────────┐   ┌──────────────┐  │
│  │ Mission Control│   │  TF Training   │   │   TFLite     │  │
│  │    TUI        │──▶│  (Python)      │──▶│  Export      │  │
│  │ (console/)    │   │ (ai_training/) │   │  (.tflite)   │  │
│  └──────┬────────┘   └────────────────┘   └──────┬───────┘  │
│         │ build & run                             │ FP32     │
└─────────┼───────────────────────────────────────-┼──────────┘
          │                                         │
┌─────────▼─────────────────────────────────────── ▼──────────┐
│  Simulated OBC  (core_engine/)                                │
│                                                               │
│  ┌─────────────┐   ┌──────────────────────────────────────┐  │
│  │ MemoryPool  │   │  InferenceEngine                     │  │
│  │ (bump alloc)│──▶│  ┌──────────────┐  ┌──────────────┐ │  │
│  └─────────────┘   │  │ Heuristic    │  │ TFLite FP32  │ │  │
│                    │  │ (default)    │  │ (optional)   │ │  │
│  ┌─────────────┐   │  └──────────────┘  └──────────────┘ │  │
│  │PUFSimulator │   └──────────────────────────────────────┘  │
│  └──────┬──────┘                                             │
│         │                                                     │
│  ┌──────▼──────┐   ┌─────────────────────────────────────┐  │
│  │CryptoSigner │──▶│ Telemetry JSON  (stdout / log)       │  │
│  │(HMAC-SHA256)│   │ {"telemetry_schema":"sentry_sat.obc… │  │
│  └─────────────┘   └─────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

Data flows in one direction: sensors produce frames, the inference engine scores
them, the crypto enclave signs the result, and the telemetry formatter serialises
everything to newline-delimited JSON for ground consumption.

---

## 3. Repository Layout

```
Sentry-Sat/
├── LICENSE
├── CONTRIBUTING.md
├── README.md                          ← this file
│
├── core_engine/                       ← C++17 CMake project
│   ├── CMakeLists.txt
│   ├── src/
│   │   ├── main.cpp                   ← mission loop entry point
│   │   ├── memory_pool.h / .cpp       ← bump allocator (SRAM arena)
│   │   ├── inference_engine.h / .cpp  ← anomaly detection (heuristic / TFLite)
│   │   ├── sensor_frame.hpp           ← deterministic 28×28 frame generators
│   │   └── telemetry_json.hpp         ← JSON emission helpers
│   ├── tests/
│   │   ├── json_self_test.cpp         ← nlohmann smoke test
│   │   └── check_telemetry_json.py    ← telemetry schema assertion
│   └── third_party/
│       └── nlohmann/json.hpp          ← vendored; no network dependency
│
├── security_enclave/                  ← C++ crypto / identity
│   └── src/
│       ├── puf_simulator.h / .cpp     ← simulated Physical Unclonable Function
│       └── crypto_signer.h / .cpp     ← HMAC-SHA256 (OpenSSL) or dummy fallback
│
├── ai_training/                       ← Python ML pipeline
│   ├── config.default.json            ← hyperparameter defaults
│   ├── config_loader.py               ← deep-merge config loader
│   ├── synthetic_frames.py            ← in-memory sensor simulation (no files)
│   ├── model_io.py                    ← shared Keras helpers
│   ├── train_model.py                 ← autoencoder training + threshold calc
│   ├── export_tflite.py               ← INT8 quantised TFLite + C array
│   ├── export_tflite_fp32.py          ← FP32 TFLite for C++ Interpreter
│   ├── simulate_acquisition.py        ← NEW: Python-side acquisition simulator
│   ├── verify_tflite.py               ← TFLite smoke test
│   ├── shap_explainer.py              ← SHAP attribution maps
│   ├── doctor.py                      ← environment check
│   └── requirements.txt
│
├── console/                           ← Textual TUI
│   ├── sentry_console.py              ← Mission Control dashboard
│   └── requirements.txt
│
└── scripts/
    └── build_tensorflow_lite.sh       ← helper for building TFLite from source
```

---

## 4. Component Deep-Dives

### 4.1 `core_engine` — C++ OBC Simulator

#### 4.1.1 MemoryPool

**Why a bump allocator?**
Space-grade and embedded hardware cannot tolerate heap fragmentation, non-
deterministic `malloc` latency, or the code-size overhead of a general allocator.
A bump allocator solves all three: allocation is a single pointer-advance (O(1),
deterministic, tiny code), and the entire arena is reclaimed in one instruction
(`offset = 0`).

**The alignment fix (v1.1)**
The original `allocate(size_t)` did not align the returned pointer.  On most
desktop x86/x86-64 targets this works by accident because `malloc` aligns to 16
bytes and the buffer happens to start there.  On Cortex-M and RISC-V targets
without hardware unaligned-access support, loading a `float*` from an odd address
is a bus fault.

The fixed `allocate(size_t, size_t align = 8)`:
1. Computes the next aligned address using `(-raw_addr) & (align-1)` — the
   standard branchless formula valid for power-of-two alignments.
2. Asserts `align` is a non-zero power of two.
3. The backing `buffer` array is annotated `alignas(kDefaultAlign)` so the
   formula's precondition (buffer starts aligned) is always satisfied.

**Trade-off**: each allocation may waste up to `align-1` bytes of padding.  For
the sizes used in this project (784 floats = 3136 bytes, 8-byte alignment) the
overhead is at most 7 bytes per allocation — negligible.

#### 4.1.2 InferenceEngine

**Two backends, two threshold scales** — the core design tension.

| Backend | Score type | Typical range | Threshold source |
|---|---|---|---|
| `heuristic_linear` | bright-pixel ratio × 10 | 0 – 10 (normal ≈ 0) | `heuristic_threshold` in JSON |
| `tflite_fp32` | reconstruction MSE | 0.0001 – 0.1 (normal ≈ 0.001) | `mse_threshold` in JSON |

**The original bug**: the single `threshold_` field was loaded from `mse_threshold`
and used by both backends.  A well-trained autoencoder produces an `mse_threshold`
around 0.003–0.01.  The heuristic score for a normal frame is 0 (no bright pixels),
but for a streak anomaly it's `28 * 10 / 784 ≈ 0.36`.  So the heuristic worked
despite the wrong threshold — but only accidentally.  A threshold of 0.003 would
have flagged *every* frame as anomalous because any single bright pixel scores
`10/784 ≈ 0.013 > 0.003`.

**The fix**: two independent threshold fields loaded from separate JSON keys,
with `active_threshold()` exposing which one is currently in use.  The heuristic
default (0.05) is independent of the autoencoder training.

**TFLite path** (when enabled at build time with `-DSENTRY_ENABLE_TFLITE=ON`):
1. Loads `anomaly_model_fp32.tflite` from the path in `obc_model_meta.json` or
   `SENTRY_TFLITE_PATH` env var.
2. Copies the float32 frame into the input tensor.
3. Invokes the interpreter.
4. Computes pixel-wise MSE between input and reconstruction.
5. Compares to `tflite_threshold_` (from `mse_threshold` in JSON).

If TFLite fails to initialise for any reason (missing file, tensor shape mismatch,
allocation error), the engine falls back to the heuristic transparently.

#### 4.1.3 sensor_frame.hpp

Provides two deterministic frame generators that match the distribution of
`synthetic_frames.py` so the heuristic and TFLite thresholds can be calibrated
consistently:

- **`fill_nominal_sensor_frame`**: dark-field noise sampled from a linear
  congruential generator (LCG) in [0, 0.2].  The LCG is seeded per call, making
  frames reproducible given the same seed — critical for regression testing.
- **`fill_anomaly_streak_frame`**: same noise floor plus one row saturated to 1.0
  at a configurable row index.  The row stripe is the simplest canonical anomaly
  pattern in satellite sensor data (laser reflection, readout defect, particle hit).

**Why LCG instead of `<random>`?**
`std::mt19937` is 2.5 KB of state.  On a microcontroller with 64 KB SRAM that is
non-trivial.  The LCG is 4 bytes of state and one multiply-add, which is why it
survives in embedded codebases.  For a simulator the quality of randomness is
irrelevant.

#### 4.1.4 telemetry_json.hpp

Emits newline-delimited JSON compatible with log aggregation pipelines (ELK, Loki,
`jq`, etc.).  Every line starts with `[json] ` so the CTest Python validator can
filter it without regex.

Fields: `telemetry_schema`, `cycle_id`, `anomaly`, `signature_hex`,
`reconstruction_mse`, `inference_backend`.

---

### 4.2 `security_enclave` — PUF & Crypto

#### 4.2.1 PUFSimulator

A Physical Unclonable Function exploits manufacturing variation (SRAM startup
state, oscillator race conditions) to produce a device-unique secret without
storing it.  The simulator returns a hard-coded string — in real hardware this
would be replaced by a call to a secure-world memory-mapped register.

**Why simulate a PUF?**
The architectural decision to make `CryptoSigner` depend on `PUFSimulator` instead
of a static key teaches the right dependency structure.  The interface is correct
even if the implementation is a stub.

#### 4.2.2 CryptoSigner

Signs a minimal tuple `(anomaly_flag, timestamp_string)` and returns a hex MAC.

**With OpenSSL** (`-DSENTRY_HAVE_OPENSSL`, set automatically when CMake finds
OpenSSL): HMAC-SHA256, standard, 64 hex characters.

**Without OpenSSL**: `dummy_hash` — additive byte sum, 2–6 hex characters.  This
is printed as a development convenience.  It provides *no* integrity guarantee.

**The release-mode guard (v1.1)**
A `#error` directive fires when:
- OpenSSL is NOT linked, AND
- `NDEBUG` is defined (i.e. CMake `Release` or `RelWithDebInfo` config), AND
- `SENTRY_ALLOW_DUMMY_MAC` is not defined.

This prevents the silent regression where a production binary appears to sign
telemetry but actually emits a trivially forgeable checksum.  To acknowledge the
dummy MAC in CI (no OpenSSL available), add `-DSENTRY_ALLOW_DUMMY_MAC=ON` to the
CMake invocation.

---

### 4.3 `ai_training` — Python / TensorFlow Pipeline

#### 4.3.1 synthetic_frames.py

Models a simplified satellite imaging chain without any external image files:

| Effect | Model |
|---|---|
| Shot noise | Uniform [0, 0.175] per pixel |
| PRNU | Multiplicative per-pixel gain N(1, 0.035²), clipped to [0.88, 1.12] |
| Horizontal banding | Sinusoidal row offset, amplitude 0.02 |
| Dead column | 15% chance per frame; one column shifted −0.08 |
| Anomaly (row streak) | One random row set to 1.0 |
| Anomaly (hotspot) | 3×3 block centred on a random interior pixel set to 1.0 |

**Why these effects?**  PRNU and banding are the two dominant fixed-pattern noise
sources in real CMOS imagers.  Dead columns appear in radiation-damaged sensors.
Row streaks and hotspots model laser dazzle and energetic particle strikes — the
two most common true anomalies in a Low Earth Orbit imaging mission.

#### 4.3.2 train_model.py

Trains a convolutional autoencoder and writes `obc_model_meta.json`.

**Architecture**:
```
Input (28, 28, 1)
  → Conv2D(8, 3×3, relu, same)
  → MaxPool2D(2×2, same)       [14, 14, 8]
  → Conv2D(4, 3×3, relu, same) [14, 14, 4]  ← bottleneck
  → UpSampling2D(2×2)          [28, 28, 4]
  → Conv2D(1, 3×3, sigmoid, same) [28, 28, 1]
Output
```

Total parameters: ≈ 660.  Intentionally tiny — this is an OBC, not a GPU server.

**Threshold calibration**: after training, the model reconstructs the test-normal
set and the MSE distribution is computed.  `mse_threshold` is set to the 95th
percentile of that distribution, meaning ≈5% of normal frames would be false-
positives.  Adjust `eval.threshold_percentile` in the config to tune the
sensitivity / specificity trade-off.

#### 4.3.3 simulate_acquisition.py *(new in v1.1)*

A Python-side reproduction of the full C++ acquisition → inference → telemetry
pipeline.  Its primary purpose is rapid prototyping and validation: you can feed
any image through the same detection path without a C++ build.

**What it adds beyond the C++ OBC**:
- Accepts real image files (PNG, JPEG, TIFF, …) via `--image`.
- Injects configurable sensor artifacts (PRNU, banding, streak) on top of loaded
  images via `--inject-anomaly`.
- Supports three backends: Keras H5, TFLite FP32, and the heuristic scorer — all
  producing the same JSON telemetry schema.
- Prints an ASCII art preview (`--ascii`) of the 28×28 frame for quick visual
  inspection.
- Can be scripted in a shell pipeline: the `[json] {…}` line goes to stdout and
  everything else to a descriptive human-readable stream.

**Why it belongs in `ai_training/` and not `console/`**:  
It depends on NumPy, OpenCV, and optionally TensorFlow.  The console is kept
lightweight (Textual only) so it can be installed without an ML stack.

---

### 4.4 `console` — Mission Control TUI

Built with [Textual](https://textual.textualize.io/), a Python async TUI framework.
The console is a thin orchestrator: it constructs subprocess `argv` lists and
streams their stdout/stderr into a `RichLog` widget in real time using
`asyncio.create_subprocess_exec`.

All heavy work runs in a `@work(exclusive=True, group="proc")` Textual worker,
which prevents concurrent jobs from interfering with each other.

**F11 — Simulate acquisition (new in v1.1)**:  
Opens a modal dialog (`AcquisitionScreen`) that collects:
- Frame source: blank for synthetic, or a file path.
- Synthetic type: `nominal` or `anomaly`.
- Artifact injection flag.
- Inference backend: `auto`, `heuristic`, `tflite`, `keras`.
- RNG seed.
- ASCII preview toggle.

On confirmation it assembles the `simulate_acquisition.py` argv and streams the
output exactly like any other job — including red-highlighted `ANOMALY` lines.

**`_ai_python()` reliability (v1.1)**:  
The function checks for `ai_training/venv/bin/python3` first, then the Windows
path, then falls back to `sys.executable`.  The fallback now logs a visible
warning in the TUI rather than silently using an interpreter that may lack
TensorFlow.

---

## 5. Design Decisions and Motivations

### Why C++17?
`std::filesystem` (used in `InferenceEngine` for path resolution and `fs::exists`
checks) requires C++17.  C++17 is also the minimum for structured bindings and
`if` initialisers, both of which improve readability in the engine code.

### Why nlohmann/json vendored?
`FetchContent` and `find_package` both require network access or a pre-installed
package.  Vendoring the single-header library means the C++ project configures and
builds offline — essential for space-sector development environments and CI without
egress.

### Why synthetic data only?
Real satellite imagery is either classified, export-controlled, or encumbered by
redistribution restrictions.  Synthetic data generated in code is always available,
reproducible given a seed, and can be made as hard or as easy as desired for
testing.  It also makes the repository entirely self-contained.

### Why a convolutional autoencoder for anomaly detection?
Autoencoders are the standard unsupervised approach for anomaly detection when
labelled anomaly examples are scarce.  The key insight: the network trained only on
normal frames learns to reconstruct normal patterns well; anomalous frames produce
high reconstruction error.  No anomaly labels needed at training time.

### Why two TFLite export paths (INT8 and FP32)?
- **INT8** (`export_tflite.py`): for MCUs with 8-bit integer arithmetic only (no
  FPU, or power budget too tight for floats).  Produces `anomaly_model_data.cc`
  for direct embedding as a C byte array.
- **FP32** (`export_tflite_fp32.py`): for the C++ TFLite Interpreter API, which
  expects float32 tensors.  Simpler pipeline (no calibration), and the OBC
  simulator is a desktop application running on hardware with FPUs.

### Why HMAC-SHA256 for telemetry authentication?
A bare hash of the payload would be trivially forgeable by a ground-station
attacker who intercepts a downlink packet.  HMAC binds the MAC to the device
root key: without knowing the PUF-derived key, an attacker cannot produce a valid
MAC even if they know the payload schema.

---

## 6. Known Limitations

| Limitation | Impact | Workaround |
|---|---|---|
| PUF key is hard-coded | Zero security | Replace `internal_key` with a real secure-element API call |
| MemoryPool has no thread safety | Not safe for multi-threaded OBC tasks | Add a spinlock around `offset` if multiple tasks share the pool |
| No RTOS / task scheduler | Single-threaded only | Integrate with FreeRTOS or RTEMS for real multi-task use |
| 5-epoch training | Model may underfit on harder datasets | Increase `epochs` in config; consider deeper architectures |
| 28×28 sensor tile | Tiny patch; real sensors output megapixels | Tile the image and aggregate scores per-tile |
| No noise calibration feedback loop | Synthetic PRNU/banding parameters are fixed | Feed real dark frames to calibrate the synthetic generator |
| ASCII art preview loses spatial structure | Hard to inspect at 28 pixels wide | Export to PNG with OpenCV when visual inspection is needed |
| `simulate_acquisition.py` has no PUF/HMAC | `signature_hex` always "n/a (python-sim)" | Not needed for testing; C++ path handles real signing |

---

## 7. Strengths

- **Zero external services**: builds and runs entirely offline.
- **Full cross-language consistency**: the 28×28 geometry, the noise model, the MSE
  formula, and the JSON schema are defined once and shared between Python and C++.
- **Calibrated thresholds**: `mse_threshold` is derived statistically from the
  training distribution, not chosen by hand.
- **Graceful degradation**: every optional dependency (OpenSSL, TFLite) has a
  working fallback; the project always builds.
- **Machine-parseable telemetry**: `[json] {…}` lines are ready for `jq`, Loki,
  ELK, or any structured log pipeline.
- **Comprehensive CI surface**: CMake + CTest + Python byte-compilation cover the
  most likely regressions without requiring a GPU or network.

---

## 8. Prerequisites

### C++ build

| Tool | Minimum | Notes |
|---|---|---|
| CMake | 3.14 | `find_package(OpenSSL)` and `CTest` |
| C++ compiler | C++17 | GCC ≥ 7, Clang ≥ 5, MSVC 2017+ |
| OpenSSL dev headers | any | `libssl-dev` (Debian/Ubuntu), `openssl@3` (Homebrew) — optional but strongly recommended |

### Python

| Library | Version | Used by |
|---|---|---|
| Python | ≥ 3.10 | All Python scripts |
| TensorFlow | ≥ 2.12 | `train_model.py`, `export_tflite*.py`, `verify_tflite.py`, `shap_explainer.py` |
| NumPy | any | All scripts |
| scikit-learn | any | `train_model.py` |
| shap | any | `shap_explainer.py` |
| opencv-python-headless | any | `simulate_acquisition.py` (image loading only) |
| matplotlib | any | Optional plotting in extensions |
| Textual | ≥ 0.47.0 | `sentry_console.py` |

---

## 9. Quick Start

### Option A — Mission Control TUI (recommended)

```bash
cd console
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python sentry_console.py
```

Use **F1** to build, **F2** to run the simulator, **F3** to train, and **F11** to
open the acquisition simulation dialog.  Press **q** to quit.

### Option B — Command line

```bash
# 1. Build C++ simulator
sudo apt-get install build-essential cmake libssl-dev   # Linux
cmake -S core_engine -B core_engine/build
cmake --build core_engine/build --parallel
./core_engine/build/sentry_sat_sim

# 2. Train AI model
cd ai_training
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python train_model.py
python export_tflite_fp32.py

# 3. Run acquisition simulator
python simulate_acquisition.py --ascii
python simulate_acquisition.py --inject-anomaly --ascii
python simulate_acquisition.py --image /path/to/image.png --ascii
```

---

## 10. Simulating a Sensor Acquisition

`ai_training/simulate_acquisition.py` reproduces the full OBC pipeline in Python.
It is also accessible from the Mission Control TUI via **F11** or the
*"Simulate acquisition"* button.

### CLI examples

```bash
# Synthetic nominal frame, auto-select best available model
python simulate_acquisition.py

# Synthetic anomaly frame with ASCII preview
python simulate_acquisition.py --inject-anomaly --ascii

# Real image file through the Keras model
python simulate_acquisition.py --image ~/sat_patch.png --model autoencoder.h5

# Real image, inject a streak artifact on top, use TFLite
python simulate_acquisition.py \
    --image ~/sat_patch.png \
    --tflite anomaly_model_fp32.tflite \
    --inject-anomaly

# Heuristic only (no model needed)
python simulate_acquisition.py --no-model --ascii

# Pipe telemetry to jq
python simulate_acquisition.py | grep '^\[json\]' | sed 's/^\[json\] //' | jq .
```

### Image loading and preprocessing

When `--image` is supplied:

1. OpenCV loads the file and converts to grayscale.
2. The image is resized to 28×28 using `INTER_AREA` (best for downscaling).
3. Pixel values are normalised to [0, 1] float32.
4. Optionally, sensor artifacts are overlaid (`--inject-anomaly`).

Any image format OpenCV supports (PNG, JPEG, TIFF, BMP, WebP, …) is accepted.

### Backend selection

| `--backend` value | Behaviour |
|---|---|
| `auto` (default) | TFLite if `.tflite` exists, else Keras if `.h5` exists, else heuristic |
| `heuristic` | Bright-pixel ratio scorer, no model needed |
| `tflite` | Requires `anomaly_model_fp32.tflite` |
| `keras` | Requires `autoencoder.h5` |

### Telemetry output

Every run emits one `[json] {…}` line to stdout matching the OBC schema, plus
the additional key `acquisition_source` indicating where the frame came from.

Example:
```json
{
  "telemetry_schema": "sentry_sat.obc.v1",
  "cycle_id": "PY-1711234567",
  "anomaly": true,
  "reconstruction_mse": 0.04217831,
  "threshold": 0.00312,
  "inference_backend": "tflite_fp32",
  "acquisition_source": "/home/user/patch.png",
  "signature_hex": "n/a (python-sim)"
}
```

---

## 11. Building the C++ Simulator

```bash
cmake -S core_engine -B core_engine/build
cmake --build core_engine/build --parallel
ctest --test-dir core_engine/build --output-on-failure
./core_engine/build/sentry_sat_sim
```

### CMake options

| Option | Default | Description |
|---|---|---|
| `SENTRY_ENABLE_TFLITE` | `OFF` | Link the TFLite C++ Interpreter |
| `TFLITE_ROOT` | `""` | Install prefix with `include/` and `lib/` |
| `SENTRY_ALLOW_DUMMY_MAC` | `OFF` | Allow dummy_hash in Release builds (CI only) |

### Environment variables at runtime

| Variable | Default | Description |
|---|---|---|
| `SENTRY_OBC_META` | `../../ai_training/obc_model_meta.json` (relative to build dir) | Path to metadata JSON |
| `SENTRY_TFLITE_PATH` | *(from meta)* | Override for the FP32 `.tflite` file |

---

## 12. Training and Exporting the AI Model

```bash
cd ai_training
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python train_model.py              # → autoencoder.h5, obc_model_meta.json
python export_tflite.py            # → anomaly_model.tflite, anomaly_model_data.cc
python export_tflite_fp32.py       # → anomaly_model_fp32.tflite
python verify_tflite.py            # smoke test
python doctor.py                   # environment check
python shap_explainer.py           # optional; saves shap_*.npy
```

### Custom configuration

Copy `config.default.json` and edit:

```json
{
  "data": {
    "synthetic": {
      "train_samples": 10000,
      "img_size": 28
    }
  },
  "train": { "epochs": 20, "batch_size": 64 },
  "eval":  { "threshold_percentile": 99 }
}
```

Then:
```bash
python train_model.py --config my_config.json
```

### Adding a `heuristic_threshold` to the metadata

After training, add the key manually if you want to tune the heuristic separately:

```json
{
  "telemetry_schema": "sentry_sat.obc_meta.v1",
  "img_size": 28,
  "mse_threshold": 0.00312,
  "heuristic_threshold": 0.05,
  "tflite_fp32_relative": "anomaly_model_fp32.tflite"
}
```

If `heuristic_threshold` is absent, the C++ default `kHeuristicDefaultThreshold`
(0.05) is used.

---

## 13. Linking Real TensorFlow Lite in C++

```bash
# Option A: use your distro's package
sudo apt-get install libtensorflow-lite-dev

# Option B: build from source (slow; ~20 min on a modern laptop)
bash scripts/build_tensorflow_lite.sh

# Then configure with TFLite enabled
cmake -S core_engine -B core_engine/build \
      -DSENTRY_ENABLE_TFLITE=ON \
      -DTFLITE_ROOT=/path/to/tflite-install
cmake --build core_engine/build --parallel
```

Verify TFLite is active by checking the boot log for:
```
[OBC-AI] TFLite FP32 model: ../../ai_training/anomaly_model_fp32.tflite
```

---

## 14. Configuration Reference

### `ai_training/config.default.json`

```jsonc
{
  "data": {
    "synthetic": {
      "train_samples":        5000,   // normal frames for autoencoder training
      "test_normal_samples":  500,    // normal frames for threshold calibration
      "test_anomaly_samples": 500,    // anomalous frames for accuracy reporting
      "img_size":             28      // MUST match kSensorH/kSensorW in C++
    }
  },
  "model": {
    "model_path": "autoencoder.h5"   // output path for trained Keras weights
  },
  "train": {
    "epochs":           5,
    "batch_size":       32,
    "validation_split": 0.1,
    "random_seed":      42
  },
  "eval": {
    "threshold_percentile": 95       // percentile of normal MSE → mse_threshold
  }
}
```

### `ai_training/obc_model_meta.json` (generated)

```jsonc
{
  "telemetry_schema":    "sentry_sat.obc_meta.v1",
  "img_size":            28,
  "mse_threshold":       0.003124,    // used by TFLite backend
  "heuristic_threshold": 0.05,        // used by heuristic backend (manual or default)
  "tflite_fp32_relative": "anomaly_model_fp32.tflite"
}
```

---

## 15. Telemetry Schema Reference

Every OBC cycle and Python acquisition emits one JSON line on stdout:

```
[json] {"telemetry_schema":"sentry_sat.obc.v1", ...}
```

| Field | Type | Description |
|---|---|---|
| `telemetry_schema` | string | Always `"sentry_sat.obc.v1"` |
| `cycle_id` | string | Mission elapsed time tag (e.g. `"T+001"`) |
| `anomaly` | bool | `true` if score > threshold |
| `signature_hex` | string | HMAC-SHA256 hex (64 chars) or dummy hash |
| `reconstruction_mse` | float | Score value (backend-dependent scale) |
| `inference_backend` | string | `"tflite_fp32"` or `"heuristic_linear"` |
| `acquisition_source` | string | Python sim only: image path or synthetic descriptor |

Parse with `jq`:
```bash
./sentry_sat_sim | grep '^\[json\]' | sed 's/^\[json\] //' | jq '{id: .cycle_id, anomaly}'
```

---

## 16. Testing

```bash
ctest --test-dir core_engine/build --output-on-failure -V
```

| Test | What it checks |
|---|---|
| `obc_json_parse_self` | nlohmann::json can parse a minimal JSON string |
| `sentry_sat_sim_smoke` | Simulator exits 0 in under 30 s |
| `sentry_telemetry_json_lines` | ≥2 `[json]` lines with correct schema fields |

Python byte-compilation (CI):
```bash
python3 -m compileall ai_training/ console/ -q
```

---

## 17. Bug Fixes and Design Notes (v1.1)

### Fix 1 — MemoryPool alignment (critical on non-x86 targets)

**Problem**: `allocate(size_t)` returned unaligned pointers.  Accessing a `float*`
at an odd address is undefined behaviour in C++ and a hardware bus fault on
Cortex-M targets without unaligned-access support.

**Fix**: `allocate(size_t size, size_t align = 8)` aligns the returned pointer
using `(-raw_addr) & (align-1)`.  The backing array is `alignas(8)`.  All callers
now pass `alignof(float)` explicitly.

### Fix 2 — InferenceEngine threshold scale mismatch (logic error)

**Problem**: a single `threshold_` was loaded from `mse_threshold` and used by
both the TFLite path (correct) and the heuristic path (wrong scale).

**Fix**: two independent threshold fields (`tflite_threshold_` and
`heuristic_threshold_`) loaded from separate JSON keys.  `active_threshold()`
exposes which is in use.  `main.cpp` now prints both the score and the threshold
it was compared against.

### Fix 3 — `dummy_hash` release-mode guard (security)

**Problem**: a release binary built without OpenSSL silently used the additive
byte-sum fallback without any indication to the operator.

**Fix**: `#error` directive fires in Release builds unless
`SENTRY_ALLOW_DUMMY_MAC=1` is defined.  The warning is also moved from
`sign_payload()` to the constructor so it appears once at startup, not once per
telemetry cycle.

### Fix 4 — `_ai_python()` silent fallback (usability)

**Problem**: if neither the `ai_training/venv` nor `console/.venv` existed,
`_ai_python()` silently fell back to `sys.executable` without telling the user.
TensorFlow calls would then fail with confusing `ModuleNotFoundError` output.

**Fix**: the fallback is preserved (it may be intentional in Docker images where
TF is installed system-wide) but the TUI now logs a dim warning line when the
fallback is used so the operator knows what is happening.

---

## 18. Extending Sentry-Sat

### Add a new anomaly type to `synthetic_frames.py`

```python
def generate_synthetic_data(...):
    ...
    if anomaly:
        kind = rng.integers(0, 3)
        if kind == 0:
            row = int(rng.integers(0, img_size))
            img[row, :, 0] = 1.0             # existing: streak
        elif kind == 1:
            r, c = rng.integers(1, img_size-1, 2)
            img[r-1:r+2, c-1:c+2, 0] = 1.0  # existing: hotspot
        else:
            # New: column streak (vertical sensor defect)
            col = int(rng.integers(0, img_size))
            img[:, col, 0] = 1.0
```

Then re-run `train_model.py` so the threshold is re-calibrated.

### Add a multi-cycle test in `main.cpp`

```cpp
for (int cycle = 1; cycle <= 10; ++cycle) {
    pool.reset();
    float* frame = static_cast<float*>(
        pool.allocate(kSensorElements * sizeof(float), alignof(float)));
    if (cycle % 3 == 0)
        fill_anomaly_streak_frame(frame, static_cast<uint32_t>(cycle), cycle % kSensorH);
    else
        fill_nominal_sensor_frame(frame, static_cast<uint32_t>(cycle));

    bool anomaly = ai_engine.run_inference(frame, kSensorElements);
    std::string sig = signer.sign_payload(anomaly, "T+" + std::to_string(cycle));
    emit_cycle_json(std::cout, "T+" + std::to_string(cycle),
                    anomaly, sig, ai_engine.last_mse(), ai_engine.backend_name());
}
```

### Add a new TUI action

1. Add a `Button` in `compose()`.
2. Add a `BINDINGS` entry.
3. Implement `_action_my_thing()` decorated with `@work(exclusive=True, group="proc")`.
4. Wire the button with `@on(Button.Pressed, "#btn_my_thing")`.

---

## 19. Outputs and Artifacts

| Artifact | Produced by | Description |
|---|---|---|
| `core_engine/build/sentry_sat_sim` | CMake build | OBC mission-loop executable |
| `ai_training/autoencoder.h5` | `train_model.py` | Keras autoencoder weights |
| `ai_training/obc_model_meta.json` | `train_model.py` | Threshold + FP32 path for OBC |
| `ai_training/anomaly_model.tflite` | `export_tflite.py` | INT8 quantised model |
| `ai_training/anomaly_model_data.cc` | `export_tflite.py` | C array for MCU embedding |
| `ai_training/anomaly_model_fp32.tflite` | `export_tflite_fp32.py` | FP32 model for C++ Interpreter |
| `ai_training/shap_anomaly.npy` | `shap_explainer.py` | SHAP values for anomalous probe |
| `ai_training/shap_normal.npy` | `shap_explainer.py` | SHAP values for nominal probe |
| `.sentry_mission.log` | Mission Control TUI | Plain-text subprocess output log |

---

## 20. License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE).
