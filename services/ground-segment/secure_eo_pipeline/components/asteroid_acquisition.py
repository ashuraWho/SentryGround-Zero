"""
Satellite Data Acquisition System - Asteroid Module
Simulates satellite data collection from NASA JPL Asteroid dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class AsteroidMeasurement:
    """Asteroid measurement data."""
    asteroid_id: str
    spk_id: str
    full_name: str
    designation: str
    name: Optional[str]
    neo: str
    pha: str
    h_mag: Optional[float]
    diameter_km: Optional[float]
    albedo: Optional[float]
    eccentricity: Optional[float]
    semi_major_au: Optional[float]
    perihelion_au: Optional[float]
    inclination_deg: Optional[float]
    period_days: Optional[float]
    moid_au: Optional[float]
    orbit_class: str
    satellite_id: str = "SENTRY-09"


class AsteroidAcquisitor:
    """
    Satellite data acquisition system for asteroids.
    Simulates SENTRY-09 collecting JPL asteroid data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-09", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[AsteroidMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load asteroid data from CSV."""
        data = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def _calculate_stats(self):
        """Calculate dataset statistics."""
        if not self.raw_data:
            return
        
        neo_count = 0
        pha_count = 0
        classes = set()
        
        for row in self.raw_data:
            if row.get('neo', '').strip() == 'Y':
                neo_count += 1
            if row.get('pha', '').strip() == 'Y':
                pha_count += 1
            cls = row.get('class', '').strip()
            if cls:
                classes.add(cls)
        
        self.stats = {
            "total_records": len(self.raw_data),
            "neo_count": neo_count,
            "pha_count": pha_count,
            "orbit_classes": list(classes),
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[AsteroidMeasurement]:
        """Acquire asteroid data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = AsteroidMeasurement(
                asteroid_id=row.get('id', '').strip(),
                spk_id=row.get('spkid', '').strip(),
                full_name=row.get('full_name', '').strip(),
                designation=row.get('pdes', '').strip(),
                name=row.get('name', '').strip() or None,
                neo=row.get('neo', '').strip(),
                pha=row.get('pha', '').strip(),
                h_mag=self._parse_float(row.get('H', '')),
                diameter_km=self._parse_float(row.get('diameter', '')),
                albedo=self._parse_float(row.get('albedo', '')),
                eccentricity=self._parse_float(row.get('e', '')),
                semi_major_au=self._parse_float(row.get('a', '')),
                perihelion_au=self._parse_float(row.get('q', '')),
                inclination_deg=self._parse_float(row.get('i', '')),
                period_days=self._parse_float(row.get('per', '')),
                moid_au=self._parse_float(row.get('moid_ld', '')),
                orbit_class=row.get('class', '').strip(),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NASA JPL Small-Body Database",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val: str) -> Optional[float]:
        """Parse float safely."""
        if not val or val == '':
            return None
        try:
            return float(val)
        except:
            return None
    
    def get_hazard_analysis(self, measurements: List[AsteroidMeasurement]) -> Dict:
        """Analyze hazardous asteroids."""
        neo_count = sum(1 for m in measurements if m.neo == 'Y')
        pha_count = sum(1 for m in measurements if m.pha == 'Y')
        
        neo_asteroids = [m for m in measurements if m.neo == 'Y']
        pha_asteroids = [m for m in measurements if m.pha == 'Y']
        
        return {
            "total_neo": neo_count,
            "total_pha": pha_count,
            "neo_percentage": (neo_count / len(measurements) * 100) if measurements else 0,
            "pha_percentage": (pha_count / len(measurements) * 100) if measurements else 0,
        }
    
    def get_orbital_analysis(self, measurements: List[AsteroidMeasurement]) -> Dict:
        """Analyze orbital characteristics."""
        eccentricities = []
        inclinations = []
        periods = []
        diameters = []
        
        for m in measurements:
            if m.eccentricity is not None:
                eccentricities.append(m.eccentricity)
            if m.inclination_deg is not None:
                inclinations.append(m.inclination_deg)
            if m.period_days is not None:
                periods.append(m.period_days)
            if m.diameter_km is not None:
                diameters.append(m.diameter_km)
        
        return {
            "avg_eccentricity": sum(eccentricities) / len(eccentricities) if eccentricities else 0,
            "avg_inclination_deg": sum(inclinations) / len(inclinations) if inclinations else 0,
            "avg_period_days": sum(periods) / len(periods) if periods else 0,
            "avg_diameter_km": sum(diameters) / len(diameters) if diameters else 0,
            "largest_km": max(diameters) if diameters else 0,
            "smallest_km": min(diameters) if diameters else 0,
        }
    
    def get_class_analysis(self, measurements: List[AsteroidMeasurement]) -> Dict:
        """Analyze orbit class distribution."""
        classes = {}
        
        for m in measurements:
            classes[m.orbit_class] = classes.get(m.orbit_class, 0) + 1
        
        return {
            "class_distribution": classes,
            "main_belt_count": classes.get("MBA", 0),
            "apollo_count": classes.get("APO", 0),
            "aten_count": classes.get("ATE", 0),
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "full_name": m.full_name,
                    "designation": m.designation,
                    "neo": m.neo,
                    "pha": m.pha,
                    "diameter_km": m.diameter_km,
                    "orbit_class": m.orbit_class,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"asteroid_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(filepath, 'w') as f:
            json.dump(telemetry, f, indent=2)
        
        return filepath
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            "satellite_id": self.satellite_id,
            "status": "ACTIVE" if self.current_measurements else "IDLE",
            "records_loaded": len(self.raw_data),
            "in_memory": len(self.current_measurements),
        }
    
    def get_ocean_summary(self, measurements: List[AsteroidMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "unique_asteroids": len(set(m.asteroid_id for m in measurements)),
            "neo_count": sum(1 for m in measurements if m.neo == 'Y'),
            "pha_count": sum(1 for m in measurements if m.pha == 'Y'),
        }
    
    def get_climate_trends(self, measurements: List[AsteroidMeasurement]) -> Dict:
        """Get climate trends for console display."""
        hazard = self.get_hazard_analysis(measurements)
        orbit = self.get_orbital_analysis(measurements)
        cls = self.get_class_analysis(measurements)
        
        return {
            "neo_count": hazard.get('total_neo', 0),
            "pha_count": hazard.get('total_pha', 0),
            "avg_period_days": orbit.get('avg_period_days', 0),
            "avg_diameter_km": orbit.get('avg_diameter_km', 0),
            "main_belt_count": cls.get('main_belt_count', 0),
        }


def initialize_asteroid_satellite(satellite_id: str = "SENTRY-09") -> AsteroidAcquisitor:
    """Initialize asteroid acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "asteroids", "asteroid_data.csv")
    
    if os.path.exists(data_path):
        return AsteroidAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Asteroid data not found at {data_path}")
        return AsteroidAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_asteroid_satellite()
    
    print("=== SENTRY-09 Asteroid Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=500)
    print(f"\nAcquired: {len(measurements)}")
    
    hazard = acquisitor.get_hazard_analysis(measurements)
    print(f"\nHazard Analysis:")
    print(f"  NEO: {hazard.get('total_neo', 0)}")
    print(f"  PHA: {hazard.get('total_pha', 0)}")
    
    orbit = acquisitor.get_orbital_analysis(measurements)
    print(f"\nOrbital Analysis:")
    print(f"  Avg Period: {orbit.get('avg_period_days', 0):.2f} days")
    print(f"  Avg Diameter: {orbit.get('avg_diameter_km', 0):.2f} km")