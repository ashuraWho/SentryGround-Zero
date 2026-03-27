import os  # For file operations
import hashlib  # For SHA-256 hashing

from cryptography.fernet import Fernet  # For symmetric encryption
from secure_eo_pipeline import config  # For key file path

# =============================================================================
# Security Utilities Module
# =============================================================================
# PURPOSE:
# This module acts as the "Cryptographic Engine" for the entire pipeline.
# It abstracts complex mathematical operations into simple function calls.
#
# DESIGN RATIONALE:
# In Earth Observation, data integrity is paramount. If a single bit is flipped
# during transmission or storage, scientific results could be invalid.
# Encryption ensures that sensitive or proprietary data remains confidential.
# =============================================================================

from typing import Optional

def generate_key() -> None:
    
    """
    Generates a new 256-bit symmetric encryption key and saves it to a file.
    
    RATIONALE:
    Symmetric encryption uses the same key for both locking and unlocking data.
    Generating a fresh, cryptographically secure random key is the first step in
    securing any system.
    """
    
    # Use Fernet's built-in generator to create a secure, random key.
    # Fernet uses AES-128 in CBC mode for encryption and HMAC-SHA256 for authentication.
    # AES = Advanced Encryption Standard
    # CBC = Cipher Block Chaining
    # HMAC = Hash-based Message Authentication Code
    key = Fernet.generate_key()  # Generates a new Fernet key
    
    # Open the designated key file path in 'wb' (write binary) mode
    # Using 'with' ensures the file is properly closed even if an error occurs
    with open(config.KEY_PATH, "wb") as key_file:  # Opens key file for binary writing
        # Write the raw bytes of the key into the file
        key_file.write(key)  # Writes key bytes to disk
    
    # Tighten file permissions where the OS allows it (best-effort on non-POSIX systems)
    try:
        os.chmod(config.KEY_PATH, 0o600)  # Attempts to set file permissions to owner-only
    except Exception:
        pass  # Ignores permission errors on unsupported platforms
    
    # Output a notification to the console for the system operator
    # In a real environment, this would be a high-priority security audit log
    print(f"[SECURITY CORE] SUCCESS: A new encryption key was written to: {config.KEY_PATH}")  # Prints success message



def load_key() -> bytes:
    
    """
    Retrieves the existing encryption key from the filesystem.
    
    RETURNS:
        bytes: The raw cryptographic key.
        
    SECURITY LOGIC:
    This function implements a "Secure Default" pattern. If the key doesn't exist,
    it creates one instead of crashing, ensuring the system is always protected.
    """
    
    # Check if the key file exists at the path defined in our central config
    if not os.path.exists(config.KEY_PATH):
        # If the file is missing, trigger the generation of a new key immediately
        generate_key()  # Generates a new key if missing
        
    try:
        # Open the key file in 'rb' (read binary) mode
        with open(config.KEY_PATH, "rb") as key_file:  # Opens key file for binary read
            # Read all bytes from the file and return them to the caller
            return key_file.read()
    except Exception as e:
        # If a hardware or permission error occurs, report it precisely
        print(f"[SECURITY CORE] FATAL ERROR: Could not read key file. Details: {e}")  # Starts exception handling
        # Re-raise the exception to stop execution; continuing without a key is unsafe
        raise



def encrypt_file(file_path: str) -> None:
    
    """
    Transforms a readable file into an encrypted blob of data.
    
    ARGUMENTS:
        file_path (str): The location of the file to be scrambled.
        
    TECHNICAL FLOW:
    Read Plaintext -> Load Key -> Apply Encryption Algorithm -> Write Ciphertext
    """
    
    # Step 1: Call our internal load_key() to get the secret bytes
    key = load_key()  # Loads the key
    
    # Step 2: Initialize the Fernet encryption object with the secret key
    # This object contains the logic for the Fernet encryption scheme
    f = Fernet(key)  # Creates a Fernet instance
    
    try:
        # Step 3: Open the target file in 'rb' mode to read the original scientific data
        with open(file_path, "rb") as file:  # Opens file for reading
            # Load the entire content into memory (Buffer)
            file_data = file.read()  # Reads all file data
            
        # Step 4: Execute the encryption transformation
        # This adds a 128-bit IV (Initialization Vector) and a 256-bit HMAC (Signature)
        encrypted_data = f.encrypt(file_data)  # Encrypts the data
        
        # Step 5: Open the SAME file in 'wb' mode to overwrite it
        with open(file_path, "wb") as file:  # Opens file for binary write
            # Write the encrypted 'ciphertext' back to disk
            file.write(encrypted_data)  # Writes encrypted data
    except FileNotFoundError:  # Handles missing file.
        # Handle cases where the requested file doesn't exist
        print(f"[SECURITY CORE] ERROR: Encryption failed. File {file_path} not found.")
    except Exception as e:  # Handles generic errors
        # Handle unexpected errors (e.g., disk full, permission denied)
        print(f"[SECURITY CORE] ERROR: Unexpected encryption failure for {file_path}. {e}")



