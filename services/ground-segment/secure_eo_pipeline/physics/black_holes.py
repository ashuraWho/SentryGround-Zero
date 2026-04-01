"""
Black Hole Physics Module for SentryGround-Zero.

Implements:
- Schwarzschild and Kerr metrics
- Accretion disk models (thin disk, ADAF, slim disk)
- Relativistic jets and Blandford-Znajek mechanism
- Event Horizon and photon ring shadows
- Gravitational wave emission from mergers
- Hawking radiation (quantum effects)

References:
- Shakura & Sunyaev (1973) - thin disk
- Narayan & Yi (1995) - ADAF
- Blandford & Znajek (1977) - jets
- Event Horizon Telescope collaboration
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

G = 6.67430e-11
C = 299792458.0
MSUN = 1.989e30
HBAR = 1.054571817e-34
KB = 1.380649e-23
SIGMA_SB = 5.670374419e-8


# =============================================================================
# BLACK HOLE METRICS
# =============================================================================

@dataclass(frozen=True)
class BlackHoleParameters:
    """Black hole parameters."""
    mass_msun: float
    spin_a: float = 0.0
    charge: float = 0.0
    m_dot_msun_yr: float = 0.0


def schwarzschild_radius(M_msun: float) -> float:
    """
    Schwarzschild radius: R_s = 2GM/c²
    Returns: meters
    """
    M_kg = M_msun * MSUN
    return 2 * G * M_kg / C**2


def Kerr_radius(M_msun: float, spin_a: float = 0.0) -> Tuple[float, float]:
    """
    Innermost stable circular orbit (ISCO) for Kerr BH.
    r_ISCO = 6GM/c² for a=0
    r_ISCO → GM/c² for a→1
    """
    M_kg = M_msun * MSUN
    R_s = 2 * G * M_kg / C**2
    
    z1 = 1 + (1 - spin_a**2)**0.5 * ((1 + spin_a)**0.5 + (1 - spin_a)**0.5)**(1.0/3.0)
    z2 = (3 * spin_a**2 + z1**2)**0.5
    
    r_isco = (3 + z2 - ((3 - z1) * (3 + z1 + 2*z2))**0.5) * G * M_kg / C**2
    
    r_horizon = (1 + (1 - spin_a**2)**0.5) * G * M_kg / C**2
    
    return r_isco, r_horizon


def ergosphere_radius(M_msun: float, spin_a: float, theta_deg: float) -> float:
    """
    Ergosphere radius for Kerr BH.
    r_ergo = GM/c² + sqrt(G²M²/c⁴ - a²cos²θ)
    """
    M_kg = M_msun * MSUN
    theta = math.radians(theta_deg)
    
    r_ergo = G * M_kg / C**2 * (1 + math.sqrt(1 - spin_a**2 * math.cos(theta)**2))
    return r_ergo


def frame_dragging_omega(M_msun: float, spin_a: float, r: float) -> float:
    """
    Frame-dragging angular velocity at radius r.
    Ω = (GM/r³) / (1 + sqrt(GM / (r c²)))
    """
    M_kg = M_msun * MSUN
    r_m = r
    
    Omega = G * M_kg / (r_m**3 * C**2) / (1 + math.sqrt(G * M_kg / (r_m * C**2)))
    return Omega


# =============================================================================
# ACCRETION DISK MODELS
# =============================================================================

def thin_disk_luminosity(m_dot_msun_yr: float, eta: float = 0.1) -> float:
    """
    Thin disk bolometric luminosity.
    L = η ṁ c²
    """
    m_dot_kg_s = m_dot_msun_yr * MSUN / (365.25 * 86400)
    return eta * m_dot_kg_s * C**2 / 3.826e26


def thin_disk_temperature(R_rs: float, m_dot_msun_yr: float, 
                         M_msun: float) -> float:
    """
    Temperature profile for Shakura-Sunyaev disk.
    T(R) = [3GMṁ / (8πσR³)]^(1/4) * [1 - (R_in/R)^(1/2)]
    
    Returns: temperature in K at radius R (in units of Rs)
    """
    M_kg = M_msun * MSUN
    m_dot = m_dot_msun_yr * MSUN / (365.25 * 86400)
    
    R_m = R_rs * schwarzschild_radius(M_msun)
    
    coeff = 3 * G * M_kg * m_dot / (8 * math.pi * SIGMA_SB * R_m**3)
    T = coeff**0.25
    
    R_in_rs = 6.0
    T *= (1 - (R_in_rs / R_rs)**0.5)**0.25
    
    return T


def disk_spectra_multitemperature(R_min: float, R_max: float, M_msun: float,
                                  m_dot_msun_yr: float, n_r: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate multicolor blackbody spectrum from accretion disk.
    
    Returns: (wavelengths_um, flux_relative)
    """
    R_sch = schwarzschild_radius(M_msun)
    
    R_in = max(R_min, 6) * R_sch
    R_out = R_max * R_sch
    
    Rs = np.linspace(R_in, R_out, n_r)
    
    temperatures = np.array([thin_disk_temperature(r / R_sch, m_dot_msun_yr, M_msun) for r in Rs])
    
    wavelengths = np.linspace(0.1, 100, 500)
    flux = np.zeros_like(wavelengths)
    
    for i, wl_um in enumerate(wavelengths):
        wl_m = wl_um * 1e-6
        for j, T in enumerate(temperatures):
            B_lambda = 2 * HBAR * C**2 / (wl_m**5) / (math.exp(HBAR * C / (wl_m * KB * T)) - 1)
            flux[i] += B_lambda * (Rs[j+1] - Rs[j]) if j < len(Rs)-1 else 0
    
    return wavelengths, flux / np.max(flux)


