import os  # For filesystem operations
import json  # To write metadata files
import time  # For timestamps
import numpy as np  # For synthetic image data

from secure_eo_pipeline import config  # For directory paths
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
