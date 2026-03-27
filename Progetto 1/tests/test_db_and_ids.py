import os

from secure_eo_pipeline import config
from secure_eo_pipeline.db import sqlite_adapter
from secure_eo_pipeline.components.ids import IntrusionDetectionSystem


def test_sqlite_seed_and_user_crud(tmp_path, monkeypatch):
    # Redirect DB path to a temporary location
    monkeypatch.setattr(config, "SQLITE_DB_PATH", os.path.join(str(tmp_path), "test.db"))
    # Force new connection
    from secure_eo_pipeline.db import sqlite_adapter as sa

    sa._CONNECTION = None  # type: ignore[attr-defined]

    conn = sqlite_adapter.get_connection()
    cur = conn.cursor()

    # Seeded users should exist
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    assert count >= 1

    # CRUD operations
    sqlite_adapter.create_user("test_user", "hash123", "user")
    user = sqlite_adapter.get_user("test_user")
    assert user is not None
    assert user["role"] == "user"

    sqlite_adapter.update_user_role("test_user", "analyst")
    user = sqlite_adapter.get_user("test_user")
    assert user["role"] == "analyst"

    sqlite_adapter.disable_user("test_user", True)
    user = sqlite_adapter.get_user("test_user")
    assert user["disabled"] is True

    sqlite_adapter.delete_user("test_user")
    assert sqlite_adapter.get_user("test_user") is None


def test_ids_ml_log_anomaly(tmp_path, monkeypatch):
    # Ensure ML is enabled for this test
    monkeypatch.setattr(config, "USE_ML", True)

    # Point IDS to a temporary log file
    log_path = os.path.join(str(tmp_path), "audit.log")
    lines = [
        "INFO - AUTH - FAILURE: Invalid password for 'admin'.",
        "INFO - AUTH - FAILURE: Invalid password for 'admin'.",
        "INFO - AUTH - FAILURE: Invalid password for 'admin'.",
        "ERROR - RESILIENCE - Backup also missing. Data loss is permanent.",
    ]
    with open(log_path, "w") as f:
        for l in lines:
            f.write(l + "\n")

    ids = IntrusionDetectionSystem(log_path=log_path)
    incidents = ids.analyze_audit_log()

    # We expect at least one brute-force incident and one ML Log Anomaly
    types = {i["type"] for i in incidents}
    assert "Brute Force Attack" in types
    assert "ML Log Anomaly" in types

