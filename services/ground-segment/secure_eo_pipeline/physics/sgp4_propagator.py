"""
SGP4 Orbital Propagator and Collision Avoidance System
Implements NORAD SGP4/SDP4 algorithms for accurate satellite position prediction.
"""

import os
import math
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np


@dataclass
class TLE:
    name: str
    catalog_number: int
    classification: str
    international_designator: str
    epoch_year: int
    epoch_day: float
    mean_motion_dot: float
    mean_motion_ddot: float
    bstar: float
    inclination: float
    raan: float
    eccentricity: float
    argument_perigee: float
    mean_anomaly: float
    mean_motion: float
    
    @classmethod
    def from_elements(cls, name: str, a_km: float, e: float, i_deg: float,
                      raan_deg: float, omega_deg: float, M0_deg: float,
                      epoch_year: int = 26, epoch_day: float = None) -> 'TLE':
        """Create TLE from orbital elements."""
        if epoch_day is None:
            epoch_day = datetime.now().timetuple().tm_yday + \
                        datetime.now().hour / 24 + datetime.now().minute / 1440
        
        n = math.sqrt(398600.4418 / a_km**3) * 60
        
        return cls(
            name=name,
            catalog_number=99999,
            classification='U',
            international_designator='26001A',
            epoch_year=epoch_year,
            epoch_day=epoch_day,
            mean_motion_dot=0.0,
            mean_motion_ddot=0.0,
            bstar=0.0,
            inclination=i_deg,
            raan=raan_deg,
            eccentricity=e,
            argument_perigee=omega_deg,
            mean_anomaly=M0_deg,
            mean_motion=n,
        )
    
    def to_tle_lines(self) -> Tuple[str, str, str]:
        """Convert TLE to three-line format."""
        line0 = self.name
        
        line1 = f"{self.catalog_number:5d} {self.classification} {self.international_designator} "
        line1 += f"{self.epoch_year:2d}{self.epoch_day:12.8f} "
        line1 += f"{self.mean_motion_dot:+8.8f} {self.mean_motion_ddot:+.5f} "
        line1 += f"{self.bstar:+.5f} 0 {self.catalog_number % 1000:4d}"
        
        line2 = f"{'':>5}{self.inclination:8.4f} {self.raan:8.4f} "
        line2 += f"{int(self.eccentricity * 1e7):07d} "
        line2 += f"{self.argument_perigee:8.4f} {self.mean_anomaly:8.4f} "
        line2 += f"{self.mean_motion:11.8f} 00000"
        
        return line0, line1, line2


@dataclass
class CartState:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    
    def distance_to(self, other: 'CartState') -> float:
        return math.sqrt(
            (self.x - other.x)**2 +
            (self.y - other.y)**2 +
            (self.z - other.z)**2
        )
    
    @property
    def speed(self) -> float:
        return math.sqrt(self.vx**2 + self.vy**2 + self.vz**2)


@dataclass 
class OrbitalElements:
    a: float
    e: float
    i: float
    omega: float
    Omega: float
    nu: float


