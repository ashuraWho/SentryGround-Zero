import os  # For filesystem operations
import json  # For metadata parsing
import numpy as np  # For data processing

from secure_eo_pipeline import config  # For paths
from secure_eo_pipeline.utils import security  # For hashing
from secure_eo_pipeline.utils.logger import audit_log  # For event logging
from secure_eo_pipeline.ml import features as ml_features
from secure_eo_pipeline.ml import models as ml_models

# =============================================================================
# Processing & Quality Control Component
# =============================================================================
# ROLE IN ARCHITECTURE:
# The "Scientific Factory".
# This component takes raw Level-0 data (raw signals) and converts them into
# Level-1 products (calibrated reflectance values).
#
# SECURITY & TRUST:
# Processing is the moment where data changes. In a secure pipeline, we must
# ensure that the data we are processing hasn't been tampered with since ingestion.
#
# QC (QUALITY CONTROL):
# We check for sensor malfunctions (NaN values) to ensure data 'Cleanliness'.
# =============================================================================

class ProcessingEngine:
    
    """
    Handles the scientific transformation and quality assurance of EO data.
    """

    def process_product(self, product_id):
        
        """
        Executes a Level-0 to Level-1 processing chain.
        
        ARGUMENTS:
            product_id (str): The unique ID of the product currently in staging.
        """
        
        # Step 1: Define paths to the input files within the Processing Staging area
        input_file = os.path.join(config.PROCESSING_DIR, f"{product_id}.npy")  # Builds input data path
        input_meta = os.path.join(config.PROCESSING_DIR, f"{product_id}.json")  # Builds input metadata path
        
        # Step 2: Log the start of the processing session
        audit_log.info(f"[PROCESS] START: Processing Level-0 -> Level-1 for {product_id}")  # Logs processing start
        
        # ---------------------------------------------------------------------
        # PHASE 1: INTEGRITY VERIFICATION (Chain of Custody)
        # ---------------------------------------------------------------------
        # Before we touch the data, we must prove it is the SAME data that was ingested.
        try:  # Starts try block for integrity
            # Step 1: Read the metadata to find the "Expected Hash"
            with open(input_meta, "r") as f:  # Opens metadata file
                meta = json.load(f)  # Loads metadata JSON
            
            # Step 2: Retrieve the hash recorded by the Ingestion component
            expected_hash = meta.get("original_hash")  # Reads `original_hash` from metadata
            
            # Step 3: Calculate the ACTUAL hash of the file right now
            actual_hash = security.calculate_hash(input_file)  # Calculates current hash of data file
            
            # Step 4: Compare. If they don't match, someone edited the file illegally!
            if actual_hash != expected_hash:  # Compares current hash to expected hash
                audit_log.error(f"[PROCESS] SECURITY ALERT: Input integrity mismatch for {product_id}!")  # Logs security alert if mismatch
                # STOP: Do not process tampered data.
                return None  # Returns None to stop processing
        except Exception as e:
            # Handle cases where files are missing or metadata is corrupted
            audit_log.error(f"[PROCESS] FAILED: Could not verify input integrity. Error: {e}")  # Logs integrity verification failure
            return None  # Returns None to stop processing

        # ---------------------------------------------------------------------
        # PHASE 2: DATA LOADING & QUALITY CONTROL (QC)
        # ---------------------------------------------------------------------
        try:  # Starts try block for data load
            # Step 1: Load the binary scientific data into memory (as a NumPy array)
            data = np.load(input_file)  # Loads NumPy array
            
            # Step 2: Perform the "Cleanliness" Check (Quality Control)
            # Sensors sometimes fail and produce 'Not a Number' (NaN) values.
            # RATIONALE: We don't want to waste storage space on garbage data.
            if np.isnan(data).any():  # Checks for NaN values
                # If even one pixel is NaN, we flag it as a Quality Failure.
                audit_log.warning(f"[QC] REJECTED: Sensor corruption (NaN) detected in product {product_id}.")  # Logs a QC warning if NaN present
                # Fail the processing step.
                return None
                
        except Exception as e:
            # Handle file read errors or memory issues
            audit_log.error(f"[PROCESS] FAILED: Data load error for {product_id}. Error: {e}")  # Logs data load error
            return None

        # ---------------------------------------------------------------------
        # PHASE 3: SCIENTIFIC TRANSFORMATION
        # ---------------------------------------------------------------------
        # Simulation: Radiometric Calibration.
        # We normalize raw sensor values into a 0.0 to 1.0 reflectance range.
        # If the data is already in [0, 1], we keep it as-is.
        if data.dtype.kind in ("i", "u"):  # Checks whether data is integer type
            # Integer data (0-255) is scaled to floating reflectance
            processed_data = data.astype(np.float32) / 255.0  # Converts integer data to float and scales
        else:
            # Float data: only scale if values exceed the expected reflectance range
            max_val = float(np.nanmax(data))  # Computes maximum value ignoring NaN
            if max_val > 1.0:  # Checks if data exceeds expected range
                processed_data = data / 255.0  # Scales down values if needed
            else:  
                processed_data = data  # Uses data directly
        
        # Clamp the values to a valid range to avoid negative or >1 artifacts
        processed_data = np.clip(processed_data, 0.0, 1.0)  # Clamps values to [0, 1]
        
        # Optional: ML-based anomaly/quality scoring on the processed data
        if getattr(config, "USE_ML", False):
            try:
                feat = ml_features.extract_eo_features(processed_data)
                score, reason = ml_models.eo_anomaly_score(feat)
                meta["ml_score"] = score
                meta["ml_flag"] = "OK" if score == 0.0 else "ANOMALOUS"
                meta["ml_reason"] = reason
                meta["ml_model"] = "threshold_eo_v1"
                audit_log.info(
                    f"[ML] EO anomaly score for {product_id}: {score:.3f} (flag={meta['ml_flag']}, reason={reason})"
                )
            except Exception as e:
                audit_log.warning(f"[ML] EO anomaly scoring failed for {product_id}: {e}")

        # Step 1: Overwrite the binary file in the staging area with the NEW processed version.
        np.save(input_file, processed_data)  # Saves processed data to the same file
        
        # ---------------------------------------------------------------------
        # PHASE 4: PROVENANCE TRACKING (Updating the Record)
        # ---------------------------------------------------------------------
        # Since the file content has changed, we must document the transformation.
        
        # Step 1: Record the new processing level and status
        meta["processing_level"] = "Level-1C" # The product has been calibrated
        meta["status"] = "PROCESSED"  # Sets status to PROCESSED
        meta["qc_status"] = "PASSED"  # Sets QC status to PASSED
        
        # Step 2: CALCULATE A NEW HASH.
        # RATIONALE: The old hash is no longer valid because the content is different.
        # We need a new "Digital Signature" for the Level-1 product.
        new_hash = security.calculate_hash(input_file)  # Calculates new hash for processed data
        # We store this as the "Processed Hash" to maintain the Chain of Custody.
        meta["processed_hash"] = new_hash  # Stores processed hash in metadata
        
        # Step 3: Save the updated metadata back to disk
        with open(input_meta, "w") as f:  # Writes updated metadata to JSON
            json.dump(meta, f, indent=4)
            
        # Step 4: Finalize the log for the audit trail
        audit_log.info(f"[PROCESS] SUCCESS: {product_id} is now Level-1 certified. New Hash: {new_hash}")  # Logs processing success
        
        # Return the path to the processed product
        return input_file
