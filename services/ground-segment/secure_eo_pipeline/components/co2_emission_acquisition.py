"""
Satellite Data Acquisition System - CO2 Emissions Module
Simulates satellite data collection from global CO2 emissions data (1990-2018).
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class CO2EmissionMeasurement:
    """CO2 emission measurement data."""
    country: str
    sector: str
    gas: str
    year_1990: float
    year_1995: float
    year_2000: float
    year_2005: float
    year_2010: float
    year_2015: float
    year_2018: float
    satellite_id: str = "SENTRY-16"


class CO2EmissionAcquisitor:
    """
    Satellite data acquisition system for CO2 emissions.
    Simulates SENTRY-16 collecting global CO2 emissions data (1990-2018).
    """
    
    def __init__(self, satellite_id: str = "SENTRY-16", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[CO2EmissionMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load CO2 data from CSV."""
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
        
        countries = set()
        total_2018 = 0
        
        for row in self.raw_data:
            country = row.get('Country', '').strip()
            if country and country != 'World':
                countries.add(country)
            try:
                total_2018 += float(row.get('2018', 0))
            except:
                pass
        
        self.stats = {
            "total_records": len(self.raw_data),
            "countries": len(countries),
            "year_range": "1990-2018",
            "total_2018_mtco2": total_2018,
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[CO2EmissionMeasurement]:
        """Acquire CO2 data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = CO2EmissionMeasurement(
                country=row.get('Country', '').strip(),
                sector=row.get('Sector', '').strip(),
                gas=row.get('Gas', '').strip(),
                year_1990=self._parse_float(row.get('1990', '0')),
                year_1995=self._parse_float(row.get('1995', '0')),
                year_2000=self._parse_float(row.get('2000', '0')),
                year_2005=self._parse_float(row.get('2005', '0')),
                year_2010=self._parse_float(row.get('2010', '0')),
                year_2015=self._parse_float(row.get('2015', '0')),
                year_2018=self._parse_float(row.get('2018', '0')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Climate Watch / CAIT (1990-2018)",
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
    
    def get_country_analysis(self, measurements: List[CO2EmissionMeasurement]) -> Dict:
        """Analyze emissions by country."""
        country_2018 = {}
        
        for m in measurements:
            if m.country and m.year_2018 > 0:
                country_2018[m.country] = m.year_2018
        
        top_emitters = sorted(country_2018.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_countries": len(country_2018),
            "top_10_emitters": top_emitters,
        }
    
    def get_trend_analysis(self, measurements: List[CO2EmissionMeasurement]) -> Dict:
        """Analyze emission trends."""
        totals = {
            "1990": 0,
            "2000": 0,
            "2010": 0,
            "2018": 0,
        }
        
        for m in measurements:
            totals["1990"] += m.year_1990
            totals["2000"] += m.year_2000
            totals["2010"] += m.year_2010
            totals["2018"] += m.year_2018
        
        change_1990_2018 = ((totals["2018"] - totals["1990"]) / totals["1990"] * 100) if totals["1990"] > 0 else 0
        
        return {
            "total_1990": totals["1990"],
            "total_2000": totals["2000"],
            "total_2010": totals["2010"],
            "total_2018": totals["2018"],
            "change_1990_2018_pct": change_1990_2018,
        }
    
    def get_top_emitters(self, measurements: List[CO2EmissionMeasurement]) -> Dict:
        """Get top 5 emitters."""
        sorted_meas = sorted(measurements, key=lambda m: m.year_2018, reverse=True)
        
        top5 = []
        for m in sorted_meas[:5]:
            if m.country and m.year_2018 > 0:
                top5.append({
                    "country": m.country,
                    "emissions_2018": m.year_2018,
                    "change_from_1990": ((m.year_2018 - m.year_1990) / m.year_1990 * 100) if m.year_1990 > 0 else 0,
                })
        
        return {"top_5": top5}
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "country": m.country,
                    "year_2018": m.year_2018,
                    "year_1990": m.year_1990,
                }
                for m in self.current_measurements[:50]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"co2_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[CO2EmissionMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "countries": len(set(m.country for m in measurements)),
            "year_range": "1990-2018",
        }
    
    def get_climate_trends(self, measurements: List[CO2EmissionMeasurement]) -> Dict:
        """Get climate trends for console display."""
        trend = self.get_trend_analysis(measurements)
        top = self.get_top_emitters(measurements)
        
        return {
            "total_2018_mtco2": trend.get('total_2018', 0),
            "total_1990_mtco2": trend.get('total_1990', 0),
            "change_pct": trend.get('change_1990_2018_pct', 0),
            "top_emitter": top.get('top_5', [{}])[0].get('country', '') if top.get('top_5') else '',
        }


def initialize_co2_satellite(satellite_id: str = "SENTRY-16") -> CO2EmissionAcquisitor:
    """Initialize CO2 emission acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "co2_emissions", "emissions.csv")
    
    if os.path.exists(data_path):
        return CO2EmissionAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: CO2 data not found at {data_path}")
        return CO2EmissionAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_co2_satellite()
    
    print("=== SENTRY-16 CO2 Emissions Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=195)
    print(f"\nAcquired: {len(measurements)}")
    
    trend = acquisitor.get_trend_analysis(measurements)
    print(f"\nTrend Analysis:")
    print(f"  1990: {trend.get('total_1990', 0):.0f} MtCO2")
    print(f"  2018: {trend.get('total_2018', 0):.0f} MtCO2")
    print(f"  Change: {trend.get('change_1990_2018_pct', 0):.1f}%")
    
    top = acquisitor.get_top_emitters(measurements)
    print(f"\nTop Emitters:")
    for t in top.get('top_5', []):
        print(f"  {t.get('country')}: {t.get('emissions_2018', 0):.0f} MtCO2")