"""
Satellite Data Acquisition System - Gravitational Waves Module
Simulates satellite data collection from LIGO gravitational waves detection data.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class GravitationalWaveMeasurement:
    """Gravitational wave measurement data."""
    detector: str
    chunk_index: int
    gps_time: int
    mean: float
    std: float
    min_val: float
    max_val: float
    peak_to_peak: float
    rms: float
    satellite_id: str = "SENTRY-12"


class GravitationalWaveAcquisitor:
    """
    Satellite data acquisition system for gravitational waves.
    Simulates SENTRY-12 collecting LIGO GW detection data (GW150914).
    """
    
    def __init__(self, satellite_id: str = "SENTRY-12", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[GravitationalWaveMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load GW data from CSV."""
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
        
        detectors = set()
        h1_count = 0
        l1_count = 0
        
        for row in self.raw_data:
            det = row.get('detector', '').strip()
            detectors.add(det)
            if det == 'H1':
                h1_count += 1
            elif det == 'L1':
                l1_count += 1
        
        self.stats = {
            "total_records": len(self.raw_data),
            "detectors": list(detectors),
            "h1_seconds": h1_count,
            "l1_seconds": l1_count,
            "event": "GW150914",
            "detection_date": "2015-09-14",
        }
    
    def acquire_data(self, limit: int = 500, offset: int = 0) -> List[GravitationalWaveMeasurement]:
        """Acquire GW data."""
        measurements = []
        
        total_needed = offset + limit
        if total_needed > len(self.raw_data):
            limit = len(self.raw_data) - offset
        
        data_slice = self.raw_data[offset:offset + limit]
        
        for row in data_slice:
            measurement = GravitationalWaveMeasurement(
                detector=row.get('detector', '').strip(),
                chunk_index=int(row.get('chunk_index', 0)),
                gps_time=int(row.get('gps_time', 0)),
                mean=float(row.get('mean', 0)),
                std=float(row.get('std', 0)),
                min_val=float(row.get('min', 0)),
                max_val=float(row.get('max', 0)),
                peak_to_peak=float(row.get('peak_to_peak', 0)),
                rms=float(row.get('rms', 0)),
                satellite_id=self.satellite_id,
            )
            measurements.append(measurement)
        
        self.current_measurements = measurements
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_acquired": len(measurements),
            "data_source": "LIGO Gravitational Waves (GW150914)",
        }
        self.acquisition_history.append(record)
        
        return measurements
    
    def get_detector_analysis(self, measurements: List[GravitationalWaveMeasurement]) -> Dict:
        """Analyze detector statistics."""
        h1_data = [m for m in measurements if m.detector == 'H1']
        l1_data = [m for m in measurements if m.detector == 'L1']
        
        def avg_rms(data):
            return sum(m.rms for m in data) / len(data) if data else 0
        
        def max_peak(data):
            return max(m.peak_to_peak for m in data) if data else 0
        
        return {
            "h1_records": len(h1_data),
            "l1_records": len(l1_data),
            "h1_avg_rms": avg_rms(h1_data),
            "l1_avg_rms": avg_rms(l1_data),
            "h1_max_peak": max_peak(h1_data),
            "l1_max_peak": max_peak(l1_data),
        }
    
    def get_signal_analysis(self, measurements: List[GravitationalWaveMeasurement]) -> Dict:
        """Analyze signal characteristics."""
        rms_values = [m.rms for m in measurements]
        peak_values = [m.peak_to_peak for m in measurements]
        std_values = [m.std for m in measurements]
        
        return {
            "avg_rms": sum(rms_values) / len(rms_values) if rms_values else 0,
            "max_rms": max(rms_values) if rms_values else 0,
            "avg_peak": sum(peak_values) / len(peak_values) if peak_values else 0,
            "max_peak": max(peak_values) if peak_values else 0,
            "avg_std": sum(std_values) / len(std_values) if std_values else 0,
        }
    
    def find_gw_event(self, measurements: List[GravitationalWaveMeasurement]) -> Dict:
        """Try to identify the GW event in the data."""
        sorted_by_rms = sorted(measurements, key=lambda m: m.rms, reverse=True)
        
        top_events = []
        for m in sorted_by_rms[:5]:
            top_events.append({
                "gps_time": m.gps_time,
                "detector": m.detector,
                "rms": m.rms,
                "peak_to_peak": m.peak_to_peak,
            })
        
        return {
            "top_candidates": top_events,
            "gps_event_start": 1126259446,
            "event": "GW150914",
        }
    
    def export_telemetry(self, output_dir: str = ".") -> str:
        """Export telemetry data."""
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "measurements": [
                {
                    "detector": m.detector,
                    "gps_time": m.gps_time,
                    "rms": m.rms,
                    "peak_to_peak": m.peak_to_peak,
                }
                for m in self.current_measurements
            ],
            "stats": self.stats,
        }
        
        filepath = os.path.join(output_dir, f"gw_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[GravitationalWaveMeasurement]) -> Dict:
        """Get summary for console display."""
        return {
            "total_records": len(measurements),
            "h1_records": sum(1 for m in measurements if m.detector == 'H1'),
            "l1_records": sum(1 for m in measurements if m.detector == 'L1'),
            "event": "GW150914",
        }
    
    def get_climate_trends(self, measurements: List[GravitationalWaveMeasurement]) -> Dict:
        """Get climate trends for console display."""
        detector = self.get_detector_analysis(measurements)
        signal = self.get_signal_analysis(measurements)
        
        return {
            "h1_max_peak": detector.get('h1_max_peak', 0),
            "l1_max_peak": detector.get('l1_max_peak', 0),
            "avg_rms": signal.get('avg_rms', 0),
            "max_rms": signal.get('max_rms', 0),
            "max_peak": signal.get('max_peak', 0),
        }


def initialize_gravitational_wave_satellite(satellite_id: str = "SENTRY-12") -> GravitationalWaveAcquisitor:
    """Initialize gravitational wave acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "gravitational_waves", "gw_data.csv")
    
    if os.path.exists(data_path):
        return GravitationalWaveAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: GW data not found at {data_path}")
        return GravitationalWaveAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_gravitational_wave_satellite()
    
    print("=== SENTRY-12 Gravitational Waves Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=64)
    print(f"\nAcquired: {len(measurements)}")
    
    detector = acquisitor.get_detector_analysis(measurements)
    print(f"\nDetector Analysis:")
    print(f"  H1 records: {detector.get('h1_records', 0)}")
    print(f"  L1 records: {detector.get('l1_records', 0)}")
    
    signal = acquisitor.get_signal_analysis(measurements)
    print(f"\nSignal Analysis:")
    print(f"  Max RMS: {signal.get('max_rms', 0):.2e}")
    print(f"  Max Peak: {signal.get('max_peak', 0):.2e}")