def adaf_accretion_rate(m_dot_eddington: float, M_msun: float) -> float:
    """
    ADAF (Advection Dominated Accretion Flow) rate.
    ṁ_ADAF ~ α² ṁ_Edd for low accretion rates
    """
    m_dot_edd = 1.4e17 * M_msun
    alpha = 0.1
    return alpha**2 * m_dot_eddington * m_dot_edd


def slim_disk_photonsphere_radius(m_dot_msun_yr: float, M_msun: float) -> float:
    """
    Photonsphere radius for super-Eddington slim disk.
    R_ph ~ 2GM/c² * ln(ṁ/ṁ_Edd)
    """
    R_s = schwarzschild_radius(M_msun)
    m_dot_edd = 1.4e17 * M_msun
    m_dot = m_dot_msun_yr * MSUN / (365.25 * 86400)
    
    if m_dot < m_dot_edd:
        return 2 * R_s
    
    return 2 * R_s * math.log(m_dot / m_dot_edd)


# =============================================================================
# JET MODELS
# =============================================================================

def blandford_znajek_power(M_msun: float, spin_a: float, B_poloidal: float) -> float:
    """
    Blandford-Znajek jet power.
    P_BZ = (1/20) * B² r_H⁴ Ω_H² (1 - Ω_H/Ω_F)
    
    Returns: power in Watts
    """
    M_kg = M_msun * MSUN
    r_H = (1 + math.sqrt(1 - spin_a**2)) * G * M_kg / C**2
    
    Omega_H = spin_a * C**3 / (2 * G * M_kg * (1 + math.sqrt(1 - spin_a**2)))
    
    P_BZ = (1.0 / 20.0) * B_poloidal**2 * r_H**4 * Omega_H**2
    
    return P_BZ


def jet_termination_radius(P_BZ: float, nISM_cm3: float = 1.0, v_jet: float = 0.99) -> float:
    """
    Jet termination radius (Bondi-Hoyle approximation).
    R_term = (P_BZ / (π ρISM v_jet³ c))^(1/2)
    """
    rho_ISM = nISM_cm3 * 1.67e-24
    R_term = (P_BZ / (math.pi * rho_ISM * (v_jet * C)**3 * C))**0.5
    return R_term


