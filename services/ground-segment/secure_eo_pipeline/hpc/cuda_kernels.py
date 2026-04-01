"""
HPC CUDA Kernels Module for SentryGround-Zero.

Implements:
- GPU-accelerated orbital propagation
- Parallel constellation simulation
- FFT-based signal processing
- Matrix operations for ML inference
- Monte Carlo simulations

Note: This module provides Python bindings and fallbacks.
For actual CUDA, install cupy: pip install cupy-cuda12x
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, Callable, Union
import numpy as np


# =============================================================================
# TRY TO IMPORT CUPY (CUDA), FALL BACK TO NUMPY
# =============================================================================

try:
    import cupy as cp  # type: ignore[import]
    HAS_CUPY = True
except ImportError:
    cp = np  # type: ignore[assignment]
    HAS_CUPY = False


def _to_numpy(arr):
    """Convert array to numpy array (no-op if already numpy)."""
    if HAS_CUPY and hasattr(arr, 'to_numpy'):
        return arr.to_numpy()  # type: ignore[union-attr]
    return arr


# =============================================================================
# ORBITAL PROPAGATION KERNELS
# =============================================================================

GM_EARTH = 3.986004418e14
R_EARTH = 6.378137e6
NUMPY_DTYPE = np.float64


def propagate_orbits_gpu(
    states: np.ndarray,
    dt_s: float,
    n_steps: int = 1
) -> np.ndarray:
    """
    Propagate multiple orbital states in parallel using GPU.
    
    Args:
        states: Array of shape (N, 6) with [x, y, z, vx, vy, vz] in ECI (km, km/s)
        dt_s: Time step in seconds
        n_steps: Number of integration steps
    
    Returns:
        Propagated states of same shape
    """
    if HAS_CUPY:
        xp = cp
        states_gpu = xp.asarray(states, dtype=xp.float64)
    else:
        xp = np
        states_gpu = states.astype(NUMPY_DTYPE)
    
    for _ in range(n_steps):
        r = xp.sqrt(states_gpu[:, 0]**2 + states_gpu[:, 1]**2 + states_gpu[:, 2]**2)
        
        a = -GM_EARTH / (r**3)
        
        states_gpu[:, 3:6] += a * states_gpu[:, :3] * dt_s
        
        states_gpu[:, 0:3] += states_gpu[:, 3:6] * dt_s
    
    if HAS_CUPY:
        return _to_numpy(states_gpu)
    return states_gpu


def compute_ground_tracks_gpu(
    states: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    times_s: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute which ground stations can see which satellites at which times.
    
    Args:
        states: (N, 6) orbital states in ECI
        lats: Ground station latitudes (deg)
        lons: Ground station longitudes (deg)
        times_s: Times to evaluate
    
    Returns:
        (visible_mask, elevations) arrays
    """
    if HAS_CUPY:
        xp = cp
        states_gpu = xp.asarray(states, dtype=xp.float64)
        lats_gpu = xp.asarray(lats, dtype=xp.float64)
        lons_gpu = xp.asarray(lons, dtype=xp.float64)
    else:
        xp = np
        states_gpu = states.astype(NUMPY_DTYPE)
        lats_gpu = lats.astype(NUMPY_DTYPE)
        lons_gpu = lons.astype(NUMPY_DTYPE)
    
    n_sats, n_gs = len(states_gpu), len(lats_gpu)
    
    visible = xp.zeros((n_sats, n_gs), dtype=xp.bool_)
    elevations = xp.zeros((n_sats, n_gs), dtype=xp.float64)
    
    r_mag = xp.sqrt(states_gpu[:, 0]**2 + states_gpu[:, 1]**2 + states_gpu[:, 2]**2)
    
    for i in range(n_gs):
        lat_rad = xp.deg2rad(lats_gpu[i])
        lon_rad = xp.deg2rad(lons_gpu[i])
        
        gs_x = (R_EARTH + 0) * xp.cos(lat_rad) * xp.cos(lon_rad)
        gs_y = (R_EARTH + 0) * xp.cos(lat_rad) * xp.sin(lon_rad)
        gs_z = (R_EARTH + 0) * xp.sin(lat_rad)
        
        dr_x = states_gpu[:, 0] - gs_x
        dr_y = states_gpu[:, 1] - gs_y
        dr_z = states_gpu[:, 2] - gs_z
        dr_mag = xp.sqrt(dr_x**2 + dr_y**2 + dr_z**2)
        
        dot = (states_gpu[:, 0] * gs_x + states_gpu[:, 1] * gs_y + states_gpu[:, 2] * gs_z) / (r_mag * R_EARTH)
        
        elev_rad = xp.arcsin(xp.clip(dot, -1, 1))
        elevations[:, i] = xp.rad2deg(elev_rad)
        visible[:, i] = elev_rad > xp.deg2rad(5.0)
    
    if HAS_CUPY:
        return _to_numpy(visible), _to_numpy(elevations)
    return visible, elevations


