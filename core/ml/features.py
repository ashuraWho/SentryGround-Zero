from typing import Dict

import numpy as np


def extract_eo_features(data: np.ndarray) -> Dict[str, float]:
    """
    Extracts simple summary statistics from EO data suitable for
    basic anomaly/quality scoring.
    """
    # Flatten spatial dimensions but keep all bands
    flat = data.reshape(-1, data.shape[-1])
    means = flat.mean(axis=0)
    stds = flat.std(axis=0)

    return {
        "mean_band_0": float(means[0]),
        "mean_band_1": float(means[1]),
        "mean_band_2": float(means[2]),
        "std_band_0": float(stds[0]),
        "std_band_1": float(stds[1]),
        "std_band_2": float(stds[2]),
    }


def extract_log_window_features(events_count: int, failed_logins: int, critical_events: int) -> Dict[str, float]:
    """
    Very small feature set for log windows. For now, meant to support
    threshold-based anomaly flags.
    """
    return {
        "events_count": float(events_count),
        "failed_logins": float(failed_logins),
        "critical_events": float(critical_events),
    }

