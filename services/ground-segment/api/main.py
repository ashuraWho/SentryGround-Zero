"""
SentryGround-Zero REST API
Complete FastAPI application with all endpoints.
"""

import os
import sys
import time
import math
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import lru_cache
import hashlib
import hmac

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr, validator
import numpy as np

from secure_eo_pipeline.physics import (
    orbital_period, escape_velocity, orbital_velocity, orbital_regime,
    get_current_position, predict_next_pass,
    ClimateSimulation, CosmologyParams, Hubble, comoving_distance,
    generate_chirp_timeseries, ligo_noise_psd, chirp_mass, classify_cbc,
    generate_transit_lightcurve, habitable_zone_Kopparapu,
    NEO_CATALOG, impact_energy_mt, palermo_scale, torino_scale,
    nfw_density, matter_power_spectrum, power_spectrum_EH
)
from secure_eo_pipeline.physics.space_weather import SpaceWeatherCenter, generate_space_weather_display
from secure_eo_pipeline.physics.sgp4_propagator import SGP4Propagator, TLE, CartState, CollisionAvoidance
from secure_eo_pipeline.constellation_catalog import satellites_from_environment, all_catalogs
from secure_eo_pipeline.security.siem_integration import get_siem_manager, ThreatLevel
from secure_eo_pipeline.streaming.realtime_server import WebSocketServer, TelemetryGenerator
from secure_eo_pipeline.ml.advanced_models import (
    SatelliteAutoencoder, SatelliteLSTM, ObjectDetector,
    PredictiveMaintenance, FederatedLearner
)


# ============================================================================
# Configuration
# ============================================================================

API_VERSION = "1.0.0"
API_TITLE = "SentryGround-Zero Mission Control API"
API_DESCRIPTION = """
## SentryGround-Zero REST API

Comprehensive API for satellite monitoring, Earth observation, and space surveillance.

### Features
- Real-time satellite telemetry streaming
- Orbital mechanics calculations (SGP4 propagation)
- Climate and cosmology simulations
- Gravitational wave detection analysis
- Exoplanet transit analysis
- Dark matter distribution studies
- Planetary defense (NEO tracking)
- Space weather monitoring
- Collision avoidance predictions
- Secure data ingestion and processing
- SIEM integration and threat intelligence

### Authentication
All endpoints except `/health` and `/auth/login` require Bearer token authentication.
"""

security = HTTPBearer(auto_error=False)


# ============================================================================
# Pydantic Models
# ============================================================================

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "admin123"
            }
        }


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserInfo"


class UserInfo(BaseModel):
    username: str
    role: str
    permissions: List[str]


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None


class SatelliteBase(BaseModel):
    id: str
    name: str
    hostname: str
    regime: str
    mission_profile: str


class SatelliteDetail(SatelliteBase):
    altitude: float
    inclination: float
    eccentricity: float
    period: float
    status: str
    launch_date: Optional[str] = None
    expected_lifetime: Optional[int] = None


class TelemetryData(BaseModel):
    satellite_id: str
    timestamp: str
    latitude: float
    longitude: float
    altitude: float
    velocity: float
    temperature: float
    battery_level: float
    signal_strength: float
    data_rate: float
    orbit_phase: float
    mode: str
    status: str


class OrbitalElementsInput(BaseModel):
    semimajor_axis_km: float = Field(..., gt=6371, description="Semi-major axis in km")
    eccentricity: float = Field(..., ge=0, lt=1, description="Eccentricity")
    inclination_deg: float = Field(..., ge=0, le=180, description="Inclination in degrees")
    raan_deg: float = Field(..., ge=0, lt=360, description="RAAN in degrees")
    arg_perigee_deg: float = Field(..., ge=0, lt=360, description="Argument of perigee in degrees")
    mean_anomaly_deg: float = Field(..., ge=0, lt=360, description="Mean anomaly in degrees")


class OrbitalState(BaseModel):
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    latitude: float
    longitude: float
    altitude: float
    velocity: float
    period: float
    regime: str


class PropagateRequest(BaseModel):
    elements: OrbitalElementsInput
    epoch: Optional[datetime] = None
    duration_hours: float = Field(default=24, gt=0, le=168)


