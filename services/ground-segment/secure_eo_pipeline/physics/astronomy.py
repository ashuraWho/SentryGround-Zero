"""
Astronomy and Astrophysics Utilities for SentryGround-Zero.

Implements:
- Celestial coordinate transformations (equatorial, ecliptic, galactic)
- Ephemeris calculations for solar system bodies
- Photometry and radiometry conversions
- Spectral analysis utilities
- Physical constants for astrophysics

References:
- Seidelmann, "Explanatory Supplement to the Astronomical Almanac"
- Bessell, "UBVRI Passbands" (2000)
- Cox, "Allen's Astrophysical Quantities"
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

# Solar system (IAU 2015)
AU_KM = 1.495978707e8
AU_M = AU_KM * 1000
R_SUN = 6.957e8
M_SUN = 1.9885e30
L_SUN = 3.828e26
T_SUN = 5772.0

# Earth
R_EARTH = 6.371e6
M_EARTH = 5.972e24
GM_EARTH = 3.986004418e14

# Speed of light
C = 299792458.0

# Planck constant
H = 6.62607015e-34
HBAR = H / (2 * math.pi)

# Boltzmann constant
KB = 1.380649e-23

# Stefan-Boltzmann constant
SIGMA = 5.670374419e-8

# Gravitational constant
G = 6.67430e-11

# Hubble constant (H0 in km/s/Mpc)
H0 = 70.0

# Critical density (g/cm³)
RHO_CRIT = 3.0 * H0**2 * 1e10 / (8 * math.pi * G)


# =============================================================================
# COORDINATE SYSTEMS
# =============================================================================

@dataclass(frozen=True)
class EquatorialCoords:
    """Equatorial coordinates (RA/Dec)."""
    ra_deg: float
    dec_deg: float


@dataclass(frozen=True)
class EclipticCoords:
    """Ecliptic coordinates."""
    lon_deg: float
    lat_deg: float


@dataclass(frozen=True)
class GalacticCoords:
    """Galactic coordinates (l, b)."""
    l_deg: float
    b_deg: float


def equatorial_to_ecliptic(ra_deg: float, dec_deg: float, obliquity_deg: float = 23.43928) -> EclipticCoords:
    """Convert equatorial (RA/Dec) to ecliptic coordinates."""
    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)
    eps = math.radians(obliquity_deg)
    
    sin_lon = math.sin(ra) * math.cos(eps) - math.tan(dec) * math.sin(eps)
    cos_lon = math.cos(ra)
    lon = math.degrees(math.atan2(sin_lon, cos_lon))
    
    sin_lat = math.sin(dec) * math.cos(eps) + math.cos(dec) * math.sin(eps) * math.sin(ra)
    lat = math.degrees(math.asin(sin_lat))
    
    return EclipticCoords(lon % 360, lat)


def ecliptic_to_equatorial(lon_deg: float, lat_deg: float, obliquity_deg: float = 23.43928) -> EquatorialCoords:
    """Convert ecliptic to equatorial (RA/Dec) coordinates."""
    lon = math.radians(lon_deg)
    lat = math.radians(lat_deg)
    eps = math.radians(obliquity_deg)
    
    sin_ra = math.sin(lon) * math.cos(eps) - math.tan(lat) * math.sin(eps)
    cos_ra = math.cos(lon)
    ra = math.degrees(math.atan2(sin_ra, cos_ra))
    
    sin_dec = math.sin(lat) * math.cos(eps) + math.cos(lat) * math.sin(eps) * math.sin(lon)
    dec = math.degrees(math.asin(sin_dec))
    
    return EquatorialCoords(ra % 360, dec)


def equatorial_to_galactic(ra_deg: float, dec_deg: float) -> GalacticCoords:
    """Convert equatorial (RA/Dec) to galactic coordinates."""
    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)
    
    alpha_GP = math.radians(192.85948)
    delta_GP = math.radians(27.12825)
    l_asc = math.radians(33.0)
    
    sin_b = math.sin(dec) * math.sin(delta_GP) + math.cos(dec) * math.cos(delta_GP) * math.cos(ra - alpha_GP)
    b = math.degrees(math.asin(sin_b))
    
    cos_b = math.cos(math.radians(b))
    sin_l = math.cos(dec) * math.sin(ra - alpha_GP) / cos_b
    cos_l = (math.sin(dec) - math.sin(delta_GP) * sin_b) / (math.cos(delta_GP) * cos_b)
    l = math.degrees(math.atan2(sin_l, cos_l)) + l_asc
    
    return GalacticCoords(l % 360, b)


def galactic_to_equatorial(l_deg: float, b_deg: float) -> EquatorialCoords:
    """Convert galactic to equatorial (RA/Dec) coordinates."""
    l = math.radians(l_deg)
    b = math.radians(b_deg)
    
    alpha_GP = math.radians(192.85948)
    delta_GP = math.radians(27.12825)
    l_asc = math.radians(33.0)
    
    sin_dec = math.sin(b) * math.sin(delta_GP) + math.cos(b) * math.cos(delta_GP) * math.cos(l - l_asc)
    dec = math.degrees(math.asin(sin_dec))
    
    cos_dec = math.cos(math.radians(dec))
    sin_ra = math.cos(b) * math.sin(l - l_asc) / cos_dec
    cos_ra = (math.sin(b) - math.sin(delta_GP) * sin_dec) / (math.cos(delta_GP) * cos_dec)
    ra = math.degrees(math.atan2(sin_ra, cos_ra)) + alpha_GP
    
    return EquatorialCoords(ra % 360, dec)


# =============================================================================
# TIME AND ASTROMETRY
# =============================================================================

def julian_date(dt: datetime) -> float:
    """Convert datetime to Julian Date (UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    unix_ms = dt.timestamp()
    return 2440587.5 + unix_ms / 86400.0


def julian_to_mjd(jd: float) -> float:
    """Convert Julian Date to Modified Julian Date."""
    return jd - 2400000.5


def mjd_to_unix(mjd: float) -> float:
    """Convert MJD to Unix timestamp."""
    return (mjd + 2400000.5 - 2440587.5) * 86400.0


def gmst(jd: float) -> float:
    """Greenwich Mean Sidereal Time in degrees."""
    T = (jd - 2451545.0) / 36525.0
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
    gmst += T * T * (0.000387933 - T / 38710000.0)
    return gmst % 360.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Angular separation between two points on sphere (degrees)."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return math.degrees(c)


# =============================================================================
# PHOTOMETRY AND RADIOMETRY
# =============================================================================

# Standard photometric passbands (central wavelengths in Angstroms)
PASSBANDS = {
    "U": 3650,
    "B": 4450,
    "V": 5510,
    "R": 6410,
    "I": 7980,
    "J": 12200,
    "H": 16300,
    "K": 21900,
}


def flux_to_mag(flux: float, flux_ref: float = 3631.0) -> float:
    """Convert flux (Jy) to magnitude (AB or Vega)."""
    return -2.5 * math.log10(flux / flux_ref)


def mag_to_flux(mag: float, flux_ref: float = 3631.0) -> float:
    """Convert magnitude to flux (Jy)."""
    return flux_ref * 10**(-0.4 * mag)


def blackbody_radiation(T: float, wavelength_angstrom: float) -> float:
    """
    Planck function B_λ(T) in erg/s/cm²/Å/sr.
    T: temperature in Kelvin
    wavelength: wavelength in Angstroms
    """
    c1 = 1.191042e-5
    c2 = 1.4387770
    lam_cm = wavelength_angstrom * 1e-8
    return c1 / (lam_cm**5) / (math.exp(c2 / (lam_cm * T)) - 1.0)


def blackbody_luminosity(T: float, R: float) -> float:
    """
    Total luminosity from Stefan-Boltzmann law.
    T: effective temperature (K)
    R: radius (solar radii)
    """
    return 4 * math.pi * (R * R_SUN)**2 * SIGMA * T**4 / L_SUN


def planet_temperature(L_star: float, a_au: float, albedo: float = 0.3) -> float:
    """
    Estimate equilibrium temperature of a planet.
    L_star: stellar luminosity (solar luminosities)
    a_au: semi-major axis (AU)
    albedo: Bond albedo
    """
    T_eq = T_SUN * (L_star**0.25) / (2 * math.sqrt(a_au)) * (1 - albedo)**0.25
    return T_eq


def transit_depth(R_p: float, R_star: float) -> float:
    """
    Calculate transit depth for a planet transit.
    Returns: (R_p/R_star)²
    """
    return (R_p / R_star)**2


# =============================================================================
# DARK MATTER AND COSMOLOGY
# =============================================================================

def nfw_profile(r: float, rho_0: float, r_s: float) -> float:
    """
    Navarro-Frenk-White dark matter density profile.
    ρ(r) = ρ₀ / [(r/r_s)(1 + r/r_s)²]
    
    Args:
        r: radius (kpc)
        rho_0: characteristic density (M☉/kpc³)
        r_s: scale radius (kpc)
    
    Returns:
        density (M☉/kpc³)
    """
    x = r / r_s
    return rho_0 / (x * (1 + x)**2)


def jeans_escape_velocity(r: float, M_enc: float) -> float:
    """
    Jeans escape velocity at radius r.
    v_esc = sqrt(2|GM(r)/r|)
    Returns: km/s
    """
    return math.sqrt(2 * G * M_enc * 1.989e30 / (r * 3.0857e16)) / 1000


def schwarschild_radius(M: float) -> float:
    """
    Schwarzschild radius for a mass.
    Returns: meters
    """
    return 2 * G * M * 1.989e30 / (C**2)


def eddington_luminosity(M: float) -> float:
    """
    Eddington luminosity limit.
    M: black hole mass (solar masses)
    Returns: L☉
    """
    return 3.2e4 * M


def gravitational_wave_strain(h_plus: float, h_cross: float) -> float:
    """
    Calculate gravitational wave strain amplitude.
    h = sqrt(h₊² + h×²)
    """
    return math.sqrt(h_plus**2 + h_cross**2)


# =============================================================================
# STELLAR ASTROPHYSICS
# =============================================================================

def main_sequence_luminosity(M: float) -> float:
    """
    Approximate main-sequence luminosity (L☉) from mass (M☉).
    Uses mass-luminosity relation: L ∝ M^3.5
    """
    return M**3.5


def main_sequence_radius(M: float) -> float:
    """
    Approximate main-sequence radius (R☉) from mass (M☉).
    Uses mass-radius relation: R ∝ M^0.8
    """
    return M**0.8


def main_sequence_lifetime(M: float) -> float:
    """
    Main sequence lifetime in years.
    t_MS ≈ 10^10 * M / L (M☉ years)
    """
    return 1e10 * M / main_sequence_luminosity(M)


def centrifugal_velocity(r_kpc: float, M_total_msun: float) -> float:
    """
    Circular velocity from enclosed mass (keplerian).
    v_c = sqrt(GM/r)
    Returns: km/s
    """
    return math.sqrt(G * M_total_msun * 1.989e30 / (r_kpc * 3.0857e19)) / 1000


# =============================================================================
# SPECTRAL ANALYSIS
# =============================================================================

def doppler_shift(wavelength_rest: float, velocity_km_s: float) -> float:
    """
    Calculate observed wavelength from Doppler shift.
    Positive velocity = recession (redshift)
    Returns: observed wavelength
    """
    beta = velocity_km_s / C * 1000
    return wavelength_rest * math.sqrt((1 + beta) / (1 - beta))


def redshift_to_velocity(z: float) -> float:
    """
    Convert redshift to recession velocity (km/s).
    Uses relativistic formula for accuracy.
    """
    beta = ((z + 1)**2 - 1) / ((z + 1)**2 + 1)
    return beta * C / 1000


def velocity_to_redshift(v_km_s: float) -> float:
    """
    Convert velocity to redshift.
    """
    beta = v_km_s / C * 1000
    return math.sqrt((1 + beta) / (1 - beta)) - 1


# =============================================================================
# ASTEROID AND SMALL BODY MECHANICS
# =============================================================================

def hohmann_transfer_dv(r1_km: float, r2_km: float) -> Tuple[float, float]:
    """
    Calculate Hohmann transfer delta-v.
    Returns: (burn at periapsis, burn at apoapsis) in km/s
    """
    mu = GM_EARTH / 1e9
    
    v1 = math.sqrt(mu / r1_km)
    v2 = math.sqrt(mu / r2_km)
    
    v_transfer = math.sqrt(2 * mu * r2_km / (r1_km * (r1_km + r2_km)))
    
    dv1 = abs(v_transfer - v1)
    dv2 = abs(v2 - v_transfer)
    
    return dv1, dv2


def asteroid_absolute_magnitude(H: float, G: float, phase_deg: float) -> float:
    """
    Compute asteroid apparent magnitude using H-G system.
    H: absolute magnitude
    G: slope parameter
    phase: phase angle in degrees
    """
    phi = math.radians(phase_deg)
    tan_half = math.tan(phi / 2)
    
    if phase_deg < 15:
        A = math.exp(-163.606 * tan_half)
        B = 1.36066 * tan_half + 0.98664 * tan_half**2 - 0.11904 * tan_half**3 + 0.02543 * tan_half**4
    else:
        A = math.exp(-3.33 * tan_half**0.63)
        B = math.exp(-1.87 * tan_half**1.22)
    
    B1 = A * B
    B2 = (1 - A) * B
    
    phi_ag = B1 + B2
    
    return H - 2.5 * math.log10(phi_ag)


def hill_sphere_radius(a_km: float, M_body: float, M_central: float) -> float:
    """
    Calculate Hill sphere radius for a body.
    a: semi-major axis of body
    M_body: mass of body
    M_central: mass of central body
    Returns: Hill radius in km
    """
    return a_km * (M_body / (3 * M_central))**(1/3)


# =============================================================================
# INSTRUMENT RADIOMETRY
# =============================================================================

def snr_photon_collected(N_photons: float, QE: float, dark_current_e_s: float, 
                         read_noise_e: float, shot_noise_sky: float) -> float:
    """
    Calculate signal-to-noise ratio for photon-collecting instrument.
    
    Args:
        N_photons: photons from source per second
        QE: quantum efficiency
        dark_current_e_s: dark current in e-/s
        read_noise_e: read noise in e-
        shot_noise_sky: sky background noise in e-/s
    
    Returns:
        SNR
    """
    signal = N_photons * QE
    noise_squared = signal + dark_current_e_s + read_noise_e**2 + shot_noise_sky
    return signal / math.sqrt(noise_squared)


def pixel_scale(altitude_km: float, focal_length_mm: float, pixel_size_um: float) -> float:
    """
    Calculate ground pixel scale (m) for pushbroom imager.
    
    Args:
        altitude_km: satellite altitude
        focal_length_mm: telescope focal length
        pixel_size_um: detector pixel size
    
    Returns:
        ground sample distance (m)
    """
    pixel_rad = pixel_size_um * 1e-6 / (focal_length_mm * 1e-3)
    return altitude_km * 1000 * pixel_rad


def integration_time_required(flux_jy: float, aperture_m: float, throughput: float,
                            QE: float, target_snr: float, system_temp_K: Optional[float] = None) -> float:
    """
    Estimate integration time for target SNR.
    Returns: seconds
    """
    nu = C / (5500e-10)
    hnu = H * nu
    
    signal_power = flux_jy * 1e-26 * math.pi * (aperture_m / 2)**2 * throughput * QE
    
    if system_temp_K:
        noise_power = KB * system_temp_K * 1e6
        noise_variance = noise_power**2
    else:
        noise_variance = signal_power * hnu
    
    N_signal = signal_power / hnu
    N_noise = math.sqrt(noise_variance) / hnu
    
    return (target_snr * N_noise / N_signal)**2
