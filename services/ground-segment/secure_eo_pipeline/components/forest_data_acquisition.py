"""
Satellite Data Acquisition System - Forest Health Module
Simulates satellite data collection from forest health measurements.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class ForestMeasurement:
    """Forest health measurement data."""
    plot_id: int
    latitude: float
    longitude: float
    dbh: float  # cm
    tree_height: float  # m
    crown_width_ns: float
    crown_width_ew: float
    slope: float  # degrees
    elevation: float  # m
    temperature: float  # °C
    humidity: float  # %
    soil_tn: float  # g/kg
    soil_tp: float  # g/kg
    soil_ap: float  # g/kg
    soil_an: float  # g/kg
    menhinick_index: float
    gleason_index: float
    disturbance_level: int
    fire_risk_index: float
    health_status: str
    satellite_id: str = "SENTRY-02"


class ForestDataAcquisitor:
    """
    Satellite data acquisition system for forest health.
    Simulates SENTRY-02 collecting forest ecosystem data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-02", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[ForestMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self.stats = {
            "total_records": len(self.raw_data),
            "healthy_count": 0,
            "unhealthy_count": 0,
            "avg_dbh": 0,
            "avg_height": 0,
            "avg_fire_risk": 0,
            "diversity_index_avg": 0,
        }
        
        if self.raw_data:
            self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load forest data from CSV."""
        data = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def _calculate_stats(self):
        """Calculate dataset statistics."""
        for row in self.raw_data:
            status = row.get('Health_Status', '').strip()
            if 'healthy' in status.lower():
                if 'very' in status.lower():
                    self.stats["very_healthy_count"] = self.stats.get("very_healthy_count", 0) + 1
                else:
                    self.stats["healthy_count"] += 1
            elif 'sub' in status.lower():
                self.stats["sub_healthy_count"] = self.stats.get("sub_healthy_count", 0) + 1
            elif status == 'Unhealthy':
                self.stats["unhealthy_count"] += 1
        
        if self.raw_data:
            self.stats["avg_dbh"] = sum(float(r.get('DBH', 0)) for r in self.raw_data) / len(self.raw_data)
            self.stats["avg_height"] = sum(float(r.get('Tree_Height', 0)) for r in self.raw_data) / len(self.raw_data)
            self.stats["avg_fire_risk"] = sum(float(r.get('Fire_Risk_Index', 0)) for r in self.raw_data) / len(self.raw_data)
            
            menhinick = [float(r.get('Menhinick_Index', 0)) for r in self.raw_data if r.get('Menhinick_Index')]
            if menhinick:
                self.stats["diversity_index_avg"] = sum(menhinick) / len(menhinick)
    
    def acquire_data(self, limit: Optional[int] = None, 
                    health_filter: Optional[str] = None,
                    min_fire_risk: Optional[float] = None,
                    max_fire_risk: Optional[float] = None) -> List[ForestMeasurement]:
        """Acquire forest health measurements."""
        measurements = []
        
        for row in self.raw_data:
            try:
                if health_filter:
                    status = row.get('Health_Status', '').strip()
                    if health_filter.lower() not in status.lower():
                        continue
                
                fire_risk = float(row.get('Fire_Risk_Index', 0))
                if min_fire_risk is not None and fire_risk < min_fire_risk:
                    continue
                if max_fire_risk is not None and fire_risk > max_fire_risk:
                    continue
                
                measurement = ForestMeasurement(
                    plot_id=int(row.get('Plot_ID', 0)),
                    latitude=float(row.get('Latitude', 0)),
                    longitude=float(row.get('Longitude', 0)),
                    dbh=float(row.get('DBH', 0)),
                    tree_height=float(row.get('Tree_Height', 0)),
                    crown_width_ns=float(row.get('Crown_Width_North_South', 0)),
                    crown_width_ew=float(row.get('Crown_Width_East_West', 0)),
                    slope=float(row.get('Slope', 0)),
                    elevation=float(row.get('Elevation', 0)),
                    temperature=0,  # Not in dataset
                    humidity=0,    # Not in dataset
                    soil_tn=float(row.get('Soil_TN', 0)),
                    soil_tp=float(row.get('Soil_TP', 0)),
                    soil_ap=float(row.get('Soil_AP', 0)),
                    soil_an=float(row.get('Soil_AN', 0)),
                    menhinick_index=float(row.get('Menhinick_Index', 0)),
                    gleason_index=float(row.get('Gleason_Index', 0)),
                    disturbance_level=int(float(row.get('Disturbance_Level', 0))),
                    fire_risk_index=fire_risk,
                    health_status=row.get('Health_Status', 'Unknown').strip(),
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
    
    def _record_acquisition(self, measurements: List[ForestMeasurement]):
        """Record acquisition event."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_count": len(measurements),
            "healthy": sum(1 for m in measurements if m.health_status == 'Healthy'),
            "unhealthy": sum(1 for m in measurements if m.health_status == 'Unhealthy'),
        }
        self.acquisition_history.append(record)
    
    def get_regional_analysis(self, measurements: List[ForestMeasurement]) -> Dict:
        """Analyze measurements by region."""
        if not measurements:
            return {}
        
        by_health = {"Healthy": [], "Unhealthy": [], "Sub-Healthy": [], "Very Healthy": []}
        by_disturbance = {}
        
        for m in measurements:
            status = m.health_status
            if status not in by_health:
                by_health[status] = []
            by_health[status].append(m)
            
            d = m.disturbance_level
            if d not in by_disturbance:
                by_disturbance[d] = []
            by_disturbance[d].append(m)
        
        return {
            "total_plots": len(measurements),
            "healthy_plots": len(by_health.get("Healthy", [])) + len(by_health.get("Very Healthy", [])),
            "unhealthy_plots": len(by_health.get("Unhealthy", [])),
            "sub_healthy_plots": len(by_health.get("Sub-Healthy", [])),
            "very_healthy_plots": len(by_health.get("Very Healthy", [])),
            "health_ratio": len(by_health.get("Healthy", [])) / len(measurements) if measurements else 0,
            "avg_dbh": sum(m.dbh for m in measurements) / len(measurements),
            "avg_height": sum(m.tree_height for m in measurements) / len(measurements),
            "avg_fire_risk": sum(m.fire_risk_index for m in measurements) / len(measurements),
            "avg_diversity": sum(m.menhinick_index for m in measurements) / len(measurements),
            "avg_elevation": sum(m.elevation for m in measurements) / len(measurements),
            "avg_slope": sum(m.slope for m in measurements) / len(measurements),
        }
    
    def get_soil_analysis(self, measurements: List[ForestMeasurement]) -> Dict:
        """Analyze soil conditions."""
        if not measurements:
            return {}
        
        return {
            "avg_soil_tn": sum(m.soil_tn for m in measurements) / len(measurements),
            "avg_soil_tp": sum(m.soil_tp for m in measurements) / len(measurements),
            "avg_soil_ap": sum(m.soil_ap for m in measurements) / len(measurements),
            "avg_soil_an": sum(m.soil_an for m in measurements) / len(measurements),
            "min_tn": min(m.soil_tn for m in measurements),
            "max_tn": max(m.soil_tn for m in measurements),
            "min_tp": min(m.soil_tp for m in measurements),
            "max_tp": max(m.soil_tp for m in measurements),
        }
    
    def export_telemetry(self, output_dir: str) -> str:
        """Export telemetry data."""
        os.makedirs(output_dir, exist_ok=True)
        
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "dataset_stats": self.stats,
            "recent_acquisitions": self.acquisition_history[-10:],
        }
        
        filepath = os.path.join(output_dir, f"forest_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(filepath, 'w') as f:
            json.dump(telemetry, f, indent=2)
        
        return filepath
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            "satellite_id": self.satellite_id,
            "status": "ACTIVE" if self.current_measurements else "IDLE",
            "records_loaded": self.stats["total_records"],
            "in_memory": len(self.current_measurements),
        }


def initialize_forest_satellite(satellite_id: str = "SENTRY-02") -> ForestDataAcquisitor:
    """Initialize forest data acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "forest_health", "forest_health_data.csv")
    
    if os.path.exists(data_path):
        return ForestDataAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Forest data not found at {data_path}")
        return ForestDataAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_forest_satellite()
    
    print("=== SENTRY-02 Forest Health Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=100)
    print(f"\nAcquired {len(measurements)} measurements")
    
    analysis = acquisitor.get_regional_analysis(measurements)
    print(f"\nRegional Analysis:")
    print(f"  Total plots: {analysis.get('total_plots', 0)}")
    print(f"  Healthy: {analysis.get('healthy_plots', 0)}")
    print(f"  Unhealthy: {analysis.get('unhealthy_plots', 0)}")
    print(f"  Avg DBH: {analysis.get('avg_dbh', 0):.2f} cm")
    print(f"  Avg Fire Risk: {analysis.get('avg_fire_risk', 0):.3f}")