# SentryGround-Zero Documentation

Welcome to SentryGround-Zero, a comprehensive satellite monitoring and Earth observation system that integrates astrophysics, cosmology, planetary science, and climate modeling.

## Overview

SentryGround-Zero is a simulation framework for satellite operations that includes:

- **Orbital Mechanics**: SGP4 propagation, ground tracks, pass prediction
- **Astrophysics**: Coordinate transforms, photometry, stellar physics
- **Gravitational Waves**: LIGO-style detection and parameter estimation
- **Exoplanets**: Transit photometry, atmospheric spectra, habitable zones
- **Dark Matter**: NFW profiles, direct/indirect detection
- **Black Holes**: Kerr metrics, accretion disks, Hawking radiation
- **Cosmology**: N-body simulations, Bolshoi-style ICs, structure formation
- **Planetary Defense**: NEO catalog, impact prediction, deflection strategies
- **Climate Science**: Energy balance, ocean circulation, carbon cycle

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/SentryGround-Zero.git
cd SentryGround-Zero

# Install dependencies
make install-deps

# Build space segment
make build-space

# Run tests
make test
```

## Quick Start

### Using Docker

```bash
docker-compose up --build -d
docker attach sentryground-zero-ground-segment-1
```

### Local Development

```bash
# Ground segment
cd services/ground-segment
python main.py

# Space segment
cd services/space-segment
./core_engine/build/sentry_sat_sim
```

## Modules

### Physics Module (`secure_eo_pipeline/physics/`)

The physics module contains all scientific computation:

- `orbital.py` - Orbital mechanics
- `astronomy.py` - Astrophysics utilities
- `gravitational_waves.py` - GW physics
- `exoplanets.py` - Exoplanet science
- `dark_matter.py` - Dark matter physics
- `black_holes.py` - Black hole physics
- `cosmology_sim.py` - Cosmological simulations
- `planetary_defense.py` - NEO and impact analysis
- `climate_ocean.py` - Climate and ocean models

### Database Module (`secure_eo_pipeline/database/`)

PostgreSQL/TimescaleDB models for:

- Satellite catalog
- Orbital state history
- Telemetry time-series
- Science products

### Streaming Module (`secure_eo_pipeline/streaming/`)

Real-time WebSocket server for:

- Satellite position streaming
- Telemetry broadcasts
- Pass event notifications

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Space Segment (C++)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  OBC Loop   │  │  ML Engine  │  │  Telemetry  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Ground Segment (Python)                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │  CLI    │  │Dashboard│  │Physics  │  │ Database │  │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │
└─────────────────────────────────────────────────────────┘
```

## API Reference

### Physics Functions

#### Orbital Mechanics

```python
from secure_eo_pipeline.physics import propagate_orbit, orbital_period

# Calculate orbital period
period = orbital_period(semi_major_axis_km=7000)

# Propagate orbit
state = propagate_orbit(orbital_elements, julian_date)
```

#### Gravitational Waves

```python
from secure_eo_pipeline.physics import generate_chirp_timeseries

times, h_plus, h_cross = generate_chirp_timeseries(
    m1=30.0, m2=25.0, distance_mpc=410.0
)
```

#### Climate Science

```python
from secure_eo_pipeline.physics import ClimateSimulation

sim = ClimateSimulation()
sim.step(dt_years=1.0)
print(sim.get_state())
```

## License

MIT License
