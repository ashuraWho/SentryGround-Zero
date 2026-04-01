# Sentry-Ground Zero: Unified Makefile

.PHONY: all build-space run-ground test-all clean install-deps

all: build-space install-deps

install-deps:
	@echo "Installing python dependencies for EO_DataSecurity..."
	cd services/ground-segment && python3 -m pip install -r requirements.txt

build-space:
	@echo "Building SentrySat C++ Engine (Space Segment)..."
	cmake -S services/space-segment/core_engine -B services/space-segment/core_engine/build -DSENTRY_ALLOW_DUMMY_MAC=ON
	cmake --build services/space-segment/core_engine/build --parallel

run-ground: build-space
	@echo "Launching EO_DataSecurity Command Center (Ground Segment)..."
	cd services/ground-segment && python3 main.py

test-all: build-space install-deps
	@echo "Running SentrySat C++ Tests..."
	cd services/space-segment && ctest --test-dir core_engine/build --output-on-failure
	@echo "Running EO_DataSecurity Python Tests..."
	cd services/ground-segment && make test || python3 -m pytest tests/ -v

clean:
	@echo "Cleaning up build artifacts and simulation data..."
	rm -rf services/space-segment/core_engine/build
	rm -rf services/ground-segment/simulation_data
	rm -rf services/ground-segment/__pycache__
	rm -rf services/ground-segment/secure_eo_pipeline/__pycache__
	rm -f services/ground-segment/audit.log
	rm -f services/ground-segment/secure_eo_pipeline.db
