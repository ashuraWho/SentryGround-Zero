"""
Satellite Data Acquisition System - Star Type Module
Simulates satellite data collection from Star Type dataset (HR Diagram).
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


STAR_TYPES = {
    0: "Red Dwarf",
    1: "Brown Dwarf", 
    2: "White Dwarf",
    3: "Main Sequence",
    4: "SuperGiants",
    5: "HyperGiants",
}

SPECTRAL_CLASSES = ["O", "B", "A", "F", "G", "K", "M"]


@dataclass
class StarMeasurement:
    """Star measurement data."""
    temperature_k: float
    luminosity: float
    radius: float
    absolute_magnitude: float
    star_type: int
    star_color: str
    spectral_class: str
    satellite_id: str = "SENTRY-11"


class StarTypeAcquisitor:
    """
    Satellite data acquisition system for stars.
    Simulates SENTRY-11 collecting star classification data (HR Diagram).
    """
    
    def __init__(self, satellite_id: str = "SENTRY-11", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[StarMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load star data from CSV."""
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
        
        type_counts = {}
        color_counts = {}
        spectral_counts = {}
        
        for row in self.raw_data:
            try:
                star_type = int(row.get('Star type', 0))
                type_counts[star_type] = type_counts.get(star_type, 0) + 1
            except:
                pass
            
            color = row.get('Star color', '').strip()
            if color:
                color_counts[color] = color_counts.get(color, 0) + 1
            
            spectral = row.get('Spectral Class', '').strip()
            if spectral:
                spectral_counts[spectral] = spectral_counts.get(spectral, 0) + 1
        
        temps = []
        for row in self.raw_data:
            try:
                temps.append(float(row.get('Temperature (K)', 0)))
            except:
                pass
        
        self.stats = {
            "total_records": len(self.raw_data),
            "star_types": type_counts,
            "star_colors": len(color_counts),
            "spectral_classes": len(spectral_counts),
            "temp_range_k": f"{min(temps)}-{max(temps)}" if temps else "N/A",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[StarMeasurement]:
        """Acquire star data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            try:
                star_type = int(row.get('Star type', 0))
            except:
                star_type = 0
            
            measurement = StarMeasurement(
                temperature_k=self._parse_float(row.get('Temperature (K)', '0')),
                luminosity=self._parse_float(row.get('Luminosity(L/Lo)', '0')),
                radius=self._parse_float(row.get('Radius(R/Ro)', '0')),
                absolute_magnitude=self._parse_float(row.get('Absolute magnitude(Mv)', '0')),
                star_type=star_type,
                star_color=row.get('Star color', '').strip(),
                spectral_class=row.get('Spectral Class', '').strip(),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Star Type Dataset (HR Diagram)",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val: str) -> float:
        """Parse float safely."""
        if not val or val == '':
            return 0.0
        try:
            return float(val)
        except:
            return 0.0
    
    def get_type_analysis(self, measurements: List[StarMeasurement]) -> Dict:
        """Analyze star type distribution."""
        type_counts = {}
        for m in measurements:
            type_name = STAR_TYPES.get(m.star_type, f"Type {m.star_type}")
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            "type_counts": type_counts,
            "main_sequence": type_counts.get("Main Sequence", 0),
            "red_dwarfs": type_counts.get("Red Dwarf", 0),
            "supergiants": type_counts.get("SuperGiants", 0),
            "hypergiants": type_counts.get("HyperGiants", 0),
        }
    
    def get_physical_analysis(self, measurements: List[StarMeasurement]) -> Dict:
        """Analyze physical characteristics."""
        temps = [m.temperature_k for m in measurements if m.temperature_k > 0]
        lums = [m.luminosity for m in measurements if m.luminosity > 0]
        radii = [m.radius for m in measurements if m.radius > 0]
        mags = [m.absolute_magnitude for m in measurements]
        
        return {
            "avg_temperature_k": sum(temps) / len(temps) if temps else 0,
            "min_temperature_k": min(temps) if temps else 0,
            "max_temperature_k": max(temps) if temps else 0,
            "avg_luminosity": sum(lums) / len(lums) if lums else 0,
            "avg_radius": sum(radii) / len(radii) if radii else 0,
            "avg_absolute_magnitude": sum(mags) / len(mags) if mags else 0,
        }
    
    def get_spectral_analysis(self, measurements: List[StarMeasurement]) -> Dict:
        """Analyze spectral class distribution."""
        spectral_counts = {}
        color_counts = {}
        
        for m in measurements:
            if m.spectral_class:
                spectral_counts[m.spectral_class] = spectral_counts.get(m.spectral_class, 0) + 1
            if m.star_color:
                color_counts[m.star_color] = color_counts.get(m.star_color, 0) + 1
        
        return {
            "spectral_counts": spectral_counts,
            "color_counts": color_counts,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "temperature_k": m.temperature_k,
                    "luminosity": m.luminosity,
                    "radius": m.radius,
                    "star_type": STAR_TYPES.get(m.star_type, f"Type {m.star_type}"),
                    "spectral_class": m.spectral_class,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"star_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[StarMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "unique_types": len(set(m.star_type for m in measurements)),
            "unique_colors": len(set(m.star_color for m in measurements)),
        }
    
    def get_climate_trends(self, measurements: List[StarMeasurement]) -> Dict:
        """Get climate trends for console display."""
        type_analysis = self.get_type_analysis(measurements)
        phys = self.get_physical_analysis(measurements)
        
        return {
            "main_sequence": type_analysis.get('main_sequence', 0),
            "red_dwarfs": type_analysis.get('red_dwarfs', 0),
            "supergiants": type_analysis.get('supergiants', 0),
            "avg_temp_k": phys.get('avg_temperature_k', 0),
            "avg_radius": phys.get('avg_radius', 0),
        }


def initialize_star_satellite(satellite_id: str = "SENTRY-11") -> StarTypeAcquisitor:
    """Initialize star type acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "stars", "star_data.csv")
    
    if os.path.exists(data_path):
        return StarTypeAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Star data not found at {data_path}")
        return StarTypeAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_star_satellite()
    
    print("=== SENTRY-11 Star Type Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=240)
    print(f"\nAcquired: {len(measurements)}")
    
    type_analysis = acquisitor.get_type_analysis(measurements)
    print(f"\nStar Type Analysis:")
    for t, c in type_analysis.get('type_counts', {}).items():
        print(f"  {t}: {c}")
    
    phys = acquisitor.get_physical_analysis(measurements)
    print(f"\nPhysical Analysis:")
    print(f"  Avg Temperature: {phys.get('avg_temperature_k', 0):.0f} K")
    print(f"  Avg Radius: {phys.get('avg_radius', 0):.2f} R☉")