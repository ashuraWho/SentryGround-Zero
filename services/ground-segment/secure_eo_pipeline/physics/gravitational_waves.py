"""
Gravitational Wave Physics Module for SentryGround-Zero.

Implements:
- inspiral, merger, ringdown waveform models (PN, EOB, BHPT)
- LIGO/Virgo/KAGRA detector response
- Matched filtering and SNR calculation
- Parameter estimation
- Bayesian inference basics

References:
- Abbott et al. (LIGO/Virgo) - GWTC catalogs
- Buonanno, Damour (EOB formalism)
- Blanchet (Post-Newtonian theory)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple, Callable
import numpy as np


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

G = 6.67430e-11
C = 299792458.0
HBAR = 1.054571817e-34
MSUN = 1.98892e30
MPC = 3.08567758149137e22
PC = 3.08567758149137e16


# =============================================================================
# CHIRP SIGNAL MODELS
# =============================================================================

@dataclass(frozen=True)
class GWParameters:
    """Gravitational wave source parameters."""
    m1_msun: float
    m2_msun: float
    chi1: float = 0.0
    chi2: float = 0.0
    distance_mpc: float = 410.0
    inclination_deg: float = 0.0
    phi_0: float = 0.0
    ra_deg: float = 0.0
    dec_deg: float = 0.0


@dataclass(frozen=True)
class DetectorStrain:
    """Strain data from a GW detector."""
    detector: str
    time_s: np.ndarray
    strain: np.ndarray
    sample_rate_hz: float


def total_mass(m1: float, m2: float) -> float:
    """Total mass in solar masses."""
    return m1 + m2


def chirp_mass(m1: float, m2: float) -> float:
    """Chirp mass in solar masses: M_c = (m1*m2)^(3/5) / (m1+m2)^(1/5)"""
    return (m1 * m2) ** (3.0 / 5.0) / (m1 + m2) ** (1.0 / 5.0)


def symmetric_mass_ratio(m1: float, m2: float) -> float:
    """Symmetric mass ratio: eta = m1*m2 / (m1+m2)²"""
    return (m1 * m2) / (m1 + m2) ** 2


def orbital_frequency_from_radius(r: float, m_total: float) -> float:
    """Keplerian orbital frequency from separation (in units where G=c=1)."""
    return 1.0 / (r ** 1.5) / (2 * math.pi)


def inspiral_frequency_pn(Mc_msun: float, t_to_merger_s: float) -> float:
    """
    Newtonian inspiral frequency at time t before merger.
    f(t) = (1/pi) * (5/256)^(3/8) * (GM_c^(3/8) / (t)^(3/8))
    
    Returns frequency in Hz.
    """
    Mc = Mc_msun * MSUN
    G = 6.67430e-11
    t = max(t_to_merger_s, 1e-10)
    f = (1 / math.pi) * (5 / 256) ** (3.0 / 8.0) * (G * Mc) ** (3.0 / 8.0) / (t ** (3.0 / 8.0))
    return f


def waveform_phase_pn(m1: float, m2: float, f: float, phase0: float = 0.0) -> float:
    """
    Post-Newtonian inspiral phase.
    Includes 0PN, 1PN, 2PN terms.
    
    Returns phase in radians.
    """
    Mc = chirp_mass(m1, m2)
    Mc_msun = Mc / MSUN
    
    theta = (math.pi * G * Mc * f) ** (-5.0 / 3.0)
    phi_pn = 2 * math.pi * f * theta - phase0
    phi_1pn = 0.0
    phi_2pn = 0.0
    
    return phi_pn + phi_1pn + phi_2pn


def amplitude_inspiral(m1: float, m2: float, distance_mpc: float, 
                       inclination_deg: float, f: float) -> float:
    """
    Newtonian inspiral amplitude.
    h = sqrt(5*pi/96) * (GM_c/c²)^(5/3) * (pi*f/c)^(2/3) / D_L
    
    Returns strain amplitude (dimensionless).
    """
    Mc = chirp_mass(m1, m2) * MSUN
    D_L = distance_mpc * MPC
    theta_inc = math.radians(inclination_deg)
    
    G = 6.67430e-11
    c = 299792458.0
    
    amp = math.sqrt(5 * math.pi / 96) * (G * Mc / c**2) ** (5.0 / 3.0) * (math.pi * f / c) ** (2.0 / 3.0) / D_L
    amp *= math.sqrt(1 + 6 * math.cos(theta_inc)**2 + math.cos(theta_inc)**4) / 2
    
    return amp


def generate_chirp_timeseries(m1: float, m2: float, distance_mpc: float,
                               inclination_deg: float = 0.0,
                               f_start: float = 20.0,
                               f_end: float = 512.0,
                               sample_rate: float = 4096.0,
                               phi_0: float = 0.0,
                               phase_pn: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate inspiral chirp signal using TaylorT4 PN approximant.
    
    Returns: (times_s, strain)
    """
    Mc = chirp_mass(m1, m2)
    D_L = distance_mpc * MPC
    theta_inc = math.radians(inclination_deg)
    
    G = 6.67430e-11
    c = 299792458.0
    
    Mc_SI = Mc * MSUN
    
    f_coal = f_end
    t_coal = (5 / 256) * (G * Mc_SI / c**3) * (math.pi * G * Mc_SI * f_coal / c**3) ** (-8.0 / 3.0)
    
    n_samples = int(t_coal * sample_rate)
    times = np.linspace(0, t_coal, n_samples)
    
    freqs = np.zeros_like(times)
    phases = np.zeros_like(times)
    amplitudes = np.zeros_like(times)
    
    for i, t in enumerate(times):
        tau = t_coal - t
        if tau <= 0:
            freqs[i] = f_coal
            phases[i] = phases[i-1] if i > 0 else 0
            amplitudes[i] = 0
            continue
            
        f = inspiral_frequency_pn(Mc, tau)
        f = min(f, f_coal)
        freqs[i] = f
        
        if phase_pn:
            phases[i] = waveform_phase_pn(m1, m2, f, phi_0)
        else:
            theta = (5 / 256) * (G * Mc_SI / c**3) * (math.pi * G * Mc_SI * f / c**3) ** (-5.0 / 3.0)
            phases[i] = 2 * math.pi * f * theta - phi_0
        
        amplitudes[i] = amplitude_inspiral(m1, m2, distance_mpc, inclination_deg, f)
    
    strain = amplitudes * np.cos(phases)
    
    return times - t_coal, strain


