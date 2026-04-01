"""
Space Weather Module
Monitors solar activity, geomagnetic storms, and space radiation.
"""

import math
import random
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np


@dataclass
class SolarFlare:
    date: datetime
    classification: str
    intensity: float
    probability: float
    duration_hours: float
    affected_frequencies: List[str]
    radiation_storm: bool


@dataclass
class GeomagneticStorm:
    date: datetime
    kp_index: float
    severity: str
    duration_hours: float
    affected_satellites: int


@dataclass
class SpaceWeatherReport:
    timestamp: datetime
    solar_cycle_phase: str
    sunspot_number: int
    f10_7_flux: float
    solar_wind_speed: float
    bx_interplanetary: float
    by_interplanetary: float
    bz_interplanetary: float
    proton_density: float
    electron_density: float
    temperature: float
    kp_index: float
    ap_index: float
    fluence_1mev: float
    fluence_10mev: float
    fluence_100mev: float


class SolarActivityMonitor:
    """Monitor and predict solar activity."""
    
    CYCLE_PERIOD = 11.0
    CYCLE_START = datetime(2019, 12, 1)
    
    def __init__(self):
        self.cycle_day = (datetime.now() - self.CYCLE_START).days
        self.cycle_fraction = (self.cycle_day / 365) % self.CYCLE_PERIOD / self.CYCLE_PERIOD
    
    def get_solar_cycle_phase(self) -> str:
        """Get current solar cycle phase."""
        phase = self.cycle_fraction
        if phase < 0.1:
            return "MINIMUM"
        elif phase < 0.4:
            return "ASCENDING"
        elif phase < 0.6:
            return "MAXIMUM"
        elif phase < 0.9:
            return "DESCENDING"
        else:
            return "MINIMUM"
    
    def predict_sunspot_number(self, date: datetime = None) -> int:
        """Predict sunspot number based on solar cycle."""
        if date is None:
            date = datetime.now()
        
        phase = ((date - self.CYCLE_START).days / 365) % self.CYCLE_PERIOD / self.CYCLE_PERIOD
        
        amplitude = 120 * math.sin(phase * math.pi)
        noise = random.gauss(0, 20)
        
        return max(0, int(amplitude + noise))
    
    def predict_f107(self, date: datetime = None) -> float:
        """Predict F10.7 solar radio flux."""
        ssn = self.predict_sunspot_number(date)
        return 63.7 + 0.73 * ssn + random.gauss(0, 5)
    
    def predict_flare_probability(self, class_type: str = "M") -> float:
        """Predict probability of solar flare of given class."""
        ssn = self.predict_sunspot_number()
        
        probabilities = {
            "X": max(0.001, (ssn - 50) / 5000),
            "M": max(0.01, (ssn - 20) / 500),
            "C": max(0.1, (ssn + 30) / 300),
            "B": max(0.5, (ssn + 50) / 200),
        }
        
        return probabilities.get(class_type, 0.1)


class SolarWindModel:
    """Model solar wind conditions."""
    
    def predict_solar_wind(self, date: datetime = None) -> Dict[str, float]:
        """Predict solar wind parameters."""
        if date is None:
            date = datetime.now()
        
        hour = date.hour + date.minute / 60
        
        speed = 400 + 100 * math.sin(hour * math.pi / 12) + random.gauss(0, 30)
        density = 5 + 2 * math.sin(hour * math.pi / 12) + random.gauss(0, 1)
        temperature = 1e5 + 2e4 * math.sin(hour * math.pi / 12) + random.gauss(0, 1e4)
        
        bx = random.gauss(0, 2)
        by = random.gauss(0, 3)
        bz = random.gauss(0, 4)
        
        return {
            "speed_km_s": speed,
            "proton_density_cm3": density,
            "temperature_K": temperature,
            "bx_nt": bx,
            "by_nt": by,
            "bz_nt": bz,
            "b_total_nt": math.sqrt(bx**2 + by**2 + bz**2),
        }


