"""
Satellite Data Acquisition System - Galaxy Dataset Module
Simulates satellite data collection from COMBO-17 galaxy survey data.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class GalaxyMeasurement:
    """Galaxy measurement data."""
    nr: int
    r_mag: float
    r_mag_err: float
    apdrmag: float
    mumax: float
    mcz: float
    mcz_err: float
    mczml: float
    chi2red: float
    bj_mag: float
    vj_mag: float
    redshift: float
    u_mag: float
    b_mag: float
    v_mag: float
    r_mag_abs: float
    satellite_id: str = "SENTRY-13"


class GalaxyAcquisitor:
    """
    Satellite data acquisition system for galaxies.
    Simulates SENTRY-13 collecting COMBO-17 galaxy survey data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-13", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[GalaxyMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load galaxy data from CSV."""
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
        
        redshifts = []
        r_mags = []
        
        for row in self.raw_data:
            try:
                mcz = float(row.get('Mcz', 0))
                if mcz > 0:
                    redshifts.append(mcz)
            except:
                pass
            
            try:
                rmag = float(row.get('Rmag', 0))
                if rmag > 0:
                    r_mags.append(rmag)
            except:
                pass
        
        self.stats = {
            "total_records": len(self.raw_data),
            "avg_redshift": sum(redshifts) / len(redshifts) if redshifts else 0,
            "min_redshift": min(redshifts) if redshifts else 0,
            "max_redshift": max(redshifts) if redshifts else 0,
            "avg_r_mag": sum(r_mags) / len(r_mags) if r_mags else 0,
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[GalaxyMeasurement]:
        """Acquire galaxy data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = GalaxyMeasurement(
                nr=int(row.get('Nr', 0)),
                r_mag=self._parse_float(row.get('Rmag', '0')),
                r_mag_err=self._parse_float(row.get('e.Rmag', '0')),
                apdrmag=self._parse_float(row.get('ApDRmag', '0')),
                mumax=self._parse_float(row.get('mu_max', '0')),
                mcz=self._parse_float(row.get('Mcz', '0')),
                mcz_err=self._parse_float(row.get('e.Mcz', '0')),
                mczml=self._parse_float(row.get('MCzml', '0')),
                chi2red=self._parse_float(row.get('chi2red', '0')),
                bj_mag=self._parse_float(row.get('BjMAG', '0')),
                vj_mag=self._parse_float(row.get('VjMAG', '0')),
                redshift=self._parse_float(row.get('Mcz', '0')),
                u_mag=self._parse_float(row.get('UbMAG', '0')),
                b_mag=self._parse_float(row.get('BbMAG', '0')),
                v_mag=self._parse_float(row.get('VnMAG', '0')),
                r_mag_abs=self._parse_float(row.get('rsMAG', '0')),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "COMBO-17 Galaxy Survey",
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
    
    def get_redshift_analysis(self, measurements: List[GalaxyMeasurement]) -> Dict:
        """Analyze redshift distribution."""
        redshifts = [m.redshift for m in measurements if m.redshift > 0]
        
        if not redshifts:
            return {"error": "No valid redshifts"}
        
        return {
            "avg_redshift": sum(redshifts) / len(redshifts),
            "min_redshift": min(redshifts),
            "max_redshift": max(redshifts),
            "z_count": len(redshifts),
        }
    
    def get_luminosity_analysis(self, measurements: List[GalaxyMeasurement]) -> Dict:
        """Analyze galaxy luminosities."""
        r_mags = [m.r_mag for m in measurements if m.r_mag > 0]
        r_abs = [m.r_mag_abs for m in measurements if m.r_mag_abs > 0]
        
        bright = sum(1 for m in measurements if m.r_mag < 20)
        faint = sum(1 for m in measurements if m.r_mag >= 20)
        
        return {
            "avg_r_mag": sum(r_mags) / len(r_mags) if r_mags else 0,
            "bright_galaxies": bright,
            "faint_galaxies": faint,
            "avg_abs_r": sum(r_abs) / len(r_abs) if r_abs else 0,
        }
    
    def get_morphology_analysis(self, measurements: List[GalaxyMeasurement]) -> Dict:
        """Analyze galaxy sizes/morphology."""
        sizes = [m.apdrmag for m in measurements if m.apdrmag > 0]
        
        point_sources = sum(1 for m in measurements if m.apdrmag <= 0)
        extended = sum(1 for m in measurements if m.apdrmag > 0)
        
        return {
            "avg_size": sum(sizes) / len(sizes) if sizes else 0,
            "point_sources": point_sources,
            "extended_galaxies": extended,
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "nr": m.nr,
                    "r_mag": m.r_mag,
                    "redshift": m.redshift,
                    "apdrmag": m.apdrmag,
                }
                for m in self.current_measurements[:100]
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"galaxy_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[GalaxyMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "unique_galaxies": len(set(m.nr for m in measurements)),
            "avg_r_mag": sum(m.r_mag for m in measurements if m.r_mag > 0) / len(measurements),
        }
    
    def get_climate_trends(self, measurements: List[GalaxyMeasurement]) -> Dict:
        """Get climate trends for console display."""
        z_analysis = self.get_redshift_analysis(measurements)
        lum = self.get_luminosity_analysis(measurements)
        morph = self.get_morphology_analysis(measurements)
        
        return {
            "avg_redshift": z_analysis.get('avg_redshift', 0),
            "max_redshift": z_analysis.get('max_redshift', 0),
            "bright_galaxies": lum.get('bright_galaxies', 0),
            "extended_galaxies": morph.get('extended_galaxies', 0),
        }


def initialize_galaxy_satellite(satellite_id: str = "SENTRY-13") -> GalaxyAcquisitor:
    """Initialize galaxy acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "galaxies", "combo17_galaxies.csv")
    
    if os.path.exists(data_path):
        return GalaxyAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Galaxy data not found at {data_path}")
        return GalaxyAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_galaxy_satellite()
    
    print("=== SENTRY-13 COMBO-17 Galaxy Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=500)
    print(f"\nAcquired: {len(measurements)}")
    
    z_analysis = acquisitor.get_redshift_analysis(measurements)
    print(f"\nRedshift Analysis:")
    print(f"  Avg: {z_analysis.get('avg_redshift', 0):.3f}")
    print(f"  Max: {z_analysis.get('max_redshift', 0):.3f}")
    
    lum = acquisitor.get_luminosity_analysis(measurements)
    print(f"\nLuminosity Analysis:")
    print(f"  Bright: {lum.get('bright_galaxies', 0)}")
    print(f"  Faint: {lum.get('faint_galaxies', 0)}")