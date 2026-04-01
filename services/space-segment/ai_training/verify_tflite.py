# Load a .tflite flatbuffer and run one forward pass to verify interpreter wiring.
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test TFLite model I/O")
    parser.add_argument("--tflite", default="anomaly_model.tflite", type=Path)
    args = parser.parse_args()

    if not args.tflite.is_file():
        raise SystemExit(f"Missing {args.tflite}")

    import tensorflow as tf

    interpreter = tf.lite.Interpreter(model_path=str(args.tflite))
    interpreter.allocate_tensors()
    in_det = interpreter.get_input_details()[0]
    out_det = interpreter.get_output_details()[0]

    shape = tuple(d if d > 0 else 1 for d in in_det["shape"])
    if in_det["dtype"] == np.int8:
        x = np.zeros(shape, dtype=np.int8)
    else:
        x = np.random.randn(*shape).astype(np.float32) * 0.1

    interpreter.set_tensor(in_det["index"], x)
    interpreter.invoke()
    y = interpreter.get_tensor(out_det["index"])
    print("OK — input shape:", shape, "output shape:", y.shape, "dtype:", y.dtype)


if __name__ == "__main__":
    main()
