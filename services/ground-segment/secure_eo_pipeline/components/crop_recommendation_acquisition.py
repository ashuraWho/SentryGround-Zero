"""
Satellite Data Acquisition System - Crop Recommendation Module
Simulates satellite data collection from crop recommendation dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class CropRecommendationData:
    """Crop recommendation measurement data."""
    nitrogen: float
    phosphorus: float
    potassium: float
    temperature: float
    humidity: float
    ph_value: float
    rainfall: float
    crop: str
    satellite_id: str = "SENTRY-19"


class CropRecommendationAcquisitor:
    """
    Satellite data acquisition system for crop recommendation.
    Simulates SENTRY-19 collecting crop recommendation data based on soil and weather.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-19", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[CropRecommendationData] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load crop recommendation data from CSV."""
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
        
        crops = set()
        n_values = []
        
        for row in self.raw_data:
            crop = row.get('Crop', '').strip()
            if crop:
                crops.add(crop)
            
            try:
                n = float(row.get('Nitrogen', 0))
                if n > 0:
                    n_values.append(n)
            except:
                pass
        
        self.stats = {
            "total_records": len(self.raw_data),
            "unique_crops": len(crops),
            "crop_types": sorted(list(crops)),
            "location": "Agricultural Research Data",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[CropRecommendationData]:
        """Acquire crop recommendation data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = CropRecommendationData(
                nitrogen=self._parse_float(row.get('Nitrogen')),
                phosphorus=self._parse_float(row.get('Phosphorus')),
                potassium=self._parse_float(row.get('Potassium')),
                temperature=self._parse_float(row.get('Temperature')),
                humidity=self._parse_float(row.get('Humidity')),
                ph_value=self._parse_float(row.get('pH_Value')),
                rainfall=self._parse_float(row.get('Rainfall')),
                crop=row.get('Crop', '').strip(),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Crop Recommendation Dataset",
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
    
    def get_crop_analysis(self, measurements: List[CropRecommendationData]) -> Dict:
        """Analyze crop distribution."""
        crop_counts = {}
        for m in measurements:
            if m.crop:
                crop_counts[m.crop] = crop_counts.get(m.crop, 0) + 1
        
        return {
            "crop_distribution": crop_counts,
            "total_crops": len(crop_counts),
        }
    
    def get_soil_analysis(self, measurements: List[CropRecommendationData]) -> Dict:
        """Analyze soil nutrient levels."""
        n_values = [m.nitrogen for m in measurements if m.nitrogen is not None]
        p_values = [m.phosphorus for m in measurements if m.phosphorus is not None]
        k_values = [m.potassium for m in measurements if m.potassium is not None]
        
        return {
            "avg_nitrogen": sum(n_values) / len(n_values) if n_values else 0,
            "avg_phosphorus": sum(p_values) / len(p_values) if p_values else 0,
            "avg_potassium": sum(k_values) / len(k_values) if k_values else 0,
            "min_nitrogen": min(n_values) if n_values else 0,
            "max_nitrogen": max(n_values) if n_values else 0,
        }
    
    def get_weather_analysis(self, measurements: List[CropRecommendationData]) -> Dict:
        """Analyze weather conditions."""
        temps = [m.temperature for m in measurements if m.temperature is not None]
        humidity = [m.humidity for m in measurements if m.humidity is not None]
        rainfall = [m.rainfall for m in measurements if m.rainfall is not None]
        
        return {
            "avg_temperature": sum(temps) / len(temps) if temps else 0,
            "avg_humidity": sum(humidity) / len(humidity) if humidity else 0,
            "avg_rainfall": sum(rainfall) / len(rainfall) if rainfall else 0,
        }
    
    def get_ph_analysis(self, measurements: List[CropRecommendationData]) -> Dict:
        """Analyze pH levels."""
        ph_values = [m.ph_value for m in measurements if m.ph_value is not None]
        
        acidic = sum(1 for p in ph_values if p < 5.5)
        neutral = sum(1 for p in ph_values if 5.5 <= p <= 7.5)
        alkaline = sum(1 for p in ph_values if p > 7.5)
        
        return {
            "avg_ph": sum(ph_values) / len(ph_values) if ph_values else 0,
            "acidic_soil": acidic,
            "neutral_soil": neutral,
            "alkaline_soil": alkaline,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "crop": m.crop,
                    "nitrogen": m.nitrogen,
                    "phosphorus": m.phosphorus,
                    "potassium": m.potassium,
                    "temperature": m.temperature,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"crop_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[CropRecommendationData]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "unique_crops": len(set(m.crop for m in measurements if m.crop)),
            "location": "Agricultural Research Data",
        }
    
    def get_climate_trends(self, measurements: List[CropRecommendationData]) -> Dict:
        """Get climate trends for console display."""
        soil = self.get_soil_analysis(measurements)
        weather = self.get_weather_analysis(measurements)
        
        return {
            "avg_nitrogen": soil.get('avg_nitrogen', 0),
            "avg_phosphorus": soil.get('avg_phosphorus', 0),
            "avg_potassium": soil.get('avg_potassium', 0),
            "avg_temperature": weather.get('avg_temperature', 0),
            "avg_rainfall": weather.get('avg_rainfall', 0),
        }


def initialize_crop_recommendation_satellite(satellite_id: str = "SENTRY-19") -> CropRecommendationAcquisitor:
    """Initialize crop recommendation acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "crop_recommendation", "Crop_Recommendation.csv")
    
    if os.path.exists(data_path):
        return CropRecommendationAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Crop recommendation data not found at {data_path}")
        return CropRecommendationAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_crop_recommendation_satellite()
    
    print("=== SENTRY-19 Crop Recommendation Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=2200)
    print(f"\nAcquired: {len(measurements)}")
    
    crop_analysis = acquisitor.get_crop_analysis(measurements)
    print(f"\nCrop Distribution:")
    for crop, count in crop_analysis.get('crop_distribution', {}).items():
        print(f"  {crop}: {count}")
    
    soil = acquisitor.get_soil_analysis(measurements)
    print(f"\nSoil Analysis:")
    print(f"  Avg Nitrogen: {soil.get('avg_nitrogen', 0):.1f}")
    print(f"  Avg Phosphorus: {soil.get('avg_phosphorus', 0):.1f}")
    print(f"  Avg Potassium: {soil.get('avg_potassium', 0):.1f}")
    
    weather = acquisitor.get_weather_analysis(measurements)
    print(f"\nWeather:")
    print(f"  Avg Temperature: {weather.get('avg_temperature', 0):.1f}°C")
    print(f"  Avg Humidity: {weather.get('avg_humidity', 0):.1f}%")
    print(f"  Avg Rainfall: {weather.get('avg_rainfall', 0):.1f} mm")