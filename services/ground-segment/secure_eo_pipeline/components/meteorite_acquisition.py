"""
Satellite Data Acquisition System - Meteorite Module
Simulates satellite data collection from NASA Meteorite Landings dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class MeteoriteMeasurement:
    """Meteorite measurement data."""
    name: str
    meteorite_id: int
    nametype: str
    recclass: str
    mass_grams: Optional[float]
    fall: str
    year: Optional[int]
    latitude: Optional[float]
    longitude: Optional[float]
    satellite_id: str = "SENTRY-10"


class MeteoriteAcquisitor:
    """
    Satellite data acquisition system for meteorites.
    Simulates SENTRY-10 collecting NASA meteorite landings data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-10", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[MeteoriteMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load meteorite data from CSV."""
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
        
        fell_count = 0
        found_count = 0
        classes = set()
        valid_count = 0
        relict_count = 0
        
        for row in self.raw_data:
            fall = row.get('fall', '').strip()
            if fall == 'Fell':
                fell_count += 1
            elif fall == 'Found':
                found_count += 1
            
            cls = row.get('recclass', '').strip()
            if cls:
                classes.add(cls)
            
            ntype = row.get('nametype', '').strip()
            if ntype == 'Valid':
                valid_count += 1
            elif ntype == 'Relict':
                relict_count += 1
        
        years = []
        for row in self.raw_data:
            try:
                year = int(row.get('year', 0))
                if 860 <= year <= 2016:
                    years.append(year)
            except:
                pass
        
        self.stats = {
            "total_records": len(self.raw_data),
            "fell_count": fell_count,
            "found_count": found_count,
            "valid_count": valid_count,
            "relict_count": relict_count,
            "unique_classes": len(classes),
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[MeteoriteMeasurement]:
        """Acquire meteorite data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            try:
                meteorite_id = int(row.get('id', 0))
            except:
                meteorite_id = 0
            
            try:
                year = int(row.get('year', 0))
                if not (860 <= year <= 2016):
                    year = None
            except:
                year = None
            
            try:
                mass = float(row.get('mass', 0))
                if mass <= 0:
                    mass = None
            except:
                mass = None
            
            try:
                lat = float(row.get('reclat', 0))
                lon = float(row.get('reclong', 0))
                if lat == 0 and lon == 0:
                    lat = None
                    lon = None
            except:
                lat = None
                lon = None
            
            measurement = MeteoriteMeasurement(
                name=row.get('name', '').strip(),
                meteorite_id=meteorite_id,
                nametype=row.get('nametype', '').strip(),
                recclass=row.get('recclass', '').strip(),
                mass_grams=mass,
                fall=row.get('fall', '').strip(),
                year=year,
                latitude=lat,
                longitude=lon,
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NASA Meteorite Landings",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def get_fall_analysis(self, measurements: List[MeteoriteMeasurement]) -> Dict:
        """Analyze fall vs found statistics."""
        fell = sum(1 for m in measurements if m.fall == 'Fell')
        found = sum(1 for m in measurements if m.fall == 'Found')
        
        total_mass_fell = sum(m.mass_grams for m in measurements if m.fall == 'Fell' and m.mass_grams)
        total_mass_found = sum(m.mass_grams for m in measurements if m.fall == 'Found' and m.mass_grams)
        
        return {
            "fell_count": fell,
            "found_count": found,
            "fell_percentage": (fell / len(measurements) * 100) if measurements else 0,
            "total_mass_fell_kg": total_mass_fell / 1000,
            "total_mass_found_kg": total_mass_found / 1000,
        }
    
    def get_class_analysis(self, measurements: List[MeteoriteMeasurement]) -> Dict:
        """Analyze meteorite class distribution."""
        classes = {}
        
        for m in measurements:
            cls = m.recclass
            classes[cls] = classes.get(cls, 0) + 1
        
        top_classes = sorted(classes.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "unique_classes": len(classes),
            "top_classes": top_classes,
        }
    
    def get_geographical_analysis(self, measurements: List[MeteoriteMeasurement]) -> Dict:
        """Analyze geographical distribution."""
        valid_locs = [m for m in measurements if m.latitude is not None and m.longitude is not None]
        
        if not valid_locs:
            return {"valid_locations": 0}
        
        lats = [m.latitude for m in valid_locs]
        lons = [m.longitude for m in valid_locs]
        
        north_cnt = sum(1 for m in valid_locs if m.latitude > 0)
        south_cnt = sum(1 for m in valid_locs if m.latitude < 0)
        
        return {
            "valid_locations": len(valid_locs),
            "avg_latitude": sum(lats) / len(lats),
            "avg_longitude": sum(lons) / len(lons),
            "north_hemisphere": north_cnt,
            "south_hemisphere": south_cnt,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "name": m.name,
                    "recclass": m.recclass,
                    "mass_grams": m.mass_grams,
                    "fall": m.fall,
                    "year": m.year,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"meteorite_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[MeteoriteMeasurement]) -> Dict:
        """Get summary for console display."""
        fall = self.get_fall_analysis(measurements)
        
        years = [m.year for m in measurements if m.year]
        
        return {
            "total_records": len(measurements),
            "fell": fall.get('fell_count', 0),
            "found": fall.get('found_count', 0),
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
        }
    
    def get_climate_trends(self, measurements: List[MeteoriteMeasurement]) -> Dict:
        """Get climate trends for console display."""
        fall = self.get_fall_analysis(measurements)
        geo = self.get_geographical_analysis(measurements)
        cls = self.get_class_analysis(measurements)
        
        largest = max((m.mass_grams for m in measurements if m.mass_grams), default=0)
        
        return {
            "fell_count": fall.get('fell_count', 0),
            "found_count": fall.get('found_count', 0),
            "total_mass_kg": (fall.get('total_mass_fell_kg', 0) + fall.get('total_mass_found_kg', 0)),
            "largest_mass_kg": largest / 1000 if largest else 0,
            "unique_classes": cls.get('unique_classes', 0),
        }


def initialize_meteorite_satellite(satellite_id: str = "SENTRY-10") -> MeteoriteAcquisitor:
    """Initialize meteorite acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "meteorites", "meteorite-landings.csv")
    
    if os.path.exists(data_path):
        return MeteoriteAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Meteorite data not found at {data_path}")
        return MeteoriteAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_meteorite_satellite()
    
    print("=== SENTRY-10 Meteorite Landings Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=500)
    print(f"\nAcquired: {len(measurements)}")
    
    fall = acquisitor.get_fall_analysis(measurements)
    print(f"\nFall Analysis:")
    print(f"  Fell: {fall.get('fell_count', 0)}")
    print(f"  Found: {fall.get('found_count', 0)}")
    
    geo = acquisitor.get_geographical_analysis(measurements)
    print(f"\nGeographical Analysis:")
    print(f"  Valid Locations: {geo.get('valid_locations', 0)}")
    print(f"  North: {geo.get('north_hemisphere', 0)}, South: {geo.get('south_hemisphere', 0)}")