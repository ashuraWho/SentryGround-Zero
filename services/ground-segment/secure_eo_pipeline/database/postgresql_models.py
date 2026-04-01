"""
PostgreSQL/TimescaleDB Models for SentryGround-Zero.

Implements:
- TimescaleDB hypertables for time-series telemetry
- Satellite orbital state history
- Sensor observation data
- Science product metadata
- Ground station contacts

SQLAlchemy ORM models with TimescaleDB extensions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import (
    Column, String, Integer, BigInteger, Float, Boolean, DateTime,
    ForeignKey, Index, Text, JSON, Numeric, Enum, UniqueConstraint,
    create_engine, event
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB, TSTZRANGE
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Session, joinedload
from sqlalchemy.sql import func, text


Base = declarative_base()


# =============================================================================
# ENUMS
# =============================================================================

class SatelliteStatus(PyEnum):
    OPERATIONAL = "operational"
    STANDBY = "standby"
    SAFE_MODE = "safe_mode"
    EOL = "end_of_life"
    DECOMMISSIONED = "decommissioned"


class SensorType(PyEnum):
    OPTICAL_IMAGER = "optical_imager"
    SAR = "sar"
    HYPERSPECTRAL = "hyperspectral"
    THERMAL_IR = "thermal_ir"
    RADAR_ALTIMETER = "radar_altimeter"
    GNSS_RO = "gnss_occultation"
    GRAVITY_GRADIOMETER = "gravity_gradiometer"
    MAGNETOMETER = "magnetometer"
    PARTICLE_DETECTOR = "particle_detector"
    X_RAY_SPECTROMETER = "x_ray_spectrometer"
    GRAVITATIONAL_WAVE = "gravitational_wave"


class ProductLevel(PyEnum):
    RAW = "RAW"
    L0 = "L0"
    L1A = "L1A"
    L1B = "L1B"
    L2 = "L2"
    L2A = "L2A"
    L3 = "L3"
    L4 = "L4"


class OrbitRegime(PyEnum):
    LEO = "LEO"
    MEO = "MEO"
    GEO = "GEO"
    HEO = "HEO"
    LUNAR = "LUNAR"
    INTERPLANETARY = "interplanetary"


# =============================================================================
# SATELLITE MODELS
# =============================================================================

class Satellite(Base):
    """Satellite catalog entry."""
    __tablename__ = "satellites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    norad_id = Column(Integer, unique=True, index=True)
    cospas_id = Column(String(12), unique=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    owner = Column(String(100))
    operator = Column(String(100))
    
    satellite_type = Column(String(50))
    mission_class = Column(String(50))
    
    launch_date = Column(DateTime(timezone=True))
    launch_vehicle = Column(String(50))
    launch_site = Column(String(100))
    
    decay_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(SatelliteStatus), default=SatelliteStatus.OPERATIONAL)
    
    mass_kg = Column(Float)
    power_w = Column(Float)
    design_life_years = Column(Float)
    
    orbit_regime = Column(Enum(OrbitRegime))
    
    tle_line1 = Column(String(69))
    tle_line2 = Column(String(69))
    tle_epoch = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sensors = relationship("Sensor", back_populates="satellite", cascade="all, delete-orphan")
    orbital_states = relationship("OrbitalState", back_populates="satellite", cascade="all, delete-orphan")
    contacts = relationship("GroundStationContact", back_populates="satellite", cascade="all, delete-orphan")
    products = relationship("ScienceProduct", back_populates="satellite", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_satellites_name_lower", text("lower(name)")),
        Index("ix_satellites_status_regime", "status", "orbit_regime"),
    )


class Sensor(Base):
    """Satellite sensor/payload definition."""
    __tablename__ = "sensors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    satellite_id = Column(UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(100), nullable=False)
    sensor_type = Column(Enum(SensorType), nullable=False)
    
    wavelength_min_nm = Column(Float)
    wavelength_max_nm = Column(Float)
    spectral_bands = Column(ARRAY(Float))
    
    spatial_resolution_m = Column(Float)
    swath_width_km = Column(Float)
    field_of_view_deg = Column(Float)
    
    pointing_accuracy_deg = Column(Float)
    pointing_range_deg = Column(JSONB)
    
    data_rate_mbps = Column(Float)
    quantization_bits = Column(Integer)
    
    calibration_date = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    satellite = relationship("Satellite", back_populates="sensors")
    observations = relationship("SensorObservation", back_populates="sensor", cascade="all, delete-orphan")
    modes = relationship("SensorMode", back_populates="sensor", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("satellite_id", "name", name="uq_sensor_satellite_name"),
    )


class SensorMode(Base):
    """Sensor operating modes."""
    __tablename__ = "sensor_modes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_id = Column(UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(50), nullable=False)
    description = Column(Text)
    
    spatial_resolution_m = Column(Float)
    swath_width_km = Column(Float)
    integration_time_s = Column(Float)
    
    compression = Column(String(50))
    coding_rate = Column(Float)
    
    science_modes = Column(ARRAY(String(50)))

    sensor = relationship("Sensor", back_populates="modes")


# =============================================================================
# ORBITAL STATE MODELS
# =============================================================================

class OrbitalState(Base):
    """Orbital state vector history (hypertable)."""
    __tablename__ = "orbital_states"
    __table_args__ = {
        "postgresql_partition_by": "RANGE (time)",
    }

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    satellite_id = Column(UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False)
    
    time = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    
    x_km = Column(Float, nullable=False)
    y_km = Column(Float, nullable=False)
    z_km = Column(Float, nullable=False)
    vx_km_s = Column(Float, nullable=False)
    vy_km_s = Column(Float, nullable=False)
    vz_km_s = Column(Float, nullable=False)
    
    latitude_deg = Column(Float)
    longitude_deg = Column(Float)
    altitude_km = Column(Float)
    
    period_s = Column(Float)
    eccentricity = Column(Float)
    inclination_deg = Column(Float)
    semi_major_axis_km = Column(Float)
    
    mean_anomaly_deg = Column(Float)
    raan_deg = Column(Float)
    arg_perigee_deg = Column(Float)
    
    eclipse_flag = Column(Boolean, default=False)
    sun_beta_angle_deg = Column(Float)
    
    position_source = Column(String(20), default="SGP4")

    satellite = relationship("Satellite", back_populates="orbital_states")

    __table_args__ = (
        Index("ix_orbital_states_satellite_time", "satellite_id", "time"),
        Index("ix_orbital_states_altitude", "altitude_km"),
    )


class TLESeries(Base):
    """TLE data series for satellite."""
    __tablename__ = "tle_series"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    satellite_id = Column(UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False)
    
    tle_line1 = Column(String(69), nullable=False)
    tle_line2 = Column(String(69), nullable=False)
    
    epoch = Column(DateTime(timezone=True), nullable=False, index=True)
    mean_motion_dot = Column(Float)
    mean_motion_ddot = Column(Float)
    bstar = Column(Float)
    
    inclination_deg = Column(Float)
    raan_deg = Column(Float)
    eccentricity = Column(Float)
    arg_perigee_deg = Column(Float)
    mean_anomaly_deg = Column(Float)
    mean_motion_rev_day = Column(Float)
    
    ephemeris_type = Column(Integer, default=0)
    element_set_number = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_tle_series_satellite_epoch", "satellite_id", "epoch"),
    )


# =============================================================================
# GROUND STATION MODELS
# =============================================================================

class GroundStation(Base):
    """Ground station definition."""
    __tablename__ = "ground_stations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    short_name = Column(String(20))
    
    latitude_deg = Column(Float, nullable=False)
    longitude_deg = Column(Float, nullable=False)
    altitude_m = Column(Float, default=0.0)
    
    min_elevation_deg = Column(Float, default=5.0)
    max_range_km = Column(Float)
    
    antenna_diameter_m = Column(Float)
    frequency_tx_mhz = Column(Float)
    frequency_rx_mhz = Column(Float)
    
    max_data_rate_mbps = Column(Float)
    network = Column(String(50))
    
    operator = Column(String(100))
    location = Column(String(200))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contacts = relationship("GroundStationContact", back_populates="ground_station")
    passes = relationship("PassPrediction", back_populates="ground_station")


class GroundStationContact(Base):
    """Satellite-ground station contact events."""
    __tablename__ = "ground_station_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    satellite_id = Column(UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False)
    ground_station_id = Column(UUID(as_uuid=True), ForeignKey("ground_stations.id", ondelete="CASCADE"), nullable=False)
    
    contact_start = Column(DateTime(timezone=True), nullable=False, index=True)
    contact_end = Column(DateTime(timezone=True), nullable=False)
    
    max_elevation_deg = Column(Float)
    aot_s = Column(Float)
    
    contact_type = Column(String(20))
    data_volume_mb = Column(Float)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    satellite = relationship("Satellite", back_populates="contacts")
    ground_station = relationship("GroundStation", back_populates="contacts")

    __table_args__ = (
        Index("ix_contacts_satellite_time", "satellite_id", "contact_start"),
        Index("ix_contacts_gs_time", "ground_station_id", "contact_start"),
    )


class PassPrediction(Base):
    """Scheduled pass predictions."""
    __tablename__ = "pass_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    satellite_id = Column(UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False)
    ground_station_id = Column(UUID(as_uuid=True), ForeignKey("ground_stations.id", ondelete="CASCADE"), nullable=False)
    
    aos_time = Column(DateTime(timezone=True), nullable=False, index=True)
    los_time = Column(DateTime(timezone=True), nullable=False)
    max_el_time = Column(DateTime(timezone=True))
    
    aos_azimuth_deg = Column(Float)
    los_azimuth_deg = Column(Float)
    max_elevation_deg = Column(Float)
    
    duration_s = Column(Float)
    max_range_km = Column(Float)
    
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="scheduled")
    
    satellite_name = Column(String(100))
    ground_station_name = Column(String(100))

    ground_station = relationship("GroundStation", back_populates="passes")

    __table_args__ = (
        Index("ix_pass_pred_satellite_time", "satellite_id", "aos_time"),
        Index("ix_pass_pred_gs_time", "ground_station_id", "aos_time"),
    )


# =============================================================================
# SCIENCE DATA MODELS
# =============================================================================

class SensorObservation(Base):
    """Sensor observation metadata (hypertable for time-series)."""
    __tablename__ = "sensor_observations"
    __table_args__ = {
        "postgresql_partition_by": "RANGE (observation_time)",
    }

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_id = Column(UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False)
    
    observation_time = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    
    orbit_number = Column(Integer)
    frame_id = Column(String(50))
    
    center_lat_deg = Column(Float)
    center_lon_deg = Column(Float)
    
    start_lat_deg = Column(Float)
    start_lon_deg = Column(Float)
    end_lat_deg = Column(Float)
    end_lon_deg = Column(Float)
    
    cloud_fraction = Column(Float)
    snow_fraction = Column(Float)
    
    solar_zenith_deg = Column(Float)
    solar_azimuth_deg = Column(Float)
    view_zenith_deg = Column(Float)
    
    exposure_s = Column(Float)
    gain = Column(Float)
    
    mode_name = Column(String(50))
    product_level = Column(Enum(ProductLevel))
    
    data_size_bytes = Column(BigInteger)
    checksum = Column(String(64))
    
    file_path = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sensor = relationship("Sensor", back_populates="observations")
    products = relationship("ScienceProduct", back_populates="observation")

    __table_args__ = (
        Index("ix_observations_sensor_time", "sensor_id", "observation_time"),
        Index("ix_observations_location", "center_lat_deg", "center_lon_deg"),
    )


class ScienceProduct(Base):
    """Processed science product metadata."""
    __tablename__ = "science_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    satellite_id = Column(UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False)
    observation_id = Column(UUID(as_uuid=True), ForeignKey("sensor_observations.id", ondelete="SET NULL"), nullable=True)
    
    product_id = Column(String(100), unique=True, nullable=False, index=True)
    product_name = Column(String(200))
    product_type = Column(String(50), nullable=False, index=True)
    
    level = Column(Enum(ProductLevel), nullable=False)
    
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    center_lat_deg = Column(Float)
    center_lon_deg = Column(Float)
    spatial_extent_km2 = Column(Float)
    
    bounding_box = Column(JSONB)
    
    parameters = Column(JSONB)
    
    file_path = Column(Text)
    file_size_bytes = Column(BigInteger)
    checksum = Column(String(64))
    
    s3_bucket = Column(String(100))
    s3_key = Column(String(500))
    
    thumbnail_path = Column(Text)
    
    processing_version = Column(String(20))
    processing_software = Column(String(100))
    processing_time = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    published = Column(Boolean, default=False)
    published_at = Column(DateTime(timezone=True))

    satellite = relationship("Satellite", back_populates="products")
    observation = relationship("SensorObservation", back_populates="products")
    quality_info = relationship("ProductQuality", back_populates="product", uselist=False)
    downloads = relationship("ProductDownload", back_populates="product")

    __table_args__ = (
        Index("ix_products_type_time", "product_type", "start_time"),
        Index("ix_products_location", "center_lat_deg", "center_lon_deg"),
        Index("ix_products_satellite_time", "satellite_id", "start_time"),
    )


class ProductQuality(Base):
    """Product quality metrics."""
    __tablename__ = "product_quality"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("science_products.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    radiometric_quality = Column(String(20))
    geometric_quality = Column(String(20))
    completeness_pct = Column(Float)
    
    saturation_pct = Column(Float)
    no_data_pct = Column(Float)
    cloud_pct = Column(Float)
    
    errors = Column(JSONB)
    warnings = Column(JSONB)
    
    validated = Column(Boolean, default=False)
    validated_by = Column(String(100))
    validated_at = Column(DateTime(timezone=True))

    product = relationship("ScienceProduct", back_populates="quality_info")


class ProductDownload(Base):
    """Product download/access log."""
    __tablename__ = "product_downloads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("science_products.id", ondelete="CASCADE"), nullable=False)
    
    user_id = Column(String(100))
    ip_address = Column(String(45))
    
    download_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    bytes_downloaded = Column(BigInteger)
    download_method = Column(String(20))
    
    api_key = Column(String(50))

    product = relationship("ScienceProduct", back_populates="downloads")


# =============================================================================
# TELEMETRY MODELS
# =============================================================================

class TelemetryRecord(Base):
    """Raw telemetry records (hypertable)."""
    __tablename__ = "telemetry_records"
    __table_args__ = {
        "postgresql_partition_by": "RANGE (time)",
    }

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    satellite_id = Column(UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False, index=True)
    
    time = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    
    packet_id = Column(BigInteger)
    apid = Column(Integer)
    
    timestamp_unix = Column(BigInteger)
    
    voltage_bus_v = Column(Float)
    current_bus_a = Column(Float)
    power_w = Column(Float)
    
    temp_battery_k = Column(Float)
    temp_platform_k = Column(Float)
    temp_instruments_k = Column(JSONB)
    
    storage_used_bytes = Column(BigInteger)
    storage_total_bytes = Column(BigInteger)
    
    data_rate_mbps = Column(Float)
    packets_lost = Column(Integer)
    
    mode = Column(String(30))
    error_flags = Column(Integer)
    
    cpu_utilization = Column(Float)
    memory_usage_bytes = Column(BigInteger)
    
    hk_summary = Column(JSONB)

    __table_args__ = (
        Index("ix_telemetry_satellite_time", "satellite_id", "time"),
    )


class TelemetryStatistics(Base):
    """Aggregated telemetry statistics (continuous aggregate)."""
    __tablename__ = "telemetry_statistics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    satellite_id = Column(UUID(as_uuid=True), ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False)
    
    bucket = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    interval = Column(String(20), nullable=False, primary_key=True)
    
    power_avg_w = Column(Float)
    power_min_w = Column(Float)
    power_max_w = Column(Float)
    
    temp_avg_k = Column(Float)
    temp_min_k = Column(Float)
    temp_max_k = Column(Float)
    
    data_rate_avg_mbps = Column(Float)
    data_rate_total_mb = Column(Float)
    
    storage_avg_pct = Column(Float)
    packets_lost_total = Column(BigInteger)
    
    uptime_s = Column(BigInteger)

    __table_args__ = (
        Index("ix_telemetry_stats_satellite_bucket", "satellite_id", "bucket"),
    )


# =============================================================================
# SCHEMA MANAGEMENT
# =============================================================================

def create_hypertable(engine, table_name: str, time_column: str, chunk_interval: str = "1 day"):
    """Create TimescaleDB hypertable from regular table."""
    sql = f"""
    SELECT create_hypertable('{table_name}', '{time_column}',
                             chunk_interval => INTERVAL '{chunk_interval}',
                             if_not_exists => TRUE);
    """
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()


def create_continuous_aggregate(
    engine,
    name: str,
    view_column: str,
    table_name: str,
    bucket: str = "1 hour"
):
    """Create continuous aggregate for downsampling."""
    sql = f"""
    SELECT add_continuous_aggregate_policy('{name}',
        start_offset => INTERVAL '1 week',
        end_offset => INTERVAL '1 hour',
        schedule_interval => INTERVAL '1 hour');
    """
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()


def get_database_url(
    host: str = "localhost",
    port: int = 5432,
    database: str = "sentryground",
    user: str = "postgres",
    password: Optional[str] = None
) -> str:
    """Build PostgreSQL connection URL."""
    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    else:
        return f"postgresql://{user}@{host}:{port}/{database}"


def setup_database(
    engine,
    create_hypertables: bool = True,
    create_aggregates: bool = True
):
    """Initialize database schema."""
    Base.metadata.create_all(engine)
    
    if create_hypertables:
        create_hypertable(engine, "orbital_states", "time", "1 day")
        create_hypertable(engine, "sensor_observations", "observation_time", "1 week")
        create_hypertable(engine, "telemetry_records", "time", "1 hour")
    
    if create_aggregates:
        sql_telemetry_stats = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_statistics
        WITH (timescaledb.continuous) AS
        SELECT satellite_id,
               time_bucket('1 hour', time) AS bucket,
               '1 hour' AS interval,
               AVG(power_w) AS power_avg_w,
               AVG(temp_platform_k) AS temp_avg_k,
               AVG(data_rate_mbps) AS data_rate_avg_mbps,
               SUM(data_rate_mbps * 3600.0) AS data_rate_total_mb
        FROM telemetry_records
        GROUP BY satellite_id, bucket;
        """
        with engine.connect() as conn:
            conn.execute(text("COMMIT"))
            try:
                conn.execute(text(sql_telemetry_stats))
                conn.commit()
            except Exception:
                pass


