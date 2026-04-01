FROM python:3.11-slim

# Install system dependencies required for psycopg2, cryptograpy, and Fortran HPC building
RUN apt-get update && apt-get install -y \
    gcc \
    gfortran \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Install all pip requirements including the ML and Postgres modules
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Ground Segment source
COPY . /app

# Compile the high-performance Fortran 90 physics extension natively
WORKDIR /app/secure_eo_pipeline/physics
RUN python3 -m numpy.f2py -c astro_physics.f90 -m fortran_validator
WORKDIR /app

# Guarantee module resolution
ENV PYTHONPATH=/app

# Start the ESA-style interactive Mission Control CLI
CMD ["python3", "main.py"]
