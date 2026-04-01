"""Ground-side 100×100 modulation mirroring space-segment OBSERVATION_MODE (see sensor_observation.hpp)."""
from __future__ import annotations

import numpy as np


def _clip01(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0.0, 1.0)


def apply_mode_2d(img: np.ndarray, profile: str, mode: str) -> None:
    """In-place modulation on 2D float array [0,1]."""
    if not mode or mode == "default":
        return
    p = (profile or "dark_matter").strip().lower()
    m = mode.strip().lower().replace(" ", "_").replace("-", "_")
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w]

    if p in ("earth", "earth_observation", "earth_climate"):
        if m == "climate":
            img[:] = _clip01(img + 0.12 * np.sin((xx + yy) * 0.35))
        elif m == "vegetation":
            img[:] = _clip01(img + 0.18 * np.sin(xx * 0.45) * np.sin(yy * 0.52))
        elif m == "desert":
            img[:] = _clip01(img * 0.82 + 0.08 * np.sin(yy * 0.7))
        elif m in ("ocean", "sea"):
            img[:] = _clip01(img * 0.35 + 0.45 * np.sin(xx * 0.22) * np.sin(yy * 0.18))
        elif m in ("urban", "cities"):
            g = ((xx % 5) == 0) | ((yy % 5) == 0)
            img[:] = _clip01(img + g.astype(np.float64) * 0.22)

    if p == "earth_climate":
        if m in ("jet_stream", "jet"):
            img[:] = _clip01(img + 0.14 * np.sin((xx + 2 * yy) * 0.31))
        elif m in ("hadley_cell", "hadley"):
            img[:] = _clip01(img + 0.1 * np.sin(yy * 0.25))
        elif m in ("storm_system", "storm"):
            dx, dy = xx - 16, yy - 12
            img[:] = _clip01(img + 0.25 * np.exp(-(dx * dx + dy * dy) / 15.0))
        elif m in ("sea_ice", "ice"):
            mask = (yy < 8) | (yy > 20)
            img[:] = _clip01(img + mask.astype(np.float64) * 0.35)

    if p == "stellar":
        if m == "photosphere":
            img[:] = _clip01(np.power(np.maximum(img, 1e-6), 0.85))
        elif m in ("sunspots", "starspots"):
            d1 = np.sqrt((xx - 36) ** 2 + (yy - 44) ** 2)
            d2 = np.sqrt((xx - 76) ** 2 + (yy - 64) ** 2)
            img[:] = np.where(d1 < 12, img * 0.35, img)
            img[:] = np.where(d2 < 11, img * 0.4, img)
            img[:] = _clip01(img)
        elif m == "luminosity":
            img[:] = _clip01(img * 1.25)
        elif m in ("temperature", "temperature_map"):
            cx = np.abs(xx - w // 2) + np.abs(yy - h // 2)
            img[:] = _clip01(img * (0.55 + 0.45 * (1.0 - cx / max(h, w))))

    if p == "deep_space":
        if m == "galaxy_cluster":
            dx, dy = xx - w // 2, yy - h // 2
            img[:] = _clip01(img + 0.35 * np.exp(-(dx * dx + dy * dy) / 400.0))
        elif m in ("cmb_proxy", "cmb"):
            img[:] = _clip01(img + 0.06 * np.sin(xx * 0.9 + yy * 0.7))
        elif m == "deep_field":
            img[:] = _clip01(img * 1.15)

    if p == "dark_matter":
        if m == "subhalo":
            dx, dy = xx - 72, yy - 32
            img[:] = _clip01(img + 0.25 * np.exp(-(dx * dx + dy * dy) / 180.0))
        elif m in ("merger_stream", "merger"):
            img[:] = _clip01(img + 0.2 * np.exp(-((xx - yy) / 24.0) ** 2))
        elif m in ("nfw_core", "core"):
            dx, dy = xx - w // 2, yy - h // 2
            img[:] = _clip01(img + 0.15 * np.exp(-(dx * dx + dy * dy) / 250.0))

    if p == "exoplanet":
        if m == "transit":
            mask = np.abs(xx - w // 2) < 18
            img[:, :] = np.where(mask, img * 0.55, img)
            img[:] = _clip01(img)
        elif m in ("phase_curve", "phase"):
            img[:] = _clip01(img * (0.75 + 0.25 * np.sin(xx * 0.4)))
        elif m in ("secondary_eclipse", "eclipse"):
            m1 = np.abs(xx - 32) < 12
            m2 = np.abs(xx - 72) < 12
            img[:] = np.where(m1 | m2, img * 0.62, img)
            img[:] = _clip01(img)
        elif m in ("reflection", "glint"):
            g = ((xx + yy) % 7) == 0
            img[:] = _clip01(img + g.astype(np.float64) * 0.35)

    if p == "black_hole":
        r = np.sqrt((xx - w // 2) ** 2 + (yy - h // 2) ** 2)
        if m == "shadow":
            img[:] = np.where(r < 18, img * 0.2, img)
            img[:] = _clip01(img)
        elif m in ("accretion_disk", "disk"):
            ring = (r > 22) & (r < 40)
            img[:] = _clip01(img + ring.astype(np.float64) * 0.25)
        elif m in ("jet_proxy", "jet"):
            jet = np.abs(xx - w // 2) < 8
            img[:] = _clip01(img + jet.astype(np.float64) * 0.3)
        elif m in ("ring_only", "ring"):
            img[:] = np.where(r < 28, img * 0.15, img)
            img[:] = _clip01(img)

    if p == "gravitational_wave":
        t = xx.astype(np.float64) / max(w, 1)
        if m == "ringdown":
            img[:] = _clip01(img + 0.15 * np.sin(t * 25.0) * np.exp(-t * 4.0))
        elif m in ("stochastic_bg", "stochastic"):
            img[:] = _clip01(img + np.random.RandomState(42).rand(*img.shape) * 0.08)

    if p == "asteroid":
        if m == "regolith":
            img[:] = _clip01(img + np.random.RandomState(7).rand(*img.shape) * 0.06)
        elif m == "craters":
            for cx, cy in [(32, 36), (72, 60), (48, 80)]:
                d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
                img[:] = np.where(d < 14, img * 0.45, img)
            img[:] = _clip01(img)
        elif m in ("rotation", "rotation_curve"):
            img[:] = _clip01(img * (0.65 + 0.35 * (xx / max(w, 1))))
        elif m in ("binary_proxy", "binary"):
            d1 = np.sqrt((xx - 40) ** 2 + (yy - 56) ** 2)
            d2 = np.sqrt((xx - 72) ** 2 + (yy - 56) ** 2)
            img[:] = np.where((d1 < 16) | (d2 < 14), _clip01(img + 0.2), img)

    if p == "survey":
        if m == "mosaic":
            g = np.where(xx < w // 2, 1.0, 0.92) * np.where(yy < h // 2, 1.0, 0.88)
            img[:] = _clip01(img * g)
        elif m in ("strip_map", "strips"):
            s = (xx % 6) < 2
            img[:] = _clip01(img * (1.0 + s.astype(np.float64) * 0.12))
        elif m in ("multi_band", "multiband"):
            img[:] = _clip01(img + 0.05 * np.sin(xx * 1.1) * np.cos(yy * 1.05))
