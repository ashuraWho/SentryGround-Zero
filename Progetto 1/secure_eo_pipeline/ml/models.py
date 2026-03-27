from typing import Dict, Tuple


def eo_anomaly_score(features: Dict[str, float]) -> Tuple[float, str]:
    """
    Computes a simple anomaly score for EO data based on band statistics.

    For now this is purely threshold-based:
    - If standard deviation is extremely low across all bands, data may be flat/saturated.
    - If means are near 0 or 1, data may be clipped.
    """
    stds = [features["std_band_0"], features["std_band_1"], features["std_band_2"]]
    means = [features["mean_band_0"], features["mean_band_1"], features["mean_band_2"]]

    avg_std = sum(stds) / len(stds)
    avg_mean = sum(means) / len(means)

    score = 0.0
    reasons = []

    if avg_std < 0.02:
        score += 0.6
        reasons.append("very_low_variance")

    if avg_mean < 0.05 or avg_mean > 0.95:
        score += 0.4
        reasons.append("extreme_mean")

    if score == 0.0:
        flag = "OK"
    elif score < 0.5:
        flag = "MILD_ANOMALY"
    else:
        flag = "ANOMALOUS"

    return score, ";".join(reasons) if reasons else "none"


def log_window_anomaly_score(features: Dict[str, float]) -> Tuple[float, str]:
    """
    Very simple anomaly score for a window of log events. Currently:
    - High ratio of failed_logins to events_count
    - Any critical_events present
    """
    events_count = max(features["events_count"], 1.0)
    failed_ratio = features["failed_logins"] / events_count
    critical_events = features["critical_events"]

    score = 0.0
    reasons = []

    if failed_ratio > 0.5:
        score += 0.6
        reasons.append("many_failed_logins")

    if critical_events > 0:
        score += 0.5
        reasons.append("critical_events_present")

    if score == 0.0:
        flag = "OK"
    elif score < 0.5:
        flag = "MILD_ANOMALY"
    else:
        flag = "ANOMALOUS"

    return score, ";".join(reasons) if reasons else "none"

