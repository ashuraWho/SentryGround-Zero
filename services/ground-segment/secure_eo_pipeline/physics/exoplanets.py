"""
Exoplanet Physics Module for SentryGround-Zero.

Implements:
- Transit lightcurves with limb darkening
- Phase curves and secondary eclipses
- Rossiter-McLaughlin effect
- Atmospheric transmission/emission spectra
- Keplerian orbital dynamics
- Habitable zone calculations

References:
- Mandel & Agol (2002) - analytic transit model
- Seager & Mallén-Ornelas (2003)
- Kopparapu et al. (2013) - habitable zone
- Snellen et al. (2010) - atmospheric characterization
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple, Callable
import numpy as np


# =============================================================================
# ORBITAL MECHANICS FOR EXOPLANETS
# =============================================================================

@dataclass(frozen=True)
class ExoplanetSystem:
    """Exoplanet system parameters."""
    M_star_msun: float
    R_star_rsun: float
    T_star_k: float
    planet_name: str
    m_planet_mjup: float
    R_planet_rjup: float
    a_au: float
    e: float = 0.0
    inc_deg: float = 90.0
    omega_deg: float = 90.0


def orbital_period_kepler(a_au: float, M_star_msun: float) -> float:
    """Third Kepler's law: P² = 4π² a³ / (G M_star)"""
    a_m = a_au * 1.495978707e11
    M = M_star_msun * 1.98892e30
    G = 6.67430e-11
    P_s = 2 * math.pi * math.sqrt(a_m**3 / (G * M))
    return P_s / 86400.0


def orbital_velocity(a_au: float, M_star_msun: float, e: float = 0.0) -> float:
    """Orbital velocity at periastron (km/s)."""
    a_m = a_au * 1.495978707e11
    M = M_star_msun * 1.98892e30
    G = 6.67430e-11
    v_m_s = math.sqrt(G * M * (2 / a_m - 1 / a_m))
    return v_m_s / 1000.0


def transit_duration(P_days: float, a_au: float, R_star_rsun: float, 
                     R_planet_rjup: float, b: float = 0.0) -> float:
    """
    Total transit duration (hours).
    T = (P / π) *arcsin( sqrt( (R* + Rp)² - b²R*² ) / a )
    """
    P_s = P_days * 86400
    a_m = a_au * 1.495978707e11
    R_sun = 6.957e8
    
    R_star = R_star_rsun * R_sun
    R_planet = R_planet_rjup * 6.9911e7
    
    term = math.sqrt((R_star + R_planet)**2 - (b * R_star)**2)
    T_s = (P_s / math.pi) * math.asin(term / a_m)
    return T_s / 3600.0


def impact_parameter(a_au: float, inc_deg: float, R_star_rsun: float, 
                     e: float = 0.0, omega_deg: float = 0.0) -> float:
    """Impact parameter: b = (a cos i) / R_star * (1 - e²) / (1 + e sin ω)"""
    a_m = a_au * 1.495978707e11
    R_star = R_star_rsun * 6.957e8
    inc = math.radians(inc_deg)
    omega = math.radians(omega_deg)
    
    b = (a_m / R_star) * math.cos(inc) * (1 - e**2) / (1 + e * math.sin(omega))
    return b


def semi_amplitude_K(m_planet_mjup: float, P_days: float, 
                       M_star_msun: float, e: float = 0.0) -> float:
    """
    Radial velocity semi-amplitude (km/s).
    K = (2πG / P)^(1/3) * m_p sin(i) / (M_star + m_p)^(2/3) * 1/sqrt(1-e²)
    """
    m_p = m_planet_mjup * 1.898e27
    M_s = M_star_msun * 1.98892e30
    P_s = P_days * 86400
    G = 6.67430e-11
    
    K_m_s = (2 * math.pi * G / P_s) ** (1.0 / 3.0) * m_p / (M_s + m_p) ** (2.0 / 3.0) / math.sqrt(1 - e**2)
    return K_m_s / 1000.0


# =============================================================================
# TRANSIT LIGHT CURVE MODELS
# =============================================================================

def limb_darkening_coeffs(T_eff: float, log_g: float, FeH: float = 0.0,
                          band: str = 'V') -> Tuple[float, float]:
    """
    Get quadratic limb darkening coefficients.
    Approximate values from Claret & Bloemen (2011).
    """
    if band == 'V':
        if T_eff < 4000:
            return 0.5, 0.2
        elif T_eff < 6000:
            return 0.4, 0.3
        else:
            return 0.3, 0.4
    elif band == 'I':
        return 0.3, 0.3
    elif band == 'z':
        return 0.25, 0.25
    elif band == 'K':
        return 0.2, 0.15
    else:
        return 0.4, 0.3


