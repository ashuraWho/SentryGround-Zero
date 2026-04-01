"""
Satellite Data Acquisition System - Global Temperatures Module
Simulates satellite data collection from Berkeley Earth global temperatures.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class GlobalTemperatureData:
    """Global temperature measurement data."""
    year: int
    month: int
    month_anomaly: Optional[float]
    month_uncertainty: Optional[float]
    annual_anomaly: Optional[float]
    annual_uncertainty: Optional[float]
    five_year_anomaly: Optional[float]
    five_year_uncertainty: Optional[float]
    ten_year_anomaly: Optional[float]
    ten_year_uncertainty: Optional[float]
    twenty_year_anomaly: Optional[float]
    twenty_year_uncertainty: Optional[float]
    satellite_id: str = "SENTRY-28"


class GlobalTemperatureAcquisitor:
    """
    Satellite data acquisition system for global temperatures.
    Simulates SENTRY-28 collecting Berkeley Earth temperature data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-28", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[GlobalTemperatureData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load temperature data from CSV."""
        data = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned_row = {k.strip(): v for k, v in row.items()}
                data.append(cleaned_row)
        return data
    
    def _calculate_stats(self):
        """Calculate dataset statistics."""
        if not self.raw_data:
            return
        
        years = set()
        for row in self.raw_data:
            year = row.get('Year', '').strip()
            if year:
                years.add(int(float(year)))
        
        self.stats = {
            "total_records": len(self.raw_data),
            "year_range": f"{min(years)}-{max(years)}" if years else "Unknown",
            "data_source": "Berkeley Earth",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[GlobalTemperatureData]:
        """Acquire global temperature data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = GlobalTemperatureData(
                year=self._parse_int(row.get('Year')),
                month=self._parse_int(row.get('Month')),
                month_anomaly=self._parse_float(row.get('Month Anomaly')),
                month_uncertainty=self._parse_float(row.get('Month Unc.')),
                annual_anomaly=self._parse_float(row.get('Annual Anomaly')),
                annual_uncertainty=self._parse_float(row.get('Annual Unc.')),
                five_year_anomaly=self._parse_float(row.get('Five-year Anomaly')),
                five_year_uncertainty=self._parse_float(row.get('Five-year Unc.')),
                ten_year_anomaly=self._parse_float(row.get('Ten-year Anomaly')),
                ten_year_uncertainty=self._parse_float(row.get('Ten-year Unc.')),
                twenty_year_anomaly=self._parse_float(row.get('Twenty-year Anomaly')),
                twenty_year_uncertainty=self._parse_float(row.get('Twenty-year Unc.')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Berkeley Earth Global Temperatures",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val) -> Optional[float]:
        if val is None or val == '' or val == 'NA' or 'NaN' in str(val):
            return None
        try:
            return float(val.strip())
        except:
            return None
    
    def _parse_int(self, val) -> Optional[int]:
        if val is None or val == '':
            return None
        try:
            return int(float(val.strip()))
        except:
            return None
    
    def get_temperature_trends(self, measurements: List[GlobalTemperatureData]) -> Dict:
        """Analyze temperature trends."""
        monthly = [m.month_anomaly for m in measurements if m.month_anomaly is not None]
        
        annual_data = [(m.year, m.annual_anomaly) for m in measurements if m.year and m.annual_anomaly is not None]
        annual_data.sort(key=lambda x: x[0])
        
        if len(annual_data) >= 2:
            first_annual = annual_data[0][1]
            last_annual = annual_data[-1][1]
            total_change = last_annual - first_annual
        else:
            total_change = 0
        
        return {
            "avg_monthly_anomaly": sum(monthly) / len(monthly) if monthly else 0,
            "max_anomaly": max(monthly) if monthly else 0,
            "min_anomaly": min(monthly) if monthly else 0,
            "total_change_celsius": total_change,
        }
    
    def get_decadal_analysis(self, measurements: List[GlobalTemperatureData]) -> Dict:
        """Analyze decadal temperature patterns."""
        decades = {}
        
        for m in measurements:
            if m.ten_year_anomaly is not None:
                decade = (m.year // 10) * 10
                if decade not in decades:
                    decades[decade] = []
                decades[decade].append(m.ten_year_anomaly)
        
        decade_avg = {}
        for decade, values in decades.items():
            decade_avg[decade] = sum(values) / len(values)
        
        return decade_avg
    
    def get_recent_trend(self, measurements: List[GlobalTemperatureData], years: int = 10) -> Dict:
        """Get recent temperature trend."""
        if not measurements or not measurements[-1].year:
            return {"recent_avg": 0, "trend_per_decade": 0, "years_analyzed": years}
        
        recent = [m for m in measurements if m.year and m.year >= measurements[-1].year - years]
        
        anomalies = [m.annual_anomaly for m in recent if m.annual_anomaly is not None]
        
        if len(anomalies) >= 2:
            trend = (anomalies[-1] - anomalies[0]) / len(anomalies)
        else:
            trend = 0
        
        return {
            "recent_avg": sum(anomalies) / len(anomalies) if anomalies else 0,
            "trend_per_decade": trend * 10,
            "years_analyzed": years,
        }
    
    def get_warming_analysis(self, measurements: List[GlobalTemperatureData]) -> Dict:
        """Analyze global warming patterns."""
        pre_industrial = [m.annual_anomaly for m in measurements if m.year and m.year < 1900 and m.annual_anomaly]
        post_2000 = [m.annual_anomaly for m in measurements if m.year and m.year >= 2000 and m.annual_anomaly]
        
        pre_avg = sum(pre_industrial) / len(pre_industrial) if pre_industrial else 0
        post_avg = sum(post_2000) / len(post_2000) if post_2000 else 0
        
        warming = post_avg - pre_avg
        
        return {
            "pre_1900_avg": pre_avg,
            "post_2000_avg": post_avg,
            "warming_since_preindustrial": warming,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "year": m.year,
                    "month": m.month,
                    "anomaly": m.month_anomaly,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
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
    
    def get_ocean_summary(self, measurements: List[GlobalTemperatureData]) -> Dict:
        """Get summary for console display."""
        trends = self.get_temperature_trends(measurements)
        
        return {
            "total_records": len(measurements),
            "year_range": self.stats.get("year_range", "Unknown"),
            "total_change": trends.get('total_change_celsius', 0),
        }
    
    def get_climate_trends(self, measurements: List[GlobalTemperatureData]) -> Dict:
        """Get climate trends for console display."""
        trends = self.get_temperature_trends(measurements)
        warming = self.get_warming_analysis(measurements)
        
        return {
            "total_change": trends.get('total_change_celsius', 0),
            "warming_since_preindustrial": warming.get('warming_since_preindustrial', 0),
        }


def initialize_temperature_satellite(satellite_id: str = "SENTRY-28") -> GlobalTemperatureAcquisitor:
    """Initialize global temperature acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "global_temperatures", "Global Temperatures.csv")
    
    if os.path.exists(data_path):
        return GlobalTemperatureAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Temperature data not found at {data_path}")
        return GlobalTemperatureAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_temperature_satellite()
    
    print("=== SENTRY-28 Global Temperatures Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=2077)
    print(f"\nAcquired: {len(measurements)}")
    
    trends = acquisitor.get_temperature_trends(measurements)
    print(f"\nTemperature Trends:")
    print(f"  Avg Monthly Anomaly: {trends.get('avg_monthly_anomaly', 0):.2f}°C")
    print(f"  Max Anomaly: {trends.get('max_anomaly', 0):.2f}°C")
    print(f"  Min Anomaly: {trends.get('min_anomaly', 0):.2f}°C")
    print(f"  Total Change: {trends.get('total_change_celsius', 0):.2f}°C")
    
    warming = acquisitor.get_warming_analysis(measurements)
    print(f"\nWarming Analysis:")
    print(f"  Pre-1900 Avg: {warming.get('pre_1900_avg', 0):.2f}°C")
    print(f"  Post-2000 Avg: {warming.get('post_2000_avg', 0):.2f}°C")
    print(f"  Warming since Pre-industrial: {warming.get('warming_since_preindustrial', 0):.2f}°C")
    
    recent = acquisitor.get_recent_trend(measurements, 10)
    print(f"\nRecent Trend (last 10 years):")
    print(f"  Avg: {recent.get('recent_avg', 0):.2f}°C")
    print(f"  Trend per decade: {recent.get('trend_per_decade', 0):.2f}°C/decade")