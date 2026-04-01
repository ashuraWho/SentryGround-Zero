"""
Alembic Environment Configuration for SentryGround-Zero.

This module configures Alembic to work with both SQLite (development) 
and PostgreSQL (production) databases.
"""

from logging.config import fileConfig
import os
import sys
from datetime import datetime

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secure_eo_pipeline.database.postgresql_models import Base
from secure_eo_pipeline.db.sqlite_adapter import _get_db_path

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    """Get database URL from environment or use SQLite default."""
    use_sqlite = os.environ.get('USE_SQLITE', '1') == '1'
    
    if use_sqlite:
        db_path = _get_db_path()
        return f"sqlite:///{db_path}"
    
    pg_host = os.environ.get('PG_HOST', 'localhost')
    pg_user = os.environ.get('PG_USER', 'sentry_admin')
    pg_password = os.environ.get('PG_PASSWORD', 'secure_password_123')
    pg_dbname = os.environ.get('PG_DBNAME', 'eo_security')
    
    return f"postgresql://{pg_user}:{pg_password}@{pg_host}:5432/{pg_dbname}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
