"""Initial schema - create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('created_at', sa.String(50), nullable=True),
        sa.Column('disabled', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )

    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.String(50), nullable=True),
        sa.Column('level', sa.String(20), nullable=False),
        sa.Column('component', sa.String(100), nullable=True),
        sa.Column('user', sa.String(100), nullable=True),
        sa.Column('action', sa.String(100), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'ingestion_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.String(100), nullable=False),
        sa.Column('product_type', sa.String(50), nullable=False),
        sa.Column('satellite', sa.String(100), nullable=True),
        sa.Column('timestamp', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id')
    )

    op.create_table(
        'satellites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sat_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('regime', sa.String(50), nullable=True),
        sa.Column('altitude_km', sa.Float(), nullable=True),
        sa.Column('inclination_deg', sa.Float(), nullable=True),
        sa.Column('eccentricity', sa.Float(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('launch_date', sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sat_id')
    )

    op.create_table(
        'telemetry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sat_id', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.String(50), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('altitude_km', sa.Float(), nullable=True),
        sa.Column('velocity_km_s', sa.Float(), nullable=True),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('battery_pct', sa.Float(), nullable=True),
        sa.Column('signal_strength_dbm', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.String(50), nullable=True),
        sa.Column('acknowledged', sa.Integer(), nullable=True),
        sa.Column('acknowledged_by', sa.String(100), nullable=True),
        sa.Column('acknowledged_at', sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'orbital_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sat_id', sa.String(50), nullable=False),
        sa.Column('time', sa.String(50), nullable=False),
        sa.Column('x', sa.Float(), nullable=True),
        sa.Column('y', sa.Float(), nullable=True),
        sa.Column('z', sa.Float(), nullable=True),
        sa.Column('vx', sa.Float(), nullable=True),
        sa.Column('vy', sa.Float(), nullable=True),
        sa.Column('vz', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_telemetry_sat_time', 'telemetry', ['sat_id', 'timestamp'])
    op.create_index('idx_orbital_sat_time', 'orbital_states', ['sat_id', 'time'])
    op.create_index('idx_alerts_timestamp', 'alerts', ['timestamp'])


def downgrade() -> None:
    op.drop_index('idx_alerts_timestamp', table_name='alerts')
    op.drop_index('idx_orbital_sat_time', table_name='orbital_states')
    op.drop_index('idx_telemetry_sat_time', table_name='telemetry')
    op.drop_table('orbital_states')
    op.drop_table('alerts')
    op.drop_table('telemetry')
    op.drop_table('satellites')
    op.drop_table('ingestion_products')
    op.drop_table('audit_log')
    op.drop_table('users')
