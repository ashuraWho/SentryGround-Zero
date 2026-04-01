"""
Satellite Data Acquisition System - Plastic Pollution Module
Simulates satellite data collection from plastic pollution dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class PlasticPollutionData:
    """Plastic pollution measurement data."""
    entity: str
    year: int
    coastal_population: int
    per_capita_waste: float
    share_plastics: float
    share_inadequately_managed: float
    municipal_waste: int
    plastic_waste_generated: float
    inadequately_managed: float
    plastic_waste_littered: float
    per_capita_mismanaged: float
    total_mismanaged_2010: float
    total_mismanaged_2025: float
    per_capita_plastic_waste: float
    satellite_id: str = "SENTRY-21"


class PlasticPollutionAcquisitor:
    """
    Satellite data acquisition system for plastic pollution.
    Simulates SENTRY-21 collecting plastic waste data (Jambeck et al. 2015).
    """
    
    def __init__(self, satellite_id: str = "SENTRY-21", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[PlasticPollutionData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load plastic pollution data from CSV."""
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
        total_waste_2010 = []
        
        for row in self.raw_data:
            try:
                waste = float(row.get('Total mismanaged plastic waste in 2010', 0))
                if waste > 0:
                    total_waste_2010.append(waste)
            except:
                pass
        
        self.stats = {
            "total_records": len(self.raw_data),
            "countries": countries,
            "year": 2010,
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[PlasticPollutionData]:
        """Acquire plastic pollution data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = PlasticPollutionData(
                entity=row.get('Entity', '').strip(),
                year=self._parse_int(row.get('Year')),
                coastal_population=self._parse_int(row.get('Coastal population')),
                per_capita_waste=self._parse_float(row.get('Per capita waste generation rate')),
                share_plastics=self._parse_float(row.get('Share of plastics in waste stream')),
                share_inadequately_managed=self._parse_float(row.get('Share of plastic inadequately managed')),
                municipal_waste=self._parse_int(row.get('Municipal waste generated')),
                plastic_waste_generated=self._parse_float(row.get('Plastic waste generated')),
                inadequately_managed=self._parse_float(row.get('Inadequately managed plastic waste')),
                plastic_waste_littered=self._parse_float(row.get('Plastic waste littered')),
                per_capita_mismanaged=self._parse_float(row.get('Per capita mismanaged plastic waste')),
                total_mismanaged_2010=self._parse_float(row.get('Total mismanaged plastic waste in 2010')),
                total_mismanaged_2025=self._parse_float(row.get('Total mismanaged plastic waste in 2025')),
                per_capita_plastic_waste=self._parse_float(row.get('Per capita plastic waste (kg/person/day)')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Plastic Waste - Jambeck et al. (2015)",
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
    
    def _parse_int(self, val) -> Optional[int]:
        """Parse int safely."""
        if val is None or val == '' or val == 'NA':
            return None
        try:
            return int(float(val))
        except:
            return None
    
    def get_pollution_analysis(self, measurements: List[PlasticPollutionData]) -> Dict:
        """Analyze plastic pollution levels."""
        high_pollution = sum(1 for m in measurements if m.share_inadequately_managed and m.share_inadequately_managed > 50)
        low_pollution = sum(1 for m in measurements if m.share_inadequately_managed is not None and m.share_inadequately_managed < 10)
        
        return {
            "high_pollution_countries": high_pollution,
            "low_pollution_countries": low_pollution,
        }
    
    def get_top_polluters(self, measurements: List[PlasticPollutionData]) -> Dict:
        """Get top plastic polluters."""
        sorted_by_waste = sorted(
            [(m.entity, m.total_mismanaged_2010) for m in measurements if m.total_mismanaged_2010],
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "top_10": sorted_by_waste[:10],
        }
    
    def get_projection_analysis(self, measurements: List[PlasticPollutionData]) -> Dict:
        """Analyze 2025 projections."""
        increased = sum(1 for m in measurements if m.total_mismanaged_2025 and m.total_mismanaged_2010 and m.total_mismanaged_2025 > m.total_mismanaged_2010)
        
        total_2010 = sum(m.total_mismanaged_2010 for m in measurements if m.total_mismanaged_2010)
        total_2025 = sum(m.total_mismanaged_2025 for m in measurements if m.total_mismanaged_2025)
        
        return {
            "countries_with_increased_pollution": increased,
            "projected_total_2010": total_2010,
            "projected_total_2025": total_2025,
        }
    
    def get_waste_generation_analysis(self, measurements: List[PlasticPollutionData]) -> Dict:
        """Analyze waste generation patterns."""
        per_capita = [m.per_capita_waste for m in measurements if m.per_capita_waste is not None]
        plastics_share = [m.share_plastics for m in measurements if m.share_plastics is not None]
        
        return {
            "avg_per_capita_waste": sum(per_capita) / len(per_capita) if per_capita else 0,
            "avg_plastics_share": sum(plastics_share) / len(plastics_share) if plastics_share else 0,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "entity": m.entity,
                    "coastal_population": m.coastal_population,
                    "total_mismanaged_2010": m.total_mismanaged_2010,
                    "share_inadequately_managed": m.share_inadequately_managed,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"plastic_pollution_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[PlasticPollutionData]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "countries": len(set(m.entity for m in measurements if m.entity)),
            "year": 2010,
        }
    
    def get_climate_trends(self, measurements: List[PlasticPollutionData]) -> Dict:
        """Get climate trends for console display."""
        pollution = self.get_pollution_analysis(measurements)
        projection = self.get_projection_analysis(measurements)
        
        return {
            "high_pollution": pollution.get('high_pollution_countries', 0),
            "projected_increase": projection.get('countries_with_increased_pollution', 0),
        }


def initialize_plastic_pollution_satellite(satellite_id: str = "SENTRY-21") -> PlasticPollutionAcquisitor:
    """Initialize plastic pollution acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "plastic_pollution", "plastic_waste.csv")
    
    if os.path.exists(data_path):
        return PlasticPollutionAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Plastic pollution data not found at {data_path}")
        return PlasticPollutionAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_plastic_pollution_satellite()
    
    print("=== SENTRY-21 Plastic Pollution Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=200)
    print(f"\nAcquired: {len(measurements)}")
    
    pollution = acquisitor.get_pollution_analysis(measurements)
    print(f"\nPollution Analysis:")
    print(f"  High pollution countries (>50%): {pollution.get('high_pollution_countries', 0)}")
    print(f"  Low pollution countries (<10%): {pollution.get('low_pollution_countries', 0)}")
    
    top_polluters = acquisitor.get_top_polluters(measurements)
    print(f"\nTop 5 Plastic Polluters (2010):")
    for entity, waste in top_polluters.get('top_10', [])[:5]:
        print(f"  {entity}: {waste:,.0f} tonnes")
    
    projection = acquisitor.get_projection_analysis(measurements)
    print(f"\n2025 Projections:")
    print(f"  Countries with increased pollution: {projection.get('countries_with_increased_pollution', 0)}")
    print(f"  Projected total (2025): {projection.get('projected_total_2025', 0):,.0f} tonnes")