import pytest
import os
from secure_eo_pipeline.utils import security
from secure_eo_pipeline import config

@pytest.fixture
def temp_key_file(tmp_path):
    # Create a temp key file path
    key_path = tmp_path / "test_secret.key"
    original_key_path = config.KEY_PATH
    config.KEY_PATH = str(key_path)
    
    yield key_path
    
    # Cleanup
    config.KEY_PATH = original_key_path
    if os.path.exists(key_path):
        os.remove(key_path)

def test_generate_and_load_key(temp_key_file):
    # Test generation
    security.generate_key()
    assert os.path.exists(config.KEY_PATH)
    
    # Test loading
    key = security.load_key()
    assert isinstance(key, bytes)
    assert len(key) > 0

def test_encrypt_decrypt_file(temp_key_file, tmp_path):
    # Setup
    security.generate_key()
    
    test_file = tmp_path / "top_secret.txt"
    original_content = b"This is a classified satellite image."
    
    with open(test_file, "wb") as f:
        f.write(original_content)
        
    # Encrypt
    security.encrypt_file(str(test_file))
    
    # Verify content changed (encrypted)
    with open(test_file, "rb") as f:
        encrypted_content = f.read()
    assert encrypted_content != original_content
    assert b"classified" not in encrypted_content # Basic check that plaintext is hidden
    
    # Decrypt
    security.decrypt_file(str(test_file))
    
    # Verify original content restored
    with open(test_file, "rb") as f:
        decrypted_content = f.read()
    assert decrypted_content == original_content

def test_calculate_hash(tmp_path):
    test_file = tmp_path / "data.bin"
    content = b"checksum_me"
    
    with open(test_file, "wb") as f:
        f.write(content)
        
    # Calculate hash
    hash1 = security.calculate_hash(str(test_file))
    assert hash1 is not None
    assert len(hash1) == 64 # SHA-256 hex digest length
    
    # Modify file and check hash changes
    with open(test_file, "wb") as f:
        f.write(content + b"_modified")
        
    hash2 = security.calculate_hash(str(test_file))
    assert hash1 != hash2
