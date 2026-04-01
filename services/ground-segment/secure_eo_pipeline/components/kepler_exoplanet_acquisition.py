"""
Satellite Data Acquisition System - Kepler Exoplanet Module
Simulates satellite data collection from Kepler exoplanet search results.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class ExoplanetMeasurement:
    """Kepler exoplanet measurement data."""
    kepoi_name: str
    kepler_name: Optional[str]
    disposition: str
    pdisposition: str
    score: Optional[float]
    period_days: Optional[float]
    time0bk: Optional[float]
    impact: Optional[float]
    duration_hours: Optional[float]
    depth_ppm: Optional[float]
    radius_earth: Optional[float]
    temp_k: Optional[float]
    insol_earth: Optional[float]
    snr: Optional[float]
    star_temp_k: Optional[float]
    star_logg: Optional[float]
    star_radius_sol: Optional[float]
    ra_deg: Optional[float]
    dec_deg: Optional[float]
    kepmag: Optional[float]
    satellite_id: str = "SENTRY-08"


class KeplerExoplanetAcquisitor:
    """
    Satellite data acquisition system for Kepler exoplanets.
    Simulates SENTRY-08 collecting Kepler exoplanet search results.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-08", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[ExoplanetMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load exoplanet data from CSV."""
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
        
        dispositions = set()
        confirmed = 0
        candidates = 0
        false_pos = 0
        
        for row in self.raw_data:
            disp = row.get('koi_disposition', '').strip()
            dispositions.add(disp)
            if disp == 'CONFIRMED':
                confirmed += 1
            elif disp == 'CANDIDATE':
                candidates += 1
            elif disp == 'FALSE POSITIVE':
                false_pos += 1
        
        self.stats = {
            "total_records": len(self.raw_data),
            "confirmed": confirmed,
            "candidates": candidates,
            "false_positives": false_pos,
            "dispositions": list(dispositions),
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[ExoplanetMeasurement]:
        """Acquire exoplanet data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = ExoplanetMeasurement(
                kepoi_name=row.get('kepoi_name', '').strip(),
                kepler_name=row.get('kepler_name', '').strip() or None,
                disposition=row.get('koi_disposition', '').strip(),
                pdisposition=row.get('koi_pdisposition', '').strip(),
                score=self._parse_float(row.get('koi_score', '')),
                period_days=self._parse_float(row.get('koi_period', '')),
                time0bk=self._parse_float(row.get('koi_time0bk', '')),
                impact=self._parse_float(row.get('koi_impact', '')),
                duration_hours=self._parse_float(row.get('koi_duration', '')),
                depth_ppm=self._parse_float(row.get('koi_depth', '')),
                radius_earth=self._parse_float(row.get('koi_prad', '')),
                temp_k=self._parse_float(row.get('koi_teq', '')),
                insol_earth=self._parse_float(row.get('koi_insol', '')),
                snr=self._parse_float(row.get('koi_model_snr', '')),
                star_temp_k=self._parse_float(row.get('koi_steff', '')),
                star_logg=self._parse_float(row.get('koi_slogg', '')),
                star_radius_sol=self._parse_float(row.get('koi_srad', '')),
                ra_deg=self._parse_float(row.get('ra', '')),
                dec_deg=self._parse_float(row.get('dec', '')),
                kepmag=self._parse_float(row.get('koi_kepmag', '')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "NASA Kepler Exoplanet Search",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def _parse_float(self, val: str) -> Optional[float]:
        """Parse float safely."""
        if not val or val == '':
            return None
        try:
            return float(val)
        except:
            return None
    
    def get_disposition_analysis(self, measurements: List[ExoplanetMeasurement]) -> Dict:
        """Analyze disposition statistics."""
        disposition_counts = {}
        pdisposition_counts = {}
        score_stats = {"total": 0, "count": 0, "min": 1, "max": 0}
        
        for m in measurements:
            disposition_counts[m.disposition] = disposition_counts.get(m.disposition, 0) + 1
            pdisposition_counts[m.pdisposition] = pdisposition_counts.get(m.pdisposition, 0) + 1
            
            if m.score is not None:
                score_stats["total"] += m.score
                score_stats["count"] += 1
                score_stats["min"] = min(score_stats["min"], m.score)
                score_stats["max"] = max(score_stats["max"], m.score)
        
        avg_score = score_stats["total"] / score_stats["count"] if score_stats["count"] > 0 else 0
        
        return {
            "disposition_counts": disposition_counts,
            "pdisposition_counts": pdisposition_counts,
            "avg_confidence_score": avg_score,
            "confirmed": disposition_counts.get("CONFIRMED", 0),
            "candidates": disposition_counts.get("CANDIDATE", 0),
            "false_positives": disposition_counts.get("FALSE POSITIVE", 0),
        }
    
    def get_orbital_analysis(self, measurements: List[ExoplanetMeasurement]) -> Dict:
        """Analyze orbital characteristics."""
        periods = []
        radii = []
        temps = []
        
        for m in measurements:
            if m.period_days:
                periods.append(m.period_days)
            if m.radius_earth:
                radii.append(m.radius_earth)
            if m.temp_k:
                temps.append(m.temp_k)
        
        return {
            "avg_period_days": sum(periods) / len(periods) if periods else 0,
            "min_period_days": min(periods) if periods else 0,
            "max_period_days": max(periods) if periods else 0,
            "avg_radius_earth": sum(radii) / len(radii) if radii else 0,
            "avg_temp_k": sum(temps) / len(temps) if temps else 0,
        }
    
    def get_star_analysis(self, measurements: List[ExoplanetMeasurement]) -> Dict:
        """Analyze host star characteristics."""
        temps = []
        loggs = []
        radii = []
        
        for m in measurements:
            if m.star_temp_k:
                temps.append(m.star_temp_k)
            if m.star_logg:
                loggs.append(m.star_logg)
            if m.star_radius_sol:
                radii.append(m.star_radius_sol)
        
        return {
            "avg_star_temp_k": sum(temps) / len(temps) if temps else 0,
            "avg_star_logg": sum(loggs) / len(loggs) if loggs else 0,
            "avg_star_radius": sum(radii) / len(radii) if radii else 0,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "kepoi_name": m.kepoi_name,
                    "kepler_name": m.kepler_name,
                    "disposition": m.disposition,
                    "period_days": m.period_days,
                    "radius_earth": m.radius_earth,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"exoplanet_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[ExoplanetMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "unique_planets": len(set(m.kepoi_name for m in measurements)),
            "confirmed": sum(1 for m in measurements if m.disposition == 'CONFIRMED'),
        }
    
    def get_climate_trends(self, measurements: List[ExoplanetMeasurement]) -> Dict:
        """Get climate trends for console display."""
        disp = self.get_disposition_analysis(measurements)
        orbit = self.get_orbital_analysis(measurements)
        star = self.get_star_analysis(measurements)
        
        return {
            "confirmed": disp.get('confirmed', 0),
            "candidates": disp.get('candidates', 0),
            "avg_period_days": orbit.get('avg_period_days', 0),
            "avg_radius_earth": orbit.get('avg_radius_earth', 0),
            "avg_star_temp_k": star.get('avg_star_temp_k', 0),
        }


def initialize_kepler_satellite(satellite_id: str = "SENTRY-08") -> KeplerExoplanetAcquisitor:
    """Initialize Kepler exoplanet acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "kepler", "cumulative.csv")
    
    if os.path.exists(data_path):
        return KeplerExoplanetAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Kepler data not found at {data_path}")
        return KeplerExoplanetAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_kepler_satellite()
    
    print("=== SENTRY-08 Kepler Exoplanet Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=500)
    print(f"\nAcquired: {len(measurements)}")
    
    disp = acquisitor.get_disposition_analysis(measurements)
    print(f"\nDisposition Analysis:")
    print(f"  Confirmed: {disp.get('confirmed', 0)}")
    print(f"  Candidates: {disp.get('candidates', 0)}")
    print(f"  False Positives: {disp.get('false_positives', 0)}")
    
    orbit = acquisitor.get_orbital_analysis(measurements)
    print(f"\nOrbital Analysis:")
    print(f"  Avg Period: {orbit.get('avg_period_days', 0):.2f} days")
    print(f"  Avg Radius: {orbit.get('avg_radius_earth', 0):.2f} Earth")