def decrypt_file(file_path: str) -> None:
    
    """
    Restores an encrypted file back to its original readable state.
    
    ARGUMENTS:
        file_path (str): The location of the scrambled file.
        
    SECURITY NOTE:
    Fernet decryption also verifies the HMAC signature. If the file was
    tampered with by even one bit, decryption will fail (Authenticated Encryption).
    """
    
    # Step 1: Retrieve the required secret key
    key = load_key()  # Loads the key
    
    # Step 2: Initialize the cryptographic engine
    f = Fernet(key)  # Creates a Fernet instance
    
    try:
        # Step 3: Read the encrypted 'ciphertext' from the storage medium
        with open(file_path, "rb") as file:  # Opens file for reading
            # Load the scrambled bytes into the memory buffer
            encrypted_data = file.read()  # Reads encrypted data
            
        # Step 4: Perform the decryption operation
        # This removes the IV and verifies the HMAC before returning the original data
        decrypted_data = f.decrypt(encrypted_data)  # Decrypts the data
        
        # Step 5: Overwrite the file with the clean 'plaintext' bytes
        with open(file_path, "wb") as file:  # Opens file for writing
            # Data is now usable for scientific processing again
            file.write(decrypted_data)  # Writes decrypted bytes
    except Exception as e:  # Handles decryption errors
        # Log decryption failures (often caused by wrong keys or corrupted files)
        print(f"[SECURITY CORE] ERROR: Decryption failed for {file_path}. Reason: {e}")
        # We re-raise to ensure the caller knows the data is still unreadable
        raise



def calculate_hash(file_path: str) -> Optional[str]:
    
    """
    Generates a SHA-256 'Digital Fingerprint' of any file.
    
    ARGUMENTS:
        file_path (str): The file to be fingerprinted.
        
    WHY SHA-256?
    SHA-256 is a 'One-Way' function. You can easily get a hash from a file,
    but you can never recreate the file from the hash. It is the gold standard
    for verifying that data has not been modified (Integrity).
    
    RETURNS:
        str: A 64-character hexadecimal string.
    """
    
    # Initialize the SHA-256 hashing engine from the hashlib library
    sha256_engine = hashlib.sha256()  # Creates a SHA-256 hash object
    
    try:
        # Step 1: Open the file for reading in binary mode
        with open(file_path, "rb") as f:  # Opens the file in binary mode
            # Step 2: Read the file in small 4KB (4096 bytes) chunks
            # RATIONALE: Reading a 10GB satellite image at once would crash the RAM.
            # Chunking allows us to process files of any size efficiently.
            for byte_block in iter(lambda: f.read(4096), b""):  # Iterates over 4096-byte blocks
                # Step 3: Feed each chunk into the hashing engine sequentially
                sha256_engine.update(byte_block)  # Updates hash with each chunk
                
        # Step 4: Finalize the calculation and return the result as a hex string
        # hexdigest() provides a human-readable representation of the binary hash
        return sha256_engine.hexdigest()  # Returns the hex digest
    except FileNotFoundError:  # Handles missing file
        # If the file isn't there, we can't hash it
        print(f"[SECURITY CORE] ERROR: Cannot calculate hash. {file_path} not found.")
        return None

def rotate_keys(archive_dir: str, backup_dir: str) -> bool:
    """
    Performs a full cryptographic key rotation.
    
    PROCESS:
    1. Load the OLD key.
    2. Generate a NEW key (in memory).
    3. Re-encrypt all data in Archive and Backup with the NEW key.
    4. Overwrite the key file on disk.
    
    RETURNS:
        bool: True if successful, False if critical error occurred.
    """
    print("[CRYPTO] STARTING KEY ROTATION SEQUENCE...")
    
    # 1. Load the current (soon to be old) key
    try:
        old_key_bytes = load_key()
        old_fernet = Fernet(old_key_bytes)
    except Exception as e:
        print(f"[CRYPTO] FATAL: Could not load current key: {e}")
        return False

    # 2. Generate new key
    new_key_bytes = Fernet.generate_key()
    new_fernet = Fernet(new_key_bytes)
    print("[CRYPTO] New key generated in memory.")

    # 3. Identify all encrypted files
    # We need to process both the primary archive and the backup
    targets = []
    for d in [archive_dir, backup_dir]:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".enc"):
                    targets.append(os.path.join(d, f))
    
    print(f"[CRYPTO] Found {len(targets)} encrypted objects to migrate.")

    # 4. Re-encrypt loop
    # NOTE: In a production system, this should be atomic.
    # If it crashes halfway, we'd have half files with key A and half with key B.
    # Here, for education, we assume happy path or manual recovery.
    success_count = 0
    for file_path in targets:
        try:
            # Read ciphertext
            with open(file_path, "rb") as f:
                cipher_old = f.read()
            
            # Decrypt with OLD key
            plaintext = old_fernet.decrypt(cipher_old)
            
            # Encrypt with NEW key
            cipher_new = new_fernet.encrypt(plaintext)
            
            # Write back
            with open(file_path, "wb") as f:
                f.write(cipher_new)
            
            success_count += 1
            # Optional: print(f"  > Migrated {os.path.basename(file_path)}")
            
        except Exception as e:
            print(f"[CRYPTO] ERROR migrating {file_path}: {e}")
            # If we fail to re-encrypt a file, do we stop? 
            # For this prototype, yes, to avoid a mess.
            print("[CRYPTO] ABORTING ROTATION to prevent data loss.")
            return False

    if success_count < len(targets):
        print("[CRYPTO] Warning: Not all files were migrated. Old key still active on disk.")
        return False

    # 5. Commit new key to disk
    try:
        with open(config.KEY_PATH, "wb") as f:
            f.write(new_key_bytes)
        print("[CRYPTO] SUCCESS: New key committed to keystore.")
        return True
    except Exception as e:
        print(f"[CRYPTO] CRITICAL: Re-encryption done but failed to save new key: {e}")
        print(f"[CRYPTO] EMERGENCY DUMP OF NEW KEY: {new_key_bytes.decode()}")
        return False

