"""
Constellation layout: Docker hostname -> MISSION_PROFILE + human labels + observation / instrument modes.

Modes are passed to the space API as ?mode=... and become OBSERVATION_MODE in the OBC binary
(see core_engine/src/sensor_observation.hpp).

ORBITAL PHYSICS REFERENCES:
- Kepler's 3rd Law: T² = (4π²/GM) * a³  =>  a = (GM*T²/4π²)^(1/3)
- Standard gravitational parameter: GM_earth = 3.986004418e14 m³/s²
- Earth equatorial radius: R_e = 6,378,137 m
- Standard geostationary orbit: a = 42,164 km, h = 35,786 km, T = 1436.07 min (sidereal day)
- GPS orbit: a = 26,559.7 km, h = 20,180 km, T = 717.9 min (half sidereal day)
- ISS orbit: a = 6,771 km, h = 415 km, T = 92.9 min
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


GM_EARTH = 3.986004418e14
R_EARTH = 6_378_137.0


@dataclass(frozen=True)
class OrbitalElements:
    """Keplerian orbital elements with physics-accurate values."""
    semimajor_axis_km: float
    eccentricity: float
    inclination_deg: float
    raan_deg: float = 0.0
    arg_perigee_deg: float = 0.0
    mean_anomaly_deg: float = 0.0

    @property
    def perigee_km(self) -> float:
        return self.semimajor_axis_km * (1 - self.eccentricity) - R_EARTH / 1000

    @property
    def apogee_km(self) -> float:
        return self.semimajor_axis_km * (1 + self.eccentricity) - R_EARTH / 1000

    @property
    def period_min(self) -> float:
        a_m = self.semimajor_axis_km * 1000
        T_s = 2 * 3.14159265359 * (a_m ** 3 / GM_EARTH) ** 0.5
        return T_s / 60

    @property
    def altitude_km(self) -> float:
        return self.semimajor_axis_km - R_EARTH / 1000


@dataclass(frozen=True)
class ObservationMode:
    code: str
    title: str
    hint: str = ""


@dataclass(frozen=True)
class SatelliteSpec:
    hostname: str
    mission_profile: str
    title: str
    science_focus: str
    modes: Tuple[ObservationMode, ...]
    orbital_elements: Optional[OrbitalElements] = None


# Default full constellation (matches docker-compose service names).
_DEFAULT_CONSTELLATION: Tuple[SatelliteSpec, ...] = (
    SatelliteSpec(
        "sentry-deep-space",
        "deep_space",
        "Deep-space imager",
        "Cosmology & extragalactic background",
        (
            ObservationMode("default", "Balanced / auto", "General deep field"),
            ObservationMode("deep_field", "Deep field integration", "Faint unresolved sources"),
            ObservationMode("galaxy_cluster", "Cluster / large-scale structure", "Overdensity proxy"),
            ObservationMode("cmb_proxy", "CMB anisotropy style", "Ripple-like correlated signal"),
        ),
    ),
    SatelliteSpec(
        "sentry-dark-matter",
        "dark_matter",
        "Dark-matter mapper",
        "Galactic halo & substructure (toy NFW)",
        (
            ObservationMode("default", "Standard halo", "Smooth NFW-like projection"),
            ObservationMode("subhalo", "Subhalo / substructure bump", "Secondary overdensity"),
            ObservationMode("merger_stream", "Tidal stream proxy", "Diagonal coherent feature"),
            ObservationMode("nfw_core", "Cusp / inner halo", "Brightened core"),
        ),
    ),
    SatelliteSpec(
        "sentry-earth-obs",
        "earth_observation",
        "Earth observation (EO)",
        "Land, ocean, biosphere, cities",
        (
            ObservationMode("default", "RGB / general EO", "Terrain + sparse clouds"),
            ObservationMode("climate", "Climate bands / fronts", "Large-scale structure"),
            ObservationMode("vegetation", "Vegetation / chlorophyll proxy", "Patchy biosphere signal"),
            ObservationMode("desert", "Arid regions / dunes", "High albedo stripes"),
            ObservationMode("ocean", "Open ocean", "Low-frequency swell-like pattern"),
            ObservationMode("urban", "Urban / built environment", "Grid-like modulation"),
        ),
    ),
    SatelliteSpec(
        "sentry-exoplanet",
        "exoplanet",
        "Exoplanet photometry",
        "Transits, phases, eclipses",
        (
            ObservationMode("default", "Standard transit shape", "U-shaped dip along time axis"),
            ObservationMode("transit", "Deep transit", "Stronger occultation"),
            ObservationMode("phase_curve", "Phase curve", "Asymmetric illumination"),
            ObservationMode("secondary_eclipse", "Secondary eclipse", "Two-box dip pattern"),
            ObservationMode("reflection", "Glint / reflection", "High-frequency glints"),
        ),
    ),
    SatelliteSpec(
        "sentry-stellar",
        "stellar",
        "Stellar astrophysics",
        "Photosphere, activity, luminosity",
        (
            ObservationMode("default", "Resolved disk", "Core + weak ring"),
            ObservationMode("photosphere", "Photosphere / limb darkening", "Smooth thermal disk"),
            ObservationMode("sunspots", "Starspots / cool regions", "Dark umbrae patches"),
            ObservationMode("luminosity", "Bolometric proxy", "Global brightening"),
            ObservationMode("temperature", "Temperature map proxy", "Center-to-limb trend"),
        ),
    ),
    SatelliteSpec(
        "sentry-black-hole",
        "black_hole",
        "High-energy compact object",
        "Shadow, disk, jet (toy)",
        (
            ObservationMode("default", "Ring + faint shadow", "Educational EHT-style patch"),
            ObservationMode("shadow", "Deep shadow emphasis", "Larger dark interior"),
            ObservationMode("accretion_disk", "Accretion disk", "Bright annulus"),
            ObservationMode("jet_proxy", "Relativistic jet proxy", "Narrow vertical plume"),
            ObservationMode("ring_only", "Photon ring focus", "Suppressed interior"),
        ),
    ),
    SatelliteSpec(
        "sentry-gravitational-wave",
        "gravitational_wave",
        "Gravitational-wave science",
        "Chirp, ringdown, stochastic",
        (
            ObservationMode("default", "Inspiral chirp proxy", "Frequency sweeps along X"),
            ObservationMode("chirp", "Strong chirp", "Same class, explicit label"),
            ObservationMode("ringdown", "Merger ringdown", "Damped oscillation"),
            ObservationMode("stochastic_bg", "Stochastic background", "Extra incoherent noise"),
        ),
    ),
    SatelliteSpec(
        "sentry-asteroid",
        "asteroid",
        "Small bodies",
        "Regolith, shape, binaries",
        (
            ObservationMode("default", "Single body", "Rugged terminator"),
            ObservationMode("regolith", "Regolith texture", "Micro-roughness noise"),
            ObservationMode("craters", "Cratered surface", "Circular depressions"),
            ObservationMode("rotation", "Rotation / lightcurve", "Brightness gradient"),
            ObservationMode("binary_proxy", "Binary companion", "Two lobes"),
        ),
    ),
    SatelliteSpec(
        "sentry-earth-climate",
        "earth_climate",
        "Earth climate system",
        "Jet stream, cells, storms, cryosphere",
        (
            ObservationMode("default", "General climate patch", "Bands + clouds"),
            ObservationMode("jet_stream", "Jet stream", "Baroclinic waves"),
            ObservationMode("hadley_cell", "Hadley cell proxy", "Meridional structure"),
            ObservationMode("storm_system", "Cyclone / storm", "Localized vortex"),
            ObservationMode("sea_ice", "Sea ice / polar cap", "High-latitude brightening"),
            ObservationMode("vegetation", "Surface biosphere (with climate context)", "Same as EO vegetation mod"),
            ObservationMode("ocean", "Marine surface", "Open water modulation"),
        ),
    ),
    SatelliteSpec(
        "sentry-survey",
        "survey",
        "Multi-mission survey",
        "All-in-one composite",
        (
            ObservationMode("default", "Four-way blend", "Halo + transit + EO + star"),
            ObservationMode("mosaic", "Mosaic gains", "Quadrant weighting"),
            ObservationMode("strip_map", "Along-track strips", "Striped modulation"),
            ObservationMode("multi_band", "Multi-band interference", "Spectral ripples"),
        ),
    ),
)

_PROFILE_BY_HOST: Dict[str, str] = {s.hostname: s.mission_profile for s in _DEFAULT_CONSTELLATION}


GNSS_CONSTELLATION: Tuple[SatelliteSpec, ...] = (
    SatelliteSpec(
        "gps-block-iia",
        "gnss",
        "GPS Block IIA",
        "Navstar GPS - positioning, velocity, timing",
        (
            ObservationMode("l1_ca", "C/A-code L1 (1575.42 MHz)", "Civilian ranging code"),
            ObservationMode("l1_p", "P-code L1 encrypted", "Precision code"),
            ObservationMode("l2_p", "P-code L2 (1227.60 MHz)", "Dual-frequency iono correction"),
            ObservationMode("l2c", "L2C civilian signal", "Modernized civil signal"),
        ),
        OrbitalElements(
            semimajor_axis_km=26_559.7,
            eccentricity=0.001,
            inclination_deg=55.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "gps-block-iir",
        "gnss",
        "GPS Block IIR",
        "Navstar GPS - replenishment satellites",
        (
            ObservationMode("l1_ca", "C/A-code L1", "Standard positioning"),
            ObservationMode("l1_p", "P-code L1", "Encrypted precision"),
            ObservationMode("l2_p", "P-code L2", "Dual-frequency"),
            ObservationMode("l2c", "L2C", "Modernized civilian"),
            ObservationMode("l5", "L5 (1176.45 MHz)", "Safety-of-life signal"),
        ),
        OrbitalElements(
            semimajor_axis_km=26_559.7,
            eccentricity=0.0002,
            inclination_deg=55.0,
            raan_deg=30.0,
        ),
    ),
    SatelliteSpec(
        "gps-block-iif",
        "gnss",
        "GPS Block IIF",
        "Navstar GPS - extended operations",
        (
            ObservationMode("l1_ca", "C/A L1", "Civilian"),
            ObservationMode("l1_p", "P-code L1", "Military"),
            ObservationMode("l2_p", "P-code L2", "Dual-frequency"),
            ObservationMode("l2c", "L2C", "Modernized"),
            ObservationMode("l5", "L5", "Aviation safety"),
        ),
        OrbitalElements(
            semimajor_axis_km=26_559.7,
            eccentricity=0.0005,
            inclination_deg=55.0,
            raan_deg=60.0,
        ),
    ),
    SatelliteSpec(
        "gps-block-iim",
        "gnss",
        "GPS Block III M-Code",
        "Navstar GPS - military-focused modernization",
        (
            ObservationMode("l1_m", "M-code L1 (1278.75 MHz)", "Military anti-jam"),
            ObservationMode("l2_m", "M-code L2 (1227.60 MHz)", "Military precision"),
            ObservationMode("l1_ca", "C/A-code L1", "Civilian backup"),
            ObservationMode("l2c", "L2C", "Modernized civil"),
            ObservationMode("l5", "L5", "Aviation"),
        ),
        OrbitalElements(
            semimajor_axis_km=26_559.7,
            eccentricity=0.0001,
            inclination_deg=55.0,
            raan_deg=90.0,
        ),
    ),
    SatelliteSpec(
        "galileo-foc",
        "gnss",
        "Galileo FOC (Full Operational Capability)",
        "European GNSS - dual-frequency services",
        (
            ObservationMode("e1", "E1 (1575.42 MHz)", "Open Service, Search & Rescue"),
            ObservationMode("e5a", "E5a (1176.45 MHz)", "High-precision service"),
            ObservationMode("e5b", "E5b (1207.14 MHz)", "Safety-of-life service"),
            ObservationMode("e6", "E6 (1278.75 MHz)", "Commercial service, PRS"),
        ),
        OrbitalElements(
            semimajor_axis_km=29_599.9,
            eccentricity=0.0001,
            inclination_deg=56.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "galileo-ioc",
        "gnss",
        "Galileo IOV (In-Orbit Validation)",
        "European GNSS validation satellites",
        (
            ObservationMode("e1", "E1 (1575.42 MHz)", "OS + SAR"),
            ObservationMode("e5a", "E5a (1176.45 MHz)", "I/NAV"),
            ObservationMode("e5b", "E5b (1207.14 MHz)", "F/NAV"),
        ),
        OrbitalElements(
            semimajor_axis_km=29_599.9,
            eccentricity=0.0002,
            inclination_deg=56.0,
            raan_deg=120.0,
        ),
    ),
    SatelliteSpec(
        "glonass-m",
        "gnss",
        "GLONASS-M",
        "Russian GNSS - FDMA signals",
        (
            ObservationMode("l1of", "L1OF (1602 MHz + k*0.5625 MHz)", "FDMA civilian L1"),
            ObservationMode("l2of", "L2OF (1246 MHz + k*0.4375 MHz)", "FDMA civilian L2"),
            ObservationMode("l1sf", "L1SF (FDMA military)", "Encrypted military"),
            ObservationMode("l2sf", "L2SF (FDMA military)", "Military precision"),
        ),
        OrbitalElements(
            semimajor_axis_km=25_508.0,
            eccentricity=0.0003,
            inclination_deg=64.8,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "glonass-k1",
        "gnss",
        "GLONASS-K1",
        "Russian GNSS - CDMA modernization",
        (
            ObservationMode("l1of", "L1OF FDMA", "Legacy civilian"),
            ObservationMode("l2of", "L2OF FDMA", "Legacy civilian"),
            ObservationMode("l3oc", "L3OC (1202.025 MHz)", "CDMA civilian"),
            ObservationMode("l1sc", "L1SC CDMA", "Military CDMA"),
            ObservationMode("l2sc", "L2SC CDMA", "Military CDMA"),
        ),
        OrbitalElements(
            semimajor_axis_km=25_508.0,
            eccentricity=0.0002,
            inclination_deg=64.8,
            raan_deg=45.0,
        ),
    ),
    SatelliteSpec(
        "beidou-m1",
        "gnss",
        "BeiDou MEO (IGSO-2 + MEO constellation)",
        "Chinese GNSS - BDS-3 system",
        (
            ObservationMode("b1c", "B1C (1575.42 MHz)", "Open service"),
            ObservationMode("b2a", "B2a (1176.45 MHz)", "Dual-frequency"),
            ObservationMode("b3i", "B3I (1268.52 MHz)", "Precision service"),
            ObservationMode("b2b", "B2b (1207.14 MHz)", "PPP service"),
        ),
        OrbitalElements(
            semimajor_axis_km=27_906.8,
            eccentricity=0.001,
            inclination_deg=55.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "beidou-geo",
        "gnss",
        "BeiDou GEO (Geostationary)",
        "Chinese GNSS - regional enhancement",
        (
            ObservationMode("b1", "B1 (1561.098 MHz)", "Legacy B1I"),
            ObservationMode("b2", "B2 (1207.14 MHz)", "B2a modernized"),
            ObservationMode("b3", "B3 (1268.52 MHz)", "Military B3I"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=1.5,
            raan_deg=118.0,
        ),
    ),
    SatelliteSpec(
        "qzss-ichiro",
        "gnss",
        "QZSS Ichi-Hiro",
        "Japanese augmentation - LEO augmentation",
        (
            ObservationMode("l1saif", "L1-SAIF (1575.42 MHz)", "Sub-meter augmentation"),
            ObservationMode("lex", "L-EX (1278.75 MHz)", "Centimeter augmentation"),
            ObservationMode("l1_ca", "L1 C/A", "Standard GPS compatibility"),
            ObservationMode("l2c", "L2C", "Dual-frequency"),
            ObservationMode("l5", "L5", "Aviation"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_165.0,
            eccentricity=0.075,
            inclination_deg=41.0,
            raan_deg=195.0,
            arg_perigee_deg=270.0,
        ),
    ),
    SatelliteSpec(
        "navic-irnss",
        "gnss",
        "IRNSS/NavIC",
        "Indian Regional Navigation Satellite System",
        (
            ObservationMode("l5_sps", "L5 SPS (1176.45 MHz)", "Standard positioning"),
            ObservationMode("s_sps", "S-SPS (2492.028 MHz)", "Standard positioning backup"),
            ObservationMode("l5_rs", "L5 RS (restricted)", "Encrypted military"),
            ObservationMode("s_rs", "S-RS (restricted)", "Military precision"),
        ),
        OrbitalElements(
            semimajor_axis_km=26_575.0,
            eccentricity=0.02,
            inclination_deg=29.0,
            raan_deg=55.0,
        ),
    ),
)


EARTH_OBSERVATION_CONSTELLATION: Tuple[SatelliteSpec, ...] = (
    SatelliteSpec(
        "landsat-9",
        "earth_observation",
        "Landsat 9 (LDCM)",
        "USGS - land surface monitoring since 1972",
        (
            ObservationMode("oli", "OLI (Operational Land Imager)", "Coastal aerosol, Blue, Green, Red, NIR, SWIR1, SWIR2, Cirrus"),
            ObservationMode("tirs", "TIRS-2 (Thermal Infrared Sensor)", "TIRS bands 10-11, 100m resolution"),
            ObservationMode("panchromatic", "Pan (Bands 1-9 combined)", "15m panchromatic sharpening"),
            ObservationMode("quality", "Quality Assessment band", "Cloud, cirrus, snow/ice flags"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_085.5,
            eccentricity=0.0001,
            inclination_deg=98.2,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "landsat-8",
        "earth_observation",
        "Landsat 8 (OLI-2/TIRS-2)",
        "USGS - land remote sensing",
        (
            ObservationMode("oli", "OLI-2", "9 spectral bands, coastal/aerosol to cirrus"),
            ObservationMode("tirs", "TIRS-2", "Thermal bands 10-11"),
            ObservationMode("combined", "OLI+TIRS", "Full mission data"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_085.5,
            eccentricity=0.0001,
            inclination_deg=98.2,
            raan_deg=10.0,
        ),
    ),
    SatelliteSpec(
        "sentinel-2a",
        "earth_observation",
        "Sentinel-2A",
        "ESA/Copernicus - MSI high-resolution vegetation",
        (
            ObservationMode("vnir", "VNIR bands (B2-B8)", "Blue to NIR, 10m spatial"),
            ObservationMode("swir", "SWIR bands (B8A-B12)", "Short-wave IR, 20m spatial"),
            ObservationMode("coastal", "Coastal aerosol (B1)", "Atmospheric correction, 60m"),
            ObservationMode("cirrus", "Cirrus band (B10)", "Cirrus detection, 60m"),
            ObservationMode("ndvi", "NDVI proxy mode", "Vegetation index computation"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_178.0,
            eccentricity=0.0001,
            inclination_deg=98.57,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "sentinel-2b",
        "earth_observation",
        "Sentinel-2B",
        "ESA/Copernicus - MSI twin for 5-day revisit",
        (
            ObservationMode("vnir", "VNIR bands (B2-B8)", "Blue to NIR, 10m spatial"),
            ObservationMode("swir", "SWIR bands (B8A-B12)", "Short-wave IR, 20m spatial"),
            ObservationMode("coastal", "Coastal aerosol (B1)", "Atmospheric correction"),
            ObservationMode("cirrus", "Cirrus band (B10)", "Cloud detection"),
            ObservationMode("ndvi", "NDVI proxy mode", "Vegetation monitoring"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_178.0,
            eccentricity=0.0001,
            inclination_deg=98.57,
            raan_deg=180.0,
        ),
    ),
    SatelliteSpec(
        "sentinel-1a",
        "earth_observation",
        "Sentinel-1A SAR",
        "ESA/Copernicus - C-band synthetic aperture radar",
        (
            ObservationMode("iw", "Interferometric Wide (IW)", "VV+VH dual-pol, 250km swath"),
            ObservationMode("ew", "Extra-Wide (EW)", "5-swath surveillance mode"),
            ObservationMode("sm", "Stripmap (SM)", "High-resolution stripmap"),
            ObservationMode("wv", "Wave (WV)", "Alternating VV/VH for ocean waves"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_174.0,
            eccentricity=0.0001,
            inclination_deg=98.18,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "sentinel-1b",
        "earth_observation",
        "Sentinel-1B SAR",
        "ESA/Copernicus - C-band SAR twin",
        (
            ObservationMode("iw", "Interferometric Wide (IW)", "VV+VH dual-pol, 250km swath"),
            ObservationMode("ew", "Extra-Wide (EW)", "Maritime surveillance"),
            ObservationMode("sm", "Stripmap (SM)", "High-res imaging"),
            ObservationMode("wv", "Wave (WV)", "Ocean wave spectra"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_174.0,
            eccentricity=0.0001,
            inclination_deg=98.18,
            raan_deg=180.0,
        ),
    ),
    SatelliteSpec(
        "sentinel-3a",
        "earth_observation",
        "Sentinel-3A",
        "ESA/Copernicus - ocean and land monitoring",
        (
            ObservationMode("olci", "OLCI (Ocean and Land Colour Instrument)", "21 bands, 300m, ocean color"),
            ObservationMode("slstr", "SLSTR (Sea and Land Surface Temperature)", "Thermal IR, 500m-1km"),
            ObservationMode("sral", "SRAL (SAR Altimeter)", "Surface topography, sea level"),
            ObservationMode("mwra", "MWRA (Microwave Radiometer)", "Water vapour, cloud liquid water"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_174.0,
            eccentricity=0.0001,
            inclination_deg=98.67,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "sentinel-3b",
        "earth_observation",
        "Sentinel-3B",
        "ESA/Copernicus - twin for 1.4-day revisit",
        (
            ObservationMode("olci", "OLCI", "Ocean color and land vegetation"),
            ObservationMode("slstr", "SLSTR", "Sea surface temperature"),
            ObservationMode("sral", "SRAL", "Altimetry mission"),
            ObservationMode("mwra", "MWRA", "Atmospheric correction"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_174.0,
            eccentricity=0.0001,
            inclination_deg=98.67,
            raan_deg=180.0,
        ),
    ),
    SatelliteSpec(
        "sentinel-6a",
        "earth_observation",
        "Sentinel-6 Michael Freilich",
        "ESA/NASA - Poseidon-4 altimetry, sea level",
        (
            ObservationMode("poseidon4", "Poseidon-4 SAR/Calc altimeter", "Ku/C bands, <1cm precision"),
            ObservationMode("amr-c", "AMR-C (Advanced Microwave Radiometer)", "Wet troposphere correction"),
            ObservationMode("gnss", "GNSS-POD", "Precise orbit determination"),
            ObservationMode("doris", "DORIS-NG", "Orbit positioning"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_715.0,
            eccentricity=0.0001,
            inclination_deg=66.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "gpm-core",
        "earth_observation",
        "GPM Core Observatory",
        "NASA/JAXA - Global precipitation measurement",
        (
            ObservationMode("gmi", "GMI (GPM Microwave Imager)", "13 channels, 0.65-183 GHz"),
            ObservationMode("dpr", "DPR (Dual-frequency Precipitation Radar)", "Ku+Ka band, 250m vertical"),
            ObservationMode("coordinated", "GMI+DPR combined", "Optimal precipitation retrieval"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_027.0,
            eccentricity=0.001,
            inclination_deg=65.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "smap",
        "earth_observation",
        "SMAP (Soil Moisture Active-Passive)",
        "NASA - soil moisture and freeze/thaw",
        (
            ObservationMode("radiometer", "L-band radiometer", "36km resolution soil moisture"),
            ObservationMode("radar", "L-band radar (failed 2015)", "Active soil moisture"),
            ObservationMode("combined", "Combined active-passive", "Best resolution soil moisture"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_074.0,
            eccentricity=0.001,
            inclination_deg=98.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "aqua",
        "earth_observation",
        "Aqua (EOS PM-1)",
        "NASA - atmospheric, ocean, land measurements",
        (
            ObservationMode("airs", "AIRS (Atmospheric IR Sounder)", "2378 channels, 45km"),
            ObservationMode("amsu", "AMSU-A (Microwave)", "15 channels, temperature profile"),
            ObservationMode("hsb", "HSB (Humidity Sounder - failed)", "Water vapor"),
            ObservationMode("modis", "MODIS (Moderate Resolution)", "36 bands, 250m-1km"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_078.0,
            eccentricity=0.0001,
            inclination_deg=98.2,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "terra",
        "earth_observation",
        "Terra (EOS AM-1)",
        "NASA - morning equatorial crossing (10:30 AM)",
        (
            ObservationMode("aster", "ASTER (Advanced Spaceborne Thermal)", "VNIR to TIR, 15-90m"),
            ObservationMode("ceres", "CERES (Clouds and Earth's Radiant)", "Earth radiation budget"),
            ObservationMode("misr", "MISR (Multi-angle Imaging)", "9 angles, aerosol, clouds"),
            ObservationMode("modis", "MODIS", "Land, ocean, atmosphere"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_078.0,
            eccentricity=0.0001,
            inclination_deg=98.2,
            raan_deg=180.0,
        ),
    ),
    SatelliteSpec(
        "grace-fo",
        "earth_observation",
        "GRACE-FO",
        "NASA/DLR - gravity field measurement",
        (
            ObservationMode("kbr", "K-Band Ranging", "Inter-satellite ranging, μm precision"),
            ObservationMode("gps", "GPS BlackJack", "Precise orbit determination"),
            ObservationMode("acc", "Accelerometer (SuperSTAR)", "Non-gravitational forces"),
            ObservationMode("laser", "Laser Ranging Interferometer", "New in GRACE-FO"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_873.0,
            eccentricity=0.001,
            inclination_deg=89.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "ICESat-2",
        "earth_observation",
        "ICESat-2 (ATLAS)",
        "NASA - laser altimetry, ice sheet elevation",
        (
            ObservationMode("gt3l", "Ground Track 3L (strong beam)", "6-beam laser, 0.7m spots"),
            ObservationMode("gt3r", "Ground Track 3R (weak beam)", "Strong/weak pair, photon counting"),
            ObservationMode("bkg", "Background photons", "Atmospheric background"),
            ObservationMode("seaice", "Sea ice mode", "Polar ocean ice"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_940.0,
            eccentricity=0.0001,
            inclination_deg=92.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "planet-dove-f9",
        "earth_observation",
        "Planet Dove F9 (Flock-3p)",
        "Planet Labs - 3U CubeSat constellations",
        (
            ObservationMode("panchromatic", "Pan (Bands 1-4 combined)", "3-5m panchromatic"),
            ObservationMode("msi", "MSI (4-band)", "NIR, Red, Green, Blue"),
            ObservationMode("blue_nir", "Blue+NIR bands", "NDVI computation"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_865.0,
            eccentricity=0.001,
            inclination_deg=97.44,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "planet-dove-f2",
        "earth_observation",
        "Planet Dove F2 (Flock-2p)",
        "Planet Labs - sun-synchronous sub-constellation",
        (
            ObservationMode("panchromatic", "Pan", "Sub-meter class imaging"),
            ObservationMode("msi", "MSI (4-band)", "RGB + NIR composite"),
            ObservationMode("hd_video", "HD video mode", "SkySat capture mode"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_865.0,
            eccentricity=0.001,
            inclination_deg=97.44,
            raan_deg=120.0,
        ),
    ),
    SatelliteSpec(
        "skysat-c10",
        "earth_observation",
        "SkySat-C10",
        "Planet Labs - sub-meter high-resolution imaging",
        (
            ObservationMode("panchromatic", "Pan (0.5m GSD)", "High-res monochrome"),
            ObservationMode("msi", "MSI (4-band, 2m)", "Color composite"),
            ObservationMode("video", "Video mode (30fps)", "90-second strip collections"),
            ObservationMode("stereo", "Stereo tri-stripe", "DEM generation"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_920.0,
            eccentricity=0.001,
            inclination_deg=97.4,
            raan_deg=30.0,
        ),
    ),
    SatelliteSpec(
        "worldview-3",
        "earth_observation",
        "WorldView-3",
        "Maxar - ultra-high resolution commercial imaging",
        (
            ObservationMode("panchromatic", "Panchromatic (0.31m)", "Maximum resolution visible"),
            ObservationMode("msi_8", "MSI 8-band (1.24m)", "Coastal to SWIR-2"),
            ObservationMode("cavis", "CAVIS (atmospheric)", "Cloud, aerosol, vapor, ice, snow"),
            ObservationMode("swir", "SWIR (3.7m)", "19-band short-wave infrared"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_993.0,
            eccentricity=0.001,
            inclination_deg=97.95,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "worldview-4",
        "earth_observation",
        "WorldView-4",
        "Maxar - commercial high-resolution imaging",
        (
            ObservationMode("panchromatic", "Panchromatic (0.31m)", "Visible band"),
            ObservationMode("msi", "MSI 8-band (1.24m)", "Multispectral"),
            ObservationMode("geometric", "Geometric mode", "Best NIIRS for mapping"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_030.0,
            eccentricity=0.001,
            inclination_deg=98.0,
            raan_deg=90.0,
        ),
    ),
    SatelliteSpec(
        "planetScope-dove",
        "earth_observation",
        "PlanetScope Dove (3U form factor)",
        "Planet Labs - daily global imaging",
        (
            ObservationMode("rgb", "RGB (Blue-Green-Red)", "4m ground sample distance"),
            ObservationMode("nir", "NIR band", "Vegetation health proxy"),
            ObservationMode("blue_ndvi", "Blue+Red+NIR", "NDVI and NDRE calculation"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_850.0,
            eccentricity=0.001,
            inclination_deg=97.5,
            raan_deg=240.0,
        ),
    ),
)


STORAGE_CONSTELLATION: Tuple[SatelliteSpec, ...] = (
    SatelliteSpec(
        "starlink-v1.5-550",
        "storage",
        "Starlink Gen 1 Shell 3 (550 km)",
        "SpaceX - broadband constellation shell 3",
        (
            ObservationMode("user_link", "Ku-band user link (10.7-12.7 GHz)", "Downlink to user terminals"),
            ObservationMode("gateway_link", "Ka-band gateway (17.8-19.3 GHz)", "Ground station uplinks"),
            ObservationMode("inter_sat", "Optical ISL (1064 nm)", "Inter-satellite laser links"),
            ObservationMode("steering", "Phased array steering", "Beamforming to users"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_922.0,
            eccentricity=0.0001,
            inclination_deg=53.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "starlink-v1.5-540",
        "storage",
        "Starlink Gen 1 Shell 5 (540 km)",
        "SpaceX - polar coverage shell",
        (
            ObservationMode("user_link", "Ku-band user link", "Global coverage"),
            ObservationMode("gateway_link", "Ka-band gateway", "Network backbone"),
            ObservationMode("inter_sat", "Optical ISL", "Polar inter-plane links"),
            ObservationMode("polar", "Polar mode", "Arctic/Antarctic coverage"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_910.0,
            eccentricity=0.0001,
            inclination_deg=97.6,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "starlink-v2-mini",
        "storage",
        "Starlink Gen 2 Mini (530 km)",
        "SpaceX - expanded V-band constellation",
        (
            ObservationMode("v_band", "V-band (37.5-43.5 GHz)", "High capacity links"),
            ObservationMode("ku_band", "Ku-band (10.7-18 GHz)", "Legacy compatibility"),
            ObservationMode("inter_sat", "Optical ISL", "Mesh networking"),
            ObservationMode("spatial", "Spatial isolation", "Frequency reuse"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_898.0,
            eccentricity=0.0001,
            inclination_deg=53.0,
            raan_deg=60.0,
        ),
    ),
    SatelliteSpec(
        "oneweb-gen1",
        "storage",
        "OneWeb Gen 1 (1,200 km)",
        "Arianespace/Airbus - LEO broadband",
        (
            ObservationMode("user", "Ku-band user (12.75-14.5 GHz)", "User terminal links"),
            ObservationMode("gateway", "Ka-band gateway (27.5-30 GHz)", "Hubs and gateways"),
            ObservationMode("gg", "Gateway-to-gateway", "Inter-satellite mesh"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_378.0,
            eccentricity=0.001,
            inclination_deg=87.9,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "oneweb-gen2",
        "storage",
        "OneWeb Gen 2 (MEO + LEO)",
        "Arianespace - next-gen constellation",
        (
            ObservationMode("leo_user", "LEO Ku-band", "Low latency user"),
            ObservationMode("meo_user", "MEO LEO Ku-band", "Polar coverage"),
            ObservationMode("optical", "Optical inter-satellite", "High throughput backhaul"),
        ),
        OrbitalElements(
            semimajor_axis_km=20_100.0,
            eccentricity=0.001,
            inclination_deg=55.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "iridium-next",
        "storage",
        "Iridium NEXT (78 satellites)",
        "Iridium - L-band mobile voice/data",
        (
            ObservationMode("l_band", "L-band (1.6 GHz)", "Voice and data services"),
            ObservationMode("ka_gateway", "Ka-band gateway (29 GHz)", "Ground station links"),
            ObservationMode("adsb", "ADS-B (1090 MHz)", "Aircraft tracking"),
            ObservationMode("ais", "AIS (162 MHz)", "Ship tracking"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_160.0,
            eccentricity=0.001,
            inclination_deg=86.4,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "globalstar-gsm",
        "storage",
        "Globalstar GSP-100 (32 satellites)",
        "SpaceX - S-band mobile satellite phone",
        (
            ObservationMode("sdma", "SDMA (2483.5-2500 MHz)", "Space-division multiple access"),
            ObservationMode("scpc", "SCPC (single carrier per channel)", "Point-to-point"),
            ObservationMode("simplex", "Simplex data (2411-2418 MHz)", "IoT and tracking"),
        ),
        OrbitalElements(
            semimajor_axis_km=8_380.0,
            eccentricity=0.001,
            inclination_deg=52.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "orbcomm-og2",
        "storage",
        "Orbcomm OG2 (17 satellites)",
        "SpaceX - VHF data exchange (M2M/IoT)",
        (
            ObservationMode("vde", "VDE (VHF Data Exchange)", " duplex machine-to-machine"),
            ObservationMode("idm", "IDM (Integrated Detection and Monitoring)", "Asset tracking"),
            ObservationMode("gmh", "GMH (Global Messaging Hub)", "Global coverage mode"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_050.0,
            eccentricity=0.001,
            inclination_deg=47.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "SES-O3b",
        "storage",
        "O3b MEO (20 satellites @ 8,062 km)",
        "SES - Ka-band MEO broadband",
        (
            ObservationMode("ka_hub", "Ka-band hub (28.6-29.1 GHz)", "Gateway connectivity"),
            ObservationMode("ka_user", "Ka-band user (19.7-20.2 GHz)", "Enterprise access"),
            ObservationMode("beam", "Steerable beams", "Dynamic coverage"),
        ),
        OrbitalElements(
            semimajor_axis_km=14_623.0,
            eccentricity=0.001,
            inclination_deg=0.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "SES-O3b-mPOWER",
        "storage",
        "O3b mPOWER (11 satellites)",
        "SES -第二代 MEO, 动态波束",
        (
            ObservationMode("ka_band", "Ka-band (17.7-19.3 GHz)", "High throughput"),
            ObservationMode("dynamic", "Dynamic beamforming", "Software-defined coverage"),
            ObservationMode("edge", "Edge computing mode", "On-orbit processing"),
        ),
        OrbitalElements(
            semimajor_axis_km=14_623.0,
            eccentricity=0.001,
            inclination_deg=0.0,
            raan_deg=180.0,
        ),
    ),
)


GEOSTATIONARY_CONSTELLATION: Tuple[SatelliteSpec, ...] = (
    SatelliteSpec(
        "goes-east",
        "geo_meteorology",
        "GOES-16 (GOES-East)",
        "NOAA - full disk every 15min, CONUS every 5min",
        (
            ObservationMode("abi_r", "ABI Red band (0.64 μm)", "Visible cloud tracking"),
            ObservationMode("abi_ir", "ABI IR bands (10.3 μm)", "Cloud top temperature"),
            ObservationMode("geo_color", "GEOCOLOR (natural + night IR)", "Day/night composite"),
            ObservationMode("sst", "Sea Surface Temperature", "Ocean thermal analysis"),
            ObservationMode("ash", "Ash detection (11.2 μm)", "Volcanic ash tracking"),
            ObservationMode("so2", "SO2 detection (8.5 μm)", "Sulfur dioxide monitoring"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=0.1,
            raan_deg=-75.2,
        ),
    ),
    SatelliteSpec(
        "goes-west",
        "geo_meteorology",
        "GOES-18 (GOES-West)",
        "NOAA - Pacific coverage",
        (
            ObservationMode("abi_r", "ABI Red band (0.64 μm)", "Visible cloud imaging"),
            ObservationMode("abi_ir", "ABI IR bands (10.3 μm)", "Thermal imaging"),
            ObservationMode("geo_color", "GEOCOLOR", "Natural color daylight, IR night"),
            ObservationMode("sst", "Sea Surface Temperature", "Eastern Pacific SST"),
            ObservationMode("fire", "Fire detection", "Active fire monitoring"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=0.1,
            raan_deg=-136.0,
        ),
    ),
    SatelliteSpec(
        "meteosat-11",
        "geo_meteorology",
        "Meteosat-11 (0° full disc)",
        "EUMETSAT - MSG-4, 15-min rapid scan",
        (
            ObservationMode("vis", "VIS (0.8 μm)", "High-resolution visible"),
            ObservationMode("ir", "IR (10.8 μm)", "Infrared window"),
            ObservationMode("wv", "WV (6.2/7.3 μm)", "Water vapor upper level"),
            ObservationMode("hrv", "HRV (broadband visible)", "Full disk, 1km resolution"),
            ObservationMode("dust", "Dust RGB", "Desert dust detection"),
            ObservationMode("fog", "Fog/stratus RGB", "Low cloud visibility"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=0.5,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "meteosat-10",
        "geo_meteorology",
        "Meteosat-10 (Indian Ocean 63°E)",
        "EUMETSAT - Indian Ocean coverage",
        (
            ObservationMode("vis", "VIS (0.8 μm)", "Visible imaging"),
            ObservationMode("ir", "IR (10.8 μm)", "Infrared window"),
            ObservationMode("wv", "WV (6.2 μm)", "Upper troposphere humidity"),
            ObservationMode("rgb", "RGB composites", "Natural color, dust, fog"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=0.5,
            raan_deg=63.0,
        ),
    ),
    SatelliteSpec(
        "himawari-9",
        "geo_meteorology",
        "Himawari-9",
        "JMA - East Asia + Western Pacific coverage",
        (
            ObservationMode("ahi_vis", "AHI Band 3 (0.64 μm)", "Visible (1km)"),
            ObservationMode("ahi_ir", "AHI Band 13 (10.4 μm)", "IR window (2km)"),
            ObservationMode("true_color", "True color RGB", "Natural color composite"),
            ObservationMode("ash", "Ash RGB", "Volcanic ash detection"),
            ObservationMode("sst", "SST (4 μm)", "Sea surface temperature"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=0.1,
            raan_deg=140.7,
        ),
    ),
    SatelliteSpec(
        "fengyun-4a",
        "geo_meteorology",
        "Fengyun-4A",
        "CMA - Chinese geostationary weather satellite",
        (
            ObservationMode("grapes", "GRAPES model assimilation", "Numerical weather prediction"),
            ObservationMode("ir1", "IR1 (10.8 μm)", "Infrared window"),
            ObservationMode("ir2", "IR2 (12 μm)", "Window band with moisture"),
            ObservationMode("wv", "WV (6.3 μm)", "Water vapor channel"),
            ObservationMode("vis", "VIS (0.55-0.75 μm)", "Visible imagery"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=1.0,
            raan_deg=104.7,
        ),
    ),
    SatelliteSpec(
        "insat-3d",
        "geo_meteorology",
        "INSAT-3D",
        "ISRO - Indian weather and environmental monitoring",
        (
            ObservationMode("imd", "Imager 6-channel (1km-4km)", "Six-channel radiometer"),
            ObservationMode("insat_6d", "6S Sounder (19 channels)", "Atmospheric temperature/humidity"),
            ObservationMode("sar", "Search and Rescue (406 MHz)", "Emergency beacon detection"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=1.5,
            raan_deg=74.0,
        ),
    ),
    SatelliteSpec(
        "inmarsat-6",
        "geo_communications",
        "Inmarsat-6 F1 (I-6 F1)",
        "L-band + Ka-band mobile communications",
        (
            ObservationMode("l_band", "L-band (1.5/1.6 GHz)", "Global mobile voice/data"),
            ObservationMode("ka_band", "Ka-band (2 GHz / 30 GHz)", "High throughput GX services"),
            ObservationMode("beam_gx", "Global Xpress beams", "Maritime, aviation, government"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=0.5,
            raan_deg=25.0,
        ),
    ),
    SatelliteSpec(
        "alexandra-1",
        "geo_communications",
        "Alexandra-1 (Hotbird 13F)",
        "Eutelsat - European video broadcasting",
        (
            ObservationMode("ku_band", "Ku-band (10.7-12.75 GHz)", "Video broadcast to Europe"),
            ObservationMode("europe", "Europe spot beams", "DTH television"),
            ObservationMode("africa", "Africa spot beams", "Sub-Saharan coverage"),
            ObservationMode("mena", "MENA beam", "Middle East coverage"),
        ),
        OrbitalElements(
            semimajor_axis_km=42_164.0,
            eccentricity=0.0001,
            inclination_deg=0.1,
            raan_deg=13.0,
        ),
    ),
)


DEEP_SPACE_CONSTELLATION: Tuple[SatelliteSpec, ...] = (
    SatelliteSpec(
        "voyager-1",
        "deep_space",
        "Voyager 1",
        "NASA - interstellar space probe (1977-2025: 165+ AU)",
        (
            ObservationMode("cr_mag", "Cosmic Ray System (CRS)", "High-energy particle detection"),
            ObservationMode("mag", "Dual Magnetometers", "Interstellar magnetic field"),
            ObservationMode("pps", "Plasma Science (PLS)", "Plasma density and velocity"),
            ObservationMode("pls", "Low-Energy Charged Particles", "Solar wind termination shock"),
        ),
        OrbitalElements(
            semimajor_axis_km=2.5e10,
            eccentricity=0.99,
            inclination_deg=35.0,
            raan_deg=0.0,
            arg_perigee_deg=0.0,
            mean_anomaly_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "voyager-2",
        "deep_space",
        "Voyager 2",
        "NASA - only probe to visit all four giant planets",
        (
            ObservationMode("cr_mag", "CRS", "Galactic cosmic rays"),
            ObservationMode("mag", "Magnetometers", "Heliographic and IPH coordinates"),
            ObservationMode("pps", "PLS", "Interstellar plasma"),
            ObservationMode("pls_lecp", "LECP", "Low-energy charged particles"),
        ),
        OrbitalElements(
            semimajor_axis_km=2.0e10,
            eccentricity=0.98,
            inclination_deg=79.0,
            raan_deg=0.0,
            arg_perigee_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "james-webb",
        "deep_space",
        "James Webb Space Telescope",
        "NASA/ESA/CSA - L2 halo orbit, infrared (0.6-28.5 μm)",
        (
            ObservationMode("nircam", "NIRCam (0.6-5 μm)", "Near-IR imaging + coronagraphy"),
            ObservationMode("nirspec", "NIRSpec (0.6-5.3 μm)", "Multi-object spectroscopy"),
            ObservationMode("miri", "MIRI (4.9-28.8 μm)", "Mid-IR imaging and spectroscopy"),
            ObservationMode("nirpgrism", "NIRCam grism mode", "Transiting exoplanet spectroscopy"),
            ObservationMode("coronagraph", "Coronagraphic masks", "Exoplanet direct imaging"),
        ),
        OrbitalElements(
            semimajor_axis_km=1_501_000.0,
            eccentricity=0.008,
            inclination_deg=33.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "soho",
        "deep_space",
        "SOHO (Solar and Heliospheric Observatory)",
        "NASA/ESA - L1 orbit, solar monitoring since 1995",
        (
            ObservationMode("eit", "EIT (Extreme ultraviolet Imaging Telescope)", "171/195/284/304 Å EUV"),
            ObservationMode("lasco_c2", "LASCO C2 (white light)", "White-light coronagraph"),
            ObservationMode("lasco_c3", "LASCO C3 (white light)", "Outer corona imaging"),
            ObservationMode("mdi", "MDI/SDO (magnetogram)", "Solar surface magnetic field"),
            ObservationMode("cds", "CDS (Coronal Diagnostic Spectrometer)", "UV spectroscopy"),
        ),
        OrbitalElements(
            semimajor_axis_km=1_501_000.0,
            eccentricity=0.004,
            inclination_deg=0.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "chandra",
        "deep_space",
        "Chandra X-ray Observatory",
        "NASA - high-resolution X-ray astronomy (0.1-10 keV)",
        (
            ObservationMode("acis", "ACIS (Advanced CCD Imaging Spectrometer)", "0.2-10 keV, imaging spectroscopy"),
            ObservationMode("hrc", "HRC (High Resolution Camera)", "0.1-10 keV, high spatial res"),
            ObservationMode("heg", "HETG (High Energy Transmission Grating)", "0.4-10 keV spectroscopy"),
            ObservationMode("meg", "LETG (Low Energy Transmission Grating)", "0.09-6 keV, high res"),
        ),
        OrbitalElements(
            semimajor_axis_km=107_000.0,
            eccentricity=0.0004,
            inclination_deg=28.5,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "herschel",
        "deep_space",
        "Herschel Space Observatory",
        "ESA - far-infrared and submillimetre (55-672 μm)",
        (
            ObservationMode("pacs", "PACS (Photodetecting Array Camera)", "55-210 μm imaging/spectroscopy"),
            ObservationMode("hifi", "HIFI (Heterodyne Instrument)", "157-212/240-625 μm heterodyne"),
            ObservationMode("spire", "SPIRE (Spectral and Photometric Imaging)", "200-500 μm photometry/spectroscopy"),
        ),
        OrbitalElements(
            semimajor_axis_km=1_497_000.0,
            eccentricity=0.003,
            inclination_deg=0.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "planck",
        "deep_space",
        "Planck Space Observatory",
        "ESA - cosmic microwave background (30-857 GHz)",
        (
            ObservationMode("lfi", "LFI (Low Frequency Instrument)", "30-70 GHz radiometers"),
            ObservationMode("hfi", "HFI (High Frequency Instrument)", "100-857 GHz bolometers"),
            ObservationMode("full", "Combined LFI+HFI", "Full sky CMB anisotropy"),
        ),
        OrbitalElements(
            semimajor_axis_km=1_499_000.0,
            eccentricity=0.002,
            inclination_deg=85.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "spitzer",
        "deep_space",
        "Spitzer Space Telescope",
        "NASA - infrared space telescope (3.6-160 μm)",
        (
            ObservationMode("irac", "IRAC (4-channel infrared array)", "3.6/4.5/5.8/8.0 μm imaging"),
            ObservationMode("irs", "IRS (Infrared Spectrograph)", "5.3-38 μm spectroscopy"),
            ObservationMode("mips", "MIPS (Multiband Imaging Photometer)", "24/70/160 μm imaging"),
        ),
        OrbitalElements(
            semimajor_axis_km=157_000_000.0,
            eccentricity=0.0001,
            inclination_deg=0.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "kepler",
        "deep_space",
        "Kepler Space Telescope",
        "NASA - exoplanet transit photometry (photometric precision 20 ppm)",
        (
            ObservationMode("long_cadence", "Long cadence (30 min)", "Photometry of 100,000+ stars"),
            ObservationMode("short_cadence", "Short cadence (1 min)", "Asteroseismology"),
            ObservationMode("ffis", "FFI (Full Frame Image)", "Background stars + galaxies"),
        ),
        OrbitalElements(
            semimajor_axis_km=149_000_000.0,
            eccentricity=0.0001,
            inclination_deg=0.5,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "tess",
        "deep_space",
        "TESS (Transiting Exoplanet Survey Satellite)",
        "NASA - all-sky exoplanet survey (85% coverage in 2 years)",
        (
            ObservationMode("sector_2min", "2-minute cadence", "10,000+ target stars per sector"),
            ObservationMode("ffis", "FFI (30 min cadence)", "Full frame images"),
            ObservationMode("global", "Global observing plan", "Northern then southern ecliptic hemispheres"),
        ),
        OrbitalElements(
            semimajor_axis_km=373_000.0,
            eccentricity=0.01,
            inclination_deg=37.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "mro",
        "deep_space",
        "Mars Reconnaissance Orbiter",
        "NASA - Mars imaging, spectroscopy, communication relay",
        (
            ObservationMode("hirise", "HiRISE (0.4-1.0 μm)", "0.3m/pixel stereo imaging"),
            ObservationMode("crism", "CRISM (0.36-3.92 μm)", "Mineralogy spectroscopy"),
            ObservationMode("ctx", "CTX (Context Camera)", "6m/pixel mono imaging"),
            ObservationMode("marsi", "MARCI (wide-angle)", "Weather monitoring, 10 m/pixel"),
            ObservationMode("mola", "MOLA (laser altimeter)", "Topography 100m precision"),
        ),
        OrbitalElements(
            semimajor_axis_km=3_650.0,
            eccentricity=0.009,
            inclination_deg=93.0,
            raan_deg=0.0,
            arg_perigee_deg=270.0,
        ),
    ),
    SatelliteSpec(
        "juno",
        "deep_space",
        "Juno (Jupiter Polar Orbiter)",
        "NASA - Jupiter interior, magnetosphere, aurora",
        (
            ObservationMode("jiram", "JIRAM (1-5 μm)", "Jupiter aurora and atmospheric spectroscopy"),
            ObservationMode("mwi", "MWR (Microwave Radiometer)", "1.3-50 cm atmospheric probing"),
            ObservationMode("juno_cam", "JunoCam (visible)", "Public outreach, storm tracking"),
            ObservationMode("magnetometer", "Magnetometers", "Jupiter magnetic field mapping"),
            ObservationMode("waves", "Waves (plasma)", "Radio and plasma wave science"),
        ),
        OrbitalElements(
            semimajor_axis_km=11_300.0,
            eccentricity=0.71,
            inclination_deg=90.0,
            raan_deg=0.0,
            arg_perigee_deg=90.0,
            mean_anomaly_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "cassini",
        "deep_space",
        "Cassini-Huygens",
        "NASA/ESA - Saturn system (1997-2017, 294 orbits)",
        (
            ObservationMode("iss", "Imaging Science Subsystem", "Narrow/wide angle visible imaging"),
            ObservationMode("vims", "VIMS (0.35-5.1 μm)", "VNIR/SWIR spectral imaging"),
            ObservationMode("cacs", "CIRS (Fourier transform IR)", "Thermal emission spectroscopy"),
            ObservationMode("mags", "Magnetometer", "Saturn magnetosphere"),
            ObservationMode("rpws", "RPWS (Radio/Plasma)", "Plasma wave science"),
        ),
        OrbitalElements(
            semimajor_axis_km=9_000.0,
            eccentricity=0.98,
            inclination_deg=64.0,
            raan_deg=0.0,
            arg_perigee_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "new-horizons",
        "deep_space",
        "New Horizons",
        "NASA - Pluto, Kuiper Belt (Arrokoth flyby 2019)",
        (
            ObservationMode("lorri", "LORRI (panchromatic)", "Long-range imaging, 4.9 μrad/pixel"),
            ObservationMode("ralph", "Ralph (color imager+spectrometer)", "0.4-2.5 μm surface mapping"),
            ObservationMode("rex", "REX (radio science)", "Atmospheric occultation"),
            ObservationMode("pepssi", "PEPSSI (energetic particles)", "Plasma ions/neutrons"),
            ObservationMode("swap", "SWAP (solar wind)", "Solar wind at Pluto distance"),
        ),
        OrbitalElements(
            semimajor_axis_km=5_000_000.0,
            eccentricity=0.97,
            inclination_deg=2.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "parker-solar-probe",
        "deep_space",
        "Parker Solar Probe",
        "NASA - solar corona, closest: 6.1 million km (2025)",
        (
            ObservationMode("wispr", "WISPR (white light)", "Inner heliosphere imaging"),
            ObservationMode("swooap", "SWEA (particles)", "Solar wind electron velocity"),
            ObservationMode("summy", "FIELDS (electric/magnetic)", "DC electric and magnetic fields"),
            ObservationMode("isois", "ISOIS (particles)", "Energetic particle acceleration"),
        ),
        OrbitalElements(
            semimajor_axis_km=14_000.0,
            eccentricity=0.94,
            inclination_deg=3.0,
            raan_deg=0.0,
            arg_perigee_deg=144.0,
        ),
    ),
    SatelliteSpec(
        "europa-clipper",
        "deep_space",
        "Europa Clipper",
        "NASA - Europa subsurface ocean characterization",
        (
            ObservationMode("misr_e", "MISE (infrared)", "Europa subsurface composition"),
            ObservationMode("eis", "EIS (wide-angle camera)", "Geological mapping"),
            ObservationMode("mas", "MASS (mass spectrometer)", "Exosphere composition"),
            ObservationMode("rpx", "REASON (ice-penetrating radar)", "Ice shell thickness"),
            ObservationMode("mags", "Magnetometer", "Subsurface ocean detection"),
        ),
        OrbitalElements(
            semimajor_axis_km=13_500.0,
            eccentricity=0.47,
            inclination_deg=86.0,
            raan_deg=0.0,
            arg_perigee_deg=90.0,
        ),
    ),
)


HUMAN_SPACEFLIGHT_CONSTELLATION: Tuple[SatelliteSpec, ...] = (
    SatelliteSpec(
        "iss",
        "human_spaceflight",
        "International Space Station",
        "NASA/Roscosmos/ESA/JAXA/CSA - LEO, h=420km, 92.9 min period",
        (
            ObservationMode("cupola", "Cupola observation", "ISS Earth observation window"),
            ObservationMode("ecssa", "ECOSTRESS (JPL)", "Plant temperature stress"),
            ObservationMode("gwu", "Global Learning and Observations (GLO)", "Student science"),
            ObservationMode("radiation", "Radiation monitoring", "ISS dosimetry"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_795.0,
            eccentricity=0.0005,
            inclination_deg=51.64,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "tiangong-space-station",
        "human_spaceflight",
        "Tiangong Space Station (CSS)",
        "CMSA - Chinese LEO station (~400km altitude)",
        (
            ObservationMode("hert", "Heavenly Earth Observation", "Earth observation module"),
            ObservationMode("mengtian", "Mengtian experiment module", "Microgravity experiments"),
            ObservationMode("xuntian", "Xuntian (survey telescope)", "Opto-electronic surveillance"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_790.0,
            eccentricity=0.001,
            inclination_deg=41.5,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "hubble",
        "human_spaceflight",
        "Hubble Space Telescope",
        "NASA/ESA - LEO 540km, visible to near-IR (0.1-2.5 μm)",
        (
            ObservationMode("wfc3_uv", "WFC3 UV/Vis (200-1000 nm)", "UV and optical imaging"),
            ObservationMode("wfc3_ir", "WFC3 IR (800-1700 nm)", "Near-infrared imaging"),
            ObservationMode("acs", "ACS (0.1-1.0 μm)", "Wide-field imaging"),
            ObservationMode("cos", "COS (115-320 nm)", "UV spectroscopy"),
            ObservationMode("stis", "STIS (115-1000 nm)", "UV/optical spectroscopy"),
            ObservationMode("nicmos", "NICMOS (0.8-2.4 μm)", "Near-IR imaging (legacy)"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_913.0,
            eccentricity=0.0003,
            inclination_deg=28.47,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "tiangong-2",
        "human_spaceflight",
        "Tiangong-2 (deorbited 2019)",
        "CMSA - Chinese space lab, docking tests",
        (
            ObservationMode("panoramic", "Panoramic camera", "Earth observation"),
            ObservationMode("polaris", "Polaris camera", "Multi-angle imaging"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_810.0,
            eccentricity=0.001,
            inclination_deg=42.79,
            raan_deg=0.0,
        ),
    ),
)


LUNAR_CONSTELLATION: Tuple[SatelliteSpec, ...] = (
    SatelliteSpec(
        "artemis-1-orion",
        "lunar",
        "Artemis I Orion",
        "NASA - uncrewed lunar flyby, Distant Retrograde Orbit",
        (
            ObservationMode("ocss", "OCSS (Optical Communications)", "High-data-rate comms demo"),
            ObservationMode("eivp", "EIVP (engineering cameras)", "External view monitoring"),
            ObservationMode("headlamps", "Headlamps (UV/visible)", "Navigation reference"),
        ),
        OrbitalElements(
            semimajor_axis_km=58_000.0,
            eccentricity=0.58,
            inclination_deg=28.0,
            raan_deg=0.0,
            arg_perigee_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "lunar-reconnaissance-orbiter",
        "lunar",
        "LRO (Lunar Reconnaissance Orbiter)",
        "NASA - lunar mapping, 50km polar orbit",
        (
            ObservationMode("lolaim", "LOLA (laser altimeter)", "Topography, 1m vertical precision"),
            ObservationMode("lroc_nac", "NAC (narrow angle camera)", "0.5-2.0 m/pixel imaging"),
            ObservationMode("lroc_wac", "WAC (wide angle camera)", "100 m/pixel, 7-color UV"),
            ObservationMode("diviner", "DIVINER (thermal)", "Regolith temperature, mineralogy"),
            ObservationMode("lend", "LEND (neutron spectrometer)", "Hydrogen/water ice deposits"),
            ObservationMode("crater", "Mini-RF (synthetic aperture)", "Radar ice detection"),
        ),
        OrbitalElements(
            semimajor_axis_km=1_790.0,
            eccentricity=0.001,
            inclination_deg=90.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "chandrayaan-2-orbiter",
        "lunar",
        "Chandrayaan-2 Orbiter",
        "ISRO - lunar south pole volatiles investigation",
        (
            ObservationMode("iirs", "IIRS (imaging spectrometer)", "0.55-2.5 μm surface mapping"),
            ObservationMode("tgc", "TMC (terrain mapping camera)", "5m DEM generation"),
            ObservationMode("chace-2", "CHACE-2 (mass spectrometer)", "Exosphere composition"),
            ObservationMode("xsm", "XSM (X-ray spectrometer)", "Minor element abundance"),
        ),
        OrbitalElements(
            semimajor_axis_km=1_785.0,
            eccentricity=0.001,
            inclination_deg=88.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "kaguya-selene",
        "lunar",
        "Kaguya (SELENE)",
        "JAXA - lunar orbiter (2007-2009), GRAIL precursors",
        (
            ObservationMode("terrain", "Terrain Camera (TC)", "Stereo imaging"),
            ObservationMode("msr", "Multispectral Imager (MI)", "VNIR mineralogy"),
            ObservationMode("xrs", "X-ray Spectrometer", "Major element mapping"),
            ObservationMode("rstar", "RSAT (radar sounder)", "Subsurface radar"),
        ),
        OrbitalElements(
            semimajor_axis_km=1_788.0,
            eccentricity=0.001,
            inclination_deg=90.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "luna-25",
        "lunar",
        "Luna 25 (Luna-Glob)",
        "Roscosmos - lunar south pole lander (crashed 2023)",
        (
            ObservationMode("adron", "ADRON (neutron/gamma)", "Water ice detection"),
            ObservationMode("pilot", "PILOT-D (navigation)", "Descent guidance test"),
            ObservationMode("laser", "LIDAR (laser ranging)", "Surface profiling"),
        ),
        OrbitalElements(
            semimajor_axis_km=1_790.0,
            eccentricity=0.001,
            inclination_deg=90.0,
            raan_deg=0.0,
        ),
    ),
)


SAR_CONSTELLATION: Tuple[SatelliteSpec, ...] = (
    SatelliteSpec(
        " radarsat-2",
        "sar",
        "RADARSAT-2",
        "CSA/MDA - C-band SAR, multi-polarization",
        (
            ObservationMode("spotlight", "SpotLight (3m)", "High-res urban imaging"),
            ObservationMode("stripmap", "Stripmap (8m)", "Wide-area mapping"),
            ObservationMode("scanSAR", "ScanSAR (25m)", "Wide swath monitoring"),
            ObservationMode("ocean", "Ocean surveillance mode", "Maritime domain awareness"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_177.0,
            eccentricity=0.0001,
            inclination_deg=98.6,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        " radarsat-constellation",
        "sar",
        "RADARSAT Constellation (3 satellites)",
        "CSA - C-band SAR, daily revisit Canada",
        (
            ObservationMode("swf", "Standard Wide (150km)", "Land and sea monitoring"),
            ObservationMode("sms", "Standard Medium (50km)", "Agricultural and ice"),
            ObservationMode("ext", "Extended High (20m)", "Mountainous terrain"),
            ObservationMode("marine", "Marine (polar)", "Iceberg detection"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_177.0,
            eccentricity=0.0001,
            inclination_deg=97.74,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "terrasar-x",
        "sar",
        "TerraSAR-X",
        "DLR/Airbus - X-band SAR, 1-16m resolution",
        (
            ObservationMode("spotlight", "SpotLight (1m)", "Very high-res urban"),
            ObservationMode("stripmap", "Stripmap (3m)", "High-res mapping"),
            ObservationMode("scanSAR", "ScanSAR (16m)", "Wide area monitoring"),
            ObservationMode("himage", "High-resolution Spotlight", "Best resolution mode"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_948.0,
            eccentricity=0.001,
            inclination_deg=97.44,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "tanDEM-x",
        "sar",
        "TanDEM-X",
        "DLR - bistatic SAR with TerraSAR-X, global DEM",
        (
            ObservationMode("stripmap", "Stripmap bistatic", "Along-track interferometry"),
            ObservationMode("spotlight", "SpotLight bistatic", "High-res DEM"),
            ObservationMode("hrm", "HRM (Horizontal Receive)", "Cross-pol measurements"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_948.0,
            eccentricity=0.001,
            inclination_deg=97.44,
            raan_deg=180.0,
        ),
    ),
    SatelliteSpec(
        "alos-2",
        "sar",
        "ALOS-2 (Daichi-2)",
        "JAXA - L-band SAR, disaster monitoring",
        (
            ObservationMode("stripmap", "Stripmap (3-10m)", "Standard SAR imaging"),
            ObservationMode("scanSAR", "ScanSAR (25-100m)", "Wide area monitoring"),
            ObservationMode("palsar2", "PALSAR-2 (polarimetric)", "Forest/non-forest classification"),
            ObservationMode("disaster", "Disaster mode", "Emergency response"),
        ),
        OrbitalElements(
            semimajor_axis_km=7_035.0,
            eccentricity=0.001,
            inclination_deg=97.4,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "capella-3",
        "sar",
        "Capella-3 (Whitney)",
        "Capella Space - X-band SAR, sub-meter resolution",
        (
            ObservationMode("spotlight", "SpotLight (0.5m)", "Sub-meter stripmap"),
            ObservationMode("stripmap", "Stripmap (1-2m)", "High-res wide area"),
            ObservationMode("circle", "Circle (SpotLight)", "Multiple angles on target"),
            ObservationMode("sleuth", "SLEUTH (video)", "Moving target indication"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_850.0,
            eccentricity=0.001,
            inclination_deg=53.0,
            raan_deg=0.0,
        ),
    ),
    SatelliteSpec(
        "iceye-x",
        "sar",
        "ICEYE (X-1, X-2, X-4)",
        "ICEYE - microsatellite SAR, frequent revisit",
        (
            ObservationMode("spotlight", "SpotLight (0.5-1m)", "Very high-res imaging"),
            ObservationMode("stripmap", "Stripmap (3m)", "Standard mode"),
            ObservationMode("scanSAR", "ScanSAR wide (20m)", "Large area coverage"),
            ObservationMode("dwell", "Dwell-mode (coherent change)", "Subtle change detection"),
        ),
        OrbitalElements(
            semimajor_axis_km=6_860.0,
            eccentricity=0.001,
            inclination_deg=97.5,
            raan_deg=0.0,
        ),
    ),
)


def satellites_from_environment() -> List[SatelliteSpec]:
    """Order follows SPACE_SEGMENT_HOSTS; unknown hosts still get a generic spec."""
    raw = os.getenv("SPACE_SEGMENT_HOSTS", "")
    hosts = [h.strip() for h in raw.split(",") if h.strip()]
    if not hosts:
        return list(_DEFAULT_CONSTELLATION)
    out: List[SatelliteSpec] = []
    for h in hosts:
        spec = next((s for s in _DEFAULT_CONSTELLATION if s.hostname == h), None)
        if spec:
            out.append(spec)
        else:
            prof = _PROFILE_BY_HOST.get(h, "dark_matter")
            out.append(
                SatelliteSpec(
                    h,
                    prof,
                    h.replace("sentry-", "").replace("-", " ").title(),
                    "Custom / unknown node",
                    (ObservationMode("default", "Standard acquisition", ""),),
                )
            )
    return out


def spec_for_host(hostname: str) -> Optional[SatelliteSpec]:
    for s in satellites_from_environment():
        if s.hostname == hostname:
            return s
    return None


def all_catalogs() -> Dict[str, Tuple[SatelliteSpec, ...]]:
    """Return all available satellite catalogs keyed by name."""
    return {
        "sentry": _DEFAULT_CONSTELLATION,
        "gnss": GNSS_CONSTELLATION,
        "earth_observation": EARTH_OBSERVATION_CONSTELLATION,
        "storage": STORAGE_CONSTELLATION,
        "geostationary": GEOSTATIONARY_CONSTELLATION,
        "deep_space": DEEP_SPACE_CONSTELLATION,
        "human_spaceflight": HUMAN_SPACEFLIGHT_CONSTELLATION,
        "lunar": LUNAR_CONSTELLATION,
        "sar": SAR_CONSTELLATION,
    }


def orbital_period_from_semimajor(a_km: float) -> float:
    """
    Kepler's 3rd Law: T = 2π * sqrt(a³ / GM)
    Returns period in minutes.
    """
    a_m = a_km * 1000.0
    T_s = 2 * 3.141592653589793 * (a_m ** 3 / GM_EARTH) ** 0.5
    return T_s / 60.0


def orbital_velocity_at_radius(r_km: float, a_km: float, e: float = 0.0) -> float:
    """
    Vis-viva equation: v = sqrt(GM * (2/r - 1/a))
    Returns velocity in km/s.
    """
    r_m = r_km * 1000.0
    a_m = a_km * 1000.0
    v_m_s = (GM_EARTH * (2.0 / r_m - 1.0 / a_m)) ** 0.5
    return v_m_s / 1000.0


def escape_velocity_from_radius(r_km: float) -> float:
    """v_esc = sqrt(2GM/r), returns km/s."""
    r_m = r_km * 1000.0
    return (2 * GM_EARTH / r_m) ** 0.5 / 1000.0


def geosynchronous_radius_km() -> float:
    """Standard GEO: T = 1436.07 min (sidereal day) => a = 42,164 km."""
    return orbital_period_from_semimajor(42_164.0) / 60.0 - 1436.07 < 0.1 and 42_164.0


ORBITAL_REGIMES = {
    "leo": (R_EARTH / 1000 + 200, R_EARTH / 1000 + 2000),
    "meo": (R_EARTH / 1000 + 2000, R_EARTH / 1000 + 35786),
    "geo": (R_EARTH / 1000 + 35786 - 200, R_EARTH / 1000 + 35786 + 200),
    "l1": (1_495_000, 1_505_000),
    "l2": (1_495_000, 1_505_000),
    "molniya": (6_700, 39_700),
    "transfer": (6_678, 42_164),
}