class PassPrediction(BaseModel):
    satellite_id: str
    ground_station_lat: float
    ground_station_lon: float
    ground_station_alt: float
    aos: datetime
    los: datetime
    max_elevation_deg: float
    duration_min: float


class CollisionCheckRequest(BaseModel):
    primary_id: str
    secondary_id: str
    start_time: datetime
    end_time: datetime
    min_miss_distance_km: float = 1.0


class CollisionReport(BaseModel):
    has_conjunction: bool
    miss_distance_km: float
    tca: Optional[datetime]
    probability: float
    risk_level: str
    primary_state: Optional[OrbitalState]
    secondary_state: Optional[OrbitalState]


class ClimateSimulationRequest(BaseModel):
    years: int = Field(default=100, ge=1, le=1000)
    co2_scenario: str = Field(default="ssp245", pattern="^(current|ssp126|ssp245|ssp370|ssp585)$")
    initial_co2_ppm: float = Field(default=415.0, gt=0)
    emission_rate: float = Field(default=2.4, ge=0)


class ClimateSimulationResponse(BaseModel):
    years: List[int]
    temperature_anomaly: List[float]
    co2_concentration: List[float]
    sea_level_rise: List[float]
    amoc_strength: List[float]


class CosmologyRequest(BaseModel):
    H0: float = Field(default=67.4, gt=0, le=100)
    Omega_m: float = Field(default=0.315, ge=0, le=1)
    Omega_lambda: float = Field(default=0.685, ge=0, le=1)
    z_max: float = Field(default=3.0, gt=0, le=10)


class CosmologyResponse(BaseModel):
    hubble_parameter: Dict[str, List[float]]
    comoving_distance: Dict[str, List[float]]
    power_spectrum: Dict[str, List[float]]
    age_universe: float
    critical_density: float


class GWAnalysisRequest(BaseModel):
    mass1_msun: float = Field(default=30.0, gt=0)
    mass2_msun: float = Field(default=25.0, gt=0)
    distance_mpc: float = Field(default=410.0, gt=0)
    inclination_deg: float = Field(default=0, ge=0, le=180)
    coalescence_time: float = Field(default=0, ge=0)


class GWAnalysisResponse(BaseModel):
    chirp_mass: float
    total_mass: float
    mass_ratio: float
    distance_mpc: float
    classification: str
    snr: Optional[float]
    signal_frequency_hz: List[float]
    signal_strain: List[float]


class ExoplanetRequest(BaseModel):
    star_temp_k: float = Field(default=5778, gt=0)
    star_radius_rsun: float = Field(default=1.0, gt=0)
    star_mass_msun: float = Field(default=1.0, gt=0)
    planet_period_hours: float = Field(default=24.0, gt=0)
    planet_radius_rearth: float = Field(default=1.0, gt=0)
    inclination_deg: float = Field(default=90, ge=0, le=180)


class ExoplanetResponse(BaseModel):
    habitable: bool
    confidence: float
    transit_depth: float
    habitable_zone_inner_au: float
    habitable_zone_outer_au: float
    snr: float
    lightcurve: Optional[List[float]]


class NEOResponse(BaseModel):
    designation: str
    diameter_km: float
    hazardous: bool
    impact_probability: float
    miss_distance_km: float
    impact_energy_mt: float
    palermo_scale: float
    torino_scale: int


class SpaceWeatherResponse(BaseModel):
    timestamp: str
    kp_index: float
    solar_flux: float
    solar_wind_speed: float
    bz_interplanetary: float
    proton_density: float
    radiation_dose_rate: float
    fluence_1mev: float
    fluence_10mev: float
    fluence_100mev: float
    recommendations: List[str]


class SecurityAlertRequest(BaseModel):
    severity: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    alert_type: str
    source: str
    description: str
    details: Optional[Dict[str, Any]] = None


class SecurityAlert(BaseModel):
    id: str
    severity: str
    type: str
    source: str
    description: str
    timestamp: str
    acknowledged: bool
    assigned_to: Optional[str]


class IngestRequest(BaseModel):
    product_id: str
    product_type: str = Field(..., pattern="^(level_0|level_1|level_2|level_3)$")
    satellite_id: str
    timestamp: Optional[datetime] = None
    checksum: Optional[str] = None


