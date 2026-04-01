"""
Satellite Data Acquisition System - Space Weather Module
Simulates satellite data collection from NASA space weather dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class SpaceWeatherData:
    """Space weather measurement data."""
    event_id: str
    event_type: str
    begin_time: str
    peak_time: Optional[str]
    end_time: Optional[str]
    class_type: str
    source_location: str
    active_region: Optional[str]
    instruments: str
    note: str
    kp_index: Optional[str]
    satellite_id: str = "SENTRY-23"


class SpaceWeatherAcquisitor:
    """
    Satellite data acquisition system for space weather.
    Simulates SENTRY-23 collecting NASA DONKI space weather data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-23", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[SpaceWeatherData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load space weather data from CSV."""
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
        
        event_types = {}
        years = set()
        
        for row in self.raw_data:
            etype = row.get('event_type', 'Unknown')
            event_types[etype] = event_types.get(etype, 0) + 1
            
            year = row.get('year', '')
            if year:
                years.add(year)
        
        self.stats = {
            "total_records": len(self.raw_data),
            "event_types": event_types,
            "year_range": f"{min(years)}-{max(years)}" if years else "Unknown",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[SpaceWeatherData]:
        """Acquire space weather data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = SpaceWeatherData(
                event_id=row.get('event_id', ''),
                event_type=row.get('event_type', ''),
                begin_time=row.get('begin_time', ''),
                peak_time=row.get('peak_time') or None,
                end_time=row.get('end_time') or None,
                class_type=row.get('class_type', ''),
                source_location=row.get('source_location', ''),
                active_region=row.get('active_region') or None,
                instruments=row.get('instruments', ''),
                note=row.get('note', ''),
                kp_index=row.get('kp_index') or None,
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NASA DONKI Space Weather",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def get_event_type_analysis(self, measurements: List[SpaceWeatherData]) -> Dict:
        """Analyze event type distribution."""
        event_counts = {}
        for m in measurements:
            if m.event_type:
                event_counts[m.event_type] = event_counts.get(m.event_type, 0) + 1
        
        return event_counts
    
    def get_flare_analysis(self, measurements: List[SpaceWeatherData]) -> Dict:
        """Analyze solar flare intensities."""
        flares = [m for m in measurements if m.event_type == 'Solar Flare' and m.class_type]
        
        x_class = sum(1 for f in flares if f.class_type and f.class_type.startswith('X'))
        m_class = sum(1 for f in flares if f.class_type and f.class_type.startswith('M'))
        c_class = sum(1 for f in flares if f.class_type and f.class_type.startswith('C'))
        
        return {
            "total_flares": len(flares),
            "x_class": x_class,
            "m_class": m_class,
            "c_class": c_class,
        }
    
    def get_storm_analysis(self, measurements: List[SpaceWeatherData]) -> Dict:
        """Analyze geomagnetic storm levels."""
        storms = [m for m in measurements if m.event_type == 'Geomagnetic Storm' and m.kp_index]
        
        g5 = sum(1 for s in storms if s.kp_index and 'G5' in s.kp_index)
        g4 = sum(1 for s in storms if s.kp_index and 'G4' in s.kp_index)
        g3 = sum(1 for s in storms if s.kp_index and 'G3' in s.kp_index)
        
        return {
            "total_storms": len(storms),
            "g5_extreme": g5,
            "g4_severe": g4,
            "g3_strong": g3,
        }
    
    def get_active_region_analysis(self, measurements: List[SpaceWeatherData]) -> Dict:
        """Analyze most active solar regions."""
        regions = {}
        for m in measurements:
            if m.active_region:
                regions[m.active_region] = regions.get(m.active_region, 0) + 1
        
        top_regions = sorted(regions.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "top_active_regions": top_regions,
            "total_active_regions": len(regions),
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "event_type": m.event_type,
                    "class_type": m.class_type,
                    "begin_time": m.begin_time,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"spaceweather_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[SpaceWeatherData]) -> Dict:
        """Get summary for console display."""
        event_types = self.get_event_type_analysis(measurements)
        
        return {
            "total_records": len(measurements),
            "event_types": len(event_types),
            "year_range": self.stats.get("year_range", "Unknown"),
        }
    
    def get_climate_trends(self, measurements: List[SpaceWeatherData]) -> Dict:
        """Get climate trends for console display."""
        event_types = self.get_event_type_analysis(measurements)
        flare = self.get_flare_analysis(measurements)
        storm = self.get_storm_analysis(measurements)
        
        return {
            "solar_flares": event_types.get("Solar Flare", 0),
            "cmes": event_types.get("CME", 0),
            "geomagnetic_storms": event_types.get("Geomagnetic Storm", 0),
        }


def initialize_space_weather_satellite(satellite_id: str = "SENTRY-23") -> SpaceWeatherAcquisitor:
    """Initialize space weather acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "space_weather", "space_weather_unified.csv")
    
    if os.path.exists(data_path):
        return SpaceWeatherAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Space weather data not found at {data_path}")
        return SpaceWeatherAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_space_weather_satellite()
    
    print("=== SENTRY-23 Space Weather Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=1748)
    print(f"\nAcquired: {len(measurements)}")
    
    event_types = acquisitor.get_event_type_analysis(measurements)
    print(f"\nEvent Type Distribution:")
    for etype, count in event_types.items():
        print(f"  {etype}: {count}")
    
    flare = acquisitor.get_flare_analysis(measurements)
    print(f"\nSolar Flare Analysis:")
    print(f"  X-class: {flare.get('x_class', 0)}")
    print(f"  M-class: {flare.get('m_class', 0)}")
    print(f"  C-class: {flare.get('c_class', 0)}")
    
    storm = acquisitor.get_storm_analysis(measurements)
    print(f"\nGeomagnetic Storm Analysis:")
    print(f"  G5 (Extreme): {storm.get('g5_extreme', 0)}")
    print(f"  G4 (Severe): {storm.get('g4_severe', 0)}")
    print(f"  G3 (Strong): {storm.get('g3_strong', 0)}")