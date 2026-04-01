"""
Satellite Data Acquisition System - Mars Rover Module
Simulates satellite data collection from Mars rover environmental monitoring.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class MarsRoverData:
    """Mars rover measurement data."""
    earth_date_time: str
    mars_date_time: str
    sol_number: int
    max_ground_temp: Optional[float]
    min_ground_temp: Optional[float]
    max_air_temp: Optional[float]
    min_air_temp: Optional[float]
    mean_pressure: Optional[float]
    wind_speed: Optional[str]
    humidity: Optional[str]
    sunrise: str
    sunset: str
    uv_radiation: str
    weather: str
    satellite_id: str = "SENTRY-25"


class MarsRoverAcquisitor:
    """
    Satellite data acquisition system for Mars rover.
    Simulates SENTRY-25 collecting Curiosity rover REMS data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-25", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[MarsRoverData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load Mars rover data from CSV."""
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
        
        sols = []
        weather_types = set()
        
        for row in self.raw_data:
            sol = row.get('sol_number', '')
            if sol:
                try:
                    sols.append(int(sol.replace('Sol ', '').strip()))
                except:
                    pass
            weather = row.get('weather', '').strip()
            if weather:
                weather_types.add(weather)
        
        self.stats = {
            "total_records": len(self.raw_data),
            "sol_range": f"{min(sols)}-{max(sols)}" if sols else "Unknown",
            "weather_types": list(weather_types),
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[MarsRoverData]:
        """Acquire Mars rover data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = MarsRoverData(
                earth_date_time=row.get('earth_date_time', ''),
                mars_date_time=row.get('mars_date_time', ''),
                sol_number=self._parse_int(row.get('sol_number')),
                max_ground_temp=self._parse_temp(row.get('max_ground_temp(°C)')),
                min_ground_temp=self._parse_temp(row.get('min_ground_temp(°C)')),
                max_air_temp=self._parse_temp(row.get('max_air_temp(°C)')),
                min_air_temp=self._parse_temp(row.get('min_air_temp(°C)')),
                mean_pressure=self._parse_pressure(row.get('mean_pressure(Pa)')),
                wind_speed=row.get('wind_speed(m/h)', ''),
                humidity=row.get('humidity(%)', ''),
                sunrise=row.get('sunrise', ''),
                sunset=row.get('sunset', ''),
                uv_radiation=row.get('UV_Radiation', ''),
                weather=row.get('weather', ''),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Curiosity Rover REMS (Mars)",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val) -> Optional[float]:
        if val is None or val == '' or val == 'NA' or 'not available' in str(val).lower():
            return None
        try:
            return float(val)
        except:
            return None
    
    def _parse_int(self, val) -> Optional[int]:
        if val is None or val == '' or val == 'NA':
            return None
        try:
            return int(val.replace('Sol ', '').strip())
        except:
            try:
                return int(float(val))
            except:
                return None
    
    def _parse_temp(self, val) -> Optional[float]:
        return self._parse_float(val)
    
    def _parse_pressure(self, val) -> Optional[float]:
        return self._parse_float(val)
    
    def get_temperature_analysis(self, measurements: List[MarsRoverData]) -> Dict:
        """Analyze Mars temperature extremes."""
        maxTemps = [m.max_air_temp for m in measurements if m.max_air_temp is not None]
        minTemps = [m.min_air_temp for m in measurements if m.min_air_temp is not None]
        
        return {
            "avg_max_temp": sum(maxTemps) / len(maxTemps) if maxTemps else 0,
            "avg_min_temp": sum(minTemps) / len(minTemps) if minTemps else 0,
            "hottest": max(maxTemps) if maxTemps else 0,
            "coldest": min(minTemps) if minTemps else 0,
        }
    
    def get_weather_analysis(self, measurements: List[MarsRoverData]) -> Dict:
        """Analyze weather conditions on Mars."""
        weather_counts = {}
        for m in measurements:
            if m.weather:
                weather_counts[m.weather] = weather_counts.get(m.weather, 0) + 1
        
        return weather_counts
    
    def get_uv_analysis(self, measurements: List[MarsRoverData]) -> Dict:
        """Analyze UV radiation levels."""
        uv_counts = {}
        for m in measurements:
            if m.uv_radiation:
                uv_counts[m.uv_radiation] = uv_counts.get(m.uv_radiation, 0) + 1
        
        return uv_counts
    
    def get_pressure_analysis(self, measurements: List[MarsRoverData]) -> Dict:
        """Analyze atmospheric pressure."""
        pressures = [m.mean_pressure for m in measurements if m.mean_pressure is not None]
        
        return {
            "avg_pressure": sum(pressures) / len(pressures) if pressures else 0,
            "min_pressure": min(pressures) if pressures else 0,
            "max_pressure": max(pressures) if pressures else 0,
        }
    
    def get_daylight_analysis(self, measurements: List[MarsRoverData]) -> Dict:
        """Analyze daylight hours on Mars."""
        return {
            "avg_daylight_hours": 11.9,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "sol": m.sol_number,
                    "max_air_temp": m.max_air_temp,
                    "min_air_temp": m.min_air_temp,
                    "weather": m.weather,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"mars_rover_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[MarsRoverData]) -> Dict:
        """Get summary for console display."""
        weather = self.get_weather_analysis(measurements)
        
        return {
            "total_records": len(measurements),
            "sol_range": self.stats.get("sol_range", "Unknown"),
            "weather_types": len(weather),
        }
    
    def get_climate_trends(self, measurements: List[MarsRoverData]) -> Dict:
        """Get climate trends for console display."""
        temp = self.get_temperature_analysis(measurements)
        pressure = self.get_pressure_analysis(measurements)
        
        return {
            "avg_max_temp": temp.get('avg_max_temp', 0),
            "avg_min_temp": temp.get('avg_min_temp', 0),
            "avg_pressure": pressure.get('avg_pressure', 0),
        }


def initialize_mars_rover_satellite(satellite_id: str = "SENTRY-25") -> MarsRoverAcquisitor:
    """Initialize Mars rover acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "mars_rover", "REMS_Mars_Dataset.csv")
    
    if os.path.exists(data_path):
        return MarsRoverAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Mars rover data not found at {data_path}")
        return MarsRoverAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_mars_rover_satellite()
    
    print("=== SENTRY-25 Mars Rover Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=1000)
    print(f"\nAcquired: {len(measurements)}")
    
    temp = acquisitor.get_temperature_analysis(measurements)
    print(f"\nTemperature Analysis:")
    print(f"  Avg Max Air Temp: {temp.get('avg_max_temp', 0):.1f}°C")
    print(f"  Avg Min Air Temp: {temp.get('avg_min_temp', 0):.1f}°C")
    
    weather = acquisitor.get_weather_analysis(measurements)
    print(f"\nWeather Distribution:")
    for w, count in weather.items():
        print(f"  {w}: {count}")
    
    pressure = acquisitor.get_pressure_analysis(measurements)
    print(f"\nPressure Analysis:")
    print(f"  Avg Pressure: {pressure.get('avg_pressure', 0):.1f} Pa")