class GeomagneticIndex:
    """Calculate geomagnetic indices Kp, ap, Dst."""
    
    def __init__(self):
        self.solar_wind = SolarWindModel()
    
    def predict_kp(self, date: datetime = None) -> float:
        """Predict Kp index (0-9 scale)."""
        if date is None:
            date = datetime.now()
        
        wind = self.solar_wind.predict_solar_wind(date)
        
        speed_factor = (wind["speed_km_s"] - 400) / 100
        bz_factor = max(0, -wind["bz_nt"]) / 5
        density_factor = (wind["proton_density_cm3"] - 5) / 2
        
        base_kp = 2 + speed_factor + bz_factor + density_factor
        
        hourly_variation = 1.5 * math.sin((date.hour - 6) * math.pi / 12)
        
        kp = base_kp + hourly_variation + random.gauss(0, 0.5)
        
        return max(0, min(9, round(kp)))
    
    def kp_to_ap(self, kp: float) -> float:
        """Convert Kp to ap index."""
        kp_table = {
            0: 0, 1: 3, 2: 7, 3: 15, 4: 27,
            5: 48, 6: 80, 7: 132, 8: 207, 9: 300
        }
        kp_int = int(min(9, max(0, kp)))
        return kp_table.get(kp_int, 15)
    
    def predict_dst(self, date: datetime = None) -> float:
        """Predict Dst index (nT)."""
        if date is None:
            date = datetime.now()
        
        wind = self.solar_wind.predict_solar_wind(date)
        
        bz = wind["bz_nt"]
        speed = wind["speed_km_s"]
        
        dst = -20 * max(0, -bz) * (speed - 400) / 400
        
        storm = self.predict_kp(date) >= 5
        
        if storm:
            dst -= random.uniform(20, 50)
        
        return dst
    
    def assess_storm_severity(self, kp: float) -> str:
        """Assess geomagnetic storm severity."""
        if kp >= 7:
            return "SEVERE"
        elif kp >= 6:
            return "STRONG"
        elif kp >= 5:
            return "MODERATE"
        elif kp >= 4:
            return "MINOR"
        else:
            return "QUIET"


class RadiationEnvironment:
    """Calculate space radiation environment."""
    
    def __init__(self):
        self.solar_monitor = SolarActivityMonitor()
    
    def predict_fluence(
        self,
        energy_mev: float,
        duration_days: float = 1.0,
        altitude_km: float = 550.0
    ) -> float:
        """
        Predict particle fluence at given energy and altitude.
        
        Args:
            energy_mev: Particle energy in MeV
            duration_days: Duration in days
            altitude_km: Altitude in km
            
        Returns:
            Fluence in particles/cm²/day
        """
        solar_phase = self.solar_monitor.get_solar_cycle_phase()
        
        if energy_mev <= 1:
            base_fluence = 1e8
        elif energy_mev <= 10:
            base_fluence = 1e7
        elif energy_mev <= 100:
            base_fluence = 1e5
        else:
            base_fluence = 1e2
        
        if solar_phase == "MAXIMUM":
            factor = 0.3
        elif solar_phase == "ASCENDING":
            factor = 0.5
        elif solar_phase == "DESCENDING":
            factor = 0.7
        else:
            factor = 1.0
        
        if altitude_km > 1000:
            altitude_factor = 1.5
        elif altitude_km > 500:
            altitude_factor = 1.2
        else:
            altitude_factor = 1.0
        
        fluence = base_fluence * factor * altitude_factor * duration_days
        fluence *= random.uniform(0.8, 1.2)
        
        return fluence
    
    def total_dose_rate(
        self,
        altitude_km: float,
        shielding_g_cm2: float = 1.0,
        duration_hours: float = 1.0
    ) -> float:
        """
        Calculate total ionizing dose rate.
        
        Args:
            altitude_km: Altitude in km
            shielding_g_cm2: Shielding in g/cm²
            duration_hours: Duration in hours
            
        Returns:
            Dose in rads
        """
        altitude_factor = math.exp(-altitude_km / 10000)
        
        shielding_factor = math.exp(-shielding_g_cm2 / 10)
        
        base_rate = 0.01
        
        dose_rate = base_rate * altitude_factor * shielding_factor
        
        return dose_rate * duration_hours


