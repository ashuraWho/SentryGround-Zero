"""
Satellite Data Acquisition System - Deforestation Module
Simulates satellite data collection from SDG 15 deforestation dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class DeforestationData:
    """Deforestation measurement data."""
    iso3c: str
    forests_2000: float
    forests_2020: float
    trend: float
    satellite_id: str = "SENTRY-20"


class DeforestationAcquisitor:
    """
    Satellite data acquisition system for deforestation.
    Simulates SENTRY-20 collecting SDG 15 forest cover data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-20", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[DeforestationData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load deforestation data from CSV."""
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
        
        countries = len(self.raw_data)
        forest_2000 = []
        forest_2020 = []
        
        for row in self.raw_data:
            try:
                f2000 = float(row.get('forests_2000', 0))
                f2020 = float(row.get('forests_2020', 0))
                if f2000 > 0:
                    forest_2000.append(f2000)
                if f2020 > 0:
                    forest_2020.append(f2020)
            except:
                pass
        
        self.stats = {
            "total_records": len(self.raw_data),
            "countries": countries,
            "year_range": "2000-2020",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[DeforestationData]:
        """Acquire deforestation data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = DeforestationData(
                iso3c=row.get('iso3c', '').strip().strip('"'),
                forests_2000=self._parse_float(row.get('forests_2000')),
                forests_2020=self._parse_float(row.get('forests_2020')),
                trend=self._parse_float(row.get('trend')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "SDG 15 Forest Cover Data (2000-2020)",
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
    
    def get_trend_analysis(self, measurements: List[DeforestationData]) -> Dict:
        """Analyze forest cover trends."""
        increasing = sum(1 for m in measurements if m.trend and m.trend > 0)
        decreasing = sum(1 for m in measurements if m.trend and m.trend < 0)
        stable = sum(1 for m in measurements if m.trend == 0)
        
        return {
            "increasing": increasing,
            "decreasing": decreasing,
            "stable": stable,
        }
    
    def get_country_analysis(self, measurements: List[DeforestationData]) -> Dict:
        """Analyze countries with most deforestation."""
        sorted_by_trend = sorted(
            [(m.iso3c, m.trend) for m in measurements if m.trend is not None],
            key=lambda x: x[1]
        )
        
        worst_deforestation = sorted_by_trend[:5]
        best_reforestation = sorted_by_trend[-5:][::-1]
        
        return {
            "worst_deforestation": worst_deforestation,
            "best_reforestation": best_reforestation,
        }
    
    def get_global_analysis(self, measurements: List[DeforestationData]) -> Dict:
        """Calculate global forest cover statistics."""
        forest_2000 = [m.forests_2000 for m in measurements if m.forests_2000 is not None]
        forest_2020 = [m.forests_2020 for m in measurements if m.forests_2020 is not None]
        
        return {
            "avg_forest_2000": sum(forest_2000) / len(forest_2000) if forest_2000 else 0,
            "avg_forest_2020": sum(forest_2020) / len(forest_2020) if forest_2020 else 0,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "country": m.iso3c,
                    "forests_2000": m.forests_2000,
                    "forests_2020": m.forests_2020,
                    "trend": m.trend,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"deforestation_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[DeforestationData]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "countries": len(set(m.iso3c for m in measurements if m.iso3c)),
            "year_range": "2000-2020",
        }
    
    def get_climate_trends(self, measurements: List[DeforestationData]) -> Dict:
        """Get climate trends for console display."""
        trend = self.get_trend_analysis(measurements)
        global_avg = self.get_global_analysis(measurements)
        
        return {
            "increasing": trend.get('increasing', 0),
            "decreasing": trend.get('decreasing', 0),
            "avg_forest_2000": global_avg.get('avg_forest_2000', 0),
            "avg_forest_2020": global_avg.get('avg_forest_2020', 0),
        }


def initialize_deforestation_satellite(satellite_id: str = "SENTRY-20") -> DeforestationAcquisitor:
    """Initialize deforestation acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "deforestation", "goal15.forest_shares.csv")
    
    if os.path.exists(data_path):
        return DeforestationAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Deforestation data not found at {data_path}")
        return DeforestationAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_deforestation_satellite()
    
    print("=== SENTRY-20 Deforestation Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=238)
    print(f"\nAcquired: {len(measurements)}")
    
    trend = acquisitor.get_trend_analysis(measurements)
    print(f"\nTrend Analysis:")
    print(f"  Countries with increasing forest: {trend.get('increasing', 0)}")
    print(f"  Countries with decreasing forest: {trend.get('decreasing', 0)}")
    print(f"  Countries with stable forest: {trend.get('stable', 0)}")
    
    global_avg = acquisitor.get_global_analysis(measurements)
    print(f"\nGlobal Average:")
    print(f"  Forest Cover 2000: {global_avg.get('avg_forest_2000', 0):.1f}%")
    print(f"  Forest Cover 2020: {global_avg.get('avg_forest_2020', 0):.1f}%")
    
    country = acquisitor.get_country_analysis(measurements)
    print(f"\nMost Deforested Countries:")
    for c, t in country.get('worst_deforestation', []):
        print(f"  {c}: {t:.1f}%")