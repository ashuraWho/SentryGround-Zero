# Train a convolutional autoencoder on in-memory simulated satellite sensor frames.
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

# Merge defaults with optional user JSON for reproducible hyperparameters.
from config_loader import load_training_config
# All training images are generated in code (no CSV / external imagery files).
from synthetic_frames import build_dataset_from_config, generate_synthetic_data  # noqa: F401


def build_conv_autoencoder(img_size: int) -> tf.keras.Model:
    # Input matches simulated acquisition patches: (height, width, single channel).
    input_img = tf.keras.Input(shape=(img_size, img_size, 1))
    x = layers.Conv2D(8, (3, 3), activation="relu", padding="same")(input_img)
    x = layers.MaxPooling2D((2, 2), padding="same")(x)
    encoded = layers.Conv2D(4, (3, 3), activation="relu", padding="same")(x)
    x = layers.UpSampling2D((2, 2))(encoded)
    decoded = layers.Conv2D(1, (3, 3), activation="sigmoid", padding="same")(x)
    return models.Model(input_img, decoded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Sentry-Sat autoencoder on synthetic sensor data")
    parser.add_argument("--config", type=str, default=None, help="Path to JSON overriding defaults")
    args = parser.parse_args()

    cfg = load_training_config(args.config)
    tf.random.set_seed(int(cfg["train"].get("random_seed", 42)))

    print("Simulating satellite sensor acquisitions (in-memory, no external images)…")
    x_train, x_test, y_test, img_size = build_dataset_from_config(cfg["data"]["synthetic"])

    print("Building autoencoder…")
    autoencoder = build_conv_autoencoder(img_size)
    autoencoder.compile(optimizer="adam", loss="mse")

    tr = cfg["train"]
    print("Training…")
    autoencoder.fit(
        x_train,
        x_train,
        epochs=int(tr["epochs"]),
        batch_size=int(tr["batch_size"]),
        validation_split=float(tr["validation_split"]),
        verbose=1,
    )

    print("Evaluating…")
    reconstructions = autoencoder.predict(x_test)
    mse = np.mean(np.square(x_test - reconstructions), axis=(1, 2, 3))

    ev = cfg["eval"]
    pct = float(ev["threshold_percentile"])
    n_norm = int(cfg["data"]["synthetic"]["test_normal_samples"])
    threshold = float(np.percentile(mse[:n_norm], pct))
    predictions = (mse > threshold).astype(int)

    from sklearn.metrics import accuracy_score, roc_auc_score

    print(f"Reconstruction MSE threshold (p{pct}): {threshold:.6f}")
    if len(np.unique(y_test)) > 1:
        print(f"Anomaly detection accuracy: {accuracy_score(y_test, predictions) * 100:.2f}%")
        try:
            print(f"ROC-AUC (score=MSE): {roc_auc_score(y_test, mse):.4f}")
        except ValueError:
            pass

    model_path = str(cfg["model"]["model_path"])
    autoencoder.save(model_path)
    print(f"Model saved to {model_path}")

    # OBC/C++ runtime reads this next to the FP32 flatbuffer (after export_tflite_fp32.py).
    ai_root = Path(__file__).resolve().parent
    meta_path = ai_root / "obc_model_meta.json"
    obc_meta = {
        "telemetry_schema": "sentry_sat.obc_meta.v1",
        "img_size": img_size,
        "mse_threshold": threshold,
        "tflite_fp32_relative": "anomaly_model_fp32.tflite",
    }
    meta_path.write_text(json.dumps(obc_meta, indent=2), encoding="utf-8")
    print(f"Wrote {meta_path} (threshold for on-board MSE gate)")
    print("Next: python export_tflite_fp32.py  # then rebuild OBC with -DSENTRY_ENABLE_TFLITE=ON if desired")


if __name__ == "__main__":
    main()
