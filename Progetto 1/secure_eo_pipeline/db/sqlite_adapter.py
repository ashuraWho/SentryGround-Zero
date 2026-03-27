import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from secure_eo_pipeline import config


_CONNECTION: Optional[sqlite3.Connection] = None


def _get_db_path() -> str:
    """
    Returns the absolute path to the SQLite database file.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    # The configured path is relative to the project root (where main.py lives)
    return os.path.join(base_dir, config.SQLITE_DB_PATH)


def get_connection() -> sqlite3.Connection:
    """
    Returns a singleton SQLite connection and ensures that the schema exists.
    """
    global _CONNECTION
    if _CONNECTION is None:
        db_path = _get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _CONNECTION = sqlite3.connect(db_path)
        _CONNECTION.row_factory = sqlite3.Row
        _initialize_schema(_CONNECTION)
    return _CONNECTION


def _initialize_schema(conn: sqlite3.Connection) -> None:
    """
    Creates the required tables if they do not already exist and seeds
    initial users from config.USERS_DB when the table is empty.
    """
    cur = conn.cursor()

    # Users table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            disabled INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # Audit events table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            level TEXT NOT NULL,
            component TEXT NOT NULL,
            user TEXT,
            action TEXT,
            details TEXT NOT NULL
        )
        """
    )

    # Check if users table is empty; if so, seed from config.USERS_DB
    cur.execute("SELECT COUNT(*) AS cnt FROM users")
    row = cur.fetchone()
    if row and row["cnt"] == 0:
        now = datetime.utcnow().isoformat()
        for username, record in config.USERS_DB.items():
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role, created_at, disabled)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    record["hash"],
                    record["role"],
                    now,
                    1 if record.get("role") == "none" else 0,
                ),
            )

    conn.commit()


# -----------------------------------------------------------------------------
# User management helpers
# -----------------------------------------------------------------------------

def get_user(username: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, password_hash, role, disabled FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "username": row["username"],
        "password_hash": row["password_hash"],
        "role": row["role"],
        "disabled": bool(row["disabled"]),
    }


def list_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, role, disabled, created_at FROM users ORDER BY username")
    rows = cur.fetchall()
    return [
        {
            "username": r["username"],
            "role": r["role"],
            "disabled": bool(r["disabled"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def create_user(username: str, password_hash: str, role: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO users (username, password_hash, role, created_at, disabled)
        VALUES (?, ?, ?, ?, 0)
        """,
        (username, password_hash, role, datetime.utcnow().isoformat()),
    )
    conn.commit()


def delete_user(username: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()


def update_user_role(username: str, role: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET role = ? WHERE username = ?",
        (role, username),
    )
    conn.commit()


def disable_user(username: str, disabled: bool = True) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET disabled = ? WHERE username = ?",
        (1 if disabled else 0, username),
    )
    conn.commit()


# -----------------------------------------------------------------------------
# Audit logging helpers
# -----------------------------------------------------------------------------

def insert_audit_event(
    level: str,
    component: str,
    details: str,
    user: Optional[str] = None,
    action: Optional[str] = None,
    ts: Optional[str] = None,
) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO audit_events (ts, level, component, user, action, details)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ts or datetime.utcnow().isoformat(),
            level,
            component,
            user,
            action,
            details,
        ),
    )
    conn.commit()