def jet_magnetic_field(P_BZ: float, r: float, M_msun: float, spin_a: float) -> float:
    """
    Magnetic field at jet radius r from Blandford-Znajek power.
    B(r) = sqrt(P_BZ / (r² c)) * f(a)
    """
    r_H = (1 + math.sqrt(1 - spin_a**2)) * G * M_msun * MSUN / C**2
    
    f_a = (1.0 / 2.0) * spin_a * (1 + math.sqrt(1 - spin_a**2))
    
    B = math.sqrt(P_BZ / (r**2 * C)) * f_a / (r_H / r)
    return B


# =============================================================================
# EVENT HORIZON SHADOW (EHT)
# =============================================================================

def shadow_radius_Kerr(spin_a: float) -> float:
    """
    Angular shadow radius for Kerr BH (normalized to Rs).
    R_shadow ≈ 5.2 Rs for a=0
    R_shadow decreases for higher spin
    """
    R_shadow = 5.2 - 0.5 * spin_a
    return R_shadow


def shadow_aspect_ratio(spin_a: float) -> float:
    """
    Vertical/horizontal axis ratio of shadow.
    Approaches 1 as spin → 1 (oblate shadow)
    """
    return 1.0 - 0.06 * spin_a


def photon_ring_radius_angle(spin_a: float, D_Mpc: float, M_msun: float) -> float:
    """
    Photon ring angular radius in microarcseconds.
    θ_ring ≈ 10 μas * (M / 6.5e9 M_sun) / (D / 16.8 Mpc)
    """
    D = D_Mpc * 3.086e22
    M = M_msun * MSUN
    GMc2 = G * M / C**2
    
    theta_ring = (3 * math.sqrt(3) * GMc2) / D * 206265 * 1e6
    return theta_ring


def shadow_image_intensity(r_normalized: np.ndarray, spin_a: float) -> np.ndarray:
    """
    Simplified shadow intensity profile (EHT-like).
    I(r) ~ exp(-|r - R_shadow|² / σ²)
    """
    R_shadow = shadow_radius_Kerr(spin_a)
    sigma = 0.15
    
    intensity = np.exp(-((r_normalized - R_shadow)**2) / (2 * sigma**2))
    
    r_horizon = 1 + math.sqrt(1 - spin_a**2)
    intensity[r_normalized < r_horizon] = 0.0
    
    return intensity


# =============================================================================
# HAWKING RADIATION
# =============================================================================

def hawking_temperature(M_msun: float) -> float:
    """
    Hawking temperature: T_H = ħc³ / (8πGMk_B)
    """
    M_kg = M_msun * MSUN
    T_H = HBAR * C**3 / (8 * math.pi * G * M_kg * KB)
    return T_H


def hawking_luminosity(M_msun: float) -> float:
    """
    Hawking radiation luminosity: L = A σ T⁴
    """
    T = hawking_temperature(M_msun)
    R_s = schwarzschild_radius(M_msun)
    A = 4 * math.pi * R_s**2
    return A * SIGMA_SB * T**4


def hawking_evaporation_time(M_msun: float) -> float:
    """
    Black hole evaporation time.
    t_ev = 5120π G² M³ / (ħ c⁴)
    Returns: seconds
    """
    M_kg = M_msun * MSUN
    t_ev = 5120 * math.pi * G**2 * M_kg**3 / (HBAR * C**4)
    return t_ev / 3.17e-7


def hawking_particle_spectrum(M_msun: float, species: str = 'photon') -> Tuple[np.ndarray, np.ndarray]:
    """
    Hawking radiation spectrum (blackbody at T_H).
    
    Returns: (wavelengths_m, dN/dE)
    """
    T = hawking_temperature(M_msun)
    
    if species == 'photon':
        E_range = np.logspace(-20, -10, 100)
        dNdE = E_range**2 / (math.exp(E_range / (KB * T)) - 1)
    elif species == 'neutrino':
        E_range = np.logspace(-15, -5, 100)
        dNdE = E_range**2 / (math.exp(E_range / (KB * T)) + 1)
    else:
        E_range = np.logspace(-20, -10, 100)
        dNdE = E_range**2 / (math.exp(E_range / (KB * T)) - 1)
    
    return E_range, dNdE