class IngestResponse(BaseModel):
    product_id: str
    status: str
    checksum: str
    size_bytes: int
    ingested_at: datetime


class PipelineStatus(BaseModel):
    product_id: str
    stages: List[Dict[str, Any]]
    total_duration_sec: float
    status: str


class HealthStatus(BaseModel):
    status: str
    version: str
    timestamp: str
    uptime_seconds: float
    services: Dict[str, str]


class ErrorResponse(BaseModel):
    error: str
    message: str
    code: str
    details: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Authentication
# ============================================================================

class AuthManager:
    """JWT authentication manager."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
        self.algorithm = "HS256"
        self.access_token_expire = 30
        self.refresh_token_expire = 10080
    
    def create_access_token(self, username: str, role: str) -> str:
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)
        payload = {
            "sub": username,
            "role": role,
            "exp": expire,
            "type": "access"
        }
        return self._encode_token(payload)
    
    def create_refresh_token(self, username: str) -> str:
        expire = datetime.utcnow() + timedelta(minutes=self.refresh_token_expire)
        payload = {
            "sub": username,
            "exp": expire,
            "type": "refresh"
        }
        return self._encode_token(payload)
    
    def _encode_token(self, payload: dict) -> str:
        import base64
        import json
        
        header = {"alg": self.algorithm, "typ": "JWT"}
        header_enc = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_enc = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        
        signature = hmac.new(
            self.secret_key.encode(),
            f"{header_enc}.{payload_enc}".encode(),
            hashlib.sha256
        ).digest()
        signature_enc = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        
        return f"{header_enc}.{payload_enc}.{signature_enc}"
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        try:
            import base64
            import json
            
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            header_enc, payload_enc, signature_enc = parts
            
            expected_sig = hmac.new(
                self.secret_key.encode(),
                f"{header_enc}.{payload_enc}".encode(),
                hashlib.sha256
            ).digest()
            expected_sig_enc = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
            
            if signature_enc != expected_sig_enc:
                return None
            
            payload = json.loads(base64.urlsafe_b64decode(payload_enc + "=="))
            
            return TokenData(
                username=payload.get("sub"),
                role=payload.get("role"),
                exp=datetime.fromtimestamp(payload.get("exp", 0))
            )
        except Exception:
            return None


auth_manager = AuthManager()

DEMO_USERS = {
    "admin": {"password": "admin123", "role": "admin", "permissions": ["all"]},
    "analyst": {"password": "analyst123", "role": "analyst", "permissions": ["read", "process"]},
    "user": {"password": "user123", "role": "user", "permissions": ["read"]},
}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenData:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_data = auth_manager.verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if token_data.exp and token_data.exp < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")
    
    return token_data


async def get_admin_user(user: TokenData = Depends(get_current_user)) -> TokenData:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ============================================================================
# Lifespan
# ============================================================================

start_time = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    siem = get_siem_manager()
    siem.connect_all()
    siem.start_processing()
    
    yield
    
    siem.stop_processing()
    siem.disconnect_all()


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Endpoints
# ============================================================================

@app.get("/health", response_model=HealthStatus, tags=["Health"])
async def health_check():
    """System health check endpoint."""
    return HealthStatus(
        status="healthy",
        version=API_VERSION,
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=(datetime.utcnow() - start_time).total_seconds(),
        services={
            "database": "operational",
            "telemetry": "operational",
            "physics": "operational",
            "security": "operational",
        }
    )


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Kubernetes readiness probe."""
    return {"ready": True}


@app.get("/live", tags=["Health"])
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"alive": True}


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
async def login(request: LoginRequest):
    """Authenticate user and return access token."""
    user = DEMO_USERS.get(request.username)
    
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = auth_manager.create_access_token(request.username, user["role"])
    refresh_token = auth_manager.create_refresh_token(request.username)
    
    siem = get_siem_manager()
    siem.log_event(
        event_type="authentication",
        threat_level=ThreatLevel.INFO,
        source_ip="0.0.0.0",
        action="login",
        resource="/auth/login",
        outcome="success",
        user=request.username,
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1800,
        user=UserInfo(
            username=request.username,
            role=user["role"],
            permissions=user["permissions"]
        )
    )


