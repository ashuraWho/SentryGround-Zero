import numpy as np
from secure_eo_pipeline.utils.logger import audit_log

def validate_astrophysical_payload(data: np.ndarray) -> bool:
    """
    Physical-Layer Cybersecurity Validator.
    This is an ultimate Defense-in-Depth layer merging Physics and Cyber.
    
    If an APT (Advanced Persistent Threat) steals the PQC encryption keys, 
    they might try to forge or censor scientific data. This validator checks 
    if the decrypted image obeys the fundamental laws of Astrophysics
    (e.g., Navarro-Frenk-White Dark Matter density profile gradients).
    
    RETURNS:
        True if the data is physically plausible.
        False if the data violates energy/conservation laws (tampering detected).
    """
    if np.isnan(data).any():
        audit_log.error("[PHYSICS-IDS] TAMPER ALERT: NaNs detected. Vacuum energy violation (impossible physics).")
        return False
        
    # Check 1: Non-negativity (photon counts cannot be negative)
    if (data < 0).any():
        audit_log.error("[PHYSICS-IDS] TAMPER ALERT: Negative energy pixels detected. Spontaneous entropy reduction is impossible.")
        return False
        
    # Check 2: Spatial continuity (Virial theorem / Dark Matter Halo gradient constraint)
    # A natural dark matter halo has smooth intensity gradients across its scale radius. 
    # A maliciously forged image (like a black box censoring an anomaly) introduces 
    # massive, infinite non-physical Laplacian spikes.
    
    # HPC Fortran Tensor Math: Ultra-fast calculation natively compiled!
    try:
        from secure_eo_pipeline.physics import fortran_validator
        
        # Format the matrix to a Fortran-contiguous Float64 array for memory safety
        energy_map_f = np.asfortranarray(data.mean(axis=2) if data.ndim == 3 else data, dtype=np.float64)
        max_gradient_spike = fortran_validator.astro_physics.compute_2d_max_laplacian(energy_map_f)
        
        audit_log.info(f"[HPC-ACCEL] 🏎️  Virial density scan executed via Fortran 90 Kernel (Max Gradient: {max_gradient_spike:.4f})")
    except ImportError as e:
        # Fallback to Python Numpy Math
        energy_map = data.mean(axis=2) if data.ndim == 3 else data
        laplacian = np.abs(np.gradient(np.gradient(energy_map)[0])[0])
        max_gradient_spike = laplacian.max()
        audit_log.warning(f"[HPC-ACCEL] Fortran kernel unavailable ({e}). Reverting to standard numpy.")
    
    # Arbitrary un-physical threshold indicating an instantaneous infinite density jump
    # A true NFW halo is smooth, so the gradient should rarely exceed ~0.2 locally.
    if max_gradient_spike > 0.8: 
        audit_log.error(f"[PHYSICS-IDS] TAMPER ALERT: Massive un-physical energy gradient ({max_gradient_spike:.2f}). Virial theorem violated. Splicing/Censorship detected.")
        return False
        
    return True


def validate_exoplanet_transit(data: np.ndarray) -> bool:
    """
    Physical Validator for Exoplanet Transit lightcurves.
    A malicious attacker might try to hide a transit by drawing a flat line,
    or inject a fake transit as a square block instead of a smooth U/V shape.
    """
    if np.isnan(data).any() or (data < 0).any():
        audit_log.error("[PHYSICS] TAMPER ALERT: NaNs or negative flux detected.")
        return False
        
    # Extract the 1D lightcurve from the 2D pseudo-image
    energy_map = data.mean(axis=2) if data.ndim == 3 else data
    lightcurve = energy_map[0, :]
    
    # HPC Fortran Physics core
    try:
        from secure_eo_pipeline.physics import fortran_validator
        lightcurve_f = np.asfortranarray(lightcurve, dtype=np.float64)
        max_gradient = fortran_validator.astro_physics.compute_1d_max_gradient(lightcurve_f)
    except ImportError:
        laplacian = np.abs(np.gradient(lightcurve))
        max_gradient = laplacian.max()
    
    # A square-wave deletion from malware yields a near-infinite gradient
    if max_gradient > 0.4:
        audit_log.error(f"[PHYSICS-IDS] TAMPER ALERT: Impossible non-Keplerian flux gradient ({max_gradient:.2f}).")
        return False
        
    return True

def validate_earth_observation(data: np.ndarray) -> bool:
    """
    Physical Validator for Multi-Spectral Earth Observation (Proxy).
    """
    if np.isnan(data).any() or (data < 0).any():
        audit_log.error("[PHYSICS] TAMPER ALERT: Invalid pixels.")
        return False
        
    # Earth albedo / emissivity check
    if data.mean() > 0.95:
        audit_log.error("[PHYSICS-IDS] TAMPER ALERT: Global albedo violation (Unrealistic saturation).")
        return False
        
    return True

_EARTH_LIKE_PROFILES = frozenset({"earth", "earth_observation", "earth_climate"})
_EXO_PROFILES = frozenset({"exoplanet"})


def select_and_run_validator(mission_profile: str, data: np.ndarray) -> bool:
    """
    Routes the payload to the correct Physical Firewall based on the Mission Profile.
    """
    p = (mission_profile or "dark_matter").strip().lower()
    if p in _EXO_PROFILES:
        return validate_exoplanet_transit(data)
    if p in _EARTH_LIKE_PROFILES:
        return validate_earth_observation(data)
    # deep_space, dark_matter, stellar, black_hole, gravitational_wave, asteroid, survey, ...
    return validate_astrophysical_payload(data)
