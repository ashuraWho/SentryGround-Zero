# Export full-float32 TFLite for embedded C++ Interpreter (no INT8 calibration).
from __future__ import annotations

import argparse

import tensorflow as tf

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="autoencoder.h5", help="Trained Keras weights")
    parser.add_argument("--out", default="anomaly_model_fp32.tflite", help="Output flatbuffer path")
    args = parser.parse_args()

    print("Loading model…")
    model = tf.keras.models.load_model(args.model)

    print("Converting to float32 TFLite…")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = []  # no quantization
    tflite_model = converter.convert()

    with open(args.out, "wb") as f:
        f.write(tflite_model)
    print(f"Saved {args.out}")