def parallel_fft_spectra(signals: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute FFT of multiple signals in parallel.
    
    Args:
        signals: (N, M) array of N signals of length M
    
    Returns:
        (frequencies, power_spectra)
    """
    if HAS_CUPY:
        xp = cp
        signals_gpu = xp.asarray(signals, dtype=xp.complex128)
    else:
        xp = np
        signals_gpu = signals.astype(np.complex128)
    
    spectra = xp.fft.rfft(signals_gpu, axis=1)
    power = xp.abs(spectra) ** 2
    
    freqs = xp.fft.rfftfreq(signals.shape[1])
    
    if HAS_CUPY:
        return _to_numpy(freqs), _to_numpy(power)
    return freqs, power


# =============================================================================
# MATRIX OPERATIONS FOR ML
# =============================================================================

def batch_matrix_multiply(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """
    Batch matrix multiplication.
    
    Args:
        A: (batch, m, k)
        B: (batch, k, n)
    
    Returns:
        (batch, m, n)
    """
    if HAS_CUPY:
        A_gpu = cp.asarray(A, dtype=cp.float32)
        B_gpu = cp.asarray(B, dtype=cp.float32)
        C_gpu = cp.einsum('bik,bkj->bij', A_gpu, B_gpu)
        return _to_numpy(C_gpu)
    
    return np.einsum('bik,bkj->bij', A, B)


def batch_conv2d(images: np.ndarray, kernels: np.ndarray, 
                 stride: int = 1, padding: int = 0) -> np.ndarray:
    """
    2D convolution for batch of images.
    
    Args:
        images: (batch, height, width, channels)
        kernels: (out_channels, kH, kW, in_channels)
        stride: Convolution stride
        padding: Zero padding
    
    Returns:
        Convolved features (batch, out_h, out_w, out_channels)
    """
    if HAS_CUPY:
        images_gpu = cp.asarray(images, dtype=cp.float32)
        kernels_gpu = cp.asarray(kernels, dtype=cp.float32)
        out = cp.einsum('bhwc,oklc->bohwk', images_gpu, kernels_gpu)
        
        if stride > 1:
            out = out[:, :, ::stride, ::stride]
        if padding > 0:
            out = out[:, padding:-padding, padding:-padding, :]
        
        return _to_numpy(out)
    
    B, H, W, C = images.shape
    K, kH, kW, _ = kernels.shape
    
    out_h = (H - kH + 2 * padding) // stride + 1
    out_w = (W - kW + 2 * padding) // stride + 1
    
    output = np.zeros((B, out_h, out_w, K), dtype=np.float32)
    
    for b in range(B):
        for o in range(K):
            for i in range(out_h):
                for j in range(out_w):
                    h_start = i * stride - padding
                    w_start = j * stride - padding
                    
                    patch = images[b, 
                                  h_start:h_start+kH, 
                                  w_start:w_start+kW, :]
                    
                    if patch.shape == (kH, kW, C):
                        output[b, i, j, o] = np.sum(patch * kernels[o])
    
    return output


# =============================================================================
# MONTE CARLO SIMULATIONS
# =============================================================================

def monte_carlo_integration(
    func: Callable,
    n_samples: int,
    bounds: list,
    n_parallel: int = 1000
) -> Tuple[float, float]:
    """
    Monte Carlo integration with GPU acceleration.
    
    Args:
        func: Function to integrate
        n_samples: Number of samples
        bounds: List of (min, max) for each dimension
        n_parallel: Samples per batch
    
    Returns:
        (integral, error_estimate)
    """
    n_dims = len(bounds)
    
    if HAS_CUPY:
        rng = cp.random.default_rng()
    else:
        rng = np.random.default_rng()
    
    total = 0.0
    total_sq = 0.0
    
    volume = 1.0
    for d, (low, high) in enumerate(bounds):
        volume *= (high - low)
    
    for _ in range(n_samples // n_parallel):
        samples = np.zeros((n_parallel, n_dims))
        
        for d, (low, high) in enumerate(bounds):
            if HAS_CUPY:
                samples[:, d] = rng.uniform(low, high, size=n_parallel)
            else:
                samples[:, d] = rng.uniform(low, high, size=n_parallel)
        
        if HAS_CUPY:
            samples_gpu = cp.asarray(samples, dtype=cp.float64)
            values = func(samples_gpu)
            if hasattr(values, 'get'):
                values = values.get()
        else:
            values = func(samples)
        
        total += np.sum(values)
        total_sq += np.sum(values ** 2)
    
    mean = total / n_samples
    variance = total_sq / n_samples - mean ** 2
    error = np.sqrt(variance / n_samples) * volume
    
    return mean * volume, error


# =============================================================================
# REDUCTION OPERATIONS
# =============================================================================

def parallel_sum(arr: np.ndarray, axis: int = 0) -> np.ndarray:
    """Parallel sum reduction."""
    if HAS_CUPY:
        arr_gpu = cp.asarray(arr, dtype=cp.float64)
        return _to_numpy(cp.sum(arr_gpu, axis=axis))
    return np.sum(arr, axis=axis)


def parallel_max(arr: np.ndarray, axis: int = 0) -> np.ndarray:
    """Parallel max reduction."""
    if HAS_CUPY:
        arr_gpu = cp.asarray(arr, dtype=cp.float64)
        return _to_numpy(cp.max(arr_gpu, axis=axis))
    return np.max(arr, axis=axis)


def parallel_mean_std(arr: np.ndarray, axis: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    """Parallel mean and standard deviation."""
    if HAS_CUPY:
        arr_gpu = cp.asarray(arr, dtype=cp.float64)
        mean_val = _to_numpy(cp.mean(arr_gpu, axis=axis))
        std_val = _to_numpy(cp.std(arr_gpu, axis=axis))
        return mean_val, std_val
    
    return np.mean(arr, axis=axis), np.std(arr, axis=axis)


# =============================================================================
# N-BODY SIMULATION
# =============================================================================

def nbody_simulation(
    masses: np.ndarray,
    positions: np.ndarray,
    velocities: np.ndarray,
    dt: float,
    n_steps: int,
    G: float = 6.67430e-11
) -> Tuple[np.ndarray, np.ndarray]:
    """
    N-body gravitational simulation using leapfrog integration.
    
    Args:
        masses: (N,) mass in kg
        positions: (N, 3) position in m
        velocities: (N, 3) velocity in m/s
        dt: Time step in seconds
        n_steps: Number of integration steps
    
    Returns:
        (final_positions, final_velocities)
    """
    N = len(masses)
    
    if HAS_CUPY:
        xp = cp
        masses_gpu = cp.asarray(masses, dtype=cp.float64)
        pos = cp.asarray(positions, dtype=cp.float64)
        vel = cp.asarray(velocities, dtype=cp.float64)
    else:
        xp = np
        masses_gpu = masses.astype(NUMPY_DTYPE)
        pos = positions.astype(NUMPY_DTYPE)
        vel = velocities.astype(NUMPY_DTYPE)
    
    for step in range(n_steps):
        acc = xp.zeros((N, 3), dtype=xp.float64)
        
        for i in range(N):
            for j in range(N):
                if i != j:
                    r_vec = pos[j] - pos[i]
                    r_mag = xp.sqrt(xp.sum(r_vec**2)) + 1e-10
                    acc[i] += G * masses_gpu[j] * r_vec / (r_mag**3)
        
        vel += acc * dt * 0.5
        pos += vel * dt
        vel += acc * dt * 0.5
    
    if HAS_CUPY:
        return _to_numpy(pos), _to_numpy(vel)
    return pos, vel


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def has_gpu() -> bool:
    """Check if GPU (CUDA) is available."""
    return HAS_CUPY


def gpu_info() -> dict:
    """Get GPU information."""
    if HAS_CUPY:
        device = cp.cuda.Device()  # type: ignore[attr-defined]
        props = cp.cuda.runtime.getDeviceProperties(device.id)  # type: ignore[attr-defined]
        return {
            'name': props['name'].decode(),
            'compute_units': props['multiProcessorCount'],
            'memory_mb': props['totalGlobalMem'] / (1024**2),
            'cuda_version': cp.cuda.runtime.runtimeGetVersion(),  # type: ignore[attr-defined]
        }
    return {'gpu_available': False}


def synchronize_gpu():
    """Synchronize GPU operations."""
    if HAS_CUPY:
        cp.cuda.Stream.null.synchronize()  # type: ignore[attr-defined]