# =============================================================================
# GRAVITATIONAL WAVES FROM BH MERGERS
# =============================================================================

def quasinormal_frequency(M_msun: float, l: int = 2, m: int = 2) -> float:
    """
    BH quasinormal mode frequency.
    f_QNM = (1 / (2π)) * (c³ / GM) * k(a)
    k(l) ≈ 0.3737 + 0.2267 a + 0.376 a²
    """
    M_kg = M_msun * MSUN
    k = 0.3737 + 0.2267 * 0.7 + 0.376 * 0.7**2
    
    f_QNM = (C**3 / (2 * math.pi * G * M_kg)) * k / 1000
    return f_QNM


def ringdown_damping_time(M_msun: float, l: int = 2, spin_a: float = 0.7) -> float:
    """
    Ringdown damping time.
    τ = 2 / (n ω_I) where n ≈ 0.0887 / (1-a)^0.37
    """
    M_kg = M_msun * MSUN
    n_param = 0.0887 / (1 - spin_a)**0.37
    omega_R = quasinormal_frequency(M_msun, l) * 2 * math.pi
    
    tau = 2 / (n_param * omega_R)
    return tau


def final_spin_after_merger(m1_msun: float, m2_msun: float, 
                           chi1: float, chi2: float) -> float:
    """
    Final spin parameter from BBH merger.
    Rezzolla et al. (2008) formula.
    """
    M = m1_msun + m2_msun
    eta = m1_msun * m2_msun / M**2
    
    chi_final = (m1_msun * chi1 + m2_msun * chi2) / M
    
    S = 2 * math.sqrt(3) * eta
    delta_m = (m1_msun - m2_msun) / M
    
    a_f = chi_final + S * delta_m - 0.1229 * eta * chi_final**2
    
    return min(0.998, max(0.0, a_f))


def final_mass_after_merger(m1_msun: float, m2_msun: float, 
                           E_rad_fraction: float = 0.056) -> float:
    """
    Final mass after merger (energy radiated away).
    """
    M_initial = m1_msun + m2_msun
    M_rad = E_rad_fraction * M_initial
    return M_initial - M_rad


# =============================================================================
# RELATIVISTIC BEAMING
# =============================================================================

def relativistic_doppler_factor(beta: float, cos_theta: float) -> float:
    """
    Relativistic Doppler factor.
    δ = 1 / [Γ (1 - β cosθ)]
    """
    Gamma = 1.0 / math.sqrt(1 - beta**2)
    return 1.0 / (Gamma * (1 - beta * cos_theta))


def beaming_angle(Gamma: float) -> float:
    """
    Relativistic beaming opening angle.
    θ_jet ≈ 1 / Γ
    """
    return math.degrees(1.0 / Gamma)


def apparent_luminosity(L_intrinsic: float, D_L_mpc: float, 
                       beta: float, cos_theta: float) -> float:
    """
    Apparent bolometric luminosity with Doppler boosting.
    L_app = δ^p * L_intrinsic
    p ≈ 3 for jets, p ≈ 2 for disks
    """
    delta = relativistic_doppler_factor(beta, cos_theta)
    p = 3
    return delta**p * L_intrinsic


# =============================================================================
# PANCHARATNAM BERRY PHASE (QUANTUM)
# =============================================================================

def berry_phase_curvature(B: float, theta: float, phi: float) -> float:
    """
    Berry curvature for spin-1/2 particle in magnetic field.
    Ω = (e / 2m) * B
    """
    e = 1.6e-19
    m_e = 9.11e-31
    
    Omega = (e / (2 * m_e)) * B * math.sin(theta)
    return Omega