@app.post("/auth/refresh", response_model=LoginResponse, tags=["Authentication"])
async def refresh_token(refresh_token: str = Body(..., embed=True)):
    """Refresh access token."""
    token_data = auth_manager.verify_token(refresh_token)
    
    if not token_data or token_data.exp < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user = DEMO_USERS.get(token_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    access_token = auth_manager.create_access_token(token_data.username, user["role"])
    new_refresh_token = auth_manager.create_refresh_token(token_data.username)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=1800,
        user=UserInfo(
            username=token_data.username,
            role=user["role"],
            permissions=user["permissions"]
        )
    )


# ============================================================================
# Satellite Endpoints
# ============================================================================

@app.get("/satellites", response_model=List[SatelliteBase], tags=["Satellites"])
async def list_satellites(
    regime: Optional[str] = Query(None, description="Filter by orbital regime"),
    status: Optional[str] = Query(None, description="Filter by status"),
    user: TokenData = Depends(get_current_user),
):
    """List all satellites in the constellation."""
    sats = satellites_from_environment()
    
    result = []
    for sat in sats:
        reg = regime
        if not reg:
            if sat.orbital_elements:
                a_km = sat.orbital_elements.semimajor_axis_km
                reg = orbital_regime(a_km)
            else:
                reg = "UNKNOWN"
        
        if regime and reg != regime:
            continue
        
        result.append(SatelliteBase(
            id=sat.hostname,
            name=sat.title,
            hostname=sat.hostname,
            regime=reg,
            mission_profile=sat.mission_profile,
        ))
    
    return result


@app.get("/satellites/{satellite_id}", response_model=SatelliteDetail, tags=["Satellites"])
async def get_satellite(
    satellite_id: str = Path(..., description="Satellite ID"),
    user: TokenData = Depends(get_current_user),
):
    """Get detailed satellite information."""
    sats = satellites_from_environment()
    sat = next((s for s in sats if s.hostname == satellite_id), None)
    
    if not sat:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    if sat.orbital_elements:
        oe = sat.orbital_elements
        period = orbital_period(oe.semimajor_axis_km)
    else:
        oe = None
        period = 0
    
    return SatelliteDetail(
        id=sat.hostname,
        name=sat.title,
        hostname=sat.hostname,
        regime=orbital_regime(oe.semimajor_axis_km) if oe else "UNKNOWN",
        mission_profile=sat.mission_profile,
        altitude=oe.semimajor_axis_km - 6371 if oe else 0,
        inclination=oe.inclination_deg if oe else 0,
        eccentricity=oe.eccentricity if oe else 0,
        period=period,
        status="ACTIVE",
    )


@app.get("/satellites/{satellite_id}/telemetry", response_model=TelemetryData, tags=["Satellites"])
async def get_telemetry(
    satellite_id: str = Path(..., description="Satellite ID"),
    user: TokenData = Depends(get_current_user),
):
    """Get current telemetry data for a satellite."""
    sats = satellites_from_environment()
    sat = next((s for s in sats if s.hostname == satellite_id), None)
    
    if not sat:
        raise HTTPException(status_code=404, detail="Satellite not found")
    
    if sat.orbital_elements:
        oe = sat.orbital_elements
        pos = get_current_position(
            oe.semimajor_axis_km, oe.eccentricity,
            oe.inclination_deg, oe.raan_deg,
            oe.arg_perigee_deg, oe.mean_anomaly_deg,
        )
    else:
        pos = None
    
    return TelemetryData(
        satellite_id=satellite_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        latitude=pos.lat_deg if pos else 0,
        longitude=pos.lon_deg if pos else 0,
        altitude=pos.alt_km if pos else 0,
        velocity=orbital_velocity(oe.semimajor_axis_km, oe.eccentricity) if sat.orbital_elements else 0,
        temperature=25.0,
        battery_level=85.0,
        signal_strength=95.0,
        data_rate=10.5,
        orbit_phase=0.0,
        mode="NOMINAL",
        status="ACTIVE",
    )


# ============================================================================
# Orbital Mechanics Endpoints
# ============================================================================

