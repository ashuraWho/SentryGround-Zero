"""
Orbital Mechanics Module for SentryGround-Zero.

Implements:
- Keplerian to Cartesian coordinate transforms
- SGP4/SDP4 simplified propagation
- Ground track computation
- Pass prediction
- TLE generation from OrbitalElements
- LLA (Lat/Lon/Alt) conversion

Physics references:
- Vallado, "Fundamentals of Astrodynamics and Applications"
- NOAA/NASA SP-8003 (SECULAR AND LONG-PERIOD TERMS)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

GM_EARTH = 3.986004418e14
R_EARTH = 6_378_137.0
MU_DEG = 0.05804765625
XKE = 0.07436685316871385
XJ2 = 0.00108262998905
XJ3 = -0.00000253215306
XJ4 = -0.00000161098761


@dataclass(frozen=True)
class OrbitalState:
    """Cartesian position/velocity in ECI (Earth-Centered Inertial) frame."""
    x_km: float
    y_km: float
    z_km: float
    vx_km_s: float
    vy_km_s: float
    vz_km_s: float
    timestamp: datetime


@dataclass(frozen=True)
class GeodeticState:
    """Geodetic coordinates (Latitude, Longitude, Altitude)."""
    lat_deg: float
    lon_deg: float
    alt_km: float
    timestamp: datetime


@dataclass(frozen=True)
class PassEvent:
    """Ground station pass event."""
    aos: datetime
    los: datetime
    max_elevation_deg: float
    max_time: datetime
    duration_min: float


def julian_date(dt: datetime) -> float:
    """Convert datetime to Julian Date (UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    unix_ms = dt.timestamp()
    jd = 2440587.5 + unix_ms / 86400.0
    return jd


def julian_centuries(jd: float) -> float:
    """Julian centuries from J2000.0."""
    return (jd - 2451545.0) / 36525.0


def degrees_to_radians(deg: float) -> float:
    return deg * math.pi / 180.0


def radians_to_degrees(rad: float) -> float:
    return rad * 180.0 / math.pi


def keplerian_to_cartesian(
    a_km: float,
    e: float,
    i_deg: float,
    omega_deg: float,
    Omega_deg: float,
    nu_deg: float,
    M_deg: Optional[float] = None,
) -> Tuple[float, float, float, float, float, float]:
    """
    Convert Keplerian elements to ECI Cartesian position/velocity.
    
    Args:
        a_km: Semi-major axis (km)
        e: Eccentricity
        i_deg: Inclination (deg)
        omega_deg: Argument of perigee (deg)
        Omega_deg: Right ascension of ascending node (deg)
        nu_deg: True anomaly (deg), or M_deg if M_deg provided
        M_deg: Mean anomaly (deg), alternative to nu_deg
    
    Returns:
        (x, y, z, vx, vy, vz) in km and km/s (ECI J2000)
    """
    i = degrees_to_radians(i_deg)
    Omega = degrees_to_radians(Omega_deg)
    omega = degrees_to_radians(omega_deg)
    
    if M_deg is not None:
        M = degrees_to_radians(M_deg)
        ecc_anom = _solve_kepler(M, e)
        nu = 2 * math.atan2(
            math.sqrt(1 + e) * math.sin(ecc_anom / 2),
            math.sqrt(1 - e) * math.cos(ecc_anom / 2)
        )
    else:
        nu = degrees_to_radians(nu_deg)
    
    p = a_km * (1 - e * e)
    r = p / (1 + e * math.cos(nu))
    
    x_perif = r * math.cos(nu)
    y_perif = r * math.sin(nu)
    
    v_mag = math.sqrt(GM_EARTH / p)
    vx_perif = -v_mag * math.sin(nu)
    vy_perif = v_mag * (e + math.cos(nu))
    
    cos_O = math.cos(Omega)
    sin_O = math.sin(Omega)
    cos_i = math.cos(i)
    sin_i = math.sin(i)
    cos_o = math.cos(omega)
    sin_o = math.sin(omega)
    
    Qxx = cos_o * cos_O - sin_o * sin_O * cos_i
    Qxy = cos_o * sin_O + sin_o * cos_O * cos_i
    Qyx = -sin_o * cos_O - cos_o * sin_O * cos_i
    Qyy = -sin_o * sin_O + cos_o * cos_O * cos_i
    Qzx = sin_o * sin_i
    Qzy = cos_o * sin_i
    
    x = Qxx * x_perif + Qxy * y_perif
    y = Qyx * x_perif + Qyy * y_perif
    z = Qzx * x_perif + Qzy * y_perif
    
    vx = Qxx * vx_perif + Qxy * vy_perif
    vy = Qyx * vx_perif + Qyy * vy_perif
    vz = Qzx * vx_perif + Qzy * vy_perif
    
    return x, y, z, vx, vy, vz


def _solve_kepler(M: float, e: float, tol: float = 1e-12) -> float:
    """Solve Kepler's equation M = E - e*sin(E) via Newton-Raphson."""
    if e < 0.8:
        E = M if e < 0.5 else M + e * math.sin(M)
    else:
        E = math.pi
    
    for _ in range(50):
        f = E - e * math.sin(E) - M
        if abs(f) < tol:
            return E
        f_prime = 1 - e * math.cos(E)
        E -= f / f_prime
    return E


def eci_to_geodetic(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Convert ECI (X,Y,Z) to geodetic (lat, lon, alt) using WGS84.
    
    Args:
        x, y, z: ECI position in km
    
    Returns:
        (lat_deg, lon_deg, alt_km)
    """
    a = R_EARTH / 1000.0
    f = 1.0 / 298.257223563
    e2 = 2 * f - f * f
    
    p = math.sqrt(x * x + y * y)
    lon = math.atan2(y, x)
    
    lat = math.atan2(z, p * (1 - e2))
    
    for _ in range(10):
        sin_lat = math.sin(lat)
        N = a / math.sqrt(1 - e2 * sin_lat * sin_lat)
        lat = math.atan2(z + e2 * N * sin_lat, p)
    
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    N = a / math.sqrt(1 - e2 * sin_lat * sin_lat)
    alt = p / cos_lat - N
    
    return radians_to_degrees(lat), radians_to_degrees(lon), alt


def geodetic_to_eci(lat_deg: float, lon_deg: float, alt_km: float) -> Tuple[float, float, float]:
    """
    Convert geodetic (lat, lon, alt) to ECI (X, Y, Z) using WGS84.
    """
    a = R_EARTH / 1000.0
    f = 1.0 / 298.257223563
    e2 = 2 * f - f * f
    
    lat = degrees_to_radians(lat_deg)
    lon = degrees_to_radians(lon_deg)
    
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    N = a / math.sqrt(1 - e2 * sin_lat * sin_lat)
    
    x = (N + alt_km) * cos_lat * math.cos(lon)
    y = (N + alt_km) * cos_lat * math.sin(lon)
    z = (N * (1 - e2) + alt_km) * sin_lat
    
    return x, y, z


def gmst_angle(jd: float) -> float:
    """Greenwich Mean Sidereal Time angle in radians."""
    T = (jd - 2451545.0) / 36525.0
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + T * T * (0.000387933 - T / 38710000.0)
    gmst = gmst % 360.0
    return degrees_to_radians(gmst)


def eci_to_ecef(x: float, y: float, z: float, jd: float) -> Tuple[float, float, float]:
    """
    Convert ECI to ECEF coordinates, accounting for Earth rotation.
    """
    gmst = gmst_angle(jd)
    cos_gmst = math.cos(gmst)
    sin_gmst = math.sin(gmst)
    
    return (
        x * cos_gmst + y * sin_gmst,
        -x * sin_gmst + y * cos_gmst,
        z
    )


def orbital_period(a_km: float) -> float:
    """Calculate orbital period from semi-major axis (Kepler's 3rd law)."""
    a_m = a_km * 1000.0
    T_s = 2 * math.pi * math.sqrt(a_m ** 3 / GM_EARTH)
    return T_s / 60.0


def orbital_velocity(a_km: float, e: float = 0.0, r_km: Optional[float] = None) -> float:
    """
    Calculate orbital velocity using vis-viva equation.
    If r_km provided, calculates at that radius; otherwise at semi-major axis.
    """
    if r_km is None:
        r_km = a_km
    v_m_s = math.sqrt(GM_EARTH * (2.0 / (r_km * 1000.0) - 1.0 / (a_km * 1000.0)))
    return v_m_s / 1000.0


def escape_velocity(r_km: float) -> float:
    """Calculate escape velocity at given radius."""
    return math.sqrt(2 * GM_EARTH / (r_km * 1000.0)) / 1000.0


def mean_motion(a_km: float) -> float:
    """Mean motion in revolutions per day (n)."""
    n_rad_s = math.sqrt(GM_EARTH / (a_km * 1000.0) ** 3)
    return n_rad_s * 86164.0905 / (2 * math.pi)


def sgp4_propagate(
    jd_epoch: float,
    mean_motion: float,
    eccentricity: float,
    inclination_deg: float,
    raan_deg: float,
    arg_perigee_deg: float,
    mean_anomaly_deg: float,
    jd_target: float,
) -> Optional[Tuple[float, float, float, float, float, float]]:
    """
    Simplified SGP4 propagator (simplified version from Vallado).
    
    Returns ECI position/velocity at jd_target, or None if satellite is decaying.
    """
    dt_min = (jd_target - jd_epoch) * 1440.0
    
    if abs(dt_min) > 525600:
        return None
    
    a = (XKE / mean_motion) ** (2.0 / 3.0) * (1.0 - eccentricity ** 2)
    n = mean_motion
    
    M = degrees_to_radians(mean_anomaly_deg + n * dt_min)
    e = eccentricity
    i = degrees_to_radians(inclination_deg)
    omega = degrees_to_radians(arg_perigee_deg)
    Omega = degrees_to_radians(raan_deg + mean_motion * dt_min * (1.0 + 3.0 / 2.0 * (5.0 * math.cos(i) ** 2 - 1.0) * eccentricity))
    
    E = _solve_kepler(M, e)
    nu = 2 * math.atan2(
        math.sqrt(1 + e) * math.sin(E / 2),
        math.sqrt(1 - e) * math.cos(E / 2)
    )
    
    r = a * (1 - e * math.cos(E))
    
    x_perif = r * math.cos(nu)
    y_perif = r * math.sin(nu)
    
    v_mag = math.sqrt(GM_EARTH * (2 / (r * 1000) - 1 / (a * 1000))) / 1000
    vx_perif = -v_mag * math.sin(nu)
    vy_perif = v_mag * (e + math.cos(nu))
    
    cos_O, sin_O = math.cos(Omega), math.sin(Omega)
    cos_i, sin_i = math.cos(i), math.sin(i)
    cos_o, sin_o = math.cos(omega), math.sin(omega)
    
    x = (cos_o * cos_O - sin_o * sin_O * cos_i) * x_perif + (-sin_o * cos_O - cos_o * sin_O * cos_i) * y_perif
    y = (cos_o * sin_O + sin_o * cos_O * cos_i) * x_perif + (-sin_o * sin_O + cos_o * cos_O * cos_i) * y_perif
    z = (sin_o * sin_i) * x_perif + (cos_o * sin_i) * y_perif
    
    vx = (cos_o * cos_O - sin_o * sin_O * cos_i) * vx_perif + (-sin_o * cos_O - cos_o * sin_O * cos_i) * vy_perif
    vy = (cos_o * sin_O + sin_o * cos_O * cos_i) * vx_perif + (-sin_o * sin_O + cos_o * cos_O * cos_i) * vy_perif
    vz = (sin_o * sin_i) * vx_perif + (cos_o * sin_i) * vy_perif
    
    return x, y, z, vx, vy, vz


def propagate_orbit(
    epoch: datetime,
    a_km: float,
    e: float,
    i_deg: float,
    raan_deg: float,
    arg_perigee_deg: float,
    mean_anomaly_deg: float,
    target_time: Optional[datetime] = None,
) -> OrbitalState:
    """
    Propagate orbit to target time from epoch state.
    
    Uses simplified two-body propagation with J2 perturbation for RAAN precession.
    """
    if target_time is None:
        target_time = datetime.now(timezone.utc)
    
    jd_epoch = julian_date(epoch)
    jd_target = julian_date(target_time)
    dt_min = (jd_target - jd_epoch) * 1440.0
    
    n = math.sqrt(GM_EARTH / (a_km * 1000.0) ** 3)
    
    M_dot = n * 60.0
    M_new = degrees_to_radians(mean_anomaly_deg + M_dot * dt_min)
    
    if e < 0.001:
        p = a_km * (1 - e * e)
        r = p / (1 + e * math.cos(0))
        v_mag = math.sqrt(GM_EARTH / p) / 1000
        nu = 0
    else:
        E = _solve_kepler(M_new, e)
        nu = 2 * math.atan2(
            math.sqrt(1 + e) * math.sin(E / 2),
            math.sqrt(1 - e) * math.cos(E / 2)
        )
        r = a_km * (1 - e * math.cos(E))
        v_mag = math.sqrt(GM_EARTH * (2 / (r * 1000) - 1 / (a_km * 1000))) / 1000
    
    p = a_km * (1 - e * e)
    x_perif = r * math.cos(nu)
    y_perif = r * math.sin(nu)
    vx_perif = -v_mag * math.sin(nu)
    vy_perif = v_mag * (e + math.cos(nu))
    
    i = degrees_to_radians(i_deg)
    Omega_new = degrees_to_radians(raan_deg + _raan_precession_rate(a_km, i_deg, e) * dt_min)
    omega = degrees_to_radians(arg_perigee_deg)
    
    cos_O, sin_O = math.cos(Omega_new), math.sin(Omega_new)
    cos_i, sin_i = math.cos(i), math.sin(i)
    cos_o, sin_o = math.cos(omega), math.sin(omega)
    
    Q11 = cos_o * cos_O - sin_o * sin_O * cos_i
    Q12 = cos_o * sin_O + sin_o * cos_O * cos_i
    Q21 = -sin_o * cos_O - cos_o * sin_O * cos_i
    Q22 = -sin_o * sin_O + cos_o * cos_O * cos_i
    Q31 = sin_o * sin_i
    Q32 = cos_o * sin_i
    
    x = Q11 * x_perif + Q21 * y_perif
    y = Q12 * x_perif + Q22 * y_perif
    z = Q31 * x_perif + Q32 * y_perif
    
    vx = Q11 * vx_perif + Q21 * vy_perif
    vy = Q12 * vx_perif + Q22 * vy_perif
    vz = Q31 * vx_perif + Q32 * vy_perif
    
    return OrbitalState(x, y, z, vx, vy, vz, target_time)


def _raan_precession_rate(a_km: float, i_deg: float, e: float) -> float:
    """
    J2-induced RAAN precession rate in deg/min.
    
    Formula: dΩ/dt = -1.5 * n * J2 * (R_e / p)² * cos(i)
    """
    p = a_km * (1 - e * e)
    n_rad_min = math.sqrt(GM_EARTH / (a_km * 1000) ** 3) * 60
    p_term = (R_EARTH / 1000 / p) ** 2
    return -1.5 * n_rad_min * XJ2 * p_term * math.cos(degrees_to_radians(i_deg))


def get_orbital_state_at_time(
    epoch: datetime,
    a_km: float,
    e: float,
    i_deg: float,
    raan_deg: float,
    arg_perigee_deg: float,
    mean_anomaly_deg: float,
    target_time: datetime,
) -> OrbitalState:
    """Get ECI orbital state at a specific time."""
    return propagate_orbit(epoch, a_km, e, i_deg, raan_deg, arg_perigee_deg, mean_anomaly_deg, target_time)


def get_current_position(
    a_km: float,
    e: float,
    i_deg: float,
    raan_deg: float,
    arg_perigee_deg: float,
    mean_anomaly_deg: float,
    epoch: Optional[datetime] = None,
) -> GeodeticState:
    """
    Calculate current geodetic position from orbital elements.
    Uses epoch as reference, or current time if not provided.
    """
    if epoch is None:
        epoch = datetime.now(timezone.utc)
    
    state = propagate_orbit(epoch, a_km, e, i_deg, raan_deg, arg_perigee_deg, mean_anomaly_deg)
    jd = julian_date(state.timestamp)
    
    ecef_x, ecef_y, ecef_z = eci_to_ecef(state.x_km, state.y_km, state.z_km, jd)
    lat, lon, alt = eci_to_geodetic(ecef_x, ecef_y, ecef_z)
    
    return GeodeticState(lat, lon, alt, state.timestamp)


def predict_next_pass(
    gs_lat: float,
    gs_lon: float,
    gs_alt_km: float,
    a_km: float,
    e: float,
    i_deg: float,
    raan_deg: float,
    arg_perigee_deg: float,
    mean_anomaly_deg: float,
    min_elevation_deg: float = 5.0,
    duration_hours: float = 24.0,
) -> list[PassEvent]:
    """
    Predict satellite passes over a ground station.
    
    Args:
        gs_lat: Ground station latitude (deg)
        gs_lon: Ground station longitude (deg)
        gs_alt_km: Ground station altitude (km)
        Orbital elements...
        min_elevation_deg: Minimum elevation for pass
        duration_hours: Prediction window
    
    Returns:
        List of PassEvent objects
    """
    gs_x, gs_y, gs_z = geodetic_to_eci(gs_lat, gs_lon, gs_alt_km)
    
    T_orb_min = orbital_period(a_km)
    T_orb_s = T_orb_min * 60
    steps = int(duration_hours * 3600 / 10)
    
    passes = []
    in_pass = False
    pass_start = None
    max_el = 0.0
    max_el_time = None
    
    epoch = datetime.now(timezone.utc)
    
    for step in range(steps):
        t = epoch.timestamp() + step * 10
        target_time = datetime.fromtimestamp(t, tz=timezone.utc)
        
        state = propagate_orbit(epoch, a_km, e, i_deg, raan_deg, arg_perigee_deg, mean_anomaly_deg, target_time)
        jd = julian_date(target_time)
        
        ecef_x, ecef_y, ecef_z = eci_to_ecef(state.x_km, state.y_km, state.z_km, jd)
        
        dx = ecef_x - gs_x
        dy = ecef_y - gs_y
        dz = ecef_z - gs_z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        
        gs_gs_dist = math.sqrt(gs_x * gs_x + gs_y * gs_y + gs_z * gs_z)
        sat_gs_dist = dist * 1000
        
        dot = (gs_x * ecef_x + gs_y * ecef_y + gs_z * ecef_z) / (gs_gs_dist * sat_gs_dist)
        dot = max(-1.0, min(1.0, dot))
        el_rad = math.asin(dot)
        el_deg = radians_to_degrees(el_rad)
        
        if el_deg >= min_elevation_deg:
            if not in_pass:
                in_pass = True
                pass_start = target_time
            if el_deg > max_el:
                max_el = el_deg
                max_el_time = target_time
        else:
            if in_pass and pass_start and max_el_time:
                duration = (target_time - pass_start).total_seconds() / 60
                if duration > 0.5:
                    passes.append(PassEvent(
                        aos=pass_start,
                        los=target_time,
                        max_elevation_deg=max_el,
                        max_time=max_el_time,
                        duration_min=duration
                    ))
                in_pass = False
                max_el = 0.0
                max_el_time = None
                pass_start = None
    
    if in_pass and pass_start and max_el_time:
        passes.append(PassEvent(
            aos=pass_start,
            los=datetime.fromtimestamp(epoch.timestamp() + duration_hours * 3600, tz=timezone.utc),
            max_elevation_deg=max_el,
            max_time=max_el_time,
            duration_min=(datetime.fromtimestamp(epoch.timestamp() + duration_hours * 3600, tz=timezone.utc) - pass_start).total_seconds() / 60
        ))
    
    return passes


def generate_tle_from_elements(
    name: str,
    a_km: float,
    e: float,
    i_deg: float,
    raan_deg: float,
    arg_perigee_deg: float,
    mean_anomaly_deg: float,
    epoch: Optional[datetime] = None,
) -> Tuple[str, str, str]:
    """
    Generate a TLE (Two-Line Element) from orbital elements.
    
    Returns:
        (line0_name, line1, line2)
    """
    if epoch is None:
        epoch = datetime.now(timezone.utc)
    
    n = mean_motion(a_km)
    n_sixd = round(n * 1000000)
    n_first = n_sixd // 100
    n_last = n_sixd % 100
    
    e_int = int(round(e * 10000000))
    
    i_int = int(round(i_deg * 10000))
    
    raan_int = int(round(raan_deg * 10000))
    
    omega_int = int(round(arg_perigee_deg * 10000))
    
    M_int = int(round(mean_anomaly_deg * 10000))
    
    year = epoch.year
    if year < 2000:
        year -= 1900
    else:
        year -= 2000
    
    day_of_year = epoch.timetuple().tm_yday
    seconds = epoch.hour * 3600 + epoch.minute * 60 + epoch.second
    day_frac = day_of_year + seconds / 86400.0
    
    sat_num = 99999
    
    line0 = name.upper().replace(' ', '-')[:24].ljust(24)
    line1 = (
        f"1 {sat_num:5d}U 99999A   {year:2d}{day_frac:12.8f}  .00000000  00000-0  00000-0 0  "
        f"{str(raan_int).zfill(8)}"
    )
    checksum1 = sum(int(c) for c in line1 if c.isdigit()) % 10
    line1 += f"{checksum1}"
    
    line2 = (
        f"2 {sat_num:5d} "
        f"{str(i_int).zfill(8)} "
        f"{str(raan_int).zfill(8)} "
        f"{str(omega_int).zfill(8)} "
        f"{str(e_int).zfill(8)} "
        f"{str(M_int).zfill(8)} "
        f"{str(n_first).zfill(8)}"
    )
    checksum2 = sum(int(c) for c in line2 if c.isdigit()) % 10
    line2 += f"{checksum2}"
    
    return line0, line1, line2


def orbital_regime(a_km: float) -> str:
    """Determine orbital regime from semi-major axis."""
    alt = a_km - R_EARTH / 1000
    
    if alt < 2000:
        return "LEO"
    elif alt < 35786:
        return "MEO"
    elif 35786 <= alt < 40000:
        return "GEO"
    elif 380000 < a_km < 400000:
        return "Lunar Transfer"
    elif a_km > 380000:
        return "HEO/Planetary"
    elif 6500 < a_km < 7000 and alt < 2000:
        return "ISS-like LEO"
    elif 14500 < a_km < 15000:
        return "GPS/MEO"
    else:
        return "HEO"


def daylight_fraction(inc_deg: float, raan_deg: float = 0.0) -> float:
    """
    Estimate fraction of orbit in sunlight (no eclipse).
    Simplified: assumes circular orbit.
    """
    beta = abs(raan_deg)
    if inc_deg < 90:
        daylight = 1.0 - abs(90 - inc_deg) / 180
    else:
        daylight = 1.0 - abs(inc_deg - 90) / 180
    return max(0.5, min(1.0, daylight))


def eclipse_duration(period_min: float, inc_deg: float, alt_km: float) -> float:
    """
    Estimate maximum eclipse duration in minutes.
    Uses simple geometric shadow model.
    """
    if inc_deg < 90:
        beta = inc_deg
    else:
        beta = 180 - inc_deg
    
    r_earth_deg = math.asin(R_EARTH / (R_EARTH + alt_km))
    eclipse_half_angle = math.asin(math.cos(degrees_to_radians(beta)) / (1 + alt_km / R_EARTH))
    
    eclipse_frac = 1 - eclipse_half_angle / math.pi
    return max(0, period_min * eclipse_frac)


def dopsion_factor(gs_lat: float, sat_el_deg: float) -> float:
    """
    Calculate GPS/DGNSS Dilution of Precision approximation.
    Simplified geometric factor.
    """
    if sat_el_deg < 5:
        return 10.0
    elif sat_el_deg < 15:
        return 5.0
    elif sat_el_deg < 30:
        return 2.5
    elif sat_el_deg < 45:
        return 1.5
    else:
        return 1.0
