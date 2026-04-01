"""
Satellite Data Acquisition System - Sea Level Module
Simulates satellite data collection from NASA sea level dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class SeaLevelData:
    """Sea level measurement data."""
    year: int
    gmsl_gia_not_applied: float
    gmsl_gia_applied: float
    smoothed_gmsl: float
    std_dev: float
    satellite_id: str = "SENTRY-22"


class SeaLevelAcquisitor:
    """
    Satellite data acquisition system for sea level.
    Simulates SENTRY-22 collecting NASA sea level data (1993-2021).
    """
    
    def __init__(self, satellite_id: str = "SENTRY-22", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[SeaLevelData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load sea level data from CSV."""
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
        
        years = [int(row.get('Year', 0)) for row in self.raw_data]
        
        self.stats = {
            "total_records": len(self.raw_data),
            "year_range": f"{min(years)}-{max(years)}",
            "data_source": "NASA Satellite Altimetry",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[SeaLevelData]:
        """Acquire sea level data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = SeaLevelData(
                year=int(row.get('Year', 0)),
                gmsl_gia_not_applied=self._parse_float(row.get('GMSL_GIA_not_applied_mm')),
                gmsl_gia_applied=self._parse_float(row.get('GMSL_GIA_applied_mm')),
                smoothed_gmsl=self._parse_float(row.get('Smoothed_GMSL_mm')),
                std_dev=self._parse_float(row.get('Std_Dev_mm')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NASA Sea Level Data (1993-2021)",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val) -> Optional[float]:
        """Parse float safely."""
        if val is None or val == '' or val == 'NA':
            return None
        try:
            return float(val)
        except:
            return None
    
    def get_rise_analysis(self, measurements: List[SeaLevelData]) -> Dict:
        """Analyze sea level rise."""
        if not measurements:
            return {}
        
        first = measurements[0].smoothed_gmsl
        last = measurements[-1].smoothed_gmsl
        total_rise = last - first
        
        years = measurements[-1].year - measurements[0].year
        rate_per_year = total_rise / years if years > 0 else 0
        
        return {
            "total_rise_mm": total_rise,
            "rate_mm_per_year": rate_per_year,
            "start_year": measurements[0].year,
            "end_year": measurements[-1].year,
        }
    
    def get_trend_analysis(self, measurements: List[SeaLevelData]) -> Dict:
        """Analyze sea level trends."""
        increasing_years = 0
        for i in range(1, len(measurements)):
            if measurements[i].smoothed_gmsl > measurements[i-1].smoothed_gmsl:
                increasing_years += 1
        
        return {
            "years_with_increase": increasing_years,
            "total_years": len(measurements),
        }
    
    def get_projection(self, measurements: List[SeaLevelData]) -> Dict:
        """Project future sea level."""
        if not measurements:
            return {}
        
        rise = self.get_rise_analysis(measurements)
        rate = rise.get('rate_mm_per_year', 0)
        
        return {
            "projected_2030": (measurements[-1].smoothed_gmsl + rate * 9),
            "projected_2050": (measurements[-1].smoothed_gmsl + rate * 29),
            "projected_2100": (measurements[-1].smoothed_gmsl + rate * 79),
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "year": m.year,
                    "gmsl_mm": m.smoothed_gmsl,
                    "std_dev": m.std_dev,
                }
                for m in self.current_measurements
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"sealevel_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[SeaLevelData]) -> Dict:
        """Get summary for console display."""
        if not measurements:
            return {}
        
        rise = self.get_rise_analysis(measurements)
        
        return {
            "total_records": len(measurements),
            "year_range": f"{rise.get('start_year', 0)}-{rise.get('end_year', 0)}",
            "total_rise_mm": rise.get('total_rise_mm', 0),
        }
    
    def get_climate_trends(self, measurements: List[SeaLevelData]) -> Dict:
        """Get climate trends for console display."""
        rise = self.get_rise_analysis(measurements)
        projection = self.get_projection(measurements)
        
        return {
            "total_rise": rise.get('total_rise_mm', 0),
            "rate_per_year": rise.get('rate_mm_per_year', 0),
            "projection_2050": projection.get('projected_2050', 0),
        }


def initialize_sea_level_satellite(satellite_id: str = "SENTRY-22") -> SeaLevelAcquisitor:
    """Initialize sea level acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "sea_level", "sea_level.csv")
    
    if os.path.exists(data_path):
        return SeaLevelAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Sea level data not found at {data_path}")
        return SeaLevelAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_sea_level_satellite()
    
    print("=== SENTRY-22 Sea Level Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=29)
    print(f"\nAcquired: {len(measurements)}")
    
    rise = acquisitor.get_rise_analysis(measurements)
    print(f"\nSea Level Rise Analysis:")
    print(f"  Total Rise: {rise.get('total_rise_mm', 0):.1f} mm")
    print(f"  Rate: {rise.get('rate_mm_per_year', 0):.2f} mm/year")
    print(f"  Period: {rise.get('start_year', 0)}-{rise.get('end_year', 0)}")
    
    projection = acquisitor.get_projection(measurements)
    print(f"\nFuture Projections:")
    print(f"  2030: {projection.get('projected_2030', 0):.1f} mm")
    print(f"  2050: {projection.get('projected_2050', 0):.1f} mm")
    print(f"  2100: {projection.get('projected_2100', 0):.1f} mm")