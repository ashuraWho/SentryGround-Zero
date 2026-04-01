"""
Satellite Data Acquisition System - Volcanoes Module
Simulates satellite data collection from global volcanoes dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class VolcanoData:
    """Volcano measurement data."""
    region: str
    number: str
    volcano_name: str
    country: str
    location: str
    latitude: float
    longitude: float
    elevation: int
    volcano_type: str
    status: str
    last_eruption: str
    satellite_id: str = "SENTRY-29"


class VolcanoAcquisitor:
    """
    Satellite data acquisition system for volcanoes.
    Simulates SENTRY- collecting global volcano data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-29", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[VolcanoData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load volcano data from CSV."""
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
        
        regions = {}
        countries = {}
        types = {}
        
        for row in self.raw_data:
            region = row.get('Region', '').strip()
            country = row.get('Country', '').strip()
            vtype = row.get('Type', '').strip()
            
            if region:
                regions[region] = regions.get(region, 0) + 1
            if country:
                countries[country] = countries.get(country, 0) + 1
            if vtype:
                types[vtype] = types.get(vtype, 0) + 1
        
        self.stats = {
            "total_records": len(self.raw_data),
            "regions": len(regions),
            "countries": len(countries),
            "volcano_types": len(types),
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[VolcanoData]:
        """Acquire volcano data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = VolcanoData(
                region=row.get('Region', '').strip(),
                number=row.get('Number', '').strip(),
                volcano_name=row.get('Volcano Name', '').strip().strip('"'),
                country=row.get('Country', '').strip(),
                location=row.get('Location', '').strip(),
                latitude=self._parse_float(row.get('Latitude')),
                longitude=self._parse_float(row.get('Longitude')),
                elevation=self._parse_int(row.get('Elevation (m)')),
                volcano_type=row.get('Type', '').strip(),
                status=row.get('Status', '').strip(),
                last_eruption=row.get('Last Known Eruption', '').strip(),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Global Volcanoes 2021",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val) -> Optional[float]:
        if val is None or val == '':
            return None
        try:
            return float(val)
        except:
            return None
    
    def _parse_int(self, val) -> Optional[int]:
        if val is None or val == '':
            return None
        try:
            return int(float(val))
        except:
            return None
    
    def get_region_analysis(self, measurements: List[VolcanoData]) -> Dict:
        """Analyze volcano distribution by region."""
        regions = {}
        for m in measurements:
            if m.region:
                regions[m.region] = regions.get(m.region, 0) + 1
        
        sorted_regions = sorted(regions.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "region_counts": dict(sorted_regions),
            "total_regions": len(regions),
        }
    
    def get_country_analysis(self, measurements: List[VolcanoData]) -> Dict:
        """Analyze volcano distribution by country."""
        countries = {}
        for m in measurements:
            if m.country:
                countries[m.country] = countries.get(m.country, 0) + 1
        
        sorted_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "top_countries": sorted_countries,
            "total_countries": len(countries),
        }
    
    def get_type_analysis(self, measurements: List[VolcanoData]) -> Dict:
        """Analyze volcano types."""
        types = {}
        for m in measurements:
            if m.volcano_type:
                types[m.volcano_type] = types.get(m.volcano_type, 0) + 1
        
        sorted_types = sorted(types.items(), key=lambda x: x[1], reverse=True)
        
        return dict(sorted_types[:10])
    
    def get_elevation_analysis(self, measurements: List[VolcanoData]) -> Dict:
        """Analyze volcano elevations."""
        elevations = [m.elevation for m in measurements if m.elevation]
        
        return {
            "avg_elevation": sum(elevations) / len(elevations) if elevations else 0,
            "max_elevation": max(elevations) if elevations else 0,
            "min_elevation": min(elevations) if elevations else 0,
        }
    
    def get_status_analysis(self, measurements: List[VolcanoData]) -> Dict:
        """Analyze volcano status."""
        status_counts = {}
        for m in measurements:
            if m.status:
                status_counts[m.status] = status_counts.get(m.status, 0) + 1
        
        return status_counts
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "name": m.volcano_name,
                    "country": m.country,
                    "region": m.region,
                    "elevation": m.elevation,
                    "type": m.volcano_type,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"volcano_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[VolcanoData]) -> Dict:
        """Get summary for console display."""
        region = self.get_region_analysis(measurements)
        
        return {
            "total_records": len(measurements),
            "regions": region.get('total_regions', 0),
            "countries": self.stats.get("countries", 0),
        }
    
    def get_climate_trends(self, measurements: List[VolcanoData]) -> Dict:
        """Get climate trends for console display."""
        region = self.get_region_analysis(measurements)
        elevation = self.get_elevation_analysis(measurements)
        
        return {
            "top_region": list(region.get('region_counts', {}).items())[0] if region.get('region_counts') else ("", 0),
            "avg_elevation": elevation.get('avg_elevation', 0),
        }


def initialize_volcano_satellite(satellite_id: str = "SENTRY-29") -> VolcanoAcquisitor:
    """Initialize volcano acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "volcanoes", "volcanoes around the world in 2021.csv")
    
    if os.path.exists(data_path):
        return VolcanoAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Volcano data not found at {data_path}")
        return VolcanoAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_volcano_satellite()
    
    print("=== SENTRY-29 Volcanoes Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=1572)
    print(f"\nAcquired: {len(measurements)}")
    
    region = acquisitor.get_region_analysis(measurements)
    print(f"\nRegion Distribution:")
    for r, count in list(region.get('region_counts', {}).items())[:5]:
        print(f"  {r}: {count}")
    
    country = acquisitor.get_country_analysis(measurements)
    print(f"\nTop 5 Countries:")
    for c, count in country.get('top_countries', [])[:5]:
        print(f"  {c}: {count}")
    
    elevation = acquisitor.get_elevation_analysis(measurements)
    print(f"\nElevation Analysis:")
    print(f"  Avg: {elevation.get('avg_elevation', 0):.0f}m")
    print(f"  Max: {elevation.get('max_elevation', 0)}m")
    
    status = acquisitor.get_status_analysis(measurements)
    print(f"\nStatus Distribution:")
    for s, count in status.items():
        print(f"  {s}: {count}")