"""
Satellite Data Acquisition System - Cloud Seeding Module
Simulates satellite data collection from cloud seeding experiment data.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class CloudSeedingMeasurement:
    """Cloud seeding measurement data."""
    period: int
    seeded: str
    season: str
    nc_rain: float
    sc_rain: float
    nwc_rain: float
    te_rain: float
    satellite_id: str = "SENTRY-14"


class CloudSeedingAcquisitor:
    """
    Satellite data acquisition system for cloud seeding.
    Simulates SENTRY-14 collecting cloud seeding experiment data (Tasmania 1964-1971).
    """
    
    def __init__(self, satellite_id: str = "SENTRY-14", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[CloudSeedingMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load cloud seeding data from CSV."""
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
        
        seeded = 0
        unseeded = 0
        seasons = set()
        
        for row in self.raw_data:
            if row.get('seeded', '').strip() == 'S':
                seeded += 1
            elif row.get('seeded', '').strip() == 'U':
                unseeded += 1
            seasons.add(row.get('season', '').strip())
        
        self.stats = {
            "total_records": len(self.raw_data),
            "seeded_count": seeded,
            "unseeded_count": unseeded,
            "seasons": list(seasons),
            "experiment_years": "1964-1971",
            "location": "Tasmania",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[CloudSeedingMeasurement]:
        """Acquire cloud seeding data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = CloudSeedingMeasurement(
                period=int(row.get('period', 0)),
                seeded=row.get('seeded', '').strip(),
                season=row.get('season', '').strip(),
                nc_rain=self._parse_float(row.get('NC', '0')),
                sc_rain=self._parse_float(row.get('SC', '0')),
                nwc_rain=self._parse_float(row.get('NWC', '0')),
                te_rain=self._parse_float(row.get('TE', '0')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Cloud Seeding Experiment (Tasmania)",
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
    
    def get_seeding_analysis(self, measurements: List[CloudSeedingMeasurement]) -> Dict:
        """Analyze seeding effectiveness."""
        seeded = [m for m in measurements if m.seeded == 'S']
        unseeded = [m for m in measurements if m.seeded == 'U']
        
        def avg_te(data):
            return sum(m.te_rain for m in data) / len(data) if data else 0
        
        return {
            "seeded_count": len(seeded),
            "unseeded_count": len(unseeded),
            "avg_rain_seeded": avg_te(seeded),
            "avg_rain_unseeded": avg_te(unseeded),
        }
    
    def get_seasonal_analysis(self, measurements: List[CloudSeedingMeasurement]) -> Dict:
        """Analyze seasonal patterns."""
        seasons = {}
        for m in measurements:
            if m.season not in seasons:
                seasons[m.season] = {"seeded": [], "unseeded": []}
            
            if m.seeded == 'S':
                seasons[m.season]["seeded"].append(m.te_rain)
            else:
                seasons[m.season]["unseeded"].append(m.te_rain)
        
        result = {}
        for season, data in seasons.items():
            result[f"{season}_seeded"] = sum(data["seeded"]) / len(data["seeded"]) if data["seeded"] else 0
            result[f"{season}_unseeded"] = sum(data["unseeded"]) / len(data["unseeded"]) if data["unseeded"] else 0
        
        return result
    
    def get_control_analysis(self, measurements: List[CloudSeedingMeasurement]) -> Dict:
        """Analyze control area rainfalls."""
        nc = [m.nc_rain for m in measurements]
        sc = [m.sc_rain for m in measurements]
        nwc = [m.nwc_rain for m in measurements]
        
        return {
            "avg_nc": sum(nc) / len(nc) if nc else 0,
            "avg_sc": sum(sc) / len(sc) if sc else 0,
            "avg_nwc": sum(nwc) / len(nwc) if nwc else 0,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "period": m.period,
                    "seeded": m.seeded,
                    "season": m.season,
                    "te_rain": m.te_rain,
                }
                for m in self.current_measurements
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"cloud_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[CloudSeedingMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "seeded": sum(1 for m in measurements if m.seeded == 'S'),
            "unseeded": sum(1 for m in measurements if m.seeded == 'U'),
        }
    
    def get_climate_trends(self, measurements: List[CloudSeedingMeasurement]) -> Dict:
        """Get climate trends for console display."""
        seeding = self.get_seeding_analysis(measurements)
        control = self.get_control_analysis(measurements)
        
        return {
            "seeded_count": seeding.get('seeded_count', 0),
            "unseeded_count": seeding.get('unseeded_count', 0),
            "avg_rain_seeded": seeding.get('avg_rain_seeded', 0),
            "avg_rain_unseeded": seeding.get('avg_rain_unseeded', 0),
            "avg_control_nc": control.get('avg_nc', 0),
        }


def initialize_cloud_satellite(satellite_id: str = "SENTRY-14") -> CloudSeedingAcquisitor:
    """Initialize cloud seeding acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "cloud_seeding", "cloud_seeding.csv")
    
    if os.path.exists(data_path):
        return CloudSeedingAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Cloud data not found at {data_path}")
        return CloudSeedingAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_cloud_satellite()
    
    print("=== SENTRY-14 Cloud Seeding Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=108)
    print(f"\nAcquired: {len(measurements)}")
    
    seeding = acquisitor.get_seeding_analysis(measurements)
    print(f"\nSeeding Analysis:")
    print(f"  Seeded: {seeding.get('seeded_count', 0)}")
    print(f"  Unseeded: {seeding.get('unseeded_count', 0)}")
    print(f"  Avg Rain (Seeded): {seeding.get('avg_rain_seeded', 0):.2f} in")
    print(f"  Avg Rain (Unseeded): {seeding.get('avg_rain_unseeded', 0):.2f} in")