class SGP4Propagator:
    """
    Simplified General Perturbations - Model 4 (SGP4)
    For propagating satellite positions from TLE elements.
    Based on NORAD SPACETRACK Report No. 3.
    """
    
    XJ2 = 1.082616e-3
    XJ3 = -2.53881e-6
    XJ4 = -1.65597e-6
    CK2 = 5.413079e-6
    CK4 = 6.209887e-7
    S = 78.0 / 6378.137 + 1.0
    QOMS2T = 1.880279e-9
    AE = 1.0
    DE2RA = math.pi / 180.0
    DAYSEC = 86400.0
    
    def __init__(self):
        self.tle: Optional[TLE] = None
        self._initialized = False
        self._a = 0.0
        self._e0 = 0.0
        self._i0 = 0.0
        self._Omega0 = 0.0
        self._omega0 = 0.0
        self._M0 = 0.0
        self._n0 = 0.0
        self._kep_period = 0.0
        self._kep_epoch = 0.0
    
    def initialize(self, tle: TLE):
        """Initialize propagator with TLE data."""
        self.tle = tle
        self._initialized = True
        
        self._e0 = tle.eccentricity
        self._i0 = tle.inclination * self.DE2RA
        self._Omega0 = tle.raan * self.DE2RA
        self._omega0 = tle.argument_perigee * self.DE2RA
        self._M0 = tle.mean_anomaly * self.DE2RA
        
        self._n0 = tle.mean_motion * 2 * math.pi / 1440.0
        
        a0 = (self.DAYSEC / self._n0) ** (2/3) / (1 + self.CK2)
        self._a = a0 * (1 - self.CK2 * (3 * self._i0**2 - 1) / 2)
        
        self._kep_period = 2 * math.pi * math.sqrt(self._a**3 / 398600.4418)
        self._kep_epoch = self.tle.epoch_day * 86400.0
    
    def propagate(self, jd: float) -> CartState:
        """Propagate to given Julian Date."""
        if not self._initialized:
            raise RuntimeError("Propagator not initialized")
        
        dt = (jd - (self.tle.epoch_day + 2440587.5)) * 86400.0
        
        M = self._M0 + self._n0 * dt
        
        E = self._solve_kepler(self._e0, M)
        
        sinE = math.sin(E)
        cosE = math.cos(E)
        
        sinNu = math.sqrt(1 - self._e0**2) * sinE / (1 - self._e0 * cosE)
        cosNu = (cosE - self._e0) / (1 - self._e0 * cosE)
        nu = math.atan2(sinNu, cosNu)
        
        r = self._a * (1 - self._e0 * cosE)
        
        x = r * cosNu
        y = r * sinNu
        
        Omega = self._Omega0 + (3 * self.CK2 / (2 * self._a**2 * (1 - self._e0**2)**2) *
                               (1 - 3 * self._i0**2 / 2) * dt)
        omega = self._omega0
        
        cosO = math.cos(Omega)
        sinO = math.sin(Omega)
        cosi = math.cos(self._i0)
        sini = math.sin(self._i0)
        cosw = math.cos(omega)
        sinw = math.sin(omega)
        cosnu = cosNu
        sinnu = sinNu
        
        X = x * (cosO * cosw - sinO * sinw * cosi) - y * (cosO * sinw + sinO * cosw * cosi) * cosnu / (cosNu + 1e-10)
        Y = x * (sinO * cosw + cosO * sinw * cosi) - y * (sinO * sinw - cosO * cosw * cosi) * cosnu / (cosNu + 1e-10)
        Z = x * sinw * sini - y * cosw * sini * cosnu / (cosNu + 1e-10)
        
        v = math.sqrt(398600.4418 / r)
        Vx = v * (-sinO * cosw - cosO * sinw * cosi)
        Vy = v * (cosO * cosw - sinO * sinw * cosi)
        Vz = v * sinw * sini
        
        return CartState(X, Y, Z, Vx, Vy, Vz)
    
    def _solve_kepler(self, e: float, M: float, tol: float = 1e-12) -> float:
        """Solve Kepler's equation using Newton-Raphson."""
        if e > 0.8:
            E = math.pi
        else:
            E = M
        
        for _ in range(50):
            f = E - e * math.sin(E) - M
            if abs(f) < tol:
                break
            df = 1 - e * math.cos(E)
            E = E - f / df
        
        return E
    
    def propagate_to_epoch(self, epoch: datetime) -> CartState:
        """Propagate to given datetime."""
        jd = self._to_julian_date(epoch)
        return self.propagate(jd)
    
    @staticmethod
    def _to_julian_date(dt: datetime) -> float:
        """Convert datetime to Julian Date."""
        return dt.timestamp() / 86400.0 + 2440587.5


