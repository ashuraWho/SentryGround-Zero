"""
Dark Matter Physics Module for SentryGround-Zero.

Implements:
- Direct detection experiments (WIMP, axion, SIDM)
- Annihilation and decay signals
- NFW and alternative halo profiles
- Indirect detection (gamma rays, neutrinos)
- Gravitational lensing (strong/weak)
- Cosmological constraints

References:
- Jungman et al. (1996) - Supersymmetric dark matter
- Bertone et al. (2005) - Particle dark matter
- Tulin & Yu (2018) - Self-interacting DM
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

HBAR = 1.054571817e-34
C = 299792458.0
G = 6.67430e-11
GEV = 1.7826619e-27
CM3_S = 2.99792458e10
PC = 3.085677581e18
MPC = 3.085677581e22
MSUN = 1.989e33
RHO_CRIT = 9.2e-30


# =============================================================================
# DARK MATTER HALO MODELS
# =============================================================================

@dataclass(frozen=True)
class DMHaloParameters:
    """Dark matter halo parameters."""
    rho_s: float
    r_s: float
    r_vir: float
    c: float
    alpha: float = 1.0
    beta: float = 3.0
    gamma: float = 1.0


def nfw_density(r_kpc: float, rho_s: float, r_s: float) -> float:
    """
    NFW density profile: ρ(r) = ρ_s / [(r/r_s)(1 + r/r_s)²]
    """
    x = r_kpc / r_s
    return rho_s / (x * (1 + x)**2)


def nfw_mass_enclosed(r_kpc: float, rho_s: float, r_s: float) -> float:
    """
    NFW enclosed mass in solar masses.
    M(<r) = 4π ρ_s r_s³ [ln(1 + r/r_s) - r/r_s / (1 + r/r_s)]
    """
    x = r_kpc / r_s
    prefactor = 4 * math.pi * rho_s * r_s**3 / MSUN
    mass = prefactor * (math.log(1 + x) - x / (1 + x))
    return mass


def einasto_density(r_kpc: float, rho_s: float, r_s: float, alpha: float = 0.17) -> float:
    """
    Einasto density profile: ρ = ρ_s * exp(-2/α [(r/r_s)^α - 1])
    """
    x = (r_kpc / r_s) ** alpha
    return rho_s * np.exp(-2 / alpha * (x - 1))


def burkert_density(r_kpc: float, rho_s: float, r_s: float) -> float:
    """
    Burkert (cored) profile: ρ = ρ_s / [(1 + r/r_s)(1 + (r/r_s)²)]
    """
    x = r_kpc / r_s
    return rho_s / ((1 + x) * (1 + x**2))


def hernquist_density(r_kpc: float, rho_s: float, r_s: float) -> float:
    """
    Hernquist profile: ρ = ρ_s / [(r/r_s)(1 + r/r_s)³]
    """
    x = r_kpc / r_s
    return rho_s / (x * (1 + x)**3)


def sidm_velocity_dispersion(T: float, sigma_over_m: float) -> float:
    """
    Self-interacting DM velocity dispersion.
    σ_v = sqrt(3 k_B T / m)
    """
    KB = 1.38e-16
    m_gev = 1.0
    sigma = sigma_over_m * m_gev / GEV
    v_disp = np.sqrt(3 * KB * T / (sigma * GEV))
    return v_disp


# =============================================================================
# DIRECT DETECTION
# =============================================================================

def wimp_halo_density(rho0: float = 0.3) -> float:
    """
    Local DM density at Solar position (GeV/cm³).
    """
    return rho0


def wimp_cross_section_SI(m_chi_gev: float, A: float = 131.0) -> float:
    """
    Spin-independent WIMP-nucleon cross-section (simplified).
    σ_SI = (4/π) * (m_red / m_χ)² * (Z f_p + (A-Z) f_n)² / f_n²
    """
    m_nucleon = 0.938 * 1000
    m_red = m_chi_gev * m_nucleon / (m_chi_gev + m_nucleon)
    
    sigma0 = 1e-47
    scaling = (m_red / m_chi_gev)**2
    
    return sigma0 * scaling


def wimp_cross_section_SD(m_chi_gev: float, J: float = 3.0/4.0) -> float:
    """
    Spin-dependent WIMP-nucleon cross-section.
    """
    sigma0 = 1e-42
    return sigma0 * J / (J + 1)


def recoil_energy(ER_keV: float, m_chi_gev: float, A: float = 131.0) -> float:
    """
    Nuclear recoil energy from WIMP scattering.
    ER = (2 v² cos²θ) / c² * (m_χ * m_N / (m_χ + m_N))²
    """
    v_220 = 220.0 / 299792.458
    m_N = A * 0.9315
    
    ER_max = 2 * v_220**2 * (m_chi_gev * m_N / (m_chi_gev + m_N))**2 / m_N
    return ER_max


def annual_modulation(t_days: float, A_mod: float = 0.07) -> float:
    """
    Annual modulation signal from Earth's motion.
    S(t) = S_0 + S_m cos(2π (t - t_0) / 365.25)
    """
    t0 = 152.5
    return A_mod * np.cos(2 * math.pi * (t_days - t0) / 365.25)


def event_rate_dbd(m_chi_gev: float, T_half: float, Q: float = 3.0) -> float:
    """
    Double beta decay rate for Majorana DM.
    G ~ Q^5 / (7 years) * (GeV^-5)
    """
    G_approx = 1e-14
    G_full = G_approx * Q**5
    rate = G_full * m_chi_gev**-1
    return rate


# =============================================================================
# INDIRECT DETECTION
# =============================================================================

def annihilation_cross_section(sigma_v: float = 3e-26) -> float:
    """
    Thermal relic cross-section: <σv> = 3e-26 cm³/s
    """
    return sigma_v


def gamma_flux_from_dm(rho_local: float, m_chi_gev: float,
                       sigma_v: float = 3e-26,
                       J_delta_omega: float = 1e22) -> float:
    """
    Gamma-ray flux from DM annihilation.
    Φ = (1 / 8π) * (1 / m_χ)² * <σv> * J * (dNγ/dE)
    """
    dN = 20
    flux = (1 / (8 * math.pi)) * (rho_local / m_chi_gev)**2 * sigma_v * J_delta_omega * dN
    return flux


def neutrino_flux_from_sun(rho_local: float, m_chi_gev: float,
                            sigma_SI: float = 1e-46) -> float:
    """
    Neutrino flux from DM captured in the Sun.
    """
    capture_rate = 1e20 * rho_local * sigma_SI
    annihilation_rate = np.sqrt(capture_rate)
    
    E_nu = m_chi_gev / 2
    flux = annihilation_rate / (4 * math.pi * PC**2) / E_nu
    return flux


def antiproton_flux(m_chi_gev: float, sigma_v: float = 3e-26, rho_local: float = 0.3) -> float:
    """
    Antiproton flux from DM annihilation.
    Simplified power-law approximation.
    """
    E_kin = 10.0
    flux = sigma_v * (rho_local / m_chi_gev)**2 * (E_kin / m_chi_gev)**-2.7
    return flux


# =============================================================================
# GRAVITATIONAL LENSING
# =============================================================================

def einstein_radius(theta_e_arcsec: float, D_ls: float, D_s: float) -> float:
    """
    Einstein radius in arcseconds.
    θ_E = sqrt(4GM / c² * D_ls / (D_l D_s))
    """
    return theta_e_arcsec


def lens_equation(beta_arcsec: float, theta_arcsec: float) -> float:
    """
    Lens equation: β = θ - α(θ)
    """
    return beta_arcsec - theta_arcsec


def magnification_mu(theta_arcsec: float, beta_arcsec: float, 
                    theta_e_arcsec: float) -> Tuple[float, float]:
    """
    Magnification for point lens.
    μ = (y² + 2) / (y * sqrt(y² + 4)) or μ_total = μ+ + |μ-|
    """
    y = theta_arcsec / theta_e_arcsec
    y_sq = y * y
    
    mu_plus = (y_sq + 2) / (2 * y * np.sqrt(y_sq + 4))
    mu_minus = -(y_sq + 2) / (2 * y * np.sqrt(y_sq + 4))
    
    return abs(mu_plus), abs(mu_minus)


def strong_lensing_cross_section(theta_e_arcsec: float) -> float:
    """
    Cross-section for strong lensing (arcseconds² to sr).
    σ = π θ_E²
    """
    theta_e_sr = (theta_e_arcsec * math.pi / (180 * 3600))**2
    return math.pi * theta_e_sr


def weak_lensing_shear(gamma: float, kappa: float) -> Tuple[float, float]:
    """
    Reduced shear: g = γ / (1 - κ)
    """
    denominator = 1 - kappa
    if abs(denominator) < 1e-10:
        return gamma, gamma
    return gamma / denominator, gamma / denominator


# =============================================================================
# COSMOLOGICAL CONSTRAINTS
# =============================================================================

def relic_density_omega(m_chi_gev: float, sigma_v: float) -> float:
    """
    DM relic density from thermal freeze-out.
    Ω h² ≈ 3e-27 / <σv>
    """
    return 3e-27 / sigma_v


def free_streaming_length(m_chi_gev: float, sigma_v: float = 3e-26) -> float:
    """
    DM free-streaming length in Mpc.
    λ_fs ≈ 0.06 * (keV) / (m_χ) * (cm³/s) / <σv>
    """
    m_kev = m_chi_gev * 1e6 / 1.7826619e-27 * 1.0545718e-34
    lambda_fs = 0.06 * m_kev / m_chi_gev * 3e-26 / sigma_v
    return lambda_fs


def halo_mass_function(dn_dlnM: float, M_solar: float, z: float) -> float:
    """
    Halo mass function dN/dlnM.
    dN/dlnM = (ρ_0 / M) * f(σ) * |dlnσ/dlnM|
    """
    sigma = 1.0
    f_st = 0.5 * (1 + (sigma / 1.17)**0.17) * np.exp(-sigma**2 / 2)
    
    return (RHO_CRIT / M_solar) * f_st


def satellite_abundance(M_host: float, z: float = 0.0) -> float:
    """
    Number of satellites for host mass M_host.
    N_sat ≈ 16 * (M_host / 10^12 M_sun)^1.1
    """
    return 16 * (M_host / 1e12)**1.1


# =============================================================================
# DETECTOR SIMULATION
# =============================================================================

def detector_threshold_energy(m_chi_gev: float, A: float = 131.0) -> float:
    """
    Minimum recoil energy for detection (keV).
    E_thr ≈ (m_χ m_N / (m_χ + m_N))² * v² / m_N
    """
    m_N = A * 0.9315
    v_escape = 544.0 / 299792.458
    
    E_thr = 2 * v_escape**2 * (m_chi_gev * m_N / (m_chi_gev + m_N))**2 / m_N
    return E_thr * 1e6


def background_rate_Xenon(R_bkg: float = 1e-3) -> float:
    """
    Background event rate for XENON-like detector (counts/keV/kg/day).
    """
    return R_bkg


def signal_significance(N_signal: float, N_background: float, exposure_kg_day: float) -> float:
    """
    Compute statistical significance (sigma).
    Z = sqrt(2((N_s+N_b)ln(1+N_s/N_b) - N_s))
    """
    if N_signal <= 0:
        return 0.0
    if N_background <= 0:
        return np.sqrt(2 * N_signal)
    
    nb = N_background
    ns = N_signal
    
    significance = np.sqrt(2 * ((ns + nb) * np.log(1 + ns / nb) - ns))
    return significance


def exposure_mass_time(M_kg: float, T_days: float, efficiency: float = 0.5) -> float:
    """
    Compute exposure in kg-days.
    """
    return M_kg * T_days * efficiency


# =============================================================================
# AXION PHYSICS
# =============================================================================

def axion_mass_from_PQ_scale(f_a: float) -> float:
    """
    Axion mass from PQ scale.
    m_a = (6e-6 eV) * (10^12 GeV / f_a)
    """
    f_gev = f_a / 1.52e-27
    return 6e-6 * 1e12 / f_gev


def axion_photon_coupling(g_agg: float = 1e-12) -> float:
    """
    Axion-photon coupling: g_aγγ = α / (π f_a)
    """
    alpha = 1.0 / 137.0
    return alpha / (math.pi * g_agg)


def haloscope_frequency(m_a_uev: float) -> float:
    """
    Haloscope search frequency from axion mass.
    f = (m_a c²) / h
    """
    m_a_j = m_a_uev * 1e-6 * 1.602e-19
    return m_a_j / HBAR


def cavity_power_collected(m_a_uev: float, B_tesla: float, V_m3: float,
                          Q: float = 1e6) -> float:
    """
    Microwave cavity power from axion conversion.
    P = g² B² V m_a² Q / (π R)
    """
    g_aee = 1e-13
    rho_DM = 0.3 * 1e6
    
    P = (g_aee**2 * B_tesla**2 * V_m3 * (m_a_uev * 1e-6)**2 * Q) / (math.pi * 50)
    return P
