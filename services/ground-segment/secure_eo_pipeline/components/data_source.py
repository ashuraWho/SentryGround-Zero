import os  # For filesystem operations
import json  # To write metadata files
import subprocess
import time  # For timestamps
import numpy as np  # For synthetic image data
from typing import Optional
from datetime import datetime, timezone

from secure_eo_pipeline import config  # For directory paths
from secure_eo_pipeline.physics.observation_modes import apply_mode_2d
from secure_eo_pipeline.utils.logger import audit_log  # To record events

# =============================================================================
# Data Source Component (Simulator)
# =============================================================================
# ROLE IN ARCHITECTURE:
# This component acts as the "Satellite Instrument" (e.g., a high-res camera).
# It is responsible for creating the initial 'Raw Data' (Level-0) that enters
# the ground segment pipeline.
#
# WHY SIMULATE?
# Real Earth Observation (EO) data is often proprietary or extremely large.
# Simulation allows us to test the 'Security Logic' (how we handle the data)
# without needing access to a real multibillion-dollar satellite downlink.
# =============================================================================


def _find_monorepo_root() -> Optional[str]:
    """Locate repo root (contains services/space-segment/core_engine)."""
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        parent = os.path.dirname(d)
        if parent == d:
            return None
        if os.path.isdir(os.path.join(d, "services", "space-segment", "core_engine")):
            return d
        d = parent


def _synthetic_level0_array(mission_profile: str, observation_mode: str = "default") -> np.ndarray:
    """
    Build a 100×100×3 pseudo multispectral cube for the ground pipeline.
    Patterns mirror the space-segment MISSION_PROFILE science templates.
    """
    p = (mission_profile or "dark_matter").strip().lower()
    x = np.linspace(-5, 5, 100)
    y = np.linspace(-5, 5, 100)
    xx, yy = np.meshgrid(x, y)

    if p == "exoplanet":
        flux = 0.9 - 0.4 * np.exp(-0.5 * (x / 1.0) ** 2)
        noise = np.random.normal(0, 0.05, (100, 100))
        img = np.tile(flux, (100, 1)) + noise
    elif p in ("earth", "earth_observation"):
        terrain = np.sin(xx * 2.0) * np.cos(yy * 2.0) * 0.5 + 0.5
        noise = np.random.poisson(lam=2, size=(100, 100)) * 0.05
        img = terrain * 0.8 + noise
    elif p == "earth_climate":
        jj, ii = np.meshgrid(np.arange(100), np.arange(100), indexing="ij")
        jet = 0.18 * np.sin((jj + ii) * 0.38)
        base = np.sin(xx * 2.0) * np.cos(yy * 2.0) * 0.5 + 0.5
        clouds = (np.random.rand(100, 100) > 0.82) * 0.32
        img = np.clip(base * 0.52 + jet + clouds, 0, 1)
    elif p == "deep_space":
        img = np.random.rand(100, 100) * 0.08
        bright = np.random.rand(100, 100) > 0.97
        img = img + bright * np.random.uniform(0.45, 0.95, (100, 100))
    elif p == "stellar":
        r2 = xx**2 + yy**2
        core = np.exp(-r2 / 6.0) * 0.95
        ring = 0.12 * np.exp(-((np.sqrt(r2) - 2.8) ** 2) / 0.6)
        img = core + ring + np.random.rand(100, 100) * 0.08
    elif p == "black_hole":
        r = np.sqrt(xx**2 + yy**2)
        ring = 0.78 * np.exp(-((r - 2.9) ** 2) / 0.55)
        shadow = (r < 1.2).astype(np.float64) * 0.03
        img = ring + shadow + np.random.rand(100, 100) * 0.05
    elif p == "gravitational_wave":
        tx = np.linspace(0.0, 1.0, 100)
        phase = 2.0 * np.pi * tx * tx * 10.0
        wave = 0.48 + 0.22 * np.sin(phase)
        img = np.tile(wave, (100, 1)) + np.random.normal(0, 0.03, (100, 100))
    elif p == "asteroid":
        dx = (xx - 0.4) * 1.4
        dy = (yy + 0.2) * 1.0
        r = np.sqrt(dx**2 + dy**2)
        rugged = 0.35 * np.sin(dx * 4.2) * np.cos(dy * 3.1)
        img = np.where(r < 1.0, 0.52 + rugged, 0.12 + np.random.rand(100, 100) * 0.16)
        img = img + np.random.rand(100, 100) * 0.05
    elif p == "survey":
        r = np.sqrt(xx**2 + yy**2)
        rs = 2.0
        a = 0.5 / ((r / rs) * (1 + r / rs) ** 2 + 0.1)
        flux = 0.9 - 0.4 * np.exp(-0.5 * (x / 1.0) ** 2)
        b = np.tile(flux, (100, 1))
        c = np.sin(xx * 2.0) * np.cos(yy * 2.0) * 0.5 + 0.5
        r2 = xx**2 + yy**2
        d = np.exp(-r2 / 6.0)
        img = np.clip(0.25 * (a + b + c + d), 0, 1)
    else:
        r = np.sqrt(xx**2 + yy**2)
        r_s = 2.0
        signal = 0.5 / ((r / r_s) * (1 + r / r_s) ** 2 + 0.1)
        noise = np.random.poisson(lam=1, size=(100, 100)) * 0.05
        img = signal + noise

    img = np.clip(img.astype(np.float64), 0.0, 1.0)
    om = (observation_mode or "default").strip().lower()
    if om != "default":
        apply_mode_2d(img, p, om)
    return np.stack([img, img, img], axis=-1).astype(np.float32)


