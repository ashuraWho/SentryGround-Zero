import os  # For filesystem operations
import json  # For metadata operations 
import shutil  # For file copying

from secure_eo_pipeline import config  # For path settings
from secure_eo_pipeline.utils import security  # For encryption and decryption
from secure_eo_pipeline.utils.logger import audit_log  # For event logging

# =============================================================================
# Secure Storage & Archiving Component
# =============================================================================
# ROLE IN ARCHITECTURE:
# The "Secure Bank Vault".
# This component is responsible for the final stage of the data lifecycle.
# It ensures that valuable EO products are stored safely for years to come.
#
# KEY SECURITY REQUIREMENT: Encryption at Rest.
# We must ensure that files stored on physical disks are unreadable to anyone
# who does not possess the secret master key.
#
# DESIGN RATIONALE:
# By encrypting data at the storage layer, we protect the mission against
# hardware theft or unauthorized disk access.
# =============================================================================

class ArchiveManager:
    
    """
    Manages the long-term secure storage, encryption, and retrieval of EO products.
    """

    def archive_product(self, product_id, cleanup=True):  # Defines `archive_product` with `cleanup` flag
        
        """
        Encrypts a processed product and moves it into the permanent archive.
        
        ARGUMENTS:
            product_id (str): The unique ID of the product to be archived.
            cleanup (bool): If True, remove cleartext staging files after archiving.
            
        RETURNS:
            str: The path to the newly created encrypted archive file.
        """
        
        # Step 1: Define the Source Paths (where the data is currently located after processing)
        source_file = os.path.join(config.PROCESSING_DIR, f"{product_id}.npy")  # Builds source data path
        source_meta = os.path.join(config.PROCESSING_DIR, f"{product_id}.json")  # Builds source metadata path
        
        # Step 2: Environmental Check - Ensure the Archive Vault folder exists on the disk
        if not os.path.exists(config.ARCHIVE_DIR):  # Creates archive directory if missing
            # Create the directory if it's missing (Secure Initialization)
            os.makedirs(config.ARCHIVE_DIR)
            
        # Step 3: Define the Destination Paths in the Archive folder
        # Note: We change the extension to .enc to signify that it is now ENCRYPTED.
        dest_file = os.path.join(config.ARCHIVE_DIR, f"{product_id}.enc")  # Builds encrypted data path
        dest_meta = os.path.join(config.ARCHIVE_DIR, f"{product_id}.json")  # Builds archive metadata path
        
        # Step 4: Log the initiation of the archiving event
        audit_log.info(f"[ARCHIVE] START: Securing product {product_id} in the vault...")  # Logs archive start
        
        # ---------------------------------------------------------------------
        # PHASE 1: ENCRYPTION FLOW
        # ---------------------------------------------------------------------
        # RATIONALE: We copy first, then encrypt the copy. This leaves a
        # temporary cleartext backup in the processing zone until it's cleared.
        
        try:
            # 1. Physically copy the binary data to the archive location
            shutil.copy(source_file, dest_file)  # Copies data file into archive
            
            # 2. PERFORM IN-PLACE ENCRYPTION (Fernet).
            # This calls our security utility to scramble the bits using the master key.
            # After this line executes, 'dest_file' becomes unreadable noise on the disk.
            security.encrypt_file(dest_file)  # Encrypts the copied file in place
            
        except Exception as e:
            # Handle encryption or filesystem errors (e.g., Disk Full)
            audit_log.error(f"[ARCHIVE] FATAL ERROR: Encryption failed for {product_id}. {e}")  # Logs encryption failure
            return None

        # ---------------------------------------------------------------------
        # PHASE 2: METADATA CATALOGING
        # ---------------------------------------------------------------------
        # RATIONALE: Metadata (the .json) is generally NOT encrypted.
        # Why? Because ground segment operators need to be able to "search" 
        # the catalog (e.g., "Find all images over Italy") without needing 
        # to decrypt every single file in the archive first.
        
        try:  # Starts try block for metadata update
            # 1. Load the existing metadata dictionary
            with open(source_meta, "r") as f:  # Opens source metadata file
                meta = json.load(f)  # Loads metadata JSON
                
            # 2. Update the status and record the physical path of the encrypted file
            meta["status"] = "ARCHIVED"  # Sets status to ARCHIVED
            meta["confidentiality"] = "HIGH (Fernet AES-128-CBC + HMAC-SHA256)"  # Sets confidentiality label
            meta["archived_path"] = dest_file  # Stores archived file path
            
            # 3. Save the final "Archived Record" into the Vault
            with open(dest_meta, "w") as f:  # Writes metadata into archive directory
                json.dump(meta, f, indent=4)
                
        except Exception as e:
            # Log errors in cataloging
            audit_log.error(f"[ARCHIVE] ERROR: Failed to update catalog for {product_id}. {e}")  # Logs metadata update failure

        # Step 5: Optionally remove cleartext artifacts from the processing zone
        if cleanup:  # Checks cleanup flag
            try:  # Starts try block for deletions
                if os.path.exists(source_file):  # Removes the cleartext data file if present
                    os.remove(source_file)
                if os.path.exists(source_meta):  # Removes the cleartext metadata if present
                    os.remove(source_meta)
            except Exception as e:
                audit_log.warning(f"[ARCHIVE] WARNING: Could not remove staging files for {product_id}. {e}")  # Logs warning if cleanup fails
        
        # Step 6: Finalize the log for the audit trail
        audit_log.info(f"[ARCHIVE] SUCCESS: Product {product_id} is now encrypted and vaulted.")  # Logs archive success
        
        # Return the path to the encrypted asset
        return dest_file



    def retrieve_product(self, product_id, output_path):
        
        """
        Fetches an encrypted product from the archive and provides a decrypted copy to the user.
        
        ARGUMENTS:
            product_id (str): The product being requested.
            output_path (str): Where the decrypted file should be delivered.
            
        LOGIC:
        The Master Archive is "Write-Only" for encryption. We never decrypt 
        the master copy itself. Instead, we decrypt a CLONE delivered to the user.
        """
        
        # Step 1: Identify the location of the encrypted master file
        archive_file = os.path.join(config.ARCHIVE_DIR, f"{product_id}.enc")  # Builds the encrypted archive file path
        
        # Step 2: Verification - Does the product exist in the vault?
        if not os.path.exists(archive_file):  # Checks if the archive file exists
            audit_log.error(f"[ARCHIVE] RETRIEVAL FAILED: {product_id} not found in storage.")  # Logs retrieval failure if missing
            return False
            
        # Step 3: Log the retrieval request
        audit_log.info(f"[ARCHIVE] START: Retrieving and decrypting {product_id} for user delivery...")  # Logs retrieval start
        
        try:  # Starts try block for retrieval
            # 1. CLONING: Copy the encrypted file to the user's requested output path.
            # This preserves the security of the primary archive.
            shutil.copy(archive_file, output_path)  # Copies the encrypted file to output path
            
            # 2. DECRYPTION: Call the security utility to restore the clone to readable state.
            # This operation requires the symmetric key.
            security.decrypt_file(output_path)  # Decrypts the copied file
            
            # Log success
            audit_log.info(f"[ARCHIVE] SUCCESS: {product_id} decrypted and delivered to {output_path}")  # Logs retrieval success
            return True  # Returns True to indicate success
            
        except Exception as e:
            # Handle decryption failures (e.g., key mismatch or corrupted archive)
            audit_log.error(f"[ARCHIVE] FATAL: Decryption failed during retrieval. {e}")  # Logs fatal decryption failure
            return False