class SpaceWeatherCenter:
    """
    Centralized space weather monitoring and prediction system.
    """
    
    def __init__(self):
        self.solar_monitor = SolarActivityMonitor()
        self.solar_wind = SolarWindModel()
        self.geo_index = GeomagneticIndex()
        self.radiation = RadiationEnvironment()
    
    def generate_report(self, date: datetime = None) -> SpaceWeatherReport:
        """Generate comprehensive space weather report."""
        if date is None:
            date = datetime.now()
        
        wind = self.solar_wind.predict_solar_wind(date)
        kp = self.geo_index.predict_kp(date)
        ap = self.geo_index.kp_to_ap(kp)
        
        return SpaceWeatherReport(
            timestamp=date,
            solar_cycle_phase=self.solar_monitor.get_solar_cycle_phase(),
            sunspot_number=self.solar_monitor.predict_sunspot_number(date),
            f10_7_flux=self.solar_monitor.predict_f107(date),
            solar_wind_speed=wind["speed_km_s"],
            bx_interplanetary=wind["bx_nt"],
            by_interplanetary=wind["by_nt"],
            bz_interplanetary=wind["bz_nt"],
            proton_density=wind["proton_density_cm3"],
            electron_density=wind["proton_density_cm3"] * 0.8,
            temperature=wind["temperature_K"],
            kp_index=kp,
            ap_index=ap,
            fluence_1mev=self.radiation.predict_fluence(1, 1, 550),
            fluence_10mev=self.radiation.predict_fluence(10, 1, 550),
            fluence_100mev=self.radiation.predict_fluence(100, 1, 550),
        )
    
    def assess_satellite_health_impact(self, satellite: Dict) -> Dict:
        """Assess impact on satellite systems."""
        report = self.generate_report()
        
        impacts = []
        total_risk = 0.0
        
        if report.kp_index >= 5:
            impacts.append({
                "system": "TDRSS Communication",
                "severity": "MEDIUM",
                "description": "Increased ionospheric scintillation",
            })
            total_risk += 0.3
        
        if report.f10_7_flux > 150:
            impacts.append({
                "system": "Thermal Control",
                "severity": "LOW",
                "description": "Elevated upper atmosphere drag",
            })
            total_risk += 0.2
        
        dose_24h = self.radiation.total_dose_rate(
            satellite.get("altitude_km", 550),
            satellite.get("shielding_g_cm2", 1.0),
            24
        )
        
        if dose_24h > 10:
            impacts.append({
                "system": "Electronics",
                "severity": "HIGH",
                "description": f"Elevated radiation dose: {dose_24h:.1f} rads",
            })
            total_risk += 0.5
        
        if total_risk > 0.7:
            risk_level = "HIGH"
        elif total_risk > 0.4:
            risk_level = "MEDIUM"
        elif total_risk > 0.1:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"
        
        return {
            "timestamp": report.timestamp,
            "overall_risk": risk_level,
            "total_risk_score": total_risk,
            "kp_index": report.kp_index,
            "dose_24h_rads": dose_24h,
            "impacts": impacts,
            "recommendations": self._generate_recommendations(report, impacts),
        }
    
    def _generate_recommendations(self, report: SpaceWeatherReport, impacts: List) -> List[str]:
        """Generate operational recommendations."""
        recs = []
        
        if report.kp_index >= 6:
            recs.append("Consider postponing critical maneuvers")
        
        if report.f10_7_flux > 180:
            recs.append("Increased atmospheric drag expected - monitor orbit")
        
        if report.bz_interplanetary < -5:
            recs.append("Southward IMF - possible auroral activity")
        
        if report.fluence_100mev > 1e4:
            recs.append("High-energy proton event - verify SEU protection")
        
        if not recs:
            recs.append("Space weather nominal - all systems operational")
        
        return recs


def generate_space_weather_display(report: SpaceWeatherReport) -> str:
    """Generate formatted space weather display."""
    
    severity = "🟢" if report.kp_index < 4 else "🟡" if report.kp_index < 6 else "🟠" if report.kp_index < 7 else "🔴"
    
    return f"""
╔════════════════════════════════════════════════════════════════════════════════╗
║                          SPACE WEATHER CONDITIONS                            ║
╠════════════════════════════════════════════════════════════════════════════════╣
║  {severity} Geomagnetic Kp Index: {report.kp_index:.0f} ({report.ap_index:.0f} nT ap)                           ║
║  Solar Cycle Phase: {report.solar_cycle_phase:<12} Sunspot #: {report.sunspot_number:<4}                    ║
║  F10.7 Flux: {report.f10_7_flux:.1f} SFU                                              ║
╠════════════════════════════════════════════════════════════════════════════════╣
║  SOLAR WIND                                                                 ║
║  Speed: {report.solar_wind_speed:.0f} km/s  |  Bz: {report.bz_interplanetary:+.1f} nT  |  Density: {report.proton_density:.1f} p/cm³    ║
╠════════════════════════════════════════════════════════════════════════════════╣
║  RADIATION ENVIRONMENT (LEO ~550 km)                                        ║
║  >1 MeV Fluence: {report.fluence_1mev:.2e} p/cm²/day                                   ║
║  >10 MeV Fluence: {report.fluence_10mev:.2e} p/cm²/day                                  ║
║  >100 MeV Fluence: {report.fluence_100mev:.2e} p/cm²/day                                 ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""
