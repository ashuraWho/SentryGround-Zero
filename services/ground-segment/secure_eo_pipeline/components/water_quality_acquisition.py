"""
Satellite Data Acquisition System - Water Quality Module
Simulates satellite data collection from Telangana groundwater quality data (2018-2020).
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class WaterQualityMeasurement:
    """Water quality measurement data."""
    sno: int
    district: str
    mandal: str
    village: str
    latitude: float
    longitude: float
    ph: float
    ec: float
    tds: float
    total_hardness: float
    sar: float
    classification: str
    rsc: float
    year: str
    satellite_id: str = "SENTRY-17"


class WaterQualityAcquisitor:
    """
    Satellite data acquisition system for water quality.
    Simulates SENTRY-17 collecting Telangana groundwater quality data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-17", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[WaterQualityMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load water quality data from CSV."""
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
        
        districts = set()
        classifications = set()
        
        for row in self.raw_data:
            if row.get('district'):
                districts.add(row.get('district').strip())
            if row.get('Classification'):
                classifications.add(row.get('Classification').strip())
        
        self.stats = {
            "total_records": len(self.raw_data),
            "districts": len(districts),
            "classifications": list(classifications),
            "year_range": "2018-2020",
            "location": "Telangana, India",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[WaterQualityMeasurement]:
        """Acquire water quality data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = WaterQualityMeasurement(
                sno=self._parse_int(row.get('sno', 0)),
                district=row.get('district', '').strip(),
                mandal=row.get('mandal', '').strip(),
                village=row.get('village', '').strip(),
                latitude=self._parse_float(row.get('lat_gis', 0)),
                longitude=self._parse_float(row.get('long_gis', 0)),
                ph=self._parse_float(row.get('pH', row.get('ph', 0))),
                ec=self._parse_float(row.get('E.C', row.get('EC', 0))),
                tds=self._parse_float(row.get('TDS', 0)),
                total_hardness=self._parse_float(row.get('T.H', 0)),
                sar=self._parse_float(row.get('SAR', 0)),
                classification=row.get('Classification', '').strip(),
                rsc=self._parse_float(row.get('RSC  meq  / L', row.get('RSC', 0))),
                year=row.get('year', ''),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "Telangana Groundwater Quality (2018-2020)",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val) -> float:
        """Parse float safely."""
        if val is None or val == '' or val == 'nan':
            return 0.0
        try:
            return float(val)
        except:
            return 0.0
    
    def _parse_int(self, val) -> int:
        """Parse int safely."""
        if val is None or val == '':
            return 0
        try:
            return int(float(val))
        except:
            return 0
    
    def get_classification_analysis(self, measurements: List[WaterQualityMeasurement]) -> Dict:
        """Analyze water quality classifications."""
        classes = {}
        for m in measurements:
            if m.classification:
                classes[m.classification] = classes.get(m.classification, 0) + 1
        
        good_quality = sum(v for k, v in classes.items() if k in ['C1S1', 'C2S1'])
        marginal = sum(v for k, v in classes.items() if k in ['C3S1', 'C3S2'])
        poor = sum(v for k, v in classes.items() if k in ['C4S1', 'C4S2', 'C4S3', 'C4S4'])
        
        return {
            "class_distribution": classes,
            "good_quality": good_quality,
            "marginal_quality": marginal,
            "poor_quality": poor,
        }
    
    def get_district_analysis(self, measurements: List[WaterQualityMeasurement]) -> Dict:
        """Analyze water quality by district."""
        district_avg_tds = {}
        
        for m in measurements:
            if m.district:
                if m.district not in district_avg_tds:
                    district_avg_tds[m.district] = []
                if m.tds > 0:
                    district_avg_tds[m.district].append(m.tds)
        
        result = {}
        for d, tds_list in district_avg_tds.items():
            result[d] = sum(tds_list) / len(tds_list) if tds_list else 0
        
        return result
    
    def get_rsc_analysis(self, measurements: List[WaterQualityMeasurement]) -> Dict:
        """Analyze RSC (Residual Sodium Carbonate) levels."""
        safe = sum(1 for m in measurements if m.rsc < 1.25)
        marginal = sum(1 for m in measurements if 1.25 <= m.rsc <= 2.5)
        unsuitable = sum(1 for m in measurements if m.rsc > 2.5)
        
        return {
            "safe_rsc": safe,
            "marginal_rsc": marginal,
            "unsuitable_rsc": unsuitable,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "district": m.district,
                    "village": m.village,
                    "classification": m.classification,
                    "tds": m.tds,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"water_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[WaterQualityMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "districts": len(set(m.district for m in measurements if m.district)),
            "year_range": "2018-2020",
        }
    
    def get_climate_trends(self, measurements: List[WaterQualityMeasurement]) -> Dict:
        """Get climate trends for console display."""
        cls = self.get_classification_analysis(measurements)
        rsc = self.get_rsc_analysis(measurements)
        
        return {
            "good_quality": cls.get('good_quality', 0),
            "marginal_quality": cls.get('marginal_quality', 0),
            "poor_quality": cls.get('poor_quality', 0),
            "safe_rsc": rsc.get('safe_rsc', 0),
            "unsuitable_rsc": rsc.get('unsuitable_rsc', 0),
        }


def initialize_water_quality_satellite(satellite_id: str = "SENTRY-17") -> WaterQualityAcquisitor:
    """Initialize water quality acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "water_quality", "telangana_water.csv")
    
    if os.path.exists(data_path):
        return WaterQualityAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Water quality data not found at {data_path}")
        return WaterQualityAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_water_quality_satellite()
    
    print("=== SENTRY-17 Water Quality Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=1106)
    print(f"\nAcquired: {len(measurements)}")
    
    cls = acquisitor.get_classification_analysis(measurements)
    print(f"\nClassification Analysis:")
    print(f"  Good (C1S1/C2S1): {cls.get('good_quality', 0)}")
    print(f"  Marginal (C3S1/C3S2): {cls.get('marginal_quality', 0)}")
    print(f"  Poor (C4S*): {cls.get('poor_quality', 0)}")
    
    rsc = acquisitor.get_rsc_analysis(measurements)
    print(f"\nRSC Analysis:")
    print(f"  Safe: {rsc.get('safe_rsc', 0)}")
    print(f"  Marginal: {rsc.get('marginal_rsc', 0)}")
    print(f"  Unsuitable: {rsc.get('unsuitable_rsc', 0)}")