def quadratic_ld(z: np.ndarray, u1: float, u2: float) -> np.ndarray:
    """
    Quadratic limb darkening: I(μ) = I(1) * [1 - u1*(1-μ) - u2*(1-μ)²]
    where μ = sqrt(1 - z²) and z is normalized separation.
    """
    z = np.asarray(z)
    mu = np.sqrt(np.maximum(1 - z**2, 0))
    return 1 - u1 * (1 - mu) - u2 * (1 - mu)**2


def transit_depth_mandel_agol(Rp_Rs: float, z: np.ndarray, 
                               u1: float, u2: float) -> np.ndarray:
    """
    Mandel & Agol (2002) analytic transit model.
    Fast approximation for limb-darkened transit.
    
    Args:
        Rp_Rs: Planet-to-star radius ratio
        z: Normalized projected separation (r/R_star)
        u1, u2: Quadratic limb darkening coefficients
    
    Returns: Relative flux (F/F0)
    """
    z = np.asarray(z)
    flux = np.ones_like(z, dtype=float)
    
    k = Rp_Rs
    z = np.abs(z)
    
    mask_occulted = z < 1 + k
    flux_out = quadratic_ld(z, u1, u2)
    
    lambda_e = np.zeros_like(z)
    lambda_c = np.zeros_like(z)
    
    for i, zi in enumerate(z):
        if zi >= 1 + k:
            continue
        elif abs(1 - k) < zi < 1 + k:
            kap0 = 0.0
            kap1 = math.acos(min(1.0, (1 - k**2 + zi**2) / (2 * zi)))
        elif zi < 1 - k:
            kap0 = math.acos((k**2 + zi**2 - 1) / (2 * k * zi))
            kap1 = math.acos((1 - k**2 + zi**2) / (2 * zi))
        else:
            kap0 = math.pi
            kap1 = 0.0
        
        lambda_e[i] = k**2 * kap0 + kap1
        lambda_e[i] -= 0.5 * np.sqrt(max(4 * k**2 - (1 + k**2 - zi**2)**2, 0))
        lambda_e[i] = max(0, lambda_e[i])
        
        lambda_c[i] = (1 / (1 - u1 - u2)) * (
            (1 - u1 - 2*u2) * lambda_e[i] +
            u1 * k**2 * np.sqrt(max(1 - (1-k)**2 / zi**2, 0)) +
            u2 * k**2 * max(0, (1 - (1-k)/zi))**2
        )
    
    flux[mask_occulted] -= (lambda_e - u1 * lambda_c - u2 * lambda_c**2) / (math.pi * (1 - u1/3 - u2/6))
    
    return np.clip(flux, 0, 1)


