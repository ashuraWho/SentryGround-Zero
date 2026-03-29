# Sentry-Ground Zero: Unified Makefile

.PHONY: all build-space run-ground test-all clean install-deps

all: build-space install-deps

install-deps:
	@echo "Installing python dependencies for EO_DataSecurity..."
	cd EO_DataSecurity && python3 -m pip install -r requirements.txt

build-space:
	@echo "Building SentrySat C++ Engine (Space Segment)..."
	cmake -S SentrySat/core_engine -B SentrySat/core_engine/build -DSENTRY_ALLOW_DUMMY_MAC=ON
	cmake --build SentrySat/core_engine/build --parallel

run-ground: build-space
	@echo "Launching EO_DataSecurity Command Center (Ground Segment)..."
	cd EO_DataSecurity && python3 main.py

test-all: build-space install-deps
	@echo "Running SentrySat C++ Tests..."
	cd SentrySat && ctest --test-dir core_engine/build --output-on-failure
	@echo "Running EO_DataSecurity Python Tests..."
	cd EO_DataSecurity && make test || python3 -m pytest tests/ -v

clean:
	@echo "Cleaning up build artifacts and simulation data..."
	rm -rf SentrySat/core_engine/build
	rm -rf EO_DataSecurity/simulation_data
	rm -rf EO_DataSecurity/__pycache__
	rm -rf EO_DataSecurity/secure_eo_pipeline/__pycache__
	rm -f EO_DataSecurity/audit.log
	rm -f EO_DataSecurity/secure_eo_pipeline.db
