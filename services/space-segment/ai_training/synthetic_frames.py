"""
Synthetic satellite sensor acquisition (in-memory).

Models a simplified imaging chain: shot noise + multiplicative PRNU (per-pixel gain
mismatch), optional horizontal banding (readout imbalance), and localized defects.
No external files — tensor batches only.
"""
import numpy as np


def _prnu_map(img_size: int, rng: np.random.Generator) -> np.ndarray:
    # Fixed-pattern equivalent: slow-varying gain around 1.0 per detector site.
    g = 1.0 + 0.035 * rng.standard_normal((img_size, img_size, 1)).astype(np.float32)
    return np.clip(g, 0.88, 1.12)


def _horizontal_banding(img_size: int, rng: np.random.Generator, amplitude: float) -> np.ndarray:
    # Low-frequency row-wise offset (clock / amplifier toy model).
    row_bias = amplitude * np.sin(
        np.linspace(0.0, 6.28, img_size, dtype=np.float32).reshape(img_size, 1, 1)
    )
    return row_bias.astype(np.float32)


def generate_synthetic_data(
    num_samples=1000,
    img_size=28,
    anomaly=False,
    *,
    prnu_seed: int | None = None,
    banding_amplitude: float = 0.02,
    dead_column_prob: float = 0.15,
):
    """
    Simulate batches of acquired sensor images (H×W×1), values in ~[0, 1].

    - Nominal: shot × PRNU + banding + optional single dead column (bias strip).
    - Anomaly: adds saturated streak or hotspot on top (external glare / spoof).
    """
    data = []
    labels = []
    for i in range(num_samples):
        seed_i = (901921 + (prnu_seed or 42) * 9973 + i) % (2**32)
        rng = np.random.default_rng(seed_i)
        prnu = _prnu_map(img_size, rng)
        shot = rng.random((img_size, img_size, 1)).astype(np.float32) * 0.175
        band = _horizontal_banding(img_size, rng, banding_amplitude)
        img = np.clip(shot * prnu + band, 0.0, 1.0)

        if rng.random() < dead_column_prob:
            col = int(rng.integers(0, img_size))
            img[:, col : col + 1, 0] = np.clip(img[:, col : col + 1, 0] - 0.08, 0.0, 1.0)

        if anomaly:
            if rng.random() > 0.5:
                row = int(rng.integers(0, img_size))
                img[row, :, 0] = 1.0
            else:
                r, c = rng.integers(1, img_size - 1, 2)
                img[r - 1 : r + 2, c - 1 : c + 2, 0] = 1.0
            labels.append(1)
        else:
            labels.append(0)
        data.append(img)
    return np.array(data, dtype=np.float32), np.array(labels)


def build_dataset_from_config(synthetic_cfg: dict):
    img_size = int(synthetic_cfg["img_size"])
    n_train = int(synthetic_cfg["train_samples"])
    n_tn = int(synthetic_cfg["test_normal_samples"])
    n_ta = int(synthetic_cfg["test_anomaly_samples"])

    x_train, _ = generate_synthetic_data(n_train, img_size=img_size, anomaly=False)
    x_test_norm, y_test_norm = generate_synthetic_data(n_tn, img_size=img_size, anomaly=False)
    x_test_anom, y_test_anom = generate_synthetic_data(n_ta, img_size=img_size, anomaly=True)
    x_test = np.concatenate([x_test_norm, x_test_anom], axis=0)
    y_test = np.concatenate([y_test_norm, y_test_anom], axis=0)
    return x_train, x_test, y_test, img_size