class EOSimulator:
    
    """
    Simulates the generation of synthetic satellite products.
    """

    def __init__(self):
        
        """
        Initializes the simulator and ensures the environment is ready.
        """
        
        # Step 1: Ensure the "Landing Zone" (Ingest Directory) exists on the disk.
        # This is where the satellite "beams down" its initial files.
        if not os.path.exists(config.INGEST_DIR):  # Checks if ingest directory exists
            # If the directory is missing, create it automatically.
            os.makedirs(config.INGEST_DIR)
            
            
            
    def generate_product(self, product_id, corrupted=False):
        
        """
        Creates a new synthetic product consisting of a binary data file and a metadata file.
        
        ARGUMENTS:
            product_id (str): A unique string to identify this specific image capture.
            corrupted (bool): A flag used for testing. If True, the data will contain 
                              invalid 'NaN' values to test Quality Control detection.
        """
        
        # Step 1: Log the start of the generation process for auditing purposes
        audit_log.info(f"[SOURCE] START: Generating simulated satellite product: {product_id}")
        
        # Step 2: Input Validation - Ensure the product_id is a valid string
        if not isinstance(product_id, str) or len(product_id) == 0:  # Checks that `product_id` is a non-empty string
            # If the ID is invalid, log an error and stop.
            audit_log.error("[SOURCE] FAILED: Invalid product_id provided.")
            return None  # Returns None to indicate failure

        # Step 3: DATA SIMULATION (The Image)
        # We generate a 3D matrix (100x100 pixels, with 3 spectral bands/colors).
        # RATIONALE: This mimics the multi-spectral format used by missions like Sentinel-2.
        data = np.random.rand(100, 100, 3).astype(np.float32)  # Creates a random float array
        
        # Step 4: ERROR INJECTION (Simulation only)
        # If the 'corrupted' flag is set, we overwrite one pixel with 'NaN' (Not a Number).
        # RATIONALE: This allows us to verify that our 'Processing' component can 
        # detect and reject faulty sensor data later in the pipeline.
        if corrupted:  # Checks the `corrupted` flag
            # We target a single pixel in the first band
            data[50, 50, 0] = np.nan  # Injects NaN into a single pixel
            
        # Step 5: FILESYSTEM PATH DEFINITION
        # The product consists of two files: a .npy (binary data) and a .json (description).
        file_name = f"{product_id}.npy"  # Defines the `.npy` file name
        # We join the path with our configured Ingest Directory
        file_path = os.path.join(config.INGEST_DIR, file_name)  # Builds the data file path
        meta_path = os.path.join(config.INGEST_DIR, f"{product_id}.json")  # Defines the metadata file path
        
        # Step 6: BINARY STORAGE
        # Save the NumPy array to a binary file on the local disk.
        # .npy is an efficient format for storing large numerical datasets.
        np.save(file_path, data)  # Saves the array to disk
        
        # Step 7: METADATA GENERATION (The Digital Label)
        # Metadata is critical for security and provenance.
        # It answers: When was this taken? By what sensor? Where in orbit?
        metadata = {  # Starts metadata dictionary
            "product_id": product_id,
            "timestamp": time.time(), # Recording the exact moment of generation
            "sensor": "Simulated-HyperSpectral-1", # Identifying the "Source of Truth"
            "orbit": 1234, # Simulated orbit number
            # Scientific metric (Randomly generated for realism)
            "cloud_cover_percentage": np.random.uniform(0, 100)
        }
        
        # Step 8: METADATA STORAGE
        # Serialize the metadata dictionary into a human-readable JSON file.
        # indent=4 makes the file easier for human operators to inspect.
        with open(meta_path, "w") as f:  # Opens metadata file for writing
            json.dump(metadata, f, indent=4)  # Dumps metadata to JSON with indentation
            
        # Step 9: COMPLETION LOGGING
        # Log that the data has successfully landed and is ready for the next stage (Ingestion).
        audit_log.info(f"[SOURCE] SUCCESS: Product files saved to: {config.INGEST_DIR}")  # Logs success event
        
        # Return the path to the binary file to the caller
        return file_path  # Returns the data file path