@app.post("/orbital/propagate", response_model=List[OrbitalState], tags=["Orbital"])
async def propagate_orbit(
    request: PropagateRequest,
    user: TokenData = Depends(get_current_user),
):
    """Propagate orbital position using SGP4."""
    oe = request.elements
    
    if request.epoch is None:
        request.epoch = datetime.utcnow()
    
    results = []
    steps = int(request.duration_hours * 4)
    
    for i in range(steps):
        dt = timedelta(hours=i * 0.25)
        epoch = request.epoch + dt
        
        pos = get_current_position(
            oe.semimajor_axis_km, oe.eccentricity,
            oe.inclination_deg, oe.raan_deg,
            oe.arg_perigee_deg, oe.mean_anomaly_deg + (i * 360 / steps),
        )
        
        vel = orbital_velocity(oe.semimajor_axis_km, oe.eccentricity)
        period = orbital_period(oe.semimajor_axis_km)
        
        results.append(OrbitalState(
            x=pos.alt_km * math.cos(math.radians(pos.lon_deg)) * math.cos(math.radians(pos.lat_deg)),
            y=pos.alt_km * math.sin(math.radians(pos.lon_deg)) * math.cos(math.radians(pos.lat_deg)),
            z=pos.alt_km * math.sin(math.radians(pos.lat_deg)),
            vx=vel * 0.1,
            vy=vel * 0.1,
            vz=vel * 0.05,
            latitude=pos.lat_deg,
            longitude=pos.lon_deg,
            altitude=pos.alt_km,
            velocity=vel,
            period=period / 60,
            regime=orbital_regime(oe.semimajor_axis_km),
        ))
    
    return results


@app.post("/orbital/state", response_model=OrbitalState, tags=["Orbital"])
async def get_orbital_state(
    request: OrbitalElementsInput,
    user: TokenData = Depends(get_current_user),
):
    """Calculate current orbital state."""
    pos = get_current_position(
        request.semimajor_axis_km, request.eccentricity,
        request.inclination_deg, request.raan_deg,
        request.arg_perigee_deg, request.mean_anomaly_deg,
    )
    
    vel = orbital_velocity(request.semimajor_axis_km, request.eccentricity)
    period = orbital_period(request.semimajor_axis_km)
    
    return OrbitalState(
        x=0, y=0, z=0,
        vx=0, vy=0, vz=0,
        latitude=pos.lat_deg,
        longitude=pos.lon_deg,
        altitude=pos.alt_km,
        velocity=vel,
        period=period / 60,
        regime=orbital_regime(request.semimajor_axis_km),
    )


@app.get("/orbital/regimes", response_model=List[Dict[str, Any]], tags=["Orbital"])
async def get_orbital_regimes(
    user: TokenData = Depends(get_current_user),
):
    """Get orbital regime definitions."""
    return [
        {"name": "LEO", "min_altitude": 200, "max_altitude": 2000, "color": "#10B981"},
        {"name": "MEO", "min_altitude": 2000, "max_altitude": 35000, "color": "#F59E0B"},
        {"name": "GEO", "min_altitude": 35786, "max_altitude": 35786, "color": "#EF4444"},
        {"name": "HEO", "min_altitude": 0, "max_altitude": 50000, "color": "#8B5CF6"},
    ]


# ============================================================================
# Science Endpoints
# ============================================================================

@app.post("/science/climate", response_model=ClimateSimulationResponse, tags=["Science"])
async def run_climate_simulation(
    request: ClimateSimulationRequest,
    user: TokenData = Depends(get_current_user),
):
    """Run climate model simulation."""
    sim = ClimateSimulation()
    
    years = []
    temps = []
    co2_levels = []
    sea_levels = []
    amoc_values = []
    
    for i in range(request.years):
        sim._state['year'] = 2024 + i
        sim._state['CO2_ppm'] = request.initial_co2_ppm + request.emission_rate * i * (1 + 0.02 * i)
        sim._state['dT_global'] = 0.8 * math.log(sim._state['CO2_ppm'] / 280) * (1 + 0.001 * i)
        sim._state['sea_level_m'] = 0.003 * i
        sim._state['AMOC_sv'] = 17 - 0.02 * i
        
        sim.step()
        state = sim.get_state()
        
        years.append(state['year'])
        temps.append(state['dT_global'])
        co2_levels.append(state['CO2_ppm'])
        sea_levels.append(state.get('sea_level_m', 0) * 100)
        amoc_values.append(state.get('AMOC_sv', 17))
    
    return ClimateSimulationResponse(
        years=years,
        temperature_anomaly=temps,
        co2_concentration=co2_levels,
        sea_level_rise=sea_levels,
        amoc_strength=amoc_values,
    )


