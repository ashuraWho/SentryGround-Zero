"""
Satellite Data Acquisition System - Air Quality Module
Simulates satellite data collection from Air Quality sensors in Italian city.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class AirQualityMeasurement:
    """Air quality measurement data."""
    date: str
    time: str
    co_mg_m3: Optional[float]
    nmhc_ug_m3: Optional[float]
    c6h6_ug_m3: Optional[float]
    nox_ppb: Optional[float]
    no2_ug_m3: Optional[float]
    temperature_c: Optional[float]
    humidity_pct: Optional[float]
    abs_humidity: Optional[float]
    sensor_co: Optional[float]
    sensor_nmhc: Optional[float]
    satellite_id: str = "SENTRY-18"


class AirQualityAcquisitor:
    """
    Satellite data acquisition system for air quality.
    Simulates SENTRY-18 collecting air quality sensor data (Italian city, 2004-2005).
    """
    
    def __init__(self, satellite_id: str = "SENTRY-18", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[AirQualityMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load air quality data from CSV."""
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
        
        dates = set()
        co_values = []
        
        for row in self.raw_data:
            date = row.get('Date', '').strip()
            if date:
                dates.add(date)
            
            try:
                co = float(row.get('CO(GT)', 0))
                if co > 0:
                    co_values.append(co)
            except:
                pass
        
        self.stats = {
            "total_records": len(self.raw_data),
            "valid_records": len(co_values),
            "year_range": "2004-2005",
            "location": "Italian City",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[AirQualityMeasurement]:
        """Acquire air quality data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = AirQualityMeasurement(
                date=row.get('Date', '').strip(),
                time=row.get('Time', '').strip(),
                co_mg_m3=self._parse_float(row.get('CO(GT)')),
                nmhc_ug_m3=self._parse_float(row.get('NMHC(GT)')),
                c6h6_ug_m3=self._parse_float(row.get('C6H6(GT)')),
                nox_ppb=self._parse_float(row.get('NOx(GT)')),
                no2_ug_m3=self._parse_float(row.get('NO2(GT)')),
                temperature_c=self._parse_float(row.get('T')),
                humidity_pct=self._parse_float(row.get('RH')),
                abs_humidity=self._parse_float(row.get('AH')),
                sensor_co=self._parse_float(row.get('PT08.S1(CO)')),
                sensor_nmhc=self._parse_float(row.get('PT08.S2(NMHC)')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Air Quality Sensors (Italian City, 2004-2005)",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val: str) -> Optional[float]:
        """Parse float safely."""
        if val is None or val == '' or val == 'NA':
            return None
        try:
            return float(val)
        except:
            return None
    
    def get_pollution_analysis(self, measurements: List[AirQualityMeasurement]) -> Dict:
        """Analyze pollution levels."""
        co_values = [m.co_mg_m3 for m in measurements if m.co_mg_m3 is not None]
        nox_values = [m.nox_ppb for m in measurements if m.nox_ppb is not None]
        no2_values = [m.no2_ug_m3 for m in measurements if m.no2_ug_m3 is not None]
        c6h6 = [m.c6h6_ug_m3 for m in measurements if m.c6h6_ug_m3 is not None]
        
        high_co = sum(1 for v in co_values if v > 10) if co_values else 0
        high_nox = sum(1 for v in nox_values if v > 200) if nox_values else 0
        
        return {
            "avg_co_mg_m3": sum(co_values) / len(co_values) if co_values else 0,
            "avg_nox_ppb": sum(nox_values) / len(nox_values) if nox_values else 0,
            "avg_no2_ug_m3": sum(no2_values) / len(no2_values) if no2_values else 0,
            "avg_benzene_ug_m3": sum(c6h6) / len(c6h6) if c6h6 else 0,
            "high_co_readings": high_co,
            "high_nox_readings": high_nox,
        }
    
    def get_meteorological_analysis(self, measurements: List[AirQualityMeasurement]) -> Dict:
        """Analyze weather conditions."""
        temps = [m.temperature_c for m in measurements if m.temperature_c is not None]
        humidity = [m.humidity_pct for m in measurements if m.humidity_pct is not None]
        
        return {
            "avg_temp_c": sum(temps) / len(temps) if temps else 0,
            "min_temp_c": min(temps) if temps else 0,
            "max_temp_c": max(temps) if temps else 0,
            "avg_humidity_pct": sum(humidity) / len(humidity) if humidity else 0,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "date": m.date,
                    "co_mg_m3": m.co_mg_m3,
                    "nox_ppb": m.nox_ppb,
                    "no2_ug_m3": m.no2_ug_m3,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"airquality_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[AirQualityMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "year_range": "2004-2005",
            "location": "Italian City",
        }
    
    def get_climate_trends(self, measurements: List[AirQualityMeasurement]) -> Dict:
        """Get climate trends for console display."""
        pollution = self.get_pollution_analysis(measurements)
        weather = self.get_meteorological_analysis(measurements)
        
        return {
            "avg_co": pollution.get('avg_co_mg_m3', 0),
            "avg_nox": pollution.get('avg_nox_ppb', 0),
            "avg_no2": pollution.get('avg_no2_ug_m3', 0),
            "avg_temp": weather.get('avg_temp_c', 0),
            "avg_humidity": weather.get('avg_humidity_pct', 0),
        }


def initialize_air_quality_satellite(satellite_id: str = "SENTRY-18") -> AirQualityAcquisitor:
    """Initialize air quality acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "air_quality", "air_quality.csv")
    
    if os.path.exists(data_path):
        return AirQualityAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Air quality data not found at {data_path}")
        return AirQualityAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_air_quality_satellite()
    
    print("=== SENTRY-18 Air Quality Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=827)
    print(f"\nAcquired: {len(measurements)}")
    
    pollution = acquisitor.get_pollution_analysis(measurements)
    print(f"\nPollution Analysis:")
    print(f"  Avg CO: {pollution.get('avg_co_mg_m3', 0):.2f} mg/m3")
    print(f"  Avg NOx: {pollution.get('avg_nox_ppb', 0):.1f} ppb")
    print(f"  Avg NO2: {pollution.get('avg_no2_ug_m3', 0):.1f} ug/m3")
    
    weather = acquisitor.get_meteorological_analysis(measurements)
    print(f"\nWeather:")
    print(f"  Avg Temp: {weather.get('avg_temp_c', 0):.1f}°C")
    print(f"  Avg Humidity: {weather.get('avg_humidity_pct', 0):.1f}%")