class SpaceSegmentReceiver:
    """
    Receives and processes downlinked telemetry directly from the SentrySat C++ pipeline.
    Acts as the physical bridge between the simulated space segment and the ground segment.
    """
    def __init__(self):
        if not os.path.exists(config.INGEST_DIR):
            os.makedirs(config.INGEST_DIR)
            
    def generate_product(
        self,
        product_id: str,
        corrupted: bool = False,
        target_host: Optional[str] = None,
        observation_mode: str = "default",
    ) -> Optional[str]:
        """
        Connects to the SentrySat space segment to trigger an acquisition and
        receives the telemetry stream (simulated).
        
        Args:
            product_id (str): The logical name for the mission dataset.
            corrupted (bool): Set to true to mock external data corruption
            target_host (str): Optional. The specific satellite node in the constellation to query.
        """
        audit_log.info(f"[SOURCE] Connecting to Space Segment for product {product_id}...")

        repo_root = _find_monorepo_root()
        sentry_bin = (
            os.path.join(repo_root, "services", "space-segment", "core_engine", "build", "sentry_sat_sim")
            if repo_root
            else None
        )

        space_host = target_host or os.getenv("SPACE_SEGMENT_HOST")
        mission_profile = "dark_matter"
        mode_q = (observation_mode or "default").strip().lower()

        try:
            if space_host:
                import urllib.parse
                import urllib.request

                q = urllib.parse.urlencode({"mode": mode_q})
                url = f"http://{space_host}:8080/scan?{q}"
                with urllib.request.urlopen(url) as response:
                    output = response.read()
                    mission_profile = (
                        response.getheader("X-Mission-Profile", "dark_matter") or "dark_matter"
                    ).strip().lower()
                    hdr_mode = response.getheader("X-Observation-Mode")
                    if hdr_mode:
                        mode_q = hdr_mode.strip().lower()
            else:
                if not sentry_bin or not os.path.isfile(sentry_bin):
                    audit_log.error(
                        "[SOURCE] No SPACE_SEGMENT_HOST and local sentry_sat_sim not found. "
                        "Set SPACE_SEGMENT_HOST or build services/space-segment/core_engine."
                    )
                    return None
                env = os.environ.copy()
                if repo_root is None:
                    audit_log.error("[SOURCE] repo_root is unexpectedly None")
                    return None
                meta_path = os.path.join(
                    repo_root, "services", "space-segment", "ai_training", "obc_model_meta.json"
                )
                env["SENTRY_OBC_META"] = meta_path
                env["OBSERVATION_MODE"] = mode_q

                result = subprocess.run(
                    [sentry_bin], capture_output=True, env=env, cwd=os.path.dirname(sentry_bin)
                )
                if result.returncode != 0:
                    audit_log.error(
                        f"[SOURCE] SentrySat execution failed. Code: {result.returncode}\nStderr: {result.stderr}"
                    )
                    return None
                output = result.stdout
        except Exception as e:
            audit_log.error(f"[SOURCE] FAILED: Could not retrieve SentrySat telemetry. Error: {e}")
            return None
            
        # Parse the binary CCSDS telemetry stream
        telemetry = None
        # SentrySat CCSDS Space Packets use a Sync Marker: 1A CF FC 1D
        sync_marker = b'\x1a\xcf\xfc\x1d'
        
        if sync_marker in output:
            packets = output.split(sync_marker)[1:]  # Ignore text logged before first sync
            
            # Use the first full packet found
            for pkt in packets:
                if len(pkt) < 6:
                    continue  # Incomplete header
                    
                # The CCSDS primary header is 6 bytes long.
                # Packet Data Length is at bytes 4-5 (0-indexed). length = len(payload) - 1
                payload_len = int.from_bytes(pkt[4:6], byteorder='big') + 1
                
                if len(pkt) >= 6 + payload_len:
                    payload_bytes = pkt[6:6+payload_len]
                    try:
                        telemetry = json.loads(payload_bytes.decode('utf-8'))
                        # Valid telemetry found! Exit parsing loop.
                        break
                    except json.JSONDecodeError:
                        pass
        
        if not telemetry:
            audit_log.error("[SOURCE] FAILED: No valid CCSDS telemetry packets found in SentrySat binary stream.")
            return None

        # Build metadata based on the SentrySat telemetry
        metadata = {
            "product_id": product_id,
            "mission_profile": mission_profile.strip().lower(),
            "observation_mode": mode_q,
            "timestamp": telemetry.get("timestamp_utc"),
            "sensor": "Sentry-Optical-Payload",
            "signature_hex": telemetry.get("hardware_signature"),
            "anomaly": telemetry.get("ai_anomaly_flag"),
            "inference_mse": telemetry.get("inference_mse"),
            "inference_backend": telemetry.get("inference_backend"),
        }
        
        # Try to add orbital state from constellation catalog
        try:
            from secure_eo_pipeline.constellation_catalog import spec_for_host
            from secure_eo_pipeline.physics.orbital import (
                get_current_position, orbital_period, orbital_regime, orbital_velocity
            )
            
            spec = spec_for_host(target_host or "")
            if spec and spec.orbital_elements:
                oe = spec.orbital_elements
                pos = get_current_position(
                    oe.semimajor_axis_km, oe.eccentricity, oe.inclination_deg,
                    oe.raan_deg, oe.arg_perigee_deg, oe.mean_anomaly_deg
                )
                metadata["orbital_state"] = {
                    "regime": orbital_regime(oe.semimajor_axis_km),
                    "semimajor_axis_km": oe.semimajor_axis_km,
                    "eccentricity": oe.eccentricity,
                    "inclination_deg": oe.inclination_deg,
                    "raan_deg": oe.raan_deg,
                    "arg_perigee_deg": oe.arg_perigee_deg,
                    "perigee_km": oe.perigee_km,
                    "apogee_km": oe.apogee_km,
                    "period_min": orbital_period(oe.semimajor_axis_km),
                    "current_lat_deg": pos.lat_deg,
                    "current_lon_deg": pos.lon_deg,
                    "current_alt_km": pos.alt_km,
                    "velocity_km_s": orbital_velocity(oe.semimajor_axis_km, oe.eccentricity),
                    "observation_time_utc": datetime.now(timezone.utc).isoformat(),
                }
        except Exception:
            pass

        data = _synthetic_level0_array(mission_profile, observation_mode=mode_q)
        
        if corrupted:
            # Malware attempts to hide the Dark Matter signal by injecting a flat blackout box.
            # This causes a massive Laplacian gradient spike which the Physics-IDS will catch.
            data[40:60, 40:60, :] = 0.0 
            
        file_name = f"{product_id}.npy"
        file_path = os.path.join(config.INGEST_DIR, file_name)
        meta_path = os.path.join(config.INGEST_DIR, f"{product_id}.json")
        
        np.save(file_path, data)
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=4)
            
        audit_log.info(f"[SOURCE] SUCCESS: SentrySat Product files downlinked to: {config.INGEST_DIR}")
        return file_path
