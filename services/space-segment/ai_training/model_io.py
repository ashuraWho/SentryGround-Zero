# Shared helpers for input tensor shapes derived from a loaded Keras model.
from __future__ import annotations

import numpy as np
import tensorflow as tf

# Synthetic frame generator for conv models matches training distribution.
from synthetic_frames import generate_synthetic_data


def input_rank(model: tf.keras.Model) -> int:
    # len((None, 28, 28, 1)) == 4 for conv; len((None, 42)) == 2 for dense vectors.
    return len(model.input_shape)


def make_calibration_batch(model: tf.keras.Model, n: int = 100) -> np.ndarray:
    # Allocate random nominal tensors in the same layout the model was trained on.
    shp = model.input_shape
    if len(shp) == 4:
        _, h, w, c = shp
        h, w, c = int(h), int(w), int(c)
        # Dark-field noise consistent with synthetic_frames baseline amplitude.
        return (np.random.rand(n, h, w, c).astype(np.float32) * 0.2).astype(np.float32)
    if len(shp) == 2:
        nf = int(shp[1])
        return np.random.rand(n, nf).astype(np.float32) * 0.2
    raise ValueError(f"Unsupported input_shape: {model.input_shape}")


def make_shap_probes(model: tf.keras.Model) -> tuple[np.ndarray, np.ndarray]:
    # Produce one nominal and one corrupted probe for contrastive explanations.
    shp = model.input_shape
    if len(shp) == 4:
        h = int(shp[1])
        xn, _ = generate_synthetic_data(1, img_size=h, anomaly=False)
        xa, _ = generate_synthetic_data(1, img_size=h, anomaly=True)
        return xn, xa
    if len(shp) == 2:
        nfeat = int(shp[1])
        xn = np.random.rand(1, nfeat).astype(np.float32) * 0.2
        xa = xn.copy()
        k = min(max(1, nfeat // 8), nfeat)
        xa[0, :k] = 1.0
        return xn, xa
    raise ValueError(f"Unsupported input_shape: {model.input_shape}")
