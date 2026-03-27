import os  # For filesystem operations
import json  # For metadata parsing
import shutil  # For file copying
from typing import Optional

from secure_eo_pipeline import config  # For directory paths
from secure_eo_pipeline.utils import security  # For hashing
from secure_eo_pipeline.utils.logger import audit_log  # For event logging

# =============================================================================
# Secure Ingestion Component
# =============================================================================
# ROLE IN ARCHITECTURE:
# The "Border Guard" / "Customs Officer".
# All data entering from the 'Data Source' (Space Segment) is considered
# "Untrusted" until it passes through this component.
#
# SECURITY PRINCIPLES:
# 1. Input Validation: Reject malformed or dangerous data before it is processed.
# 2. Integrity Baselining: Capture a "Source of Truth" hash immediately.
# 3. Secure Handover: Move data from the Landing Zone to the Internal Staging.
# =============================================================================


class IngestionManager:
    
    """
    Handles the secure intake and validation of newly arrived EO products.
    """

    def ingest_product(self, product_id: str) -> Optional[str]:
        
        """
        Validates, fingerprints, and registers a product for internal use.
        
        ARGUMENTS:
            product_id (str): The unique identifier of the product to ingest.
            
        RETURNS:
            str: The new path to the ingested file, or None if validation fails.
        """
        
        # Step 1: Log the start of the ingestion request
        audit_log.info(f"[INGEST] START: Received ingestion request for product {product_id}")  # Logs start of ingestion
        
        # Step 2: Define expected source paths in the Landing Zone (Untrusted)
        source_file = os.path.join(config.INGEST_DIR, f"{product_id}.npy")  # Builds the data file path
        source_meta = os.path.join(config.INGEST_DIR, f"{product_id}.json")  # Builds the metadata file path
        
        # ---------------------------------------------------------------------
        # PHASE 1: EXISTENCE VALIDATION
        # ---------------------------------------------------------------------
        # Check: Did both the binary data AND the metadata file arrive?
        if not os.path.exists(source_file) or not os.path.exists(source_meta):  # Checks for both data and metadata files
            # Log a critical failure if part of the product is missing
            audit_log.error(f"[INGEST] FAILED: Incomplete product. Missing files for {product_id}.")  # Logs missing file error
            return None  # Returns None to stop ingestion
            
        # ---------------------------------------------------------------------
        # PHASE 2: SCHEMA VALIDATION (Content Integrity)
        # ---------------------------------------------------------------------
        # We must ensure the metadata isn't "poisoned" or malformed.
        try:  # Starts a try block for JSON parsing
            # Step 1: Open and parse the JSON metadata
            with open(source_meta, "r") as f:  # Opens metadata file
                meta = json.load(f)  # Parses JSON into `meta`
                
            # Step 2: Define the "Minimum Viable Metadata" (MVM)
            # RATIONALE: If these keys are missing, our processing engine won't know what to do.
            required_keys = ["product_id", "timestamp", "sensor"]  # Defines `required_keys` list
            
            # Step 3: Check if all mandatory keys exist in the provided file
            if not all(key in meta for key in required_keys):  # Verifies all required keys exist
                # If any are missing, the file is invalid.
                raise ValueError(f"Missing mandatory fields: {set(required_keys) - set(meta.keys())}")  # Raises a ValueError if missing fields
                
        except (json.JSONDecodeError, ValueError) as e:  # Starts exception handling
            # Catch bad formatting or missing fields and log the specific reason
            audit_log.error(f"[INGEST] FAILED: Schema validation failed for {product_id}. Error: {e}")
            # STOP the pipeline here. Do not let invalid data proceed.
            return None

        # ---------------------------------------------------------------------
        # PHASE 3: INTEGRITY BASELINING (Digital Fingerprinting)
        # ---------------------------------------------------------------------
        # This is the most critical step for security.
        # We calculate the SHA-256 hash of the binary data at the moment of arrival.
        # RATIONALE: This hash becomes the "Legal Signature" of the file.
        file_hash = security.calculate_hash(source_file)  # Calculates SHA-256 hash of the data file
        
        # We embed this hash INSIDE the metadata.
        # This "binds" the data file to its metadata record.
        meta["original_hash"] = file_hash  # Stores the hash in metadata
        # Update the status to reflect that it has been checked
        meta["status"] = "INGESTED"  # Sets status to INGESTED
        
        # ---------------------------------------------------------------------
        # PHASE 4: SECURE HANDOVER (Isolation)
        # ---------------------------------------------------------------------
        # Once validated, we move the data to a "Trusted" processing zone.
        # RATIONALE: We want to empty the Landing Zone quickly to reduce attack surface.
        
        # Step 1: Ensure the Processing Staging directory exists
        if not os.path.exists(config.PROCESSING_DIR):  # Creates processing directory if missing
            os.makedirs(config.PROCESSING_DIR)
            
        # Step 2: Define new destination paths inside the secure boundary
        dest_file = os.path.join(config.PROCESSING_DIR, f"{product_id}.npy")  # Builds destination data path
        dest_meta = os.path.join(config.PROCESSING_DIR, f"{product_id}.json")  # Builds destination metadata path
        
        # Step 3: Physically move the data
        shutil.copy(source_file, dest_file)  # Copies data file to processing zone
        
        # Step 4: Save the UPDATED metadata (now containing the Source Hash)
        with open(dest_meta, "w") as f:  # Opens destination metadata file
            # Dump the dictionary back to JSON with clean indentation
            json.dump(meta, f, indent=4)  # Dumps updated metadata to JSON
            
        # Step 5: Finalize the log for the audit trail
        audit_log.info(f"[INGEST] SUCCESS: Product {product_id} is verified and staged. Initial Hash: {file_hash}")  # Logs ingestion success and hash
        
        # Return the new path so the pipeline can continue to 'Processing'
        return dest_file