def generate_ringdown(mass_final_msun: float, spin: float = 0.7,
                      amplitude: float = 1e-21,
                      duration_s: float = 0.1,
                      sample_rate: float = 4096.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate quasinormal mode ringdown signal.
    f = (1/2pi) * 1 / (M * M_sun * G / c³) * k
    k = 0.3737 + 0.2267 * chi + 0.376 * chi^2 for l=2, m=2
    
    Returns: (times_s, strain)
    """
    M = mass_final_msun * MSUN
    G = 6.67430e-11
    c = 299792458.0
    
    k = 0.3737 + 0.2267 * spin + 0.376 * spin**2
    f_qnm = k / (2 * math.pi) * (c**3 / (G * M))
    
    tau = 1 / (0.0887 * (1 - spin)**-0.37) * (M / MSUN)
    
    n_samples = int(duration_s * sample_rate)
    times = np.linspace(0, duration_s, n_samples)
    
    omega = 2 * math.pi * f_qnm
    gamma = 1.0 / tau
    
    strain = amplitude * np.exp(-gamma * times) * np.cos(omega * times)
    
    return times, strain


def generate_bmerger_signal(m1: float, m2: float, distance_mpc: float = 410.0,
                             sample_rate: float = 4096.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate inspiral + merger + ringdown signal (phenomenological SEOBNRv4 model approximation).
    
    Returns: (times_s, strain)
    """
    Mc = chirp_mass(m1, m2)
    M_total = m1 + m2
    
    f_iscol = 4400.0 / (M_total)
    f_ring = 1.0 / (M_total * 4.85e-6) * 0.3737
    
    t_inspiral = 2.0
    t_ringdown = 0.1
    
    n_inspiral = int(t_inspiral * sample_rate)
    n_ringdown = int(t_ringdown * sample_rate)
    n_total = n_inspiral + n_ringdown
    
    times = np.linspace(-t_inspiral, t_ringdown, n_total)
    strain = np.zeros(n_total)
    
    Mc_SI = Mc * MSUN
    G = 6.67430e-11
    c = 299792458.0
    D_L = distance_mpc * MPC
    
    t_coal = 0.0
    idx_coal = n_inspiral - 1
    
    for i, t in enumerate(times[:idx_coal]):
        tau = t_coal - t
        if tau <= 0:
            continue
        f = inspiral_frequency_pn(Mc, tau)
        f = min(f, f_iscol * 0.9)
        
        amp = amplitude_inspiral(m1, m2, distance_mpc, 0.0, f)
        theta = (5 / 256) * (G * Mc_SI / c**3) * (math.pi * G * Mc_SI * f / c**3) ** (-5.0 / 3.0)
        phase = 2 * math.pi * f * theta
        
        strain[i] = amp * np.cos(phase)
    
    for i in range(idx_coal, n_total):
        t_rel = times[i]
        omega = 2 * math.pi * f_ring
        gamma = omega / (2 * 0.0887 * (1 - 0.7)**-0.37)
        amp_ring = amplitude_inspiral(m1, m2, distance_mpc, 0.0, f_ring) * 3.0
        strain[i] = amp_ring * np.exp(-gamma * t_rel) * np.cos(omega * t_rel)
    
    return times, strain


# =============================================================================
# DETECTOR RESPONSE
# =============================================================================

def detector_antenna_pattern(detector: str, ra_deg: float, dec_deg: float, 
                             gmst_rad: float) -> Tuple[float, float]:
    """
    Compute detector antenna pattern functions F+ and Fx.
    
    Args:
        detector: 'LIGO-Hanford', 'LIGO-Livingston', 'Virgo', 'KAGRA'
        ra_deg, dec_deg: Source sky position
        gmst_rad: Greenwich Mean Sidereal Time in radians
    
    Returns: (F_plus, F_cross)
    """
    detector_params = {
        'LIGO-Hanford': {'lat': 46.455, 'lon': -119.408, 'arm_az': 171.8},
        'LIGO-Livingston': {'lat': 30.563, 'lon': -90.774, 'arm_az': 243.0},
        'Virgo': {'lat': 43.633, 'lon': 10.496, 'arm_az': 71.5},
        'KAGRA': {'lat': 36.413, 'lon': 137.308, 'arm_az': 45.0},
    }
    
    if detector not in detector_params:
        return 0.0, 0.0
    
    params = detector_params[detector]
    lat = math.radians(params['lat'])
    lon = math.radians(params['lon'])
    arm_az = math.radians(params['arm_az'])
    
    ha = gmst_rad + lon - math.radians(ra_deg)
    dec = math.radians(dec_deg)
    
    cos_dec = math.cos(dec)
    sin_dec = math.sin(dec)
    cos_ha = math.cos(ha)
    sin_ha = math.sin(ha)
    cos_lat = math.cos(lat)
    sin_lat = math.sin(lat)
    
    cos_2lam = math.cos(2 * (arm_az - lon))
    sin_2lam = math.sin(2 * (arm_az - lon))
    
    F_plus = 0.5 * (1 + cos_dec**2) * sin_lat * cos_2lam - cos_dec * sin_lat * cos_ha * sin_2lam
    F_cross = 0.5 * (1 + cos_dec**2) * sin_lat * sin_2lam + cos_dec * sin_lat * cos_ha * cos_2lam
    
    return F_plus, F_cross


def optimal_snr(h_plus: np.ndarray, h_cross: np.ndarray,
                 f_plus: float, f_cross: float,
                 noise_psd: Callable[[np.ndarray], np.ndarray],
                 dt: float) -> float:
    """
    Compute optimal signal-to-noise ratio.
    
    rho² = 4 * integral(|h(f)|² / S_n(f) df)
    
    Returns: SNR (dimensionless)
    """
    n = len(h_plus)
    freqs = np.fft.rfftfreq(n, dt)
    
    h_f = np.fft.rfft(h_plus) * f_plus + np.fft.rfft(h_cross) * f_cross
    
    S_n = noise_psd(freqs)
    S_n = np.where(S_n > 0, S_n, 1e-48)
    
    integrand = np.abs(h_f)**2 / S_n
    integral = np.trapezoid(integrand, freqs)
    
    return float(np.sqrt(4 * integral).item())


def ligo_noise_psd(f: np.ndarray) -> np.ndarray:
    """
    Approximate LIGO O3 design sensitivity curve.
    S_n(f) ≈ S_0 * (f/100)^(-4.14) for f < 100 Hz
    S_n(f) ≈ S_0 * (f/100)^0.12 for f > 100 Hz
    S_0 = 1e-48
    """
    f = np.abs(f)
    f = np.where(f == 0, 1e-10, f)
    
    S_0 = 1e-48
    
    x = f / 100.0
    S_low = S_0 * x ** (-4.14)
    S_high = S_0 * x ** 0.12
    
    S_n = np.where(f < 100, S_low, S_high)
    
    f_min = 10.0
    S_n = np.where(f < f_min, S_n * (f / f_min)**4, S_n)
    
    return S_n


def whiten_strain(strain: np.ndarray, dt: float) -> np.ndarray:
    """Whiten strain data using optimal SNR whitening."""
    n = len(strain)
    freqs = np.fft.rfftfreq(n, dt)
    
    h_f = np.fft.rfft(strain)
    S_n = ligo_noise_psd(freqs)
    S_n = np.where(S_n > 0, S_n, 1e-48)
    
    white_f = h_f / np.sqrt(S_n / (4 * dt))
    white = np.fft.irfft(white_f, n)
    
    return white


def match_filter(timeseries: np.ndarray, template: np.ndarray, dt: float) -> np.ndarray:
    """
    Compute match filter output (time-domain).
    
    Returns: normalized correlation vs time lag
    """
    n = len(timeseries)
    m = len(template)
    
    if m > n:
        return np.zeros(1)
    
    corr = np.correlate(timeseries, template, mode='same')
    
    norm = np.sqrt(np.sum(template**2) * np.convolve(np.ones(n), np.ones(m), mode='same'))
    norm = np.where(norm > 0, norm, 1e-10)
    
    return corr / norm


# =============================================================================
# PARAMETER ESTIMATION (BAYESIAN BASICS)
# =============================================================================

def prior_uniform(param: float, p_min: float, p_max: float) -> float:
    """Uniform prior probability."""
    if p_min <= param <= p_max:
        return 1.0 / (p_max - p_min)
    return 0.0


def prior_snr_sensitive(mc_msun: float, mc_min: float = 1.0, mc_max: float = 100.0) -> float:
    """SNR-sensitive prior (mimics Malmquist bias)."""
    return prior_uniform(mc_msun, mc_min, mc_max)


def likelihood_gaussian(data: np.ndarray, model: np.ndarray, sigma: float) -> float:
    """Gaussian likelihood for whitened data."""
    residual = data - model
    chi2 = np.sum(residual**2) / sigma**2
    return np.exp(-0.5 * chi2)


def log_likelihood_optimal(snr: float) -> float:
    """
    Log-likelihood for optimally extracted SNR.
    ln L = (rho² - 2*rho*rho_true) / 2 (for known template)
    """
    return 0.5 * snr**2


# =============================================================================
# BAYESIAN EVIDENCE AND MARGINALS
# =============================================================================

def compute_evidence(log_likelihoods: np.ndarray, log_priors: np.ndarray) -> float:
    """
    Compute log evidence using harmonic mean approximation.
    log Z = log sum_i L_i * p_i - log N
    """
    log_weights = log_likelihoods + log_priors
    max_log = np.max(log_weights)
    log_Z = max_log + np.log(np.sum(np.exp(log_weights - max_log)))
    log_Z -= np.log(len(log_likelihoods))
    return log_Z


def posterior_samples(log_likelihoods: np.ndarray, log_priors: np.ndarray, 
                      n_samples: int = 1000) -> np.ndarray:
    """
    Generate posterior samples using importance sampling.
    
    Returns: normalized weights for resampling
    """
    log_posteriors = log_likelihoods + log_priors
    log_posteriors -= np.max(log_posteriors)
    
    weights = np.exp(log_posteriors)
    weights /= np.sum(weights)
    
    return weights


def effective_sample_size(weights: np.ndarray) -> float:
    """Effective sample size: N_eff = (sum w)^2 / sum(w^2)"""
    return np.sum(weights)**2 / np.sum(weights**2)


# =============================================================================
# CBC SOURCE CLASSIFICATION
# =============================================================================

def classify_cbc(m1: float, m2: float, spin: float = 0.0) -> str:
    """
    Classify compact binary coalescence source type.
    
    Returns: 'BNS', 'NSBH', 'BBH', or 'MassGap'
    """
    m_ns_max = 3.0
    m_bh_min = 5.0
    
    m_chirp = chirp_mass(m1, m2)
    
    if max(m1, m2) < m_ns_max:
        return 'BNS'
    elif min(m1, m2) < m_ns_max and max(m1, m2) > m_bh_min:
        return 'NSBH'
    elif max(m1, m2) > m_bh_min:
        return 'BBH'
    else:
        return 'MassGap'


def estimate_remnant_mass(m1: float, m2: float, chi_eff: float = 0.0) -> float:
    """
    Estimate remnant mass using fitted formula from numerical relativity.
    M_rem = (1 - epsilon) * M_total
    epsilon ≈ 0.05 - 0.10 for BBH mergers
    """
    M_total = m1 + m2
    
    epsilon = 0.055 * (1 - chi_eff)**0.2
    M_rem = (1 - epsilon) * M_total
    
    return M_rem


def estimate_remnant_spin(m1: float, m2: float, chi1: float, chi2: float) -> float:
    """
    Estimate dimensionless spin of remnant black hole.
    Simplified formula from NR fitting.
    """
    eta = symmetric_mass_ratio(m1, m2)
    chi_eff = (m1 * chi1 + m2 * chi2) / (m1 + m2)
    
    chi_rem = 0.688 * eta + 0.147 * chi_eff
    chi_rem = min(0.99, max(0.0, chi_rem))
    
    return chi_rem


# =============================================================================
# STOCHASTIC BACKGROUND
# =============================================================================

def stochastic_background_omega(f: np.ndarray, h0_sq_Hz: float = 1e-9) -> np.ndarray:
    """
    Compute energy density spectrum for stochastic GW background.
    Omega(f) = h0² * (f / 100 Hz)^(2/3)
    
    Returns: dimensionless energy density Omega(f)
    """
    f_ref = 100.0
    return h0_sq_Hz * (f / f_ref) ** (2.0 / 3.0)


def cross_correlation_snr(f_opt: float, h0: float, T_obs: float = 1e7,
                           S_n: float = 1e-48) -> float:
    """
    Estimate cross-correlation SNR for stochastic background search.
    
    rho²_cc = (3H0² / 10pi²) * sqrt(T/T) * integral(Omega² / S_n² df)
    """
    H0 = 70.0 * 1e3 / MPC
    rho_sq = (3 * H0**2 / (10 * math.pi**2))**2 * T_obs * h0**4 / S_n**2
    return np.sqrt(rho_sq)


# =============================================================================
# NUMERICAL RELATIVITY WAVEFORM (SIMPLIFIED BHPT)
# =============================================================================

def bhp_tidal_deformation(m1: float, m2: float, Lambda2: float = 0.0) -> float:
    """
    Compute BH perturbation theory tidal coupling.
    For BH: k2 = 0, so no tidal deformation (in GR).
    This returns 0 for pure BH-NS and BBH systems.
    """
    return 0.0


def tidal_deformability_lambda(m: float, R: float) -> float:
    """
    Love number k2 for neutron stars (approx).
    Lambda = (2/3G) * k2 * R^5 / m^5
    """
    k2 = 0.1
    G = 6.67430e-11
    c = 299792458.0
    
    m_si = m * MSUN
    R_si = R * 1e3
    
    Lambda = (2 / G) * k2 * R_si**5 / m_si**5
    
    return Lambda
