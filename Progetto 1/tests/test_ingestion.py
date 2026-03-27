import pytest
import os
import json
import shutil
from secure_eo_pipeline.components.ingestion import IngestionManager
from secure_eo_pipeline import config

@pytest.fixture
def ingestion_manager():
    return IngestionManager()

@pytest.fixture
def setup_teardown_ingest(tmp_path):
    # Setup: Create temp directories
    base_dir = tmp_path / "simulation_data"
    ingest_dir = base_dir / "ingest_landing_zone"
    processing_dir = base_dir / "processing_staging"
    
    os.makedirs(ingest_dir)
    os.makedirs(processing_dir)
    
    # Override config paths for testing
    original_ingest = config.INGEST_DIR
    original_processing = config.PROCESSING_DIR
    
    config.INGEST_DIR = str(ingest_dir)
    config.PROCESSING_DIR = str(processing_dir)
    
    yield ingest_dir, processing_dir
    
    # Teardown: Restore config
    config.INGEST_DIR = original_ingest
    config.PROCESSING_DIR = original_processing
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)

def test_ingest_product_success(ingestion_manager, setup_teardown_ingest):
    ingest_dir, processing_dir = setup_teardown_ingest
    product_id = "test_product_001"
    
    # Create dummy data and metadata
    data_file = ingest_dir / f"{product_id}.npy"
    meta_file = ingest_dir / f"{product_id}.json"
    
    with open(data_file, "wb") as f:
        f.write(b"fake_satellite_data")
        
    metadata = {
        "product_id": product_id,
        "timestamp": "2023-01-01T00:00:00",
        "sensor": "Sentinel-2"
    }
    with open(meta_file, "w") as f:
        json.dump(metadata, f)
        
    # Run ingestion
    result_path = ingestion_manager.ingest_product(product_id)
    
    # Assertions
    assert result_path is not None
    assert os.path.exists(result_path)
    assert "processing_staging" in result_path
    
    # Check if metadata was updated with hash
    processed_meta_path = processing_dir / f"{product_id}.json"
    with open(processed_meta_path, "r") as f:
        new_meta = json.load(f)
    
    assert "original_hash" in new_meta
    assert new_meta["status"] == "INGESTED"

def test_ingest_missing_files(ingestion_manager, setup_teardown_ingest):
    ingest_dir, _ = setup_teardown_ingest
    product_id = "missing_data_product"
    
    # Create ONLY metadata, validation should fail
    meta_file = ingest_dir / f"{product_id}.json"
    with open(meta_file, "w") as f:
        json.dump({"product_id": product_id}, f)
        
    result = ingestion_manager.ingest_product(product_id)
    assert result is None

def test_ingest_invalid_schema(ingestion_manager, setup_teardown_ingest):
    ingest_dir, _ = setup_teardown_ingest
    product_id = "bad_schema_product"
    
    data_file = ingest_dir / f"{product_id}.npy"
    meta_file = ingest_dir / f"{product_id}.json"
    
    with open(data_file, "wb") as f:
        f.write(b"data")
        
    # Missing required 'sensor' field
    metadata = {
        "product_id": product_id,
        "timestamp": "2023-01-01"
    }
    with open(meta_file, "w") as f:
        json.dump(metadata, f)
        
    result = ingestion_manager.ingest_product(product_id)
    assert result is None
