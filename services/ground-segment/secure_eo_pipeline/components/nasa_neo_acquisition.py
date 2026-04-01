"""
Satellite Data Acquisition System - NASA Near Earth Objects Module
Simulates satellite data collection from NASA NEO dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class NEOData:
    """Near Earth Object measurement data."""
    id: str
    name: str
    est_diameter_min: float
    est_diameter_max: float
    relative_velocity: float
    miss_distance: float
    orbiting_body: str
    sentry_object: bool
    absolute_magnitude: float
    hazardous: bool
    satellite_id: str = "SENTRY-26"


class NEOAcquisitor:
    """
    Satellite data acquisition system for Near Earth Objects.
    Simulates SENTRY-26 collecting NASA NEO data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-26", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[NEOData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load NEO data from CSV."""
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
        
        hazardous_count = sum(1 for row in self.raw_data if row.get('hazardous', '').lower() == 'true')
        
        self.stats = {
            "total_records": len(self.raw_data),
            "hazardous_count": hazardous_count,
            "safe_count": len(self.raw_data) - hazardous_count,
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[NEOData]:
        """Acquire NEO data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = NEOData(
                id=row.get('id', ''),
                name=row.get('name', ''),
                est_diameter_min=self._parse_float(row.get('est_diameter_min')),
                est_diameter_max=self._parse_float(row.get('est_diameter_max')),
                relative_velocity=self._parse_float(row.get('relative_velocity')),
                miss_distance=self._parse_float(row.get('miss_distance')),
                orbiting_body=row.get('orbiting_body', ''),
                sentry_object=self._parse_bool(row.get('sentry_object')),
                absolute_magnitude=self._parse_float(row.get('absolute_magnitude')),
                hazardous=self._parse_bool(row.get('hazardous')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NASA NEO Earth Close Approaches",
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
    
    def _parse_bool(self, val) -> bool:
        if val is None:
            return False
        return str(val).lower() == 'true'
    
    def get_hazard_analysis(self, measurements: List[NEOData]) -> Dict:
        """Analyze hazardous objects."""
        hazardous = [m for m in measurements if m.hazardous]
        safe = [m for m in measurements if not m.hazardous]
        
        return {
            "hazardous_count": len(hazardous),
            "safe_count": len(safe),
        }
    
    def get_size_analysis(self, measurements: List[NEOData]) -> Dict:
        """Analyze object sizes."""
        sizes = [m.est_diameter_max for m in measurements if m.est_diameter_max]
        
        return {
            "avg_diameter": sum(sizes) / len(sizes) if sizes else 0,
            "largest": max(sizes) if sizes else 0,
            "smallest": min(sizes) if sizes else 0,
        }
    
    def get_velocity_analysis(self, measurements: List[NEOData]) -> Dict:
        """Analyze relative velocities."""
        velocities = [m.relative_velocity for m in measurements if m.relative_velocity]
        
        return {
            "avg_velocity": sum(velocities) / len(velocities) if velocities else 0,
            "fastest": max(velocities) if velocities else 0,
            "slowest": min(velocities) if velocities else 0,
        }
    
    def get_miss_distance_analysis(self, measurements: List[NEOData]) -> Dict:
        """Analyze miss distances."""
        distances = [m.miss_distance for m in measurements if m.miss_distance]
        
        return {
            "avg_distance_km": sum(distances) / len(distances) if distances else 0,
            "closest_km": min(distances) if distances else 0,
            "farthest_km": max(distances) if distances else 0,
        }
    
    def get_closest_approaches(self, measurements: List[NEOData], n: int = 10) -> List[Dict]:
        """Get closest approaches."""
        sorted_by_distance = sorted(
            [(m.name, m.miss_distance, m.relative_velocity, m.hazardous) 
             for m in measurements if m.miss_distance],
            key=lambda x: x[1]
        )
        
        return [{"name": x[0], "distance_km": x[1], "velocity": x[2], "hazardous": x[3]} 
                for x in sorted_by_distance[:n]]
    
    def get_magnitude_analysis(self, measurements: List[NEOData]) -> Dict:
        """Analyze absolute magnitudes."""
        magnitudes = [m.absolute_magnitude for m in measurements if m.absolute_magnitude]
        
        return {
            "avg_magnitude": sum(magnitudes) / len(magnitudes) if magnitudes else 0,
            "brightest": min(magnitudes) if magnitudes else 0,
            "dimmest": max(magnitudes) if magnitudes else 0,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "name": m.name,
                    "diameter": m.est_diameter_max,
                    "velocity": m.relative_velocity,
                    "hazardous": m.hazardous,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"neo_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[NEOData]) -> Dict:
        """Get summary for console display."""
        hazard = self.get_hazard_analysis(measurements)
        
        return {
            "total_records": len(measurements),
            "hazardous": hazard.get('hazardous_count', 0),
            "safe": hazard.get('safe_count', 0),
        }
    
    def get_climate_trends(self, measurements: List[NEOData]) -> Dict:
        """Get climate trends for console display."""
        hazard = self.get_hazard_analysis(measurements)
        size = self.get_size_analysis(measurements)
        
        return {
            "hazardous_count": hazard.get('hazardous_count', 0),
            "avg_diameter": size.get('avg_diameter', 0),
        }


def initialize_neo_satellite(satellite_id: str = "SENTRY-26") -> NEOAcquisitor:
    """Initialize NEO acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "nasa_neo", "neo.csv")
    
    if os.path.exists(data_path):
        return NEOAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: NEO data not found at {data_path}")
        return NEOAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_neo_satellite()
    
    print("=== SENTRY-26 NASA Near Earth Objects Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=5000)
    print(f"\nAcquired: {len(measurements)}")
    
    hazard = acquisitor.get_hazard_analysis(measurements)
    print(f"\nHazard Analysis:")
    print(f"  Hazardous: {hazard.get('hazardous_count', 0)}")
    print(f"  Safe: {hazard.get('safe_count', 0)}")
    
    size = acquisitor.get_size_analysis(measurements)
    print(f"\nSize Analysis:")
    print(f"  Avg Diameter: {size.get('avg_diameter', 0):.2f} km")
    print(f"  Largest: {size.get('largest', 0):.2f} km")
    
    velocity = acquisitor.get_velocity_analysis(measurements)
    print(f"\nVelocity Analysis:")
    print(f"  Avg Velocity: {velocity.get('avg_velocity', 0):.1f} km/h")
    
    miss = acquisitor.get_miss_distance_analysis(measurements)
    print(f"\nMiss Distance Analysis:")
    print(f"  Closest: {miss.get('closest_km', 0)/1e6:.2f}M km")
    
    closest = acquisitor.get_closest_approaches(measurements, 5)
    print(f"\nTop 5 Closest Approaches:")
    for c in closest:
        hazard_mark = " ⚠️ HAZARD" if c['hazardous'] else ""
        print(f"  {c['name']}: {c['distance_km']/1e6:.2f}M km{hazard_mark}")