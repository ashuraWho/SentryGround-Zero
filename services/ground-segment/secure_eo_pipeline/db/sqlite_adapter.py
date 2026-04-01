import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from secure_eo_pipeline import config


_CONNECTION = None
_IS_POSTGRES = False

def _get_db_path() -> str:
    """
    Returns the absolute path to the SQLite database file.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, config.SQLITE_DB_PATH)


def get_connection():
    """
    Returns a singleton DB connection for SQLite or PostgreSQL.
    """
    global _CONNECTION, _IS_POSTGRES
    if _CONNECTION is None:
        if os.getenv("PG_HOST"):
            import psycopg2
            from psycopg2.extras import DictCursor
            _CONNECTION = psycopg2.connect(
                host=os.getenv("PG_HOST"),
                user=os.getenv("PG_USER"),
                password=os.getenv("PG_PASSWORD"),
                dbname=os.getenv("PG_DBNAME")
            )
            # Make psycopg2 act like autocommit so we don't have to rewrite commit logic
            _CONNECTION.autocommit = True
            _IS_POSTGRES = True
            _initialize_schema(_CONNECTION)
        else:
            db_path = _get_db_path()
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            _CONNECTION = sqlite3.connect(db_path)
            _CONNECTION.row_factory = sqlite3.Row
            _initialize_schema(_CONNECTION)
    return _CONNECTION

def _exec(cur, query, params=()):
    if _IS_POSTGRES:
        # SQLite uses '?', PostgreSQL uses '%s'
        query = query.replace("?", "%s")
        # INSERT OR REPLACE -> INSERT ... ON CONFLICT
        # This is a bit tricky, we'll avoid complex replacements and just do basic ones
        if "INSERT OR REPLACE INTO users" in query:
            query = query.replace("INSERT OR REPLACE INTO users", "INSERT INTO users")
            query += " ON CONFLICT (username) DO UPDATE SET password_hash=EXCLUDED.password_hash, role=EXCLUDED.role, disabled=EXCLUDED.disabled"
    cur.execute(query, params)


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
    if _IS_POSTGRES:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id SERIAL PRIMARY KEY,
                ts TEXT NOT NULL,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                "user" TEXT,
                action TEXT,
                details TEXT NOT NULL
            )
            """
        )
    else:
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
    cnt = row[0]
    if cnt == 0:
        now = datetime.now(timezone.utc).isoformat()
        for username, record in config.USERS_DB.items():
            _exec(cur,
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
    _exec(cur,
        "SELECT username, password_hash, role, disabled FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    if not row:
        return None
        
    username_val = row["username"] if hasattr(row, 'keys') else row[0]
    password_hash_val = row["password_hash"] if hasattr(row, 'keys') else row[1]
    role_val = row["role"] if hasattr(row, 'keys') else row[2]
    disabled_val = row["disabled"] if hasattr(row, 'keys') else row[3]
    
    return {
        "username": username_val,
        "password_hash": password_hash_val,
        "role": role_val,
        "disabled": bool(disabled_val),
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
    _exec(cur,
        """
        INSERT OR REPLACE INTO users (username, password_hash, role, created_at, disabled)
        VALUES (?, ?, ?, ?, 0)
        """,
        (username, password_hash, role, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def delete_user(username: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    _exec(cur, "DELETE FROM users WHERE username = ?", (username,))
    if not _IS_POSTGRES: conn.commit()


def update_user_role(username: str, role: str) -> None:
    conn = get_connection()
    cur = conn.cursor()
    _exec(cur,
        "UPDATE users SET role = ? WHERE username = ?",
        (role, username),
    )
    if not _IS_POSTGRES: conn.commit()


def disable_user(username: str, disabled: bool = True) -> None:
    conn = get_connection()
    cur = conn.cursor()
    _exec(cur,
        "UPDATE users SET disabled = ? WHERE username = ?",
        (1 if disabled else 0, username),
    )
    if not _IS_POSTGRES: conn.commit()


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
    
    # In PostgreSQL, "user" is a reserved keyword, we quote it in schema creation but 
    # inserts can sometimes be tricky if not quoted in standard INSERT statements if quoting wasn't used everywhere.
    # To be safe, we quote `"user"` in the INSERT query for Postgres.
    query = """
        INSERT INTO audit_events (ts, level, component, "user", action, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """ if _IS_POSTGRES else """
        INSERT INTO audit_events (ts, level, component, user, action, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    _exec(cur, query,
        (
            ts or datetime.now(timezone.utc).isoformat(),
            level,
            component,
            user,
            action,
            details,
        ),
    )
    if not _IS_POSTGRES: conn.commit()

