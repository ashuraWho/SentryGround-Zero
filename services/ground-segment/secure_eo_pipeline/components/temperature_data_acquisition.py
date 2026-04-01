"""
Satellite Data Acquisition System - Temperature Change Module
Simulates satellite data collection from FAOSTAT temperature change data.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class TemperatureChangeMeasurement:
    """Temperature change measurement data."""
    area_code: str
    area_name: str
    element: str
    month: str
    year: int
    value: float  # °C change from baseline
    flag: str
    satellite_id: str = "SENTRY-03"


class TemperatureDataAcquisitor:
    """
    Satellite data acquisition system for temperature change.
    Simulates SENTRY-03 collecting climate temperature data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-03", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[TemperatureChangeMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load temperature data from CSV."""
        data = []
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def _calculate_stats(self):
        """Calculate dataset statistics."""
        if not self.raw_data:
            return
        
        years = set()
        areas = set()
        values = []
        
        for row in self.raw_data:
            try:
                years.add(int(row.get('Year', 0)))
                areas.add(row.get('Area', 'Unknown'))
                val = float(row.get('Value', 0))
                if val:
                    values.append(val)
            except (ValueError, KeyError):
                continue
        
        self.stats = {
            "total_records": len(self.raw_data),
            "unique_areas": len(areas),
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
            "avg_change": sum(values) / len(values) if values else 0,
            "max_change": max(values) if values else 0,
            "min_change": min(values) if values else 0,
        }
    
    def acquire_data(self, country: Optional[str] = None,
                    start_year: Optional[int] = None,
                    end_year: Optional[int] = None,
                    month: Optional[str] = None,
                    limit: Optional[int] = None) -> List[TemperatureChangeMeasurement]:
        """Acquire temperature change measurements."""
        measurements = []
        
        for row in self.raw_data:
            try:
                area = row.get('Area', '').strip()
                year = int(row.get('Year', 0))
                month_val = row.get('Months', '').strip()
                value_str = row.get('Value', '0').strip()
                
                if country and country.lower() not in area.lower():
                    continue
                if start_year and year < start_year:
                    continue
                if end_year and year > end_year:
                    continue
                if month and month.lower() not in month_val.lower():
                    continue
                
                if not value_str:
                    continue
                    
                value = float(value_str)
                
                measurement = TemperatureChangeMeasurement(
                    area_code=row.get('Area Code (M49)', '').strip(),
                    area_name=area,
                    element=row.get('Element', '').strip(),
                    month=month_val,
                    year=year,
                    value=value,
                    flag=row.get('Flag', '').strip(),
                    satellite_id=self.satellite_id,
                )
                measurements.append(measurement)
                
                if limit and len(measurements) >= limit:
                    break
                    
            except (ValueError, KeyError):
                continue
        
        self.current_measurements = measurements
        self._record_acquisition(measurements)
        return measurements
    
    def _record_acquisition(self, measurements: List[TemperatureChangeMeasurement]):
        """Record acquisition event."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_count": len(measurements),
        }
        self.acquisition_history.append(record)
    
    def get_global_trend(self, measurements: List[TemperatureChangeMeasurement]) -> Dict:
        """Calculate global temperature trend."""
        if not measurements:
            return {}
        
        by_year = {}
        for m in measurements:
            if m.year not in by_year:
                by_year[m.year] = []
            by_year[m.year].append(m.value)
        
        yearly_avg = {year: sum(vals)/len(vals) for year, vals in by_year.items()}
        
        years = sorted(yearly_avg.keys())
        if len(years) < 2:
            return {"trend": "insufficient_data"}
        
        first_half = years[:len(years)//2]
        second_half = years[len(years)//2:]
        
        first_avg = sum(yearly_avg[y] for y in first_half) / len(first_half)
        second_avg = sum(yearly_avg[y] for y in second_half) / len(second_half)
        
        change = second_avg - first_avg
        
        return {
            "start_year": min(years),
            "end_year": max(years),
            "total_years": len(years),
            "first_period_avg": first_avg,
            "second_period_avg": second_avg,
            "total_change": change,
            "avg_annual_change": change / len(years),
            "trend": "warming" if change > 0.1 else "cooling" if change < -0.1 else "stable",
            "yearly_averages": yearly_avg,
        }
    
    def get_country_analysis(self, measurements: List[TemperatureChangeMeasurement]) -> Dict:
        """Analyze by country."""
        if not measurements:
            return {}
        
        by_country = {}
        for m in measurements:
            if m.area_name not in by_country:
                by_country[m.area_name] = []
            by_country[m.area_name].append(m.value)
        
        country_stats = {}
        for country, values in by_country.items():
            country_stats[country] = {
                "avg": sum(values) / len(values),
                "max": max(values),
                "min": min(values),
                "count": len(values),
            }
        
        top_warming = sorted(country_stats.items(), key=lambda x: x[1]['avg'], reverse=True)[:5]
        top_cooling = sorted(country_stats.items(), key=lambda x: x[1]['avg'])[:5]
        
        return {
            "total_countries": len(by_country),
            "top_warming": [(c, s['avg']) for c, s in top_warming],
            "top_cooling": [(c, s['avg']) for c, s in top_cooling],
            "global_avg": sum(m.value for m in measurements) / len(measurements),
        }
    
    def get_seasonal_analysis(self, measurements: List[TemperatureChangeMeasurement]) -> Dict:
        """Analyze seasonal patterns."""
        if not measurements:
            return {}
        
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']
        
        seasons = {
            "Winter": ["December", "January", "February"],
            "Spring": ["March", "April", "May"],
            "Summer": ["June", "July", "August"],
            "Fall": ["September", "October", "November"],
        }
        
        monthly_avg = {m: [] for m in months}
        for m in measurements:
            if m.month in monthly_avg:
                monthly_avg[m.month].append(m.value)
        
        seasonal_avg = {}
        for season, month_list in seasons.items():
            vals = []
            for mo in month_list:
                vals.extend(monthly_avg.get(mo, []))
            seasonal_avg[season] = sum(vals) / len(vals) if vals else 0
        
        return {
            "monthly": {m: sum(vs)/len(vs) if vs else 0 for m, vs in monthly_avg.items() if vs},
            "seasonal": seasonal_avg,
        }
    
    def export_telemetry(self, output_dir: str) -> str:
        """Export telemetry data."""
        os.makedirs(output_dir, exist_ok=True)
        
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "recent_acquisitions": self.acquisition_history[-5:],
        }
        
        filepath = os.path.join(output_dir, f"temperature_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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


def initialize_temperature_satellite(satellite_id: str = "SENTRY-03") -> TemperatureDataAcquisitor:
    """Initialize temperature data acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "temperature_change", "FAOSTAT_data_en_11-1-2024.csv")
    
    if os.path.exists(data_path):
        return TemperatureDataAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Temperature data not found at {data_path}")
        return TemperatureDataAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_temperature_satellite()
    
    print("=== SENTRY-03 Temperature Change Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=500)
    print(f"\nAcquired: {len(measurements)}")
    
    trend = acquisitor.get_global_trend(measurements)
    print(f"\nGlobal Trend: {trend.get('trend', 'N/A')}")
    print(f"  Change: {trend.get('total_change', 0):.2f}°C")
    print(f"  Period: {trend.get('start_year', 'N/A')}-{trend.get('end_year', 'N/A')}")
    
    country_analysis = acquisitor.get_country_analysis(measurements)
    print(f"\nTop Warming Countries:")
    for c, v in country_analysis.get('top_warming', [])[:3]:
        print(f"  {c}: +{v:.2f}°C")