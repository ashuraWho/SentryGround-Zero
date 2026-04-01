"""
Electromagnetic Propagation Module for SentryGround-Zero.

Implements:
- Radio wave propagation (ionospheric, tropospheric)
- Radar signal processing (SAR, altimetry)
- Optical propagation (turbulence, scintillation)
- Antenna patterns and gain calculations
- Link budget analysis
- GNSS signal propagation

References:
- ITU-R propagation recommendations
- Skolnik radar handbook
- Ishimaru wave propagation
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

C = 299792458.0
F_ELECTRON = 1.602176634e-19
EPSILON_0 = 8.8541878128e-12
MU_0 = 1.25663706212e-6
BOLTZMANN = 1.380649e-23
R_EARTH = 6.371e6


# =============================================================================
# IONOSPHERIC PROPAGATION
# =============================================================================

@dataclass
class IonosphereParameters:
    """Ionospheric layer parameters."""
    NmF2: float = 1e12
    hmF2: float = 300e3
    B0: float = 200e3
    Hm: float = 50e3


def plasma_frequency(N_m3: float) -> float:
    """Plasma frequency from electron density (Hz)."""
    return 8980 * math.sqrt(N_m3)


def critical_frequency(Nm: float) -> float:
    """Critical frequency f0 (MHz)."""
    return plasma_frequency(Nm) / 1e6


def ionospheric_delay(frequency_mhz: float, TEC: float) -> float:
    """Total electron content delay (m)."""
    return 40.308 * TEC / frequency_mhz**2


def rayleigh_frequency(frequency_mhz: float, Nm: float) -> float:
    """Rayleigh (cutoff) frequency (MHz)."""
    return 0.91 * critical_frequency(Nm)


def refractive_index_ionosphere(
    frequency_mhz: float,
    Nm: float,
    B: float = 0.5
) -> float:
    """Ionospheric refractive index."""
    f = frequency_mhz * 1e6
    fp = plasma_frequency(Nm)
    
    if f < fp:
        return 0.0
    
    ne = fp**2 / f**2
    
    return 1 - ne * (1 - 0.5 * ne)


def group_delay(
    frequency_mhz: float,
    TEC: float,
    h_ionosphere: float = 350e3
) -> float:
    """Group path delay (m)."""
    f = frequency_mhz * 1e6
    return 40.308 * TEC / f**2


# =============================================================================
# TROPOSPHERIC PROPAGATION
# =============================================================================

def tropospheric_zenith_delay(
    P_mbar: float,
    T_k: float,
    e_mbar: float,
    h_station: float = 0.0
) -> float:
    """Zenith tropospheric delay (m)."""
    k1 = 77.604
    k2 = 64.79
    k3 = 377600.0
    Rd = 287.053
    g = 9.80665
    
    ZHD = 1e-6 * k1 * Rd * P_mbar / g
    ZWD = 1e-6 * (k2 - k3 / T_k) * Rd * e_mbar / g
    
    h_factor = 1.0 / (1.0 - 2.28e-5 * h_station)
    
    return (ZHD + ZWD) * h_factor


def mapping_function_niell(
    elevation_deg: float,
    h_station: float = 0.0
) -> float:
    """Niell mapping function."""
    a = 0.001185
    b = 0.00578
    c = 0.00145
    
    el = max(elevation_deg, 3.0)
    sin_el = math.sin(math.radians(el))
    cos_el = math.cos(math.radians(el))
    
    h = h_station / 1000.0
    
    ah = a * (1.0 + a * (-2.33 + 0.013 * h))
    bh = b * (1.0 + b * (0.735 - 0.05 * h))
    ch = c * (1.0 + c * (-0.12 + 0.01 * h))
    
    return (1.0 + a / (1.0 + b / (1.0 + c))) / (sin_el + ah / (sin_el + bh / (sin_el + ch)))


def slant_delay(
    elevation_deg: float,
    zenith_delay: float,
    h_station: float = 0.0
) -> float:
    """Slant path delay (m)."""
    return zenith_delay * mapping_function_niell(elevation_deg, h_station)


# =============================================================================
# RADAR PROPAGATION
# =============================================================================

def radar_range_equation(
    Pt_w: float,
    G_tx: float,
    G_rx: float,
    lambda_m: float,
    sigma_m2: float,
    R_km: float,
    L_loss: float = 1.0
) -> float:
    """Radar range equation - received power (W)."""
    R = R_km * 1000.0
    return Pt_w * G_tx * G_rx * lambda_m**2 * sigma_m2 / \
           ((4 * math.pi)**3 * R**4 * L_loss)


def radar_equation_noise(
    Pt_w: float,
    G: float,
    lambda_m: float,
    sigma_m2: float,
    R_km: float,
    T_sys_k: float,
    B_hz: float,
    L_loss: float = 1.0
) -> float:
    """Radar SNR with noise."""
    SNR = radar_range_equation(Pt_w, G, G, lambda_m, sigma_m2, R_km, L_loss)
    N = BOLTZMANN * T_sys_k * B_hz
    return SNR / N if N > 0 else 0.0


def prf_ambiguity_velocity(
    prf_hz: float,
    wavelength_m: float
) -> float:
    """Maximum unambiguous velocity (m/s)."""
    return wavelength_m * prf_hz / 4.0


def prf_ambiguity_range(
    prf_hz: float,
    c: float = C
) -> float:
    """Maximum unambiguous range (m)."""
    return c / (2 * prf_hz)


def pulse_doppler_nyquist(
    wavelength_m: float,
    v_max_m_s: float
) -> float:
    """Required PRF for given max velocity."""
    return 4 * v_max_m_s / wavelength_m


# =============================================================================
# ANTENNA PATTERNS
# =============================================================================

def antenna_gain_circular_aperture(
    diameter_m: float,
    wavelength_m: float,
    efficiency: float = 0.55
) -> float:
    """Gain for circular aperture antenna (linear)."""
    area = math.pi * (diameter_m / 2)**2
    return 10 * math.log10(efficiency * 4 * math.pi * area / wavelength_m**2)


def half_power_beamwidth(
    diameter_m: float,
    wavelength_m: float,
    efficiency: float = 0.55
) -> float:
    """HPBW in degrees."""
    return 70 * wavelength_m / (diameter_m * math.sqrt(efficiency))


def antenna_pattern_sinc(
    theta_deg: float,
    phi_deg: float,
    beamwidth_deg: float
) -> float:
    """Simplified antenna pattern (normalized)."""
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    bw = math.radians(beamwidth_deg)
    
    r = math.sqrt(theta**2 + phi**2)
    if r < 1e-10:
        return 1.0
    
    x = 2.783 * r / bw
    sinc = math.sin(x) / x if abs(x) > 1e-10 else 1.0
    return sinc**2


# =============================================================================
# LINK BUDGET
# =============================================================================

@dataclass
class LinkBudgetResult:
    """Link budget analysis result."""
    EIRP_dBW: float
    path_loss_dB: float
    received_power_dBW: float
    system_noise_temp_dBK: float
    noise_bandwidth_dBHz: float
    G_T_dBK: float
    C_N0_dBHz: float
    Eb_N0_dB: float
    margin_dB: float
    link_available: bool


def link_budget(
    frequency_mhz: float,
    tx_power_w: float,
    tx_gain_dBi: float,
    tx_line_loss_dB: float,
    distance_km: float,
    rx_gain_dBi: float,
    rx_noise_temp_k: float,
    bandwidth_hz: float,
    rx_line_loss_dB: float = 0.0,
    required_EbN0_dB: float = 10.0,
    coding_gain_dB: float = 3.0
) -> LinkBudgetResult:
    """Complete link budget analysis."""
    
    wavelength = C / (frequency_mhz * 1e6)
    
    EIRP_dBW = 10 * math.log10(tx_power_w) + tx_gain_dBi - tx_line_loss_dB
    
    loss_free_space = 20 * math.log10(4 * math.pi * distance_km * 1000 / wavelength)
    
    path_loss_dB = loss_free_space
    
    G_T_dBK = rx_gain_dBi - 10 * math.log10(BOLTZMANN * rx_noise_temp_k * 1000)
    
    C_dBW = EIRP_dBW - path_loss_dB + rx_gain_dBi - rx_line_loss_dB
    
    N0_dBW_Hz = 10 * math.log10(BOLTZMANN * rx_noise_temp_k)
    
    C_N0_dBHz = C_dBW - N0_dBW_Hz
    
    Eb_N0_dB = C_N0_dBHz - 10 * math.log10(bandwidth_hz) + coding_gain_dB
    
    margin_dB = Eb_N0_dB - required_EbN0_dB
    
    link_available = margin_dB > 0
    
    return LinkBudgetResult(
        EIRP_dBW=EIRP_dBW,
        path_loss_dB=path_loss_dB,
        received_power_dBW=C_dBW,
        system_noise_temp_dBK=10 * math.log10(rx_noise_temp_k),
        noise_bandwidth_dBHz=10 * math.log10(bandwidth_hz),
        G_T_dBK=G_T_dBK,
        C_N0_dBHz=C_N0_dBHz,
        Eb_N0_dB=Eb_N0_dB,
        margin_dB=margin_dB,
        link_available=link_available
    )


# =============================================================================
# SAR PROCESSING
# =============================================================================

def sar_resolution(
    wavelength_m: float,
    incidence_deg: float,
    R_km: float,
    L_antenna_m: float
) -> Tuple[float, float]:
    """SAR resolution (range x azimuth) in meters."""
    c = C
    
    range_res = c / (2 * 1e9)
    
    azimuth_res = L_antenna_m / 2.0
    
    return range_res, azimuth_res


def sar_ground_resolution(
    wavelength_m: float,
    incidence_deg: float,
    bandwidth_hz: float
) -> float:
    """Ground range resolution (m)."""
    c = C
    return c / (2 * bandwidth_hz * math.sin(math.radians(incidence_deg)))


def sar_integration_time(
    velocity_m_s: float,
    L_antenna_m: float,
    R_km: float
) -> float:
    """Integration time for stripmap SAR (s)."""
    return L_antenna_m * R_km * 1000 / (velocity_m_s * L_antenna_m)


def sar_noise_equivalent_sigma0(
    T_sys_k: float,
    wavelength_m: float,
    v_m_s: float,
    h_m: float,
    B_hz: float,
    incidence_deg: float,
    L_antenna_m: float
) -> float:
    """NESZ - noise equivalent sigma nought (linear)."""
    k = BOLTZMANN
    P_av = 100.0
    
    A_ground = v_m_s * self.integration_time(v_m_s, L_antenna_m, h_m/1000)
    
    SNR = P_av * wavelength_m**2 * L_antenna_m**2 / \
          (256 * math.pi**3 * k * T_sys_k * v_m_s * R_km**4 * B_hz)
    
    return 1 / SNR if SNR > 0 else float('inf')


# =============================================================================
# GNSS PROPAGATION
# =============================================================================

def gnss_signal_strength(
    P_tx_w: float,
    G_tx: float,
    R_m: float,
    G_rx: float,
    wavelength_m: float,
    polarization_loss_dB: float = 3.0
) -> float:
    """Received GNSS signal power (dBW)."""
    loss = 20 * math.log10(wavelength_m / (4 * math.pi * R_m))
    return 10 * math.log10(P_tx_w) + G_tx + G_rx - loss - polarization_loss_dB


def multipath_error(
    amplitude_ratio: float,
    phase_diff_deg: float,
    wavelength_m: float
) -> float:
    """Multipath range error (m)."""
    phi = math.radians(phase_diff_deg)
    error = amplitude_ratio * wavelength_m / (2 * math.pi) * abs(math.sin(phi / 2))
    return error


def scintillation_index(S4: float) -> float:
    """Scintillation index from S4 index."""
    return S4**2


def ionospheric_scintillation_phase_perturbation(
    sigma_phi_rad: float,
    tau_0_s: float,
    t_s: np.ndarray
) -> np.ndarray:
    """Phase perturbation from scintillation."""
    return sigma_phi_rad * np.random.randn(len(t_s))


# =============================================================================
# OPTICAL PROPAGATION
# =============================================================================

def optical_link_attenuation(
    visibility_km: float,
    wavelength_um: float = 0.55
) -> float:
    """Atmospheric extinction for optical links."""
    if visibility_km > 50:
        return 0.0
    
    k = 3.91 / visibility_km
    return k * visibility_km / (wavelength_um / 0.55)


def turbulence_cn2(h_km: float) -> float:
    """Refractive index structure constant Cn2 profile (m^-2/3)."""
    if h_km < 0.1:
        return 1.7e-14
    elif h_km < 1.0:
        return 3.9e-15
    elif h_km < 10:
        return 1.0e-16
    else:
        return 1.0e-17


def fried_parameter(
    Cn2: float,
    wavelength_m: float,
    R_m: float
) -> float:
    """Fried coherence diameter r0 (m)."""
    k = 2 * math.pi / wavelength_m
    return (0.423 * k**2 * Cn2 * R_m)**(-3/5)


def scintillation_variance(
    Cn2: float,
    wavelength_m: float,
    R_m: float,
    D_m: float
) -> float:
    """Log-amplitude variance."""
    k = 2 * math.pi / wavelength_m
    r0 = fried_parameter(Cn2, wavelength_m, R_m)
    
    sigma_I2 = 1.23 * Cn2 * k**(7/6) * R_m**(11/6) * (1 - 0.5 * (D_m / r0)**(5/6))
    return sigma_I2