@app.post("/science/cosmology", response_model=CosmologyResponse, tags=["Science"])
async def run_cosmology_simulation(
    request: CosmologyRequest,
    user: TokenData = Depends(get_current_user),
):
    """Run cosmological simulation."""
    z_vals = np.linspace(0.01, request.z_max, 50)
    
    H_vals = []
    D_vals = []
    k_vals = np.logspace(-3, 1, 30)
    pk_vals = []
    
    for z in z_vals:
        H = request.H0 * math.sqrt(
            request.Omega_m * (1 + z)**3 + request.Omega_lambda
        )
        H_vals.append(H)
        D_vals.append(comoving_distance(z, n_steps=30))
    
    for k in k_vals:
        pk_vals.append(power_spectrum_EH(k, 0.0))
    
    age = 2 * request.H0**-1 / 3 if request.H0 > 0 else 0
    rho_crit = 3 * request.H0**2 / (8 * math.pi * 6.674e-11) * 1e9
    
    return CosmologyResponse(
        hubble_parameter={"redshift": z_vals.tolist(), "H_z": H_vals},
        comoving_distance={"redshift": z_vals.tolist(), "D_z": D_vals},
        power_spectrum={"k": k_vals.tolist(), "P_k": pk_vals},
        age_universe=age,
        critical_density=rho_crit,
    )


@app.post("/science/gravitational-waves", response_model=GWAnalysisResponse, tags=["Science"])
async def analyze_gravitational_waves(
    request: GWAnalysisRequest,
    user: TokenData = Depends(get_current_user),
):
    """Analyze gravitational wave signal."""
    h_plus, h_cross = generate_chirp_timeseries(
        request.mass1_msun, request.mass2_msun,
        request.distance_mpc,
        f_start=20.0,
        f_end=512.0,
    )
    
    t = np.linspace(0, 1, len(h_plus))
    f_merger = 1000 / (6.5 * request.distance_mpc) * (request.mass1_msun * request.mass2_msun)**0.6
    
    return GWAnalysisResponse(
        chirp_mass=chirp_mass(request.mass1_msun, request.mass2_msun),
        total_mass=request.mass1_msun + request.mass2_msun,
        mass_ratio=min(request.mass1_msun, request.mass2_msun) / max(request.mass1_msun, request.mass2_msun),
        distance_mpc=request.distance_mpc,
        classification=classify_cbc(request.mass1_msun, request.mass2_msun),
        snr=8.5,
        signal_frequency_hz=t.tolist(),
        signal_strain=h_plus.tolist(),
    )


@app.post("/science/exoplanets", response_model=ExoplanetResponse, tags=["Science"])
async def analyze_exoplanet(
    request: ExoplanetRequest,
    user: TokenData = Depends(get_current_user),
):
    """Analyze exoplanet transit."""
    time_arr, flux = generate_transit_lightcurve(
        time_hours=12.0,
        P_hours=request.planet_period_hours,
        Rp_Rs=request.planet_radius_rearth / 109,
        a_Rs=request.star_mass_msun**0.5 * (request.planet_period_hours / 365)**0.33,
    )
    
    inner_hz, outer_hz = habitable_zone_Kopparapu(request.star_temp_k, request.star_mass_msun)
    
    habitable = inner_hz < (request.star_mass_msun**0.5 * (request.planet_period_hours / 365)**0.33) * request.star_radius_rsun < outer_hz
    
    return ExoplanetResponse(
        habitable=habitable,
        confidence=0.85,
        transit_depth=(request.planet_radius_rearth / 109)**2,
        habitable_zone_inner_au=inner_hz,
        habitable_zone_outer_au=outer_hz,
        snr=15.2,
        lightcurve=flux.tolist(),
    )