# =============================================================================
# QUERY HELPERS
# =============================================================================

def get_latest_orbital_state(session: Session, satellite_id: uuid.UUID) -> Optional[OrbitalState]:
    """Get most recent orbital state for satellite."""
    return session.query(OrbitalState).filter(
        OrbitalState.satellite_id == satellite_id
    ).order_by(
        OrbitalState.time.desc()
    ).first()


def get_satellite_passes(
    session: Session,
    satellite_id: uuid.UUID,
    start_time: datetime,
    end_time: datetime,
    ground_station_id: Optional[uuid.UUID] = None
) -> List[PassPrediction]:
    """Get scheduled passes for satellite in time range."""
    query = session.query(PassPrediction).filter(
        PassPrediction.satellite_id == satellite_id,
        PassPrediction.aos_time >= start_time,
        PassPrediction.aos_time <= end_time
    )
    
    if ground_station_id:
        query = query.filter(PassPrediction.ground_station_id == ground_station_id)
    
    return query.order_by(PassPrediction.aos_time).all()


def get_products_in_bbox(
    session: Session,
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    product_type: Optional[str] = None,
    limit: int = 100
) -> List[ScienceProduct]:
    """Get products within bounding box."""
    query = session.query(ScienceProduct).filter(
        ScienceProduct.center_lat_deg >= min_lat,
        ScienceProduct.center_lat_deg <= max_lat,
        ScienceProduct.center_lon_deg >= min_lon,
        ScienceProduct.center_lon_deg <= max_lon
    )
    
    if start_time:
        query = query.filter(ScienceProduct.start_time >= start_time)
    if end_time:
        query = query.filter(ScienceProduct.end_time <= end_time)
    if product_type:
        query = query.filter(ScienceProduct.product_type == product_type)
    
    return query.limit(limit).all()
