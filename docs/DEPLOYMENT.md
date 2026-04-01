# SentryGround-Zero Deployment Guide

## Overview

SentryGround-Zero is a comprehensive satellite monitoring system that integrates all scientific domains: Astrophysics, cosmology, dark matter, gravitational waves, black holes, asteroids, stars, exoplanets, Earth observation, data security, cybersecurity, AI/ML/DL, and HPC.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SentryGround-Zero                             │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Deep Space  │  │ Dark Matter│  │Earth Obs   │  │ Exoplanet   │    │
│  │   Satellites│  │  Satellites │  │ Satellites  │  │  Satellites │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │                │            │
│  ┌──────┴────────────────┴────────────────┴────────────────┴──────┐    │
│  │                      Ground Segment                           │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │    │
│  │  │ REST API    │  │ WebSocket   │  │ Streamlit   │            │    │
│  │  │ (FastAPI)   │  │ Server      │  │ Dashboard   │            │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘            │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │    │
│  │  │ CLI/TUI     │  │ SIEM       │  │ ML Models   │            │    │
│  │  │ Terminal    │  │ Integration │  │             │            │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘            │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                              │                                         │
│  ┌──────────────────────────┴───────────────────────────────┐        │
│  │                    PostgreSQL + TimescaleDB               │        │
│  │                 (Telemetry & Time-Series Data)           │        │
│  └──────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended)
- 50GB disk space

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/SentryGround-Zero.git
cd SentryGround-Zero
```

### 2. Environment Configuration

Create a `.env` file:

```bash
# PostgreSQL Configuration
POSTGRES_PASSWORD=your_secure_password_here

# Optional: Custom domain
DOMAIN=localhost
```

### 3. Build and Start

```bash
# Build all services
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### 4. Access Services

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Web Dashboard | https://localhost:8501 | admin/admin123 |
| REST API | https://localhost:8080/api/v1 | admin/admin123 |
| CLI Terminal | `docker exec -it sentryground-zero-ground-segment-1 python -m cli.terminal` | admin/admin123 |

## Services

### Ground Segment

The main ground segment service runs:
- **FastAPI REST API** - Satellite telemetry, orbital mechanics, physics simulations
- **WebSocket Server** - Real-time telemetry streaming
- **CLI Terminal** - ESA/NASA-style command interface
- **Streamlit Dashboard** - Web-based monitoring interface

### Space Satellites

Ten specialized satellite containers, each for a different scientific domain:

| Satellite | Profile | Port | Purpose |
|-----------|---------|------|---------|
| sentry-deep-space | Deep Space | 8080 | Interplanetary monitoring |
| sentry-dark-matter | Dark Matter | 8081 | Dark matter detection |
| sentry-earth-obs | Earth Observation | 8082 | Planet monitoring |
| sentry-exoplanet | Exoplanet | 8083 | Exoplanet detection |
| sentry-stellar | Stellar | 8084 | Stellar observations |
| sentry-black-hole | Black Hole | 8085 | Black hole studies |
| sentry-gravitational-wave | Gravitational Wave | 8086 | LIGO-style GW detection |
| sentry-asteroid | Asteroid | 8087 | Planetary defense |
| sentry-earth-climate | Earth Climate | 8088 | Climate simulation |
| sentry-survey | Survey | 8089 | All-sky survey |

### Database

- **PostgreSQL 15** with TimescaleDB extension
- TimescaleDB hypertables for time-series telemetry data
- Automatic data retention policies

### Nginx Reverse Proxy

- HTTPS termination with TLS 1.2/1.3
- Rate limiting (10 req/s API, 1 req/s login)
- Security headers (HSTS, CSP, X-Frame-Options)
- WebSocket support

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_PASSWORD` | secure_password_123 | PostgreSQL password |
| `USE_SQLITE` | 1 | Use SQLite instead of PostgreSQL |
| `USE_ML` | 1 | Enable ML models |
| `ENABLE_HTTPS` | 1 | Enable HTTPS |
| `PG_HOST` | db | PostgreSQL host |
| `PG_USER` | sentry_admin | PostgreSQL user |

### SSL Certificates

The `certs` service automatically generates self-signed certificates on first run. For production, replace with proper certificates:

```bash
# Copy your certificates
cp your-cert.crt services/ground-segment/certs/server.crt
cp your-cert.key services/ground-segment/certs/server.key
```

## Security Features

### Authentication

- JWT-based authentication with refresh tokens
- TOTP two-factor authentication support
- Role-based access control (admin, operator, analyst, guest)

### SIEM Integration

Built-in Security Information and Event Management:
- **Elastic Security** connector
- **Splunk** connector  
- **Syslog** forwarding
- Real-time threat intelligence feed
- Alert and incident management

### Network Security

- NetworkPolicy for pod isolation (Kubernetes)
- Rate limiting on all endpoints
- Input sanitization and validation
- SQL injection and XSS protection

## Monitoring

### Health Checks

```bash
# Check all services
curl https://localhost/health

# Check specific service
curl https://localhost:8080/api/v1/health
```

### Metrics

Prometheus metrics available at:
- Ground Segment: `http://localhost:8080/metrics`
- Kubernetes: Configured in `k8s/monitoring/`

### Logging

```bash
# View logs
docker-compose logs -f ground-segment

# View specific service
docker-compose logs -f nginx-proxy
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- Helm 3.0+
- kubectl configured

### Deploy

```bash
# Apply manifests
kubectl apply -f k8s/manifests.yaml

# Check status
kubectl get pods -n sentryground-zero

# View services
kubectl get svc -n sentryground-zero
```

### Monitoring Stack

```bash
# Deploy Prometheus + Grafana
kubectl apply -f k8s/monitoring/prometheus.yaml
kubectl apply -f k8s/monitoring/grafana.yaml
```

## Development

### Local Development

```bash
# Start services without Docker
cd services/ground-segment
pip install -r requirements.txt
python main.py
```

### Running Tests

```bash
cd services/ground-segment
python -m pytest tests/ -v

# Run only unit tests (no external services)
python -m pytest tests/ -v -m "not e2e"
```

### CLI Terminal

```bash
cd services/ground-segment
python -m cli.terminal
```

Commands:
- `help` - Show all commands
- `satellites` - Show satellite status
- `status` - Show system metrics
- `map` - Show ground track map
- `security` - Show security status
- `pipeline` - Show pipeline status
- `login` - Authenticate
- `exit` - Exit terminal

## API Documentation

OpenAPI specification available at:
- https://localhost:8080/docs (Swagger UI)
- https://localhost:8080/openapi.json (OpenAPI JSON)

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs ground-segment

# Rebuild
docker-compose build ground-segment
docker-compose up -d ground-segment
```

### Database Connection Issues

```bash
# Check database health
docker-compose exec db pg_isready -U sentry_admin

# Connect to database
docker-compose exec db psql -U sentry_admin -d eo_security
```

### SSL Certificate Issues

```bash
# Regenerate certificates
docker-compose rm -f certs
docker-compose up -d certs
```

## License

Proprietary - All rights reserved

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/SentryGround-Zero/issues
- Documentation: https://docs.sentryground-zero.example.com