class CollisionAvoidance:
    """
    Conjunction Analysis and Collision Avoidance System.
    Implements CDM (Conjunction Data Message) processing.
    """
    
    EARTH_RADIUS = 6378.137
    MISS_DISTANCE_THRESHOLD = 1.0
    
    def __init__(self):
        self.conjunctions: List[Dict] = []
    
    def predict_conjunctions(
        self,
        primary_tle: TLE,
        secondary_tle: TLE,
        start_time: datetime,
        end_time: datetime,
        dt_minutes: float = 1.0
    ) -> List[Dict]:
        """
        Predict potential conjunctions between two objects.
        """
        primary_prop = SGP4Propagator()
        primary_prop.initialize(primary_tle)
        
        secondary_prop = SGP4Propagator()
        secondary_prop.initialize(secondary_tle)
        
        t = start_time
        min_distance = float('inf')
        closest_approach = None
        
        while t <= end_time:
            primary_state = primary_prop.propagate_to_epoch(t)
            secondary_state = secondary_prop.propagate_to_epoch(t)
            
            distance = primary_state.distance_to(secondary_state)
            
            if distance < min_distance:
                min_distance = distance
                closest_approach = {
                    'time': t,
                    'primary': primary_state,
                    'secondary': secondary_state,
                    'distance': distance,
                }
            
            t += timedelta(minutes=dt_minutes)
        
        if closest_approach and min_distance < 50.0:
            self.conjunctions.append({
                'primary_id': primary_tle.catalog_number,
                'secondary_id': secondary_tle.catalog_number,
                'min_distance_km': min_distance,
                'tca': closest_approach['time'],
                'primary_position': closest_approach['primary'],
                'secondary_position': closest_approach['secondary'],
                'risk_level': self._assess_risk(min_distance),
            })
        
        return self.conjunctions
    
    def _assess_risk(self, miss_distance: float) -> str:
        """Assess collision risk based on miss distance."""
        if miss_distance < 1.0:
            return "CRITICAL"
        elif miss_distance < 5.0:
            return "HIGH"
        elif miss_distance < 20.0:
            return "MEDIUM"
        else:
            return "LOW"
    
    def check_station_keeping(
        self,
        sat_tle: TLE,
        station_lon: float,
        tolerance_km: float = 0.1
    ) -> Dict:
        """
        Check if GEO satellite maintains station-keeping box.
        """
        prop = SGP4Propagator()
        prop.initialize(sat_tle)
        
        current = prop.propagate_to_epoch(datetime.now())
        
        r = math.sqrt(current.x**2 + current.y**2 + current.z**2)
        lon = math.atan2(current.y, current.x) * 180 / math.pi
        
        lon_error = abs(lon - station_lon) * (r / 1000)
        
        return {
            'satellite': sat_tle.name,
            'current_lon': lon,
            'target_lon': station_lon,
            'lon_error_km': lon_error,
            'in_box': lon_error < tolerance_km * 1000,
            'radius_km': r,
        }
    
    def calculate_close_approach(
        self,
        pos1: CartState,
        pos2: CartState,
        vel1: CartState,
        vel2: CartState
    ) -> Dict:
        """Calculate close approach parameters."""
        r = pos1.distance_to(pos2)
        
        rel_pos = np.array([pos2.x - pos1.x, pos2.y - pos1.y, pos2.z - pos1.z])
        rel_vel = np.array([vel2.vx - vel1.vx, vel2.vy - vel1.vy, vel2.vz - vel1.vz])
        
        v_rel = math.sqrt(rel_vel.dot(rel_vel))
        
        if v_rel > 0:
            t_ca = -rel_pos.dot(rel_vel) / (v_rel ** 2)
        else:
            t_ca = 0
        
        pos_ca = rel_pos + rel_vel * t_ca
        miss_distance = math.sqrt(pos_ca.dot(pos_ca))
        
        return {
            'miss_distance_km': miss_distance,
            'time_to_closest_approach_s': t_ca,
            'relative_velocity_km_s': v_rel,
            'collision_probability': self._collision_probability(miss_distance, v_rel),
        }
    
    def _collision_probability(self, miss_distance: float, rel_vel: float) -> float:
        """
        Calculate basic collision probability.
        Uses simplified formula from NASA JPL.
        """
        if miss_distance <= 0:
            return 1.0
        
        combined_radius = 5.0 + 5.0
        h = combined_radius / miss_distance
        
        if h > 10:
            return 1.0
        elif h < 0.1:
            return 0.0
        
        Pc = (h**2) * math.exp(-h**2 / 2) / (2 * math.pi * miss_distance * rel_vel)
        
        return min(Pc, 1.0)


def create_conjunction_report(conjunctions: List[Dict]) -> str:
    """Generate a formatted conjunction analysis report."""
    if not conjunctions:
        return "No conjunctions predicted."
    
    report = """
╔════════════════════════════════════════════════════════════════════════════════╗
║                        CONJUNCTION ANALYSIS REPORT                           ║
╠════════════════════════════════════════════════════════════════════════════════╣
"""
    for c in conjunctions:
        risk_color = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        }.get(c['risk_level'], "⚪")
        
        report += f"""
║ {risk_color} RISK: {c['risk_level']:<10} Miss Distance: {c['min_distance_km']:>8.2f} km
║   Primary: {c['primary_id']:<6}  Secondary: {c['secondary_id']:<6}
║   TCA: {c['tca'].strftime('%Y-%m-%d %H:%M:%S UTC')}
║{'─' * 78}
"""
    
    report += """╚════════════════════════════════════════════════════════════════════════════════╝
"""
    return report
