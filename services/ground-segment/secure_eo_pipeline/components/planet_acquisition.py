"""
Satellite Data Acquisition System - Planets Module
Simulates satellite data collection from solar system planets dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class PlanetData:
    """Planet measurement data."""
    planet: str
    color: str
    mass: float
    diameter: int
    density: int
    surface_gravity: float
    escape_velocity: float
    rotation_period: float
    length_of_day: float
    distance_from_sun: float
    perihelion: float
    aphelion: float
    orbital_period: float
    orbital_velocity: float
    orbital_inclination: float
    orbital_eccentricity: float
    obliquity_to_orbit: float
    mean_temperature: float
    surface_pressure: str
    number_of_moons: int
    ring_system: str
    global_magnetic_field: str
    satellite_id: str = "SENTRY-24"


class PlanetAcquisitor:
    """
    Satellite data acquisition system for planets.
    Simulates SENTRY-24 collecting solar system planet data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-24", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[PlanetData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load planet data from CSV."""
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
        
        self.stats = {
            "total_records": len(self.raw_data),
            "planets": [row.get('Planet', '') for row in self.raw_data],
            "data_source": "NASA Solar System Data",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[PlanetData]:
        """Acquire planet data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = PlanetData(
                planet=row.get('Planet', ''),
                color=row.get('Color', ''),
                mass=self._parse_float(row.get('Mass (10^24kg)')),
                diameter=self._parse_int(row.get('Diameter (km)')),
                density=self._parse_int(row.get('Density (kg/m^3)')),
                surface_gravity=self._parse_float(row.get('Surface Gravity(m/s^2)')),
                escape_velocity=self._parse_float(row.get('Escape Velocity (km/s)')),
                rotation_period=self._parse_float(row.get('Rotation Period (hours)')),
                length_of_day=self._parse_float(row.get('Length of Day (hours)')),
                distance_from_sun=self._parse_float(row.get('Distance from Sun (10^6 km)')),
                perihelion=self._parse_float(row.get('Perihelion (10^6 km)')),
                aphelion=self._parse_float(row.get('Aphelion (10^6 km)')),
                orbital_period=self._parse_orbital_period(row.get('Orbital Period (days)')),
                orbital_velocity=self._parse_float(row.get('Orbital Velocity (km/s)')),
                orbital_inclination=self._parse_float(row.get('Orbital Inclination (degrees)')),
                orbital_eccentricity=self._parse_float(row.get('Orbital Eccentricity')),
                obliquity_to_orbit=self._parse_float(row.get('Obliquity to Orbit (degrees)')),
                mean_temperature=self._parse_float(row.get('Mean Temperature (C)')),
                surface_pressure=row.get('Surface Pressure (bars)', ''),
                number_of_moons=self._parse_int(row.get('Number of Moons')),
                ring_system=row.get('Ring System?', ''),
                global_magnetic_field=row.get('Global Magnetic Field?', ''),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NASA Solar System Planets",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val) -> Optional[float]:
        if val is None or val == '' or val == 'NA':
            return None
        try:
            return float(val)
        except:
            return None
    
    def _parse_int(self, val) -> Optional[int]:
        if val is None or val == '' or val == 'NA':
            return None
        try:
            return int(float(val))
        except:
            return None
    
    def _parse_orbital_period(self, val) -> Optional[float]:
        if val is None or val == '' or val == 'NA':
            return None
        try:
            return float(val.replace(',', ''))
        except:
            return None
    
    def get_planet_classification(self, measurements: List[PlanetData]) -> Dict:
        """Classify planets by type."""
        terrestrial = []
        gas_giants = []
        ice_giants = []
        
        for m in measurements:
            if m.planet in ['Mercury', 'Venus', 'Earth', 'Mars']:
                terrestrial.append(m.planet)
            elif m.planet in ['Jupiter', 'Saturn']:
                gas_giants.append(m.planet)
            elif m.planet in ['Uranus', 'Neptune']:
                ice_giants.append(m.planet)
        
        return {
            "terrestrial": terrestrial,
            "gas_giants": gas_giants,
            "ice_giants": ice_giants,
        }
    
    def get_moon_analysis(self, measurements: List[PlanetData]) -> Dict:
        """Analyze moon distribution."""
        total_moons = sum(m.number_of_moons for m in measurements)
        planets_with_moons = sum(1 for m in measurements if m.number_of_moons > 0)
        
        sorted_moons = sorted(
            [(m.planet, m.number_of_moons) for m in measurements],
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "total_moons": total_moons,
            "planets_with_moons": planets_with_moons,
            "top_moons": sorted_moons,
        }
    
    def get_temperature_analysis(self, measurements: List[PlanetData]) -> Dict:
        """Analyze temperature extremes."""
        temps = [(m.planet, m.mean_temperature) for m in measurements if m.mean_temperature is not None]
        
        hottest = max(temps, key=lambda x: x[1])
        coldest = min(temps, key=lambda x: x[1])
        
        return {
            "hottest_planet": hottest,
            "coldest_planet": coldest,
        }
    
    def get_gravity_analysis(self, measurements: List[PlanetData]) -> Dict:
        """Analyze gravity comparison to Earth."""
        earth_gravity = 9.8
        gravity_ratio = []
        
        for m in measurements:
            if m.surface_gravity:
                ratio = m.surface_gravity / earth_gravity
                gravity_ratio.append((m.planet, ratio))
        
        highest_gravity = max(gravity_ratio, key=lambda x: x[1])
        lowest_gravity = min(gravity_ratio, key=lambda x: x[1])
        
        return {
            "highest_gravity": highest_gravity,
            "lowest_gravity": lowest_gravity,
        }
    
    def get_ring_analysis(self, measurements: List[PlanetData]) -> Dict:
        """Analyze ring systems."""
        with_rings = sum(1 for m in measurements if m.ring_system == 'Yes')
        without_rings = sum(1 for m in measurements if m.ring_system == 'No')
        
        ringed_planets = [m.planet for m in measurements if m.ring_system == 'Yes']
        
        return {
            "with_rings": with_rings,
            "without_rings": without_rings,
            "ringed_planets": ringed_planets,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "planet": m.planet,
                    "mass": m.mass,
                    "diameter": m.diameter,
                    "moons": m.number_of_moons,
                    "rings": m.ring_system,
                }
                for m in self.current_measurements
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"planets_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[PlanetData]) -> Dict:
        """Get summary for console display."""
        classification = self.get_planet_classification(measurements)
        
        return {
            "total_records": len(measurements),
            "planets": len(measurements),
            "terrestrial": len(classification.get('terrestrial', [])),
            "gas_giants": len(classification.get('gas_giants', [])),
            "ice_giants": len(classification.get('ice_giants', [])),
        }
    
    def get_climate_trends(self, measurements: List[PlanetData]) -> Dict:
        """Get climate trends for console display."""
        moon = self.get_moon_analysis(measurements)
        ring = self.get_ring_analysis(measurements)
        
        return {
            "total_moons": moon.get('total_moons', 0),
            "planets_with_rings": ring.get('with_rings', 0),
        }


def initialize_planet_satellite(satellite_id: str = "SENTRY-24") -> PlanetAcquisitor:
    """Initialize planet acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "planets", "planets.csv")
    
    if os.path.exists(data_path):
        return PlanetAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Planet data not found at {data_path}")
        return PlanetAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_planet_satellite()
    
    print("=== SENTRY-24 Planet Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=8)
    print(f"\nAcquired: {len(measurements)}")
    
    classification = acquisitor.get_planet_classification(measurements)
    print(f"\nPlanet Classification:")
    print(f"  Terrestrial: {classification.get('terrestrial', [])}")
    print(f"  Gas Giants: {classification.get('gas_giants', [])}")
    print(f"  Ice Giants: {classification.get('ice_giants', [])}")
    
    moon = acquisitor.get_moon_analysis(measurements)
    print(f"\nMoon Analysis:")
    print(f"  Total Moons: {moon.get('total_moons', 0)}")
    print(f"  Planets with moons: {moon.get('planets_with_moons', 0)}")
    
    ring = acquisitor.get_ring_analysis(measurements)
    print(f"\nRing Analysis:")
    print(f"  Planets with rings: {ring.get('with_rings', 0)}")
    print(f"  Ringed planets: {ring.get('ringed_planets', [])}")
    
    temp = acquisitor.get_temperature_analysis(measurements)
    print(f"\nTemperature Analysis:")
    print(f"  Hottest: {temp.get('hottest_planet', ('', 0))}")
    print(f"  Coldest: {temp.get('coldest_planet', ('', 0))}")