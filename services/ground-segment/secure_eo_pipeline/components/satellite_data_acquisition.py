"""
Satellite Data Acquisition System - Sea Ice Extent Module
Simulates satellite data collection from NSIDC sea ice measurements.
"""

import os
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class SeaIceMeasurement:
    """Sea ice extent measurement data."""
    timestamp: datetime
    year: int
    month: int
    day: int
    extent: float  # 10^6 sq km
    missing: float  # 10^6 sq km
    source: str
    hemisphere: str
    quality_flag: str = "NOMINAL"
    satellite_id: str = "SENTRY-01"
    

@dataclass
class DataAcquisitionRecord:
    """Record of data acquisition event."""
    acquisition_id: str
    satellite_id: str
    timestamp: datetime
    data_type: str
    records_count: int
    quality_score: float
    status: str


class SeaIceDataAcquisitor:
    """
    Satellite data acquisition system for sea ice extent.
    Simulates a satellite (SENTRY-01) collecting real sea ice data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-01", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        else:
            self.raw_data = []
        
        self.acquisition_history: List[DataAcquisitionRecord] = []
        self.current_measurements: List[SeaIceMeasurement] = []
        
        self.acquisition_stats = {
            "total_acquisitions": 0,
            "total_records": 0,
            "quality_scores": [],
            "last_acquisition": None,
        }
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load raw sea ice data from CSV file."""
        data = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {}
                for key, value in row.items():
                    cleaned[key.strip()] = value.strip() if value else ''
                data.append(cleaned)
        return data
    
    def acquire_data(self, start_date: Optional[datetime] = None, 
                    end_date: Optional[datetime] = None,
                    hemisphere: Optional[str] = None) -> List[SeaIceMeasurement]:
        """
        Simulate satellite data acquisition for given date range.
        Returns list of measurements.
        """
        if not self.raw_data:
            return []
        
        measurements = []
        
        for row in self.raw_data:
            try:
                year = int(row.get('Year', row.get(' Year', '0')).strip())
                month = int(row.get('Month', row.get(' Month', '0')).strip())
                day = int(row.get('Day', row.get(' Day', '0')).strip())
                timestamp = datetime(year, month, day)
                
                if start_date and timestamp < start_date:
                    continue
                if end_date and timestamp > end_date:
                    continue
                
                hem = row.get('hemisphere', row.get('hemisphere', '')).strip()
                if hemisphere and hem.lower() != hemisphere.lower():
                    continue
                
                extent_str = row.get('Extent', row.get('     Extent', '0')).strip()
                missing_str = row.get('Missing', row.get('    Missing', '0')).strip()
                extent = float(extent_str)
                missing = float(missing_str)
                
                source = row.get('Source Data', row.get(' Source Data', '')).strip()
                
                measurement = SeaIceMeasurement(
                    timestamp=timestamp,
                    year=year,
                    month=month,
                    day=day,
                    extent=extent,
                    missing=missing,
                    source=source,
                    hemisphere=hem,
                    satellite_id=self.satellite_id,
                )
                measurements.append(measurement)
                
            except (ValueError, KeyError) as e:
                continue
        
        self.current_measurements = measurements
        
        record = DataAcquisitionRecord(
            acquisition_id=f"ACQ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(measurements)}",
            satellite_id=self.satellite_id,
            timestamp=datetime.now(),
            data_type="sea_ice_extent",
            records_count=len(measurements),
            quality_score=self._calculate_quality(measurements),
            status="COMPLETED"
        )
        
        self.acquisition_history.append(record)
        self._update_stats(record)
        
        return measurements
    
    def _calculate_quality(self, measurements: List[SeaIceMeasurement]) -> float:
        """Calculate data quality score based on missing values."""
        if not measurements:
            return 0.0
        
        total_missing = sum(m.missing for m in measurements)
        total_extent = sum(m.extent for m in measurements)
        
        if total_extent == 0:
            return 0.5
        
        quality = 1.0 - (total_missing / total_extent)
        return max(0.0, min(1.0, quality))
    
    def _update_stats(self, record: DataAcquisitionRecord):
        """Update acquisition statistics."""
        self.acquisition_stats["total_acquisitions"] += 1
        self.acquisition_stats["total_records"] += record.records_count
        self.acquisition_stats["quality_scores"].append(record.quality_score)
        self.acquisition_stats["last_acquisition"] = record.timestamp
    
    def get_latest(self, days: int = 7, hemisphere: str = "north") -> List[SeaIceMeasurement]:
        """Get latest measurements for given days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.acquire_data(start_date, end_date, hemisphere)
    
    def get_seasonal_average(self, month: int, hemisphere: str = "north") -> float:
        """Calculate average extent for a specific month across all years."""
        measurements = self.acquire_data(hemisphere=hemisphere)
        month_measurements = [m for m in measurements if m.month == month]
        
        if not month_measurements:
            return 0.0
        
        return sum(m.extent for m in month_measurements) / len(month_measurements)
    
    def get_trend(self, years: int = 10, hemisphere: str = "north") -> Dict:
        """Calculate trend in sea ice extent over given years."""
        measurements = self.acquire_data(hemisphere=hemisphere)
        
        if not measurements:
            return {"slope": 0.0, "trend": "unknown"}
        
        current_year = datetime.now().year
        cutoff_year = current_year - years
        
        recent = [m for m in measurements if m.year >= cutoff_year]
        old = [m for m in measurements if m.year < cutoff_year]
        
        if not recent or not old:
            return {"slope": 0.0, "trend": "insufficient_data"}
        
        recent_avg = sum(m.extent for m in recent) / len(recent)
        old_avg = sum(m.extent for m in old) / len(old)
        
        slope = (recent_avg - old_avg) / years
        
        return {
            "slope": slope,
            "recent_avg": recent_avg,
            "historical_avg": old_avg,
            "trend": "decreasing" if slope < -0.1 else "increasing" if slope > 0.1 else "stable"
        }
    
    def export_telemetry(self, output_dir: str) -> str:
        """Export acquisition telemetry as JSON."""
        os.makedirs(output_dir, exist_ok=True)
        
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_acquisitions": self.acquisition_stats["total_acquisitions"],
                "total_records": self.acquisition_stats["total_records"],
                "average_quality": sum(self.acquisition_stats["quality_scores"]) / 
                                 len(self.acquisition_stats["quality_scores"]) 
                                 if self.acquisition_stats["quality_scores"] else 0,
            },
            "last_acquisition": self.acquisition_stats["last_acquisition"].isoformat() 
                               if self.acquisition_stats["last_acquisition"] else None,
            "recent_records": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "extent": m.extent,
                    "hemisphere": m.hemisphere
                }
                for m in self.current_measurements[-10:]
            ]
        }
        
        output_path = os.path.join(output_dir, f"sea_ice_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_path, 'w') as f:
            json.dump(telemetry, f, indent=2)
        
        return output_path
    
    def get_current_status(self) -> Dict:
        """Get current satellite data acquisition status."""
        return {
            "satellite_id": self.satellite_id,
            "status": "ACTIVE" if self.current_measurements else "IDLE",
            "last_data": self.current_measurements[-1].timestamp.isoformat() 
                        if self.current_measurements else None,
            "records_loaded": len(self.raw_data),
            "measurements_in_memory": len(self.current_measurements),
        }


def initialize_satellite(satellite_id: str = "SENTRY-01") -> SeaIceDataAcquisitor:
    """Initialize satellite data acquisition system."""
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                            "data", "sea_ice", "seaice.csv")
    
    if os.path.exists(data_path):
        return SeaIceDataAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Sea ice data not found at {data_path}")
        return SeaIceDataAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_sentinel()
    
    print("=== SENTRY-01 Sea Ice Data Acquisition ===")
    print(f"Status: {acquisitor.get_current_status()}")
    
    measurements = acquisitor.acquire_data(hemisphere="north")
    print(f"\nAcquired {len(measurements)} measurements")
    
    if measurements:
        print(f"Latest: {measurements[-1].extent:.3f} M km²")
    
    trend = acquisitor.get_trend(years=10, hemisphere="north")
    print(f"\n10-year trend: {trend['trend']}")
    print(f"  Slope: {trend['slope']:.4f} M km²/year")
    print(f"  Recent avg: {trend['recent_avg']:.3f} M km²")
    print(f"  Historical avg: {trend['historical_avg']:.3f} M km²")