"""
Satellite Data Acquisition System - NASA Ocean Climate Module
Simulates satellite data collection from NASA ocean climate data (2018 vs 2021).
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class NASAOceanMeasurement:
    """NASA ocean climate measurement data."""
    year: str
    time_hour: int
    latitude: float
    longitude: float
    temp_drop_k: Optional[float]
    interface_temp_k: Optional[float]
    sea_ice_temp_k: Optional[float]
    rainfall: Optional[float]
    skin_temp_change_k: Optional[float]
    satellite_id: str = "SENTRY-06"


class NASAOceanAcquisitor:
    """
    Satellite data acquisition system for NASA ocean climate.
    Simulates SENTRY-06 collecting NASA ocean surface temperature data.
    Compares August 1, 2018 vs August 1, 2021.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-06", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[NASAOceanMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load NASA ocean data from CSV."""
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
        
        years = set()
        locations = set()
        
        for row in self.raw_data:
            years.add(row.get('year', ''))
            locations.add(f"{row.get('latitude', '')}:{row.get('longitude', '')}")
        
        self.stats = {
            "total_records": len(self.raw_data),
            "years": list(years),
            "locations": len(locations),
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[NASAOceanMeasurement]:
        """Acquire NASA ocean data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = NASAOceanMeasurement(
                year=row.get('year', ''),
                time_hour=int(row.get('time_hour', 0)) if row.get('time_hour') else 0,
                latitude=float(row.get('latitude', 0)) if row.get('latitude') else 0,
                longitude=float(row.get('longitude', 0)) if row.get('longitude') else 0,
                temp_drop_k=float(row.get('temp_drop_k')) if row.get('temp_drop_k') else None,
                interface_temp_k=float(row.get('interface_temp_k')) if row.get('interface_temp_k') else None,
                sea_ice_temp_k=float(row.get('sea_ice_temp_k')) if row.get('sea_ice_temp_k') else None,
                rainfall=float(row.get('rainfall')) if row.get('rainfall') else None,
                skin_temp_change_k=float(row.get('skin_temp_change_k')) if row.get('skin_temp_change_k') else None,
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NASA Ocean Climate (GEOS/DAS)",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def get_comparison_analysis(self, measurements: List[NASAOceanMeasurement]) -> Dict:
        """Analyze 2018 vs 2021 comparison."""
        data_2018 = [m for m in measurements if m.year == '2018']
        data_2021 = [m for m in measurements if m.year == '2021']
        
        if not data_2018 or not data_2021:
            return {"error": "Insufficient data for comparison"}
        
        def avg_temp(data, attr):
            vals = [getattr(m, attr) for m in data if getattr(m, attr) is not None]
            return sum(vals) / len(vals) if vals else 0
        
        analysis = {
            "records_2018": len(data_2018),
            "records_2021": len(data_2021),
            "2018_interface_temp_K": avg_temp(data_2018, 'interface_temp_k'),
            "2021_interface_temp_K": avg_temp(data_2021, 'interface_temp_k'),
            "2018_sea_ice_temp_K": avg_temp(data_2018, 'sea_ice_temp_k'),
            "2021_sea_ice_temp_K": avg_temp(data_2021, 'sea_ice_temp_k'),
            "2018_skin_change_K": avg_temp(data_2018, 'skin_temp_change_k'),
            "2021_skin_change_K": avg_temp(data_2021, 'skin_temp_change_k'),
        }
        
        analysis['interface_temp_diff_K'] = analysis['2021_interface_temp_K'] - analysis['2018_interface_temp_K']
        analysis['sea_ice_temp_diff_K'] = analysis['2021_sea_ice_temp_K'] - analysis['2018_sea_ice_temp_K']
        
        return analysis
    
    def get_daily_pattern(self, measurements: List[NASAOceanMeasurement]) -> Dict:
        """Analyze hourly patterns."""
        hourly = {}
        
        for m in measurements:
            if m.interface_temp_k is not None:
                if m.time_hour not in hourly:
                    hourly[m.time_hour] = []
                hourly[m.time_hour].append(m.interface_temp_k - 273.15)
        
        return {
            hour: sum(vals) / len(vals) for hour, vals in hourly.items()
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "year": m.year,
                    "time_hour": m.time_hour,
                    "latitude": m.latitude,
                    "longitude": m.longitude,
                    "interface_temp_K": m.interface_temp_k,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"nasa_ocean_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[NASAOceanMeasurement]) -> Dict:
        """Get summary for console display."""
        years = set(m.year for m in measurements)
        return {
            "total_records": len(measurements),
            "years": "-".join(sorted(years)),
            "comparison": "2018 vs 2021 (Aug 1)",
        }
    
    def get_climate_trends(self, measurements: List[NASAOceanMeasurement]) -> Dict:
        """Get climate trends for console display."""
        analysis = self.get_comparison_analysis(measurements)
        
        return {
            "interface_temp_change_K": analysis.get('interface_temp_diff_K', 0),
            "sea_ice_temp_change_K": analysis.get('sea_ice_temp_diff_K', 0),
            "skin_temp_change_2018_K": analysis.get('2018_skin_change_K', 0),
            "skin_temp_change_2021_K": analysis.get('2021_skin_change_K', 0),
        }


def initialize_nasa_ocean_satellite(satellite_id: str = "SENTRY-06") -> NASAOceanAcquisitor:
    """Initialize NASA ocean acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "nasa_ocean", "nasa_ocean_climate.csv")
    
    if os.path.exists(data_path):
        return NASAOceanAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: NASA ocean data not found at {data_path}")
        return NASAOceanAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_nasa_ocean_satellite()
    
    print("=== SENTRY-06 NASA Ocean Climate Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=500)
    print(f"\nAcquired: {len(measurements)}")
    
    comparison = acquisitor.get_comparison_analysis(measurements)
    print(f"\n2018 vs 2021 Comparison:")
    print(f"  Interface Temp Change: {comparison.get('interface_temp_diff_K', 0):.3f} K")
    print(f"  Sea Ice Temp Change: {comparison.get('sea_ice_temp_diff_K', 0):.3f} K")