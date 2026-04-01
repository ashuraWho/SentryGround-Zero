"""
Satellite Data Acquisition System - Weather Data Module
Simulates satellite data collection from synthetic weather data for 10 US cities.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class WeatherMeasurement:
    """Weather measurement data."""
    location: str
    date_time: str
    temperature_c: float
    humidity_pct: float
    precipitation_mm: float
    wind_speed_kmh: float
    satellite_id: str = "SENTRY-15"


class WeatherAcquisitor:
    """
    Satellite data acquisition system for weather.
    Simulates SENTRY-15 collecting weather data for 10 US cities.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-15", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[WeatherMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load weather data from CSV."""
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
        
        locations = set()
        temps = []
        
        for row in self.raw_data:
            locations.add(row.get('Location', '').strip())
            try:
                temp = float(row.get('Temperature_C', 0))
                if temp != 0:
                    temps.append(temp)
            except:
                pass
        
        self.stats = {
            "total_records": len(self.raw_data),
            "locations": list(locations),
            "num_locations": len(locations),
            "avg_temp_c": sum(temps) / len(temps) if temps else 0,
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[WeatherMeasurement]:
        """Acquire weather data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = WeatherMeasurement(
                location=row.get('Location', '').strip(),
                date_time=row.get('Date_Time', '').strip(),
                temperature_c=self._parse_float(row.get('Temperature_C', '0')),
                humidity_pct=self._parse_float(row.get('Humidity_pct', '0')),
                precipitation_mm=self._parse_float(row.get('Precipitation_mm', '0')),
                wind_speed_kmh=self._parse_float(row.get('Wind_Speed_kmh', '0')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Synthetic Weather Data (10 US Cities)",
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
    
    def get_location_analysis(self, measurements: List[WeatherMeasurement]) -> Dict:
        """Analyze data by location."""
        locations = {}
        for m in measurements:
            if m.location not in locations:
                locations[m.location] = {"temps": [], "humidity": [], "precip": [], "wind": []}
            
            locations[m.location]["temps"].append(m.temperature_c)
            locations[m.location]["humidity"].append(m.humidity_pct)
            locations[m.location]["precip"].append(m.precipitation_mm)
            locations[m.location]["wind"].append(m.wind_speed_kmh)
        
        result = {}
        for loc, data in locations.items():
            result[loc] = {
                "avg_temp": sum(data["temps"]) / len(data["temps"]),
                "avg_humidity": sum(data["humidity"]) / len(data["humidity"]),
                "avg_precip": sum(data["precip"]) / len(data["precip"]),
                "avg_wind": sum(data["wind"]) / len(data["wind"]),
            }
        
        return result
    
    def get_temperature_analysis(self, measurements: List[WeatherMeasurement]) -> Dict:
        """Analyze temperature statistics."""
        temps = [m.temperature_c for m in measurements]
        
        return {
            "avg_temp_c": sum(temps) / len(temps) if temps else 0,
            "min_temp_c": min(temps) if temps else 0,
            "max_temp_c": max(temps) if temps else 0,
        }
    
    def get_extreme_weather(self, measurements: List[WeatherMeasurement]) -> Dict:
        """Find extreme weather events."""
        hottest = max(measurements, key=lambda m: m.temperature_c)
        coldest = min(measurements, key=lambda m: m.temperature_c)
        windiest = max(measurements, key=lambda m: m.wind_speed_kmh)
        rainiest = max(measurements, key=lambda m: m.precipitation_mm)
        
        return {
            "hottest": {"location": hottest.location, "temp": hottest.temperature_c},
            "coldest": {"location": coldest.location, "temp": coldest.temperature_c},
            "windiest": {"location": windiest.location, "wind": windiest.wind_speed_kmh},
            "rainiest": {"location": rainiest.location, "precip": rainiest.precipitation_mm},
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "location": m.location,
                    "temperature_c": m.temperature_c,
                    "humidity_pct": m.humidity_pct,
                    "precipitation_mm": m.precipitation_mm,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"weather_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[WeatherMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "unique_locations": len(set(m.location for m in measurements)),
            "avg_temp_c": sum(m.temperature_c for m in measurements) / len(measurements),
        }
    
    def get_climate_trends(self, measurements: List[WeatherMeasurement]) -> Dict:
        """Get climate trends for console display."""
        loc = self.get_location_analysis(measurements)
        temp = self.get_temperature_analysis(measurements)
        extreme = self.get_extreme_weather(measurements)
        
        return {
            "num_locations": len(loc),
            "avg_temp_c": temp.get('avg_temp_c', 0),
            "min_temp_c": temp.get('min_temp_c', 0),
            "max_temp_c": temp.get('max_temp_c', 0),
            "hottest_location": extreme.get('hottest', {}).get('location', ''),
            "coldest_location": extreme.get('coldest', {}).get('location', ''),
        }


def initialize_weather_satellite(satellite_id: str = "SENTRY-15") -> WeatherAcquisitor:
    """Initialize weather acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "weather", "weather_data.csv")
    
    if os.path.exists(data_path):
        return WeatherAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Weather data not found at {data_path}")
        return WeatherAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_weather_satellite()
    
    print("=== SENTRY-15 Weather Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=500)
    print(f"\nAcquired: {len(measurements)}")
    
    loc = acquisitor.get_location_analysis(measurements)
    print(f"\nLocation Analysis ({len(loc)} cities):")
    for l, d in list(loc.items())[:3]:
        print(f"  {l}: {d.get('avg_temp_c', 0):.1f}°C")
    
    extreme = acquisitor.get_extreme_weather(measurements)
    print(f"\nExtreme Weather:")
    print(f"  Hottest: {extreme.get('hottest', {}).get('location')} ({extreme.get('hottest', {}).get('temp', 0):.1f}°C)")
    print(f"  Coldest: {extreme.get('coldest', {}).get('location')} ({extreme.get('coldest', {}).get('temp', 0):.1f}°C)")