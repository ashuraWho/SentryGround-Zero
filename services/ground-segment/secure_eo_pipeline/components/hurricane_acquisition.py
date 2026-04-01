"""
Satellite Data Acquisition System - Hurricane/Typhoon Module
Simulates satellite data collection from NOAA hurricane database.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class HurricaneMeasurement:
    """Hurricane/typhoon measurement data."""
    storm_id: str
    name: str
    date: str
    time: str
    event: str
    status: str
    latitude: float
    longitude: float
    max_wind_knots: Optional[int]
    min_pressure_mb: Optional[int]
    satellite_id: str = "SENTRY-07"


class HurricaneAcquisitor:
    """
    Satellite data acquisition system for hurricanes/typhoons.
    Simulates SENTRY-07 collecting NOAA hurricane tracking data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-07", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.atlantic_path = data_path
        self.pacific_path = data_path.replace("atlantic", "pacific") if data_path else None
        self.raw_data: List[Dict] = []
        self.current_measurements: List[HurricaneMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load hurricane data from CSV."""
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
        
        years = set()
        statuses = set()
        storms = set()
        
        for row in self.raw_data:
            date = row.get('Date', '')
            if len(date) >= 4:
                years.add(date[:4])
            statuses.add(row.get('Status', '').strip())
            storms.add(row.get('ID', '').strip())
        
        self.stats = {
            "total_records": len(self.raw_data),
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
            "unique_storms": len(storms),
            "status_types": list(statuses),
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[HurricaneMeasurement]:
        """Acquire hurricane data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            max_wind = int(row.get('Maximum Wind', -999))
            min_pressure = int(row.get('Minimum Pressure', -999))
            
            measurement = HurricaneMeasurement(
                storm_id=row.get('ID', '').strip(),
                name=row.get('Name', '').strip(),
                date=row.get('Date', ''),
                time=row.get('Time', ''),
                event=row.get('Event', '').strip(),
                status=row.get('Status', '').strip(),
                latitude=self._parse_lat(row.get('Latitude', '0')),
                longitude=self._parse_lon(row.get('Longitude', '0')),
                max_wind_knots=max_wind if max_wind > 0 else None,
                min_pressure_mb=min_pressure if min_pressure > 0 else None,
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NOAA Hurricane Database",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_lat(self, val: str) -> float:
        """Parse latitude with N/S suffix."""
        if not val:
            return 0.0
        val = val.strip()
        direction = 1
        if val.endswith('S'):
            direction = -1
            val = val[:-1]
        elif val.endswith('N'):
            val = val[:-1]
        try:
            return float(val) * direction
        except:
            return 0.0
    
    def _parse_lon(self, val: str) -> float:
        """Parse longitude with E/W suffix."""
        if not val:
            return 0.0
        val = val.strip()
        direction = 1
        if val.endswith('W'):
            direction = -1
            val = val[:-1]
        elif val.endswith('E'):
            val = val[:-1]
        try:
            return float(val) * direction
        except:
            return 0.0
    
    def get_storm_analysis(self, measurements: List[HurricaneMeasurement]) -> Dict:
        """Analyze storm statistics."""
        storms = {}
        
        for m in measurements:
            if m.storm_id not in storms:
                storms[m.storm_id] = {
                    "name": m.name,
                    "points": 0,
                    "max_wind": 0,
                    "min_pressure": 9999,
                    "status": m.status,
                }
            storms[m.storm_id]["points"] += 1
            if m.max_wind_knots and m.max_wind_knots > storms[m.storm_id]["max_wind"]:
                storms[m.storm_id]["max_wind"] = m.max_wind_knots
            if m.min_pressure_mb and m.min_pressure_mb < storms[m.storm_id]["min_pressure"]:
                storms[m.storm_id]["min_pressure"] = m.min_pressure_mb
        
        status_counts = {}
        for m in measurements:
            status_counts[m.status] = status_counts.get(m.status, 0) + 1
        
        max_wind_storm = max(storms.items(), key=lambda x: x[1]["max_wind"])
        min_pressure_storm = min(storms.items(), key=lambda x: x[1]["min_pressure"] if x[1]["min_pressure"] < 9999 else 9999)
        
        return {
            "total_storms": len(storms),
            "status_counts": status_counts,
            "strongest_storm": max_wind_storm[0],
            "strongest_wind": max_wind_storm[1]["max_wind"],
            "lowest_pressure_storm": min_pressure_storm[0],
            "lowest_pressure": min_pressure_storm[1]["min_pressure"],
        }
    
    def get_seasonal_analysis(self, measurements: List[HurricaneMeasurement]) -> Dict:
        """Analyze seasonal patterns."""
        monthly = {}
        
        for m in measurements:
            if len(m.date) >= 6:
                month = int(m.date[4:6])
                if month not in monthly:
                    monthly[month] = {"count": 0, "max_winds": []}
                monthly[month]["count"] += 1
                if m.max_wind_knots:
                    monthly[month]["max_winds"].append(m.max_wind_knots)
        
        peak_month = max(monthly.items(), key=lambda x: x[1]["count"])
        
        return {
            "peak_month": peak_month[0],
            "peak_count": peak_month[1]["count"],
            "monthly_counts": {m: v["count"] for m, v in monthly.items()},
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "storm_id": m.storm_id,
                    "name": m.name,
                    "date": m.date,
                    "status": m.status,
                    "max_wind_knots": m.max_wind_knots,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"hurricane_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[HurricaneMeasurement]) -> Dict:
        """Get summary for console display."""
        years = set(m.date[:4] for m in measurements if len(m.date) >= 4)
        return {
            "total_records": len(measurements),
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
            "unique_storms": len(set(m.storm_id for m in measurements)),
        }
    
    def get_climate_trends(self, measurements: List[HurricaneMeasurement]) -> Dict:
        """Get climate trends for console display."""
        analysis = self.get_storm_analysis(measurements)
        seasonal = self.get_seasonal_analysis(measurements)
        
        return {
            "total_storms": analysis.get('total_storms', 0),
            "strongest_wind_kt": analysis.get('strongest_wind', 0),
            "lowest_pressure_mb": analysis.get('lowest_pressure', 0) if analysis.get('lowest_pressure', 0) < 9999 else 0,
            "peak_month": seasonal.get('peak_month', 0),
        }


def initialize_hurricane_satellite(satellite_id: str = "SENTRY-07") -> HurricaneAcquisitor:
    """Initialize hurricane acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "hurricanes", "atlantic.csv")
    
    if os.path.exists(data_path):
        return HurricaneAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Hurricane data not found at {data_path}")
        return HurricaneAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_hurricane_satellite()
    
    print("=== SENTRY-07 Hurricane/Typhoon Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=500)
    print(f"\nAcquired: {len(measurements)}")
    
    analysis = acquisitor.get_storm_analysis(measurements)
    print(f"\nStorm Analysis:")
    print(f"  Total Storms: {analysis.get('total_storms', 0)}")
    print(f"  Strongest Wind: {analysis.get('strongest_wind', 0)} kt")
    print(f"  Lowest Pressure: {analysis.get('lowest_pressure', 0)} mb")