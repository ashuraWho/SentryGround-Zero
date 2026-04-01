"""
Satellite Data Acquisition System - Climate Change Module
Simulates satellite data collection from Berkeley Earth climate data.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class ClimateChangeMeasurement:
    """Climate change measurement data."""
    date: datetime
    year: int
    month: int
    land_avg_temp: Optional[float]
    land_avg_uncertainty: Optional[float]
    land_max_temp: Optional[float]
    land_min_temp: Optional[float]
    land_ocean_avg_temp: Optional[float]
    land_ocean_avg_uncertainty: Optional[float]
    country: Optional[str]
    country_temp: Optional[float]
    satellite_id: str = "SENTRY-05"


class ClimateChangeAcquisitor:
    """
    Satellite data acquisition system for climate change.
    Simulates SENTRY-05 collecting Berkeley Earth surface temperature data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-05", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.global_path = data_path
        self.country_path = data_path.replace(".csv", "_by_country.csv") if data_path else None
        self.raw_data: List[Dict] = []
        self.country_data: List[Dict] = []
        self.current_measurements: List[ClimateChangeMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        if self.country_path and os.path.exists(self.country_path):
            self.country_data = self._load_country_data(self.country_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load global temperature data from CSV."""
        data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def _load_country_data(self, filepath: str) -> List[Dict]:
        """Load country temperature data from CSV."""
        data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def _calculate_stats(self):
        """Calculate dataset statistics."""
        if not self.raw_data:
            return
        
        years = set()
        valid_temps = 0
        
        for row in self.raw_data:
            dt = row.get('dt', '')
            if dt:
                try:
                    year = int(dt.split('-')[0])
                    years.add(year)
                except:
                    pass
            
            if row.get('LandAverageTemperature'):
                valid_temps += 1
        
        self.stats = {
            "total_records": len(self.raw_data),
            "valid_temps": valid_temps,
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
            "countries": len(set(r.get('Country', '') for r in self.country_data)) if self.country_data else 0,
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[ClimateChangeMeasurement]:
        """Acquire climate data."""
        measurements = []
        
        data_slice = self.raw_data[offset:offset + limit] if offset < len(self.raw_data) else self.raw_data[:limit]
        
        for row in data_slice:
            dt = row.get('dt', '')
            if not dt:
                continue
            
            try:
                date = datetime.strptime(dt, '%Y-%m-%d')
            except:
                continue
            
            measurement = ClimateChangeMeasurement(
                date=date,
                year=date.year,
                month=date.month,
                land_avg_temp=self._parse_float(row.get('LandAverageTemperature')),
                land_avg_uncertainty=self._parse_float(row.get('LandAverageTemperatureUncertainty')),
                land_max_temp=self._parse_float(row.get('LandMaxTemperature')),
                land_min_temp=self._parse_float(row.get('LandMinTemperature')),
                land_ocean_avg_temp=self._parse_float(row.get('LandAndOceanAverageTemperature')),
                land_ocean_avg_uncertainty=self._parse_float(row.get('LandAndOceanAverageTemperatureUncertainty')),
                country=None,
                country_temp=None,
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Berkeley Earth",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val):
        """Parse float safely."""
        if val is None or val == '':
            return None
        try:
            return float(val)
        except:
            return None
    
    def get_global_trend(self, measurements: List[ClimateChangeMeasurement]) -> Dict:
        """Analyze global temperature trend."""
        yearly_temps = {}
        yearly_ocean = {}
        
        for m in measurements:
            if m.land_avg_temp is not None:
                if m.year not in yearly_temps:
                    yearly_temps[m.year] = []
                yearly_temps[m.year].append(m.land_avg_temp)
            
            if m.land_ocean_avg_temp is not None:
                if m.year not in yearly_ocean:
                    yearly_ocean[m.year] = []
                yearly_ocean[m.year].append(m.land_ocean_avg_temp)
        
        avg_by_year = {y: sum(vs)/len(vs) for y, vs in yearly_temps.items()}
        ocean_by_year = {y: sum(vs)/len(vs) for y, vs in yearly_ocean.items()}
        
        years = sorted(avg_by_year.keys())
        if len(years) >= 2:
            start_temp = avg_by_year[years[0]]
            end_temp = avg_by_year[years[-1]]
            total_change = end_temp - start_temp
            
            trend = "WARMING" if total_change > 0.5 else "COOLING" if total_change < -0.5 else "STABLE"
        else:
            total_change = 0
            trend = "UNKNOWN"
        
        return {
            "trend": trend,
            "total_change": total_change,
            "start_year": years[0] if years else None,
            "end_year": years[-1] if years else None,
            "avg_by_year": avg_by_year,
            "ocean_by_year": ocean_by_year,
        }
    
    def get_country_analysis(self, measurements: List[ClimateChangeMeasurement]) -> Dict:
        """Analyze temperature by country."""
        if not self.country_data:
            return {"total_countries": 0}
        
        country_yearly = {}
        
        for row in self.country_data[:5000]:
            country = row.get('Country', '')
            dt = row.get('dt', '')
            temp = self._parse_float(row.get('AverageTemperature'))
            
            if not country or not dt or temp is None:
                continue
            
            try:
                year = int(dt.split('-')[0])
            except:
                continue
            
            if country not in country_yearly:
                country_yearly[country] = {}
            if year not in country_yearly[country]:
                country_yearly[country][year] = []
            country_yearly[country][year].append(temp)
        
        country_changes = {}
        for country, yearly in country_yearly.items():
            years = sorted(yearly.keys())
            if len(years) >= 2:
                start = sum(yearly[years[0]]) / len(yearly[years[0]])
                end = sum(yearly[years[-1]]) / len(yearly[years[-1]])
                country_changes[country] = end - start
        
        top_warming = sorted(country_changes.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_countries": len(country_yearly),
            "country_changes": country_changes,
            "top_warming": top_warming,
        }
    
    def get_seasonal_analysis(self, measurements: List[ClimateChangeMeasurement]) -> Dict:
        """Analyze seasonal patterns."""
        months = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: [], 9: [], 10: [], 11: [], 12: []}
        
        for m in measurements:
            if m.land_avg_temp is not None:
                months[m.month].append(m.land_avg_temp)
        
        seasonal_avg = {m: sum(temps) / len(temps) if temps else None for m, temps in months.items()}
        
        return {
            "monthly_avg": seasonal_avg,
            "warmest_month": max((v, k) for k, v in seasonal_avg.items() if v is not None)[1],
            "coldest_month": min((v, k) for k, v in seasonal_avg.items() if v is not None)[1],
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "date": m.date.isoformat(),
                    "land_avg_temp": m.land_avg_temp,
                    "land_ocean_avg_temp": m.land_ocean_avg_temp,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"climate_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[ClimateChangeMeasurement]) -> Dict:
        """Get summary for console display."""
        years = sorted(set(m.year for m in measurements if m.year))
        trend = self.get_global_trend(measurements)
        
        return {
            "total_records": len(measurements),
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
            "valid_temps": sum(1 for m in measurements if m.land_avg_temp is not None),
        }
    
    def get_climate_trends(self, measurements: List[ClimateChangeMeasurement]) -> Dict:
        """Get climate trends for console display."""
        trend = self.get_global_trend(measurements)
        
        return {
            "avg_temp_change": trend.get('total_change', 0),
            "trend": trend.get('trend', 'UNKNOWN'),
            "period": f"{trend.get('start_year', 'N/A')}-{trend.get('end_year', 'N/A')}",
        }


def initialize_climate_satellite(satellite_id: str = "SENTRY-05") -> ClimateChangeAcquisitor:
    """Initialize climate change acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "climate_change", "GlobalTemperatures.csv")
    
    if os.path.exists(data_path):
        return ClimateChangeAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Climate data not found at {data_path}")
        return ClimateChangeAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_climate_satellite()
    
    print("=== SENTRY-05 Climate Change Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=500)
    print(f"\nAcquired: {len(measurements)}")
    
    trend = acquisitor.get_global_trend(measurements)
    print(f"\nGlobal Trend Analysis:")
    print(f"  Trend: {trend.get('trend', 'UNKNOWN')}")
    print(f"  Total Change: {trend.get('total_change', 0):.2f}°C")
    print(f"  Period: {trend.get('start_year', 'N/A')}-{trend.get('end_year', 'N/A')}")
    
    country = acquisitor.get_country_analysis(measurements)
    print(f"\nCountry Analysis:")
    print(f"  Countries: {country.get('total_countries', 0)}")