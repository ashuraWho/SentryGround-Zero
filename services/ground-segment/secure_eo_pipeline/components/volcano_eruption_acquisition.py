"""
Satellite Data Acquisition System - Volcano Eruptions Module
Simulates satellite data collection from NOAA volcano eruptions dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class VolcanoEruptionData:
    """Volcano eruption measurement data."""
    year: int
    month: Optional[int]
    day: Optional[int]
    tsu: str
    eq: str
    name: str
    location: str
    country: str
    latitude: float
    longitude: float
    elevation: int
    volcano_type: str
    status: str
    time: str
    vei: Optional[int]
    deaths: Optional[int]
    injuries: Optional[int]
    damage_millions: Optional[float]
    houses_destroyed: Optional[int]
    satellite_id: str = "SENTRY-30"


class VolcanoEruptionAcquisitor:
    """
    Satellite data acquisition system for volcano eruptions.
    Simulates SENTRY-30 collecting NOAA volcano eruption data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-30", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[VolcanoEruptionData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load volcano eruption data from CSV."""
        data = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Year', '').strip():
                    data.append(row)
        return data
    
    def _calculate_stats(self):
        """Calculate dataset statistics."""
        if not self.raw_data:
            return
        
        years = set()
        countries = set()
        types = set()
        
        for row in self.raw_data:
            year = row.get('Year', '').strip()
            country = row.get('Country', '').strip()
            vtype = row.get('Type', '').strip()
            
            if year:
                years.add(int(float(year)))
            if country:
                countries.add(country)
            if vtype:
                types.add(vtype)
        
        total_deaths = sum(int(float(row.get('DEATHS', 0) or 0)) for row in self.raw_data if row.get('DEATHS'))
        
        self.stats = {
            "total_records": len(self.raw_data),
            "year_range": f"{min(years)}-{max(years)}" if years else "Unknown",
            "countries": len(countries),
            "volcano_types": len(types),
            "total_deaths": total_deaths,
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[VolcanoEruptionData]:
        """Acquire volcano eruption data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = VolcanoEruptionData(
                year=self._parse_int(row.get('Year')),
                month=self._parse_int(row.get('Month')),
                day=self._parse_int(row.get('Day')),
                tsu=row.get('TSU', '').strip(),
                eq=row.get('EQ', '').strip(),
                name=row.get('Name', '').strip(),
                location=row.get('Location', '').strip(),
                country=row.get('Country', '').strip(),
                latitude=self._parse_float(row.get('Latitude')),
                longitude=self._parse_float(row.get('Longitude')),
                elevation=self._parse_int(row.get('Elevation')),
                volcano_type=row.get('Type', '').strip(),
                status=row.get('Status', '').strip(),
                time=row.get('Time', '').strip(),
                vei=self._parse_int(row.get('VEI')),
                deaths=self._parse_int(row.get('DEATHS')),
                injuries=self._parse_int(row.get('INJURIES')),
                damage_millions=self._parse_float(row.get('DAMAGE_MILLIONS_DOLLARS')),
                houses_destroyed=self._parse_int(row.get('HOUSES_DESTROYED')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NOAA Volcano Eruptions 2010-2018",
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
    
    def get_yearly_analysis(self, measurements: List[VolcanoEruptionData]) -> Dict:
        """Analyze eruptions by year."""
        years = {}
        for m in measurements:
            if m.year:
                years[m.year] = years.get(m.year, 0) + 1
        
        return dict(sorted(years.items()))
    
    def get_country_analysis(self, measurements: List[VolcanoEruptionData]) -> Dict:
        """Analyze eruptions by country."""
        countries = {}
        for m in measurements:
            if m.country:
                countries[m.country] = countries.get(m.country, 0) + 1
        
        sorted_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)
        
        return {"top_countries": sorted_countries[:10], "total_countries": len(countries)}
    
    def get_type_analysis(self, measurements: List[VolcanoEruptionData]) -> Dict:
        """Analyze volcano types."""
        types = {}
        for m in measurements:
            if m.volcano_type:
                types[m.volcano_type] = types.get(m.volcano_type, 0) + 1
        
        return dict(sorted(types.items(), key=lambda x: x[1], reverse=True))
    
    def get_impact_analysis(self, measurements: List[VolcanoEruptionData]) -> Dict:
        """Analyze eruption impacts."""
        total_deaths = sum(m.deaths for m in measurements if m.deaths)
        total_injuries = sum(m.injuries for m in measurements if m.injuries)
        total_damage = sum(m.damage_millions for m in measurements if m.damage_millions)
        
        return {
            "total_deaths": total_deaths,
            "total_injuries": total_injuries,
            "total_damage_millions": total_damage,
        }
    
    def get_vei_analysis(self, measurements: List[VolcanoEruptionData]) -> Dict:
        """Analyze Volcanic Explosivity Index."""
        vei_counts = {}
        for m in measurements:
            if m.vei is not None:
                vei_counts[m.vei] = vei_counts.get(m.vei, 0) + 1
        
        return vei_counts
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "name": m.name,
                    "country": m.country,
                    "year": m.year,
                    "vei": m.vei,
                    "deaths": m.deaths,
                }
                for m in self.current_measurements
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"volcano_eruptions_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[VolcanoEruptionData]) -> Dict:
        """Get summary for console display."""
        yearly = self.get_yearly_analysis(measurements)
        
        return {
            "total_records": len(measurements),
            "year_range": self.stats.get("year_range", "Unknown"),
            "countries": self.stats.get("countries", 0),
        }
    
    def get_climate_trends(self, measurements: List[VolcanoEruptionData]) -> Dict:
        """Get climate trends for console display."""
        impact = self.get_impact_analysis(measurements)
        vei = self.get_vei_analysis(measurements)
        
        return {
            "total_deaths": impact.get('total_deaths', 0),
            "total_damage": impact.get('total_damage_millions', 0),
        }


def initialize_volcano_eruption_satellite(satellite_id: str = "SENTRY-30") -> VolcanoEruptionAcquisitor:
    """Initialize volcano eruption acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "volcano_eruptions", "volcano_data_2010.csv")
    
    if os.path.exists(data_path):
        return VolcanoEruptionAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Volcano eruption data not found at {data_path}")
        return VolcanoEruptionAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_volcano_eruption_satellite()
    
    print("=== SENTRY-30 Volcano Eruptions Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=63)
    print(f"\nAcquired: {len(measurements)}")
    
    yearly = acquisitor.get_yearly_analysis(measurements)
    print(f"\nYearly Distribution:")
    for year, count in yearly.items():
        print(f"  {year}: {count}")
    
    country = acquisitor.get_country_analysis(measurements)
    print(f"\nTop Countries:")
    for c, count in country.get('top_countries', [])[:5]:
        print(f"  {c}: {count}")
    
    vei = acquisitor.get_vei_analysis(measurements)
    print(f"\nVEI Distribution:")
    for v, count in vei.items():
        print(f"  VEI {v}: {count}")
    
    impact = acquisitor.get_impact_analysis(measurements)
    print(f"\nImpact Analysis:")
    print(f"  Total Deaths: {impact.get('total_deaths', 0)}")
    print(f"  Total Injuries: {impact.get('total_injuries', 0)}")
    print(f"  Total Damage: ${impact.get('total_damage_millions', 0):.1f}M")