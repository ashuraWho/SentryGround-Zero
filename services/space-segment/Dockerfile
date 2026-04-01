FROM ubuntu:22.04

# Install build dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    g++ \
    make \
    python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# Copy the Space Segment source into the container
COPY . /app

# Build the C++ simulator with Dummy MAC enabled for the showcase
WORKDIR /app/core_engine
RUN cmake -B build -DSENTRY_ALLOW_DUMMY_MAC=ON
RUN cmake --build build --parallel

WORKDIR /app
# Run the simple API server to stream binary output on demand
EXPOSE 8080
CMD ["python3", "sentry_api.py"]
