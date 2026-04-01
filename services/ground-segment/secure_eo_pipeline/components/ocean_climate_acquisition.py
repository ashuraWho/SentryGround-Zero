"""
Satellite Data Acquisition System - Ocean Climate Module
Simulates satellite data collection from ocean climate & marine life dataset.
"""

import os
import csv
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class OceanClimateMeasurement:
    """Ocean climate measurement data."""
    date: datetime
    location: str
    latitude: float
    longitude: float
    sst: float  # °C
    ph_level: float
    bleaching_severity: str
    species_observed: int
    marine_heatwave: bool
    satellite_id: str = "SENTRY-04"


class OceanClimateAcquisitor:
    """
    Satellite data acquisition system for ocean climate.
    Simulates SENTRY-04 collecting marine environment data.
    """
    
    def __init__(self, satellite_id: str = "SENTRY-04", data_path: Optional[str] = None):
        self.satellite_id = satellite_id
        self.data_path = data_path
        self.raw_data: List[Dict] = []
        self.current_measurements: List[OceanClimateMeasurement] = []
        self.acquisition_history: List[Dict] = []
        
        if data_path and os.path.exists(data_path):
            self.raw_data = self._load_raw_data(data_path)
        
        self._calculate_stats()
    
    def _load_raw_data(self, filepath: str) -> List[Dict]:
        """Load ocean data from CSV."""
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
        sst_values = []
        ph_values = []
        heatwave_count = 0
        bleaching = {"None": 0, "Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        
        for row in self.raw_data:
            locations.add(row.get('Location', 'Unknown'))
            try:
                sst = float(row.get('SST (°C)', 0))
                if sst:
                    sst_values.append(sst)
                ph = float(row.get('pH Level', 0))
                if ph:
                    ph_values.append(ph)
                if row.get('Marine Heatwave', '').lower() == 'true':
                    heatwave_count += 1
                b = row.get('Bleaching Severity', 'None')
                if b in bleaching:
                    bleaching[b] += 1
            except (ValueError, KeyError):
                continue
        
        self.stats = {
            "total_records": len(self.raw_data),
            "unique_locations": len(locations),
            "avg_sst": sum(sst_values) / len(sst_values) if sst_values else 0,
            "min_sst": min(sst_values) if sst_values else 0,
            "max_sst": max(sst_values) if sst_values else 0,
            "avg_ph": sum(ph_values) / len(ph_values) if ph_values else 0,
            "heatwave_count": heatwave_count,
            "bleaching_distribution": bleaching,
        }
    
    def acquire_data(self, location: Optional[str] = None,
                    start_year: Optional[int] = None,
                    end_year: Optional[int] = None,
                    heatwave_only: bool = False,
                    limit: Optional[int] = None) -> List[OceanClimateMeasurement]:
        """Acquire ocean climate measurements."""
        measurements = []
        
        for row in self.raw_data:
            try:
                loc = row.get('Location', '').strip()
                
                if location and location.lower() not in loc.lower():
                    continue
                
                date_str = row.get('Date', '').strip()
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    date = datetime.now()
                
                if start_year and date.year < start_year:
                    continue
                if end_year and date.year > end_year:
                    continue
                
                heatwave = row.get('Marine Heatwave', 'False').lower() == 'true'
                if heatwave_only and not heatwave:
                    continue
                
                measurement = OceanClimateMeasurement(
                    date=date,
                    location=loc,
                    latitude=float(row.get('Latitude', 0)),
                    longitude=float(row.get('Longitude', 0)),
                    sst=float(row.get('SST (°C)', 0)),
                    ph_level=float(row.get('pH Level', 0)),
                    bleaching_severity=row.get('Bleaching Severity', 'None').strip(),
                    species_observed=int(row.get('Species Observed', 0)),
                    marine_heatwave=heatwave,
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
    
    def _record_acquisition(self, measurements: List[OceanClimateMeasurement]):
        """Record acquisition event."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "satellite_id": self.satellite_id,
            "records_count": len(measurements),
        }
        self.acquisition_history.append(record)
    
    def get_climate_analysis(self, measurements: List[OceanClimateMeasurement]) -> Dict:
        """Analyze ocean climate trends."""
        if not measurements:
            return {}
        
        sst_by_year = {}
        ph_by_year = {}
        heatwave_years = set()
        
        for m in measurements:
            year = m.date.year
            if year not in sst_by_year:
                sst_by_year[year] = []
                ph_by_year[year] = []
            sst_by_year[year].append(m.sst)
            ph_by_year[year].append(m.ph_level)
            if m.marine_heatwave:
                heatwave_years.add(year)
        
        yearly_sst = {y: sum(vs)/len(vs) for y, vs in sst_by_year.items()}
        yearly_ph = {y: sum(vs)/len(vs) for y, vs in ph_by_year.items()}
        
        years = sorted(yearly_sst.keys())
        if len(years) >= 2:
            first_half = years[:len(years)//2]
            second_half = years[len(years)//2:]
            
            sst_change = yearly_sst[second_half[-1]] - yearly_sst[first_half[0]]
            ph_change = yearly_ph[second_half[-1]] - yearly_ph[first_half[0]]
        else:
            sst_change = 0
            ph_change = 0
        
        return {
            "avg_sst": sum(m.sst for m in measurements) / len(measurements),
            "avg_ph": sum(m.ph_level for m in measurements) / len(measurements),
            "sst_trend": "warming" if sst_change > 0.5 else "cooling" if sst_change < -0.5 else "stable",
            "sst_change": sst_change,
            "ph_trend": "acidification" if ph_change < -0.05 else "stable",
            "ph_change": ph_change,
            "heatwave_events": len(heatwave_years),
            "yearly_sst": yearly_sst,
            "yearly_ph": yearly_ph,
        }
    
    def get_bleaching_analysis(self, measurements: List[OceanClimateMeasurement]) -> Dict:
        """Analyze coral bleaching patterns."""
        if not measurements:
            return {}
        
        by_severity = {"None": 0, "Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        for m in measurements:
            if m.bleaching_severity in by_severity:
                by_severity[m.bleaching_severity] += 1
        
        total = len(measurements)
        affected = total - by_severity["None"]
        
        return {
            "total_observations": total,
            "bleaching_events": affected,
            "bleaching_percentage": (affected / total * 100) if total > 0 else 0,
            "by_severity": by_severity,
            "critical_events": by_severity.get("Critical", 0),
            "high_events": by_severity.get("High", 0),
        }
    
    def get_location_analysis(self, measurements: List[OceanClimateMeasurement]) -> Dict:
        """Analyze by location."""
        if not measurements:
            return {}
        
        by_location = {}
        for m in measurements:
            if m.location not in by_location:
                by_location[m.location] = {
                    "count": 0,
                    "avg_sst": [],
                    "avg_ph": [],
                    "species": [],
                    "heatwaves": 0,
                }
            by_location[m.location]["count"] += 1
            by_location[m.location]["avg_sst"].append(m.sst)
            by_location[m.location]["avg_ph"].append(m.ph_level)
            by_location[m.location]["species"].append(m.species_observed)
            if m.marine_heatwave:
                by_location[m.location]["heatwaves"] += 1
        
        location_stats = {}
        for loc, data in by_location.items():
            location_stats[loc] = {
                "count": data["count"],
                "avg_sst": sum(data["avg_sst"]) / len(data["avg_sst"]),
                "avg_ph": sum(data["avg_ph"]) / len(data["avg_ph"]),
                "avg_species": sum(data["species"]) / len(data["species"]),
                "heatwave_days": data["heatwaves"],
            }
        
        return location_stats
    
    def export_telemetry(self, output_dir: str) -> str:
        """Export telemetry data."""
        os.makedirs(output_dir, exist_ok=True)
        
        telemetry = {
            "satellite_id": self.satellite_id,
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "recent_acquisitions": self.acquisition_history[-5:],
        }
        
        filepath = os.path.join(output_dir, f"ocean_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
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
    
    def get_ocean_summary(self, measurements: List[OceanClimateMeasurement]) -> Dict:
        """Get summary of ocean data."""
        years = sorted(set(m.date.year for m in measurements))
        return {
            "total_records": len(measurements),
            "year_range": f"{min(years)}-{max(years)}" if years else "N/A",
            "unique_locations": len(set(m.location for m in measurements)),
        }
    
    def get_climate_trends(self, measurements: List[OceanClimateMeasurement]) -> Dict:
        """Get climate trends summary."""
        analysis = self.get_climate_analysis(measurements)
        bleaching = self.get_bleaching_analysis(measurements)
        
        total = bleaching.get('total_affected', 0) + bleaching.get('by_severity', {}).get('None', 0)
        risk = (bleaching.get('by_severity', {}).get('High', 0) + bleaching.get('by_severity', {}).get('Critical', 0)) / max(total, 1) * 100
        
        return {
            "avg_sst_change": analysis.get('sst_change', 0),
            "avg_ph_change": analysis.get('ph_change', 0),
            "coral_bleaching_risk": risk,
        }


def initialize_ocean_satellite(satellite_id: str = "SENTRY-04") -> OceanClimateAcquisitor:
    """Initialize ocean climate acquisitor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_path = os.path.join(base_dir, "data", "ocean_climate", "realistic_ocean_climate_dataset.csv")
    
    if os.path.exists(data_path):
        return OceanClimateAcquisitor(satellite_id=satellite_id, data_path=data_path)
    else:
        print(f"Warning: Ocean data not found at {data_path}")
        return OceanClimateAcquisitor(satellite_id=satellite_id)


if __name__ == "__main__":
    acquisitor = initialize_ocean_satellite()
    
    print("=== SENTRY-04 Ocean Climate Data Acquisition ===")
    print(f"Status: {acquisitor.get_status()}")
    
    measurements = acquisitor.acquire_data(limit=200)
    print(f"\nAcquired: {len(measurements)}")
    
    climate = acquisitor.get_climate_analysis(measurements)
    print(f"\nClimate Analysis:")
    print(f"  Avg SST: {climate.get('avg_sst', 0):.2f}°C")
    print(f"  Avg pH: {climate.get('avg_ph', 0):.3f}")
    print(f"  SST Trend: {climate.get('sst_trend', 'N/A')}")
    print(f"  pH Trend: {climate.get('ph_trend', 'N/A')}")
    print(f"  Heatwave events: {climate.get('heatwave_events', 0)}")
    
    bleaching = acquisitor.get_bleaching_analysis(measurements)
    print(f"\nBleaching Analysis:")
    print(f"  Total observations: {bleaching.get('total_observations', 0)}")
    print(f"  Bleaching events: {bleaching.get('bleaching_events', 0)}")
    print(f"  Bleaching %: {bleaching.get('bleaching_percentage', 0):.1f}%")