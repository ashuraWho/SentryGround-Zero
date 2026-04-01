"""
Satellite Data Acquisition System - Earthquake Tsunami Module
Simulates satellite data collection from global earthquake-tsunami dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class EarthquakeData:
    """Earthquake measurement data."""
    magnitude: float
    cdi: int
    mmi: int
    sig: int
    nst: int
    dmin: float
    gap: float
    depth: float
    latitude: float
    longitude: float
    year: int
    month: int
    tsunami: bool
    satellite_id: str = "SENTRY-27"


class EarthquakeAcquisitor:
    """
    Satellite data acquisition system for earthquakes and tsunami risk.
    Simulates SENTRY-27 collecting global earthquake data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-27", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[EarthquakeData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load earthquake data from CSV."""
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
        
        tsunami_count = sum(1 for row in self.raw_data if row.get('tsunami', '0') == '1')
        years = set(row.get('Year', '') for row in self.raw_data if row.get('Year'))
        
        self.stats = {
            "total_records": len(self.raw_data),
            "tsunami_events": tsunami_count,
            "non_tsunami_events": len(self.raw_data) - tsunami_count,
            "year_range": f"{min(years)}-{max(years)}" if years else "Unknown",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[EarthquakeData]:
        """Acquire earthquake data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = EarthquakeData(
                magnitude=self._parse_float(row.get('magnitude')),
                cdi=self._parse_int(row.get('cdi')),
                mmi=self._parse_int(row.get('mmi')),
                sig=self._parse_int(row.get('sig')),
                nst=self._parse_int(row.get('nst')),
                dmin=self._parse_float(row.get('dmin')),
                gap=self._parse_float(row.get('gap')),
                depth=self._parse_float(row.get('depth')),
                latitude=self._parse_float(row.get('latitude')),
                longitude=self._parse_float(row.get('longitude')),
                year=self._parse_int(row.get('Year')),
                month=self._parse_int(row.get('Month')),
                tsunami=self._parse_tsunami(row.get('tsunami')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Global Earthquake-Tsunami Risk Assessment",
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
    
    def _parse_tsunami(self, val) -> bool:
        if val is None:
            return False
        return str(val) == '1'
    
    def get_tsunami_analysis(self, measurements: List[EarthquakeData]) -> Dict:
        """Analyze tsunami events."""
        tsunami = [m for m in measurements if m.tsunami]
        non_tsunami = [m for m in measurements if not m.tsunami]
        
        return {
            "tsunami_count": len(tsunami),
            "non_tsunami_count": len(non_tsunami),
            "tsunami_percentage": (len(tsunami) / len(measurements) * 100) if measurements else 0,
        }
    
    def get_magnitude_analysis(self, measurements: List[EarthquakeData]) -> Dict:
        """Analyze earthquake magnitudes."""
        magnitudes = [m.magnitude for m in measurements if m.magnitude]
        
        major = sum(1 for m in magnitudes if m >= 8.0) if magnitudes else 0
        
        return {
            "avg_magnitude": sum(magnitudes) / len(magnitudes) if magnitudes else 0,
            "max_magnitude": max(magnitudes) if magnitudes else 0,
            "min_magnitude": min(magnitudes) if magnitudes else 0,
            "major_earthquakes": major,
        }
    
    def get_depth_analysis(self, measurements: List[EarthquakeData]) -> Dict:
        """Analyze earthquake depths."""
        depths = [m.depth for m in measurements if m.depth]
        
        shallow = sum(1 for d in depths if d < 70) if depths else 0
        intermediate = sum(1 for d in depths if 70 <= d < 300) if depths else 0
        deep = sum(1 for d in depths if d >= 300) if depths else 0
        
        return {
            "avg_depth": sum(depths) / len(depths) if depths else 0,
            "shallow": shallow,
            "intermediate": intermediate,
            "deep": deep,
        }
    
    def get_yearly_trends(self, measurements: List[EarthquakeData]) -> Dict:
        """Analyze yearly trends."""
        year_counts = {}
        year_tsunami = {}
        
        for m in measurements:
            if m.year:
                year_counts[m.year] = year_counts.get(m.year, 0) + 1
                if m.tsunami:
                    year_tsunami[m.year] = year_tsunami.get(m.year, 0) + 1
        
        return {
            "yearly_counts": year_counts,
            "yearly_tsunami": year_tsunami,
        }
    
    def get_geographic_analysis(self, measurements: List[EarthquakeData]) -> Dict:
        """Analyze geographic distribution."""
        lats = [m.latitude for m in measurements if m.latitude is not None]
        lons = [m.longitude for m in measurements if m.longitude is not None]
        
        return {
            "lat_range": f"{min(lats):.1f} to {max(lats):.1f}" if lats else "Unknown",
            "lon_range": f"{min(lons):.1f} to {max(lons):.1f}" if lons else "Unknown",
        }
    
    def get_highest_magnitude(self, measurements: List[EarthquakeData]) -> List[Dict]:
        """Get highest magnitude earthquakes."""
        sorted_quakes = sorted(
            [(m.year, m.month, m.magnitude, m.depth, m.latitude, m.longitude, m.tsunami) 
             for m in measurements if m.magnitude],
            key=lambda x: x[2],
            reverse=True
        )
        
        return [{"year": x[0], "month": x[1], "magnitude": x[2], "depth": x[3], 
                 "lat": x[4], "lon": x[5], "tsunami": x[6]} for x in sorted_quakes[:10]]
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "magnitude": m.magnitude,
                    "depth": m.depth,
                    "year": m.year,
                    "tsunami": m.tsunami,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"earthquake_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[EarthquakeData]) -> Dict:
        """Get summary for console display."""
        tsunami = self.get_tsunami_analysis(measurements)
        
        return {
            "total_records": len(measurements),
            "tsunami_events": tsunami.get('tsunami_count', 0),
            "year_range": self.stats.get("year_range", "Unknown"),
        }
    
    def get_climate_trends(self, measurements: List[EarthquakeData]) -> Dict:
        """Get climate trends for console display."""
        tsunami = self.get_tsunami_analysis(measurements)
        magnitude = self.get_magnitude_analysis(measurements)
        
        return {
            "tsunami_percentage": tsunami.get('tsunami_percentage', 0),
            "avg_magnitude": magnitude.get('avg_magnitude', 0),
            "major_earthquakes": magnitude.get('major_earthquakes', 0),
        }


def initialize_earthquake_satellite(satellite_id: str = "SENTRY-27") -> EarthquakeAcquisitor:
    """Initialize earthquake acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "earthquake_tsunami", "earthquake_data_tsunami.csv")
    
    if os.path.exists(data_path):
        return EarthquakeAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Earthquake data not found at {data_path}")
        return EarthquakeAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_earthquake_satellite()
    
    print("=== SENTRY-27 Earthquake-Tsunami Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=782)
    print(f"\nAcquired: {len(measurements)}")
    
    tsunami = acquisitor.get_tsunami_analysis(measurements)
    print(f"\nTsunami Analysis:")
    print(f"  Tsunami Events: {tsunami.get('tsunami_count', 0)}")
    print(f"  Non-Tsunami: {tsunami.get('non_tsunami_count', 0)}")
    print(f"  Tsunami Rate: {tsunami.get('tsunami_percentage', 0):.1f}%")
    
    magnitude = acquisitor.get_magnitude_analysis(measurements)
    print(f"\nMagnitude Analysis:")
    print(f"  Avg Magnitude: {magnitude.get('avg_magnitude', 0):.2f}")
    print(f"  Max Magnitude: {magnitude.get('max_magnitude', 0):.1f}")
    print(f"  Major (≥8.0): {magnitude.get('major_earthquakes', 0)}")
    
    depth = acquisitor.get_depth_analysis(measurements)
    print(f"\nDepth Analysis:")
    print(f"  Shallow (<70km): {depth.get('shallow', 0)}")
    print(f"  Intermediate: {depth.get('intermediate', 0)}")
    print(f"  Deep (≥300km): {depth.get('deep', 0)}")
    
    top = acquisitor.get_highest_magnitude(measurements)
    print(f"\nTop 5 Largest Earthquakes:")
    for i, t in enumerate(top[:5]):
        tsun = "TSUNAMI" if t['tsunami'] else ""
        print(f"  {i+1}. M{t['magnitude']} ({t['year']}) {tsun}")