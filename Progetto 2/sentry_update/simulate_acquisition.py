"""
simulate_acquisition.py — Simulate an OBC sensor acquisition from an input image.

What this does
--------------
Reproduces the full on-board acquisition pipeline in Python so you can feed
*any* image (PNG, JPEG, TIFF, …) through exactly the same detection path that
the C++ OBC uses at runtime:

  1. Load the image (or generate a synthetic frame) and resize to 28×28.
  2. Normalize to [0, 1] float32 (single channel / grayscale).
  3. Optionally inject the same sensor artifacts modelled in synthetic_frames.py
     (PRNU, banding, dead column) to stress-test the anomaly gate.
  4. Run the trained Keras autoencoder or a TFLite model and compute MSE.
  5. Compare to the threshold in obc_model_meta.json and print a telemetry line.

Usage
-----
  python simulate_acquisition.py                          # synthetic nominal frame
  python simulate_acquisition.py --image path/to/img.png # real image file
  python simulate_acquisition.py --image img.png --inject-anomaly  # force anomaly artifact
  python simulate_acquisition.py --model autoencoder.h5 --image img.png
  python simulate_acquisition.py --tflite anomaly_model_fp32.tflite --image img.png

The script always writes a JSON telemetry line to stdout that matches the OBC
schema ("sentry_sat.obc.v1") so it can be piped into jq or the mission log.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

# ── Optional imports with friendly errors ──────────────────────────────────────

def _require(name: str):
    """Import a module; print a friendly message and exit if missing."""
    import importlib
    try:
        return importlib.import_module(name)
    except ImportError:
        print(f"[ERROR] '{name}' is not installed.  Run: pip install {name}",
              file=sys.stderr)
        sys.exit(1)


# ── Constants shared with C++ OBC ─────────────────────────────────────────────

SENSOR_H = 28   # kSensorH in sensor_frame.hpp
SENSOR_W = 28   # kSensorW
_HERE    = Path(__file__).resolve().parent


# ── Sensor pipeline helpers ────────────────────────────────────────────────────

def load_image_as_frame(path: Path) -> np.ndarray:
    """
    Load any image file, convert to grayscale, resize to SENSOR_H×SENSOR_W,
    and normalize to float32 in [0, 1].

    Returns shape (28, 28, 1).
    """
    cv2 = _require("cv2")
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Could not open image: {path}")
    img = cv2.resize(img, (SENSOR_W, SENSOR_H), interpolation=cv2.INTER_AREA)
    return (img.astype(np.float32) / 255.0).reshape(SENSOR_H, SENSOR_W, 1)


def synthetic_nominal_frame(seed: int = 42) -> np.ndarray:
    """
    Generate one nominal synthetic frame identical to synthetic_frames.py
    (shot noise × PRNU + banding + optional dead column) but for a single
    sample.  Shape: (28, 28, 1).
    """
    from synthetic_frames import generate_synthetic_data
    frames, _ = generate_synthetic_data(
        num_samples=1, img_size=SENSOR_H, anomaly=False, prnu_seed=seed)
    return frames[0]  # (28, 28, 1)


def synthetic_anomaly_frame(seed: int = 42) -> np.ndarray:
    """Generate one synthetic anomalous frame (row streak or hotspot)."""
    from synthetic_frames import generate_synthetic_data
    frames, _ = generate_synthetic_data(
        num_samples=1, img_size=SENSOR_H, anomaly=True, prnu_seed=seed)
    return frames[0]


def inject_sensor_artifacts(frame: np.ndarray, *, rng: np.random.Generator,
                             add_streak: bool = False) -> np.ndarray:
    """
    Overlay PRNU × banding on top of an existing frame without destroying
    structure.  Optionally inject a saturated row streak (anomaly simulation).

    Parameters
    ----------
    frame       : (H, W, 1) float32 in [0, 1].
    rng         : seeded Generator for reproducibility.
    add_streak  : if True, saturate one random row to 1.0.

    Returns modified frame (same shape, same dtype).
    """
    frame = frame.copy()
    h, w = frame.shape[:2]

    # Mild PRNU: ±3.5% per-pixel gain
    prnu = 1.0 + 0.035 * rng.standard_normal((h, w, 1)).astype(np.float32)
    prnu = np.clip(prnu, 0.88, 1.12)
    frame = np.clip(frame * prnu, 0.0, 1.0)

    # Horizontal banding: low-amplitude sinusoidal row bias
    row_bias = (0.02 * np.sin(np.linspace(0.0, 6.28, h, dtype=np.float32))
                .reshape(h, 1, 1))
    frame = np.clip(frame + row_bias, 0.0, 1.0)

    if add_streak:
        row = int(rng.integers(0, h))
        frame[row, :, 0] = 1.0
        print(f"[ACQ] Anomaly artifact injected: saturated row {row}")

    return frame.astype(np.float32)


# ── MSE computation ────────────────────────────────────────────────────────────

def compute_mse_keras(model, frame: np.ndarray) -> float:
    """Run one forward pass of a Keras autoencoder and return MSE."""
    x = frame.reshape(1, SENSOR_H, SENSOR_W, 1)
    recon = model.predict(x, verbose=0)
    return float(np.mean(np.square(x - recon)))


def compute_mse_tflite(tflite_path: Path, frame: np.ndarray) -> float:
    """Run one forward pass of a TFLite FP32 model and return MSE."""
    tf = _require("tensorflow")
    interp = tf.lite.Interpreter(model_path=str(tflite_path))
    interp.allocate_tensors()
    in_det  = interp.get_input_details()[0]
    out_det = interp.get_output_details()[0]

    x = frame.reshape(in_det["shape"]).astype(np.float32)
    interp.set_tensor(in_det["index"], x)
    interp.invoke()
    recon = interp.get_tensor(out_det["index"])
    return float(np.mean(np.square(x - recon)))


def heuristic_score(frame: np.ndarray) -> float:
    """
    Replicate the C++ heuristic: bright-pixel count × 10 / n_pixels.
    Threshold is read from obc_model_meta.json key 'heuristic_threshold'
    (default 0.05).
    """
    flat = frame.flatten()
    return float(np.sum(flat > 0.9) * 10.0 / len(flat))


# ── Threshold loading ──────────────────────────────────────────────────────────

def load_meta(meta_path: Path | None = None) -> dict:
    """Load obc_model_meta.json; return empty dict if not found."""
    if meta_path is None:
        meta_path = _HERE / "obc_model_meta.json"
    if meta_path.is_file():
        with open(meta_path, encoding="utf-8") as f:
            return json.load(f)
    print(f"[ACQ] obc_model_meta.json not found at {meta_path}; using defaults.",
          file=sys.stderr)
    return {}


# ── Telemetry output ───────────────────────────────────────────────────────────

def emit_telemetry(cycle_id: str, anomaly: bool, mse: float,
                   threshold: float, backend: str, source: str) -> None:
    """Print a JSON telemetry line matching the OBC schema + acquisition metadata."""
    record = {
        "telemetry_schema": "sentry_sat.obc.v1",
        "cycle_id":         cycle_id,
        "anomaly":          anomaly,
        "reconstruction_mse": round(mse, 8),
        "threshold":        round(threshold, 8),
        "inference_backend": backend,
        "acquisition_source": source,
        "signature_hex":    "n/a (python-sim)",  # no PUF in Python path
    }
    print("[json] " + json.dumps(record))


# ── ASCII visualisation of the 28×28 frame ────────────────────────────────────

_ASCII_RAMP = " .:-=+*#%@"

def frame_to_ascii(frame: np.ndarray, width: int = 28) -> str:
    """
    Render a (28, 28, 1) float32 frame as a compact ASCII art block.
    Each pixel maps to one character from a 10-level ramp.
    Two characters per pixel horizontally compensate for terminal aspect ratio.
    """
    h, w = frame.shape[:2]
    step_x = max(1, w // width)
    lines = []
    for r in range(0, h, 1):
        row_chars = []
        for c in range(0, w, step_x):
            val = float(frame[r, c, 0])
            idx = min(int(val * (len(_ASCII_RAMP) - 1)), len(_ASCII_RAMP) - 1)
            row_chars.append(_ASCII_RAMP[idx] * 2)
        lines.append("".join(row_chars))
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate an OBC sensor acquisition (28×28 patch, anomaly detection)")
    parser.add_argument("--image",          type=Path, default=None,
                        help="Path to input image (PNG/JPG/…). "
                             "If omitted, a synthetic frame is generated.")
    parser.add_argument("--model",          type=Path, default=_HERE / "autoencoder.h5",
                        help="Trained Keras autoencoder (.h5). Default: autoencoder.h5")
    parser.add_argument("--tflite",         type=Path, default=None,
                        help="TFLite FP32 flatbuffer. Overrides --model if present.")
    parser.add_argument("--meta",           type=Path, default=None,
                        help="Path to obc_model_meta.json (auto-detected if omitted).")
    parser.add_argument("--inject-anomaly", action="store_true",
                        help="Inject a saturated-row artifact on top of the loaded frame.")
    parser.add_argument("--seed",           type=int, default=42,
                        help="RNG seed for synthetic frames and artifact injection.")
    parser.add_argument("--cycle-id",       type=str, default=None,
                        help="Cycle identifier in telemetry (auto-generated if omitted).")
    parser.add_argument("--ascii",          action="store_true",
                        help="Print an ASCII art preview of the acquired frame.")
    parser.add_argument("--no-model",       action="store_true",
                        help="Skip model loading; use heuristic scoring only.")
    parser.add_argument("--emit-frame-rows", action="store_true",
                        help="Print raw float rows prefixed [FRAME-ROW] for TUI frame panel.")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    meta = load_meta(args.meta)

    # ── 1. Acquire frame ──────────────────────────────────────────────────────
    if args.image is not None:
        if not args.image.is_file():
            print(f"[ERROR] Image not found: {args.image}", file=sys.stderr)
            sys.exit(1)
        print(f"[ACQ] Loading image: {args.image}")
        frame = load_image_as_frame(args.image)
        source = str(args.image)
        frame = inject_sensor_artifacts(frame, rng=rng,
                                        add_streak=args.inject_anomaly)
    else:
        if args.inject_anomaly:
            print("[ACQ] Generating synthetic ANOMALY frame (seed={})".format(args.seed))
            frame  = synthetic_anomaly_frame(args.seed)
            source = f"synthetic_anomaly(seed={args.seed})"
        else:
            print("[ACQ] Generating synthetic NOMINAL frame (seed={})".format(args.seed))
            frame  = synthetic_nominal_frame(args.seed)
            source = f"synthetic_nominal(seed={args.seed})"
        frame = inject_sensor_artifacts(frame, rng=rng, add_streak=False)

    print(f"[ACQ] Frame shape: {frame.shape}  min={frame.min():.4f} "
          f"max={frame.max():.4f}  mean={frame.mean():.4f}")

    if args.ascii:
        print("\n[ACQ] Frame preview (ASCII):")
        print(frame_to_ascii(frame))
        print()

    # Emit machine-readable row data for the TUI frame panel.
    # Each line: [FRAME-ROW] f0 f1 … f27  (28 float values, one row of the frame)
    if args.emit_frame_rows:
        flat = frame.flatten().tolist()
        for row_idx in range(SENSOR_H):
            row_vals = flat[row_idx * SENSOR_W : (row_idx + 1) * SENSOR_W]
            print("[FRAME-ROW] " + " ".join(f"{v:.6f}" for v in row_vals))

    # ── 2. Run inference ──────────────────────────────────────────────────────
    cycle_id = args.cycle_id or f"PY-{int(time.time())}"

    if args.no_model:
        mse      = heuristic_score(frame)
        backend  = "heuristic_linear"
        threshold = float(meta.get("heuristic_threshold", 0.05))

    elif args.tflite is not None and args.tflite.is_file():
        print(f"[ACQ] Running TFLite FP32 model: {args.tflite}")
        mse      = compute_mse_tflite(args.tflite, frame)
        backend  = "tflite_fp32"
        threshold = float(meta.get("mse_threshold", 0.05))

    elif args.model.is_file():
        tf = _require("tensorflow")
        print(f"[ACQ] Loading Keras model: {args.model}")
        model    = tf.keras.models.load_model(str(args.model), compile=False)
        mse      = compute_mse_keras(model, frame)
        backend  = "keras_fp32"
        threshold = float(meta.get("mse_threshold", 0.05))

    else:
        print("[ACQ] No model found — falling back to heuristic scoring.")
        print(f"      (looked for: {args.model}, tflite: {args.tflite})")
        mse      = heuristic_score(frame)
        backend  = "heuristic_linear"
        threshold = float(meta.get("heuristic_threshold", 0.05))

    anomaly = mse > threshold

    # ── 3. Report ─────────────────────────────────────────────────────────────
    status = "[ANOMALY DETECTED]" if anomaly else "[nominal]"
    print(f"[ACQ] {status}  score={mse:.6f}  threshold={threshold:.6f}  "
          f"backend={backend}  cycle={cycle_id}")
    emit_telemetry(cycle_id, anomaly, mse, threshold, backend, source)


if __name__ == "__main__":
    main()