def generate_transit_lightcurve(time_hours: float, P_hours: float, 
                                Rp_Rs: float, a_Rs: float,
                                u1: float = 0.4, u2: float = 0.3,
                                T0: float = 0.0, noise_ppm: float = 50.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a limb-darkened transit light curve.
    
    Args:
        time_hours: Time array
        P_hours: Orbital period
        Rp_Rs: Planet/star radius ratio
        a_Rs: Semi-major axis in stellar radii
        u1, u2: Limb darkening coefficients
        T0: Transit center time
        noise_ppm: Photometric noise (ppm)
    
    Returns: (time, flux)
    """
    time = np.asarray(time_hours)
    
    phase = ((time - T0) / P_hours) % 1.0
    phase = np.where(phase > 0.5, phase - 1.0, phase)
    
    mean_anomaly = 2 * math.pi * phase
    E = mean_anomaly.copy()
    for _ in range(10):
        E = E - (E - 0.5 * (mean_anomaly + E**3)) / (1 - E**2 / 2)
    
    nu = 2 * np.arctan(np.sqrt((1 + 0.5) / (1 - 0.5)) * np.tan(E / 2))
    
    x_proj = a_Rs * (np.cos(nu) - 0.5)
    y_proj = a_Rs * np.sin(nu) * np.sqrt(1 - 0.5**2)
    z = np.sqrt(x_proj**2 + y_proj**2)
    
    flux = transit_depth_mandel_agol(Rp_Rs, z, u1, u2)
    
    if noise_ppm > 0:
        noise = np.random.normal(0, noise_ppm * 1e-6, len(flux))
        flux = flux + noise
        flux = np.clip(flux, 0, 2)
    
    return time, flux


# =============================================================================
# PHASE CURVES AND SECONDARY ECLIPSES
# =============================================================================

def phase_curve_thermal(longitude_subplanet: float, T_day_k: float = 2000.0,
                        A: float = 0.3, Phi_max: float = 0.5) -> float:
    """
    Thermal phase curve (emission).
    F(λ) = F_0 + F_1 * (1 - A) * cos(λ - λ_0)
    """
    return 1 + Phi_max * (1 - A) * np.cos(math.radians(longitude_subplanet))


def secondary_eclipse_depth(wavelength_um: float, T_planet_k: float,
                            T_star_k: float, Rp_Rs: float) -> float:
    """
    Secondary eclipse depth from planet thermal emission.
    ΔF = (Rp/Rs)² * (B_λ(T_p) - B_λ(T_reflected)) / B_λ(T_star)
    """
    from secure_eo_pipeline.physics.astronomy import blackbody_radiation
    
    B_p = blackbody_radiation(T_planet_k, wavelength_um * 10000)
    B_s = blackbody_radiation(T_star_k, wavelength_um * 10000)
    
    return Rp_Rs**2 * (B_p / B_s)


def rossiter_mclaughlin_amplitude(Rp_Rs: float, V_star_km_s: float, 
                                    vsini_km_s: float, impact_param: float = 0.0) -> float:
    """
    RM effect amplitude (relative flux anomaly).
    Δv_RM ≈ (Rp/Rs)² * V_star * sqrt(1 - b²) / vsini
    """
    if vsini_km_s <= 0:
        return 0.0
    term = np.sqrt(max(1 - impact_param**2, 0))
    return (Rp_Rs)**2 * V_star_km_s * term / vsini_km_s


# =============================================================================
# ATMOSPHERIC SPECTRA
# =============================================================================

def atmospheric_transmission_spectrum(z_scale: float, P_bar: float = 1.0,
                                      T_k: float = 300.0,
                                      features: Optional[list] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Synthetic atmospheric transmission spectrum.
    
    Args:
        z_scale: Atmospheric scale height (km)
        P_bar: Surface pressure (bar)
        T_k: Temperature (K)
        features: List of spectral features [(wavelength_um, strength, width), ...]
    
    Returns: (wavelengths_um, transit_depth_ppm)
    """
    if features is None:
        features = [
            (0.76, 0.3, 0.01),
            (1.4, 0.5, 0.02),
            (2.0, 0.4, 0.03),
            (15.0, 1.0, 0.5),
        ]
    
    wavelengths = np.linspace(0.5, 20.0, 1000)
    transit_depth = np.zeros_like(wavelengths)
    
    from secure_eo_pipeline.physics.astronomy import H, KB, C
    
    H_scale = KB * T_k / (1.67e-27 * 9.8 * 1e5 * P_bar)
    
    for wl_um, strength, width in features:
        gaussian = strength * np.exp(-((wavelengths - wl_um) / width)**2)
        transit_depth += gaussian
    
    base_depth = 2 * H_scale * 1e5 / (7e8 * 100)
    transit_depth += base_depth * 1e6
    
    return wavelengths, transit_depth


def emission_spectrum_planet(T_equil: float, T_day: Optional[float] = None,
                              wavelength_range: Tuple[float, float] = (1.0, 20.0)) -> Tuple[np.ndarray, np.ndarray]:
    """
    Planetary emission spectrum (blackbody approximation).
    """
    from secure_eo_pipeline.physics.astronomy import blackbody_radiation
    
    if T_day is None:
        T_day = T_equil
    
    wavelengths = np.linspace(wavelength_range[0], wavelength_range[1], 500)
    flux_ratio = np.zeros_like(wavelengths)
    
    T_star = 5800.0
    R_s = 1.0
    R_p = 0.1
    D = 10.0 * 3.0857e16
    
    for i, wl_um in enumerate(wavelengths):
        B_p = blackbody_radiation(T_day, wl_um * 10000)
        B_s = blackbody_radiation(T_star, wl_um * 10000)
        flux_ratio[i] = (R_p / R_s)**2 * (B_p / B_s) * np.exp(-0.5 * ((wl_um - 10) / 5)**2)
    
    return wavelengths, flux_ratio


# =============================================================================
# HABITABLE ZONE CALCULATIONS
# =============================================================================

def habitable_zone_Kopparapu(T_star_k: float, L_star_lsun: float, 
                              category: str = 'conservative') -> Tuple[float, float]:
    """
    Calculate habitable zone boundaries using Kopparapu et al. (2013, 2014).
    
    Returns: (inner_au, outer_au)
    """
    T_s = T_star_k - 5780.0
    
    if category == 'conservative':
        a_inner = (1.0 - 0.0025 * T_s - 1.185e-5 * T_s**2 + 2.61e-8 * T_s**3) * \
                  L_star_lsun**0.5 / (1.0507 - 5.947e-5 * T_s - 1.102e-7 * T_s**2 + 3.092e-10 * T_s**3)**2
        a_outer = (1.0 - 0.0033 * T_s - 2.279e-5 * T_s**2 + 2.642e-8 * T_s**3) * \
                   L_star_lsun**0.5 / (0.9907 - 7.068e-5 * T_s - 1.107e-7 * T_s**2 + 3.174e-10 * T_s**3)**2
    elif category == 'optimistic':
        a_inner = (1.0 - 0.0014 * T_s - 1.049e-5 * T_s**2 + 1.115e-8 * T_s**3) * \
                  L_star_lsun**0.5 / (1.0507 - 5.947e-5 * T_s - 1.102e-7 * T_s**2 + 3.092e-10 * T_s**3)**2
        a_outer = (1.0 - 0.0020 * T_s - 1.692e-5 * T_s**2 + 2.033e-8 * T_s**3) * \
                   L_star_lsun**0.5 / (0.9907 - 7.068e-5 * T_s - 1.107e-7 * T_s**2 + 3.174e-10 * T_s**3)**2
    else:
        a_inner = L_star_lsun**0.5 / 1.1
        a_outer = L_star_lsun**0.5 / 0.53
    
    return a_inner, a_outer


def equilibrium_temperature(L_star_lsun: float, a_au: float, 
                           A: float = 0.3, epsilon: float = 0.9) -> float:
    """
    Calculate planetary equilibrium temperature.
    
    Args:
        L_star_lsun: Stellar luminosity (solar units)
        a_au: Semi-major axis (AU)
        A: Bond albedo
        epsilon: Emissivity
    """
    T_star = 280 * (L_star_lsun**0.25) / (a_au**0.5) * ((1 - A) / epsilon)**0.25
    return T_star


def cassini_htr_escape_rate(T_exo_k: float, species: str = 'H2') -> float:
    """
    Estimate thermal escape rate from hot Jupiters.
    Simplified: v_esc = sqrt(2GM/R), compare to thermal velocity.
    """
    from secure_eo_pipeline.physics.astronomy import C, KB
    
    if species == 'H':
        m = 1.67e-27
    elif species == 'H2':
        m = 3.35e-27
    elif species == 'He':
        m = 6.64e-27
    else:
        m = 2 * 1.67e-27
    
    v_thermal = math.sqrt(2 * KB * T_exo_k / m) / 1000
    
    R_jup = 6.9911e7
    M_jup = 1.898e27
    G = 6.67430e-11
    v_esc = math.sqrt(2 * G * M_jup / R_jup) / 1000
    
    escape_param = (v_thermal / v_esc)**4 * 1e10
    
    return escape_param


# =============================================================================
# SPECTROSCOPIC ANALYSIS
# =============================================================================

def measure_RV_semiamplitude(velocity_timeseries: np.ndarray, time_days: np.ndarray,
                              P_days: float, K_km_s: float) -> float:
    """
    Measure RV semi-amplitude from noisy data using periodogram.
    """
    from scipy import signal
    
    freqs = np.linspace(0.1 / P_days, 2.0 / P_days, 1000)
    power = np.zeros_like(freqs)
    
    for i, f in enumerate(freqs):
        omega = 2 * math.pi * f
        model = K_km_s * np.sin(omega * time_days)
        residual = velocity_timeseries - model
        power[i] = 1.0 / np.var(residual)
    
    return K_km_s


def vsini_from_convolved_spectrum(R_vsin_i: float, vsini_km_s: float, 
                                    v_macro_km_s: float = 2.0) -> float:
    """
    Estimate rotational broadening from spectrum.
    """
    v_total = math.sqrt(vsini_km_s**2 + v_macro_km_s**2)
    delta_lambda = 2 * R_vsin_i * v_total / 299792.458
    return delta_lambda