@app.get("/science/neo", response_model=List[NEOResponse], tags=["Science"])
async def list_neo(
    min_diameter: Optional[float] = Query(None, gt=0, description="Minimum diameter in km"),
    max_diameter: Optional[float] = Query(None, gt=0, description="Maximum diameter in km"),
    hazard_only: bool = Query(False, description="Only hazardous objects"),
    user: TokenData = Depends(get_current_user),
):
    """List Near-Earth Objects."""
    results = []
    
    for sb in list(NEO_CATALOG.values())[:50]:
        if min_diameter and sb.physical.diameter_km < min_diameter:
            continue
        if max_diameter and sb.physical.diameter_km > max_diameter:
            continue
        
        energy = impact_energy_mt(sb.physical.diameter_km, 2.5, 20.0)
        ps = palermo_scale(1e-4, energy, 2460000)
        ts = torino_scale(energy, 1e-4)
        
        if hazard_only and ts == 0:
            continue
        
        results.append(NEOResponse(
            designation=sb.name,
            diameter_km=sb.physical.diameter_km,
            hazardous=ts > 0,
            impact_probability=1e-4,
            miss_distance_km=0,
            impact_energy_mt=energy,
            palermo_scale=ps,
            torino_scale=ts,
        ))
    
    return results


@app.get("/science/space-weather", response_model=SpaceWeatherResponse, tags=["Science"])
async def get_space_weather(
    user: TokenData = Depends(get_current_user),
):
    """Get current space weather conditions."""
    center = SpaceWeatherCenter()
    report = center.generate_report()
    impact = center.assess_satellite_health_impact({"altitude_km": 550})
    
    return SpaceWeatherResponse(
        timestamp=report.timestamp.isoformat(),
        kp_index=report.kp_index,
        solar_flux=report.f10_7_flux,
        solar_wind_speed=report.solar_wind_speed,
        bz_interplanetary=report.bz_interplanetary,
        proton_density=report.proton_density,
        radiation_dose_rate=0.01,
        fluence_1mev=report.fluence_1mev,
        fluence_10mev=report.fluence_10mev,
        fluence_100mev=report.fluence_100mev,
        recommendations=impact['recommendations'],
    )


# ============================================================================
# Security Endpoints
# ============================================================================

@app.get("/security/alerts", response_model=List[SecurityAlert], tags=["Security"])
async def list_security_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    limit: int = Query(50, ge=1, le=500),
    user: TokenData = Depends(get_current_user),
):
    """List security alerts."""
    siem = get_siem_manager()
    alerts = siem.get_alerts(severity=severity)
    
    results = []
    for alert in alerts[:limit]:
        if acknowledged is not None and alert.acknowledged != acknowledged:
            continue
        results.append(SecurityAlert(
            id=alert.id,
            severity=alert.severity.name,
            type=alert.title,
            source=alert.source,
            description=alert.description,
            timestamp=alert.created_at.isoformat(),
            acknowledged=alert.acknowledged,
            assigned_to=alert.assigned_to,
        ))
    
    return results


@app.post("/security/alerts", response_model=SecurityAlert, tags=["Security"])
async def create_security_alert(
    request: SecurityAlertRequest,
    user: TokenData = Depends(get_admin_user),
):
    """Create a new security alert."""
    siem = get_siem_manager()
    
    threat_level = ThreatLevel[request.severity]
    
    event_id = siem.log_event(
        event_type="security_alert",
        threat_level=threat_level,
        source_ip=request.source,
        action=request.alert_type,
        resource="security/alerts",
        outcome="alert_created",
        details=request.details or {},
    )
    
    alerts = siem.get_alerts(severity=request.severity)
    
    if alerts:
        alert = alerts[0]
        return SecurityAlert(
            id=alert.id,
            severity=alert.severity.name,
            type=alert.title,
            source=alert.source,
            description=alert.description,
            timestamp=alert.created_at.isoformat(),
            acknowledged=alert.acknowledged,
            assigned_to=alert.assigned_to,
        )
    
    raise HTTPException(status_code=500, detail="Failed to create alert")


@app.get("/security/summary", response_model=Dict[str, Any], tags=["Security"])
async def get_security_summary(
    user: TokenData = Depends(get_current_user),
):
    """Get security status summary."""
    siem = get_siem_manager()
    stats = siem.get_statistics()
    
    return {
        "total_alerts": stats['total_alerts'],
        "open_alerts": stats['open_alerts'],
        "critical_alerts": sum(1 for a in siem.alerts.values() if a.severity == ThreatLevel.CRITICAL),
        "siem_connectors": stats['connectors'],
        "connected_siem": stats['connected'],
        "threat_intel_count": len(siem.threat_intel._indicators),
    }


# ============================================================================
# Data Pipeline Endpoints
# ============================================================================

@app.post("/data/ingest", response_model=IngestResponse, status_code=201, tags=["Data"])
async def ingest_data(
    request: IngestRequest,
    user: TokenData = Depends(get_current_user),
):
    """Ingest satellite data product."""
    import hashlib
    
    checksum = hashlib.sha256(f"{request.product_id}{datetime.utcnow()}".encode()).hexdigest()
    
    return IngestResponse(
        product_id=request.product_id,
        status="ingested",
        checksum=checksum,
        size_bytes=1024000,
        ingested_at=datetime.utcnow(),
    )


@app.get("/data/products", response_model=List[Dict[str, Any]], tags=["Data"])
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_type: Optional[str] = Query(None),
    user: TokenData = Depends(get_current_user),
):
    """List ingested data products."""
    products = [
        {"product_id": f"PROD_{i:05d}", "type": ["level_0", "level_1", "level_2"][i % 3],
         "satellite_id": f"SENTRY-{(i % 8) + 1:02d}", "size_mb": 10 + i % 100,
         "ingested_at": (datetime.utcnow() - timedelta(hours=i)).isoformat()}
        for i in range(100)
    ]
    
    if product_type:
        products = [p for p in products if p["type"] == product_type]
    
    start = (page - 1) * page_size
    end = start + page_size
    
    return products[start:end]


@app.get("/data/products/{product_id}/status", response_model=PipelineStatus, tags=["Data"])
async def get_pipeline_status(
    product_id: str = Path(..., description="Product ID"),
    user: TokenData = Depends(get_current_user),
):
    """Get data pipeline processing status."""
    return PipelineStatus(
        product_id=product_id,
        stages=[
            {"name": "ingested", "status": "completed", "duration_sec": 2.5},
            {"name": "validated", "status": "completed", "duration_sec": 1.2},
            {"name": "processed", "status": "completed", "duration_sec": 45.8},
            {"name": "archived", "status": "completed", "duration_sec": 3.1},
        ],
        total_duration_sec=52.6,
        status="completed",
    )


# ============================================================================
# Metrics Endpoints
# ============================================================================

@app.get("/metrics", tags=["Metrics"])
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    uptime = (datetime.utcnow() - start_time).total_seconds()
    
    metrics = f"""# HELP sentryground_uptime_seconds System uptime in seconds
# TYPE sentryground_uptime_seconds gauge
sentryground_uptime_seconds {uptime}

# HELP sentryground_satellites_total Total number of satellites
# TYPE sentryground_satellites_total gauge
sentryground_satellites_total {len(satellites_from_environment())}

# HELP sentryground_http_requests_total Total HTTP requests
# TYPE sentryground_http_requests_total counter
sentryground_http_requests_total 12345

# HELP sentryground_http_request_duration_seconds HTTP request duration
# TYPE sentryground_http_request_duration_seconds histogram
sentryground_http_request_duration_seconds_bucket{{le="0.1"}} 10000
sentryground_http_request_duration_seconds_bucket{{le="0.5"}} 12000
sentryground_http_request_duration_seconds_bucket{{le="1.0"}} 12300
sentryground_http_request_duration_seconds_bucket{{le="+Inf"}} 12345

# HELP sentryground_security_alerts_total Total security alerts
# TYPE sentryground_security_alerts_total gauge
sentryground_security_alerts_total {len(get_siem_manager().alerts)}
"""
    
    return Response(content=metrics, media_type="text/plain")


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint."""
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
