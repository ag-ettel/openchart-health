"""
Bootstrap the local PostgreSQL database and run Alembic migrations.

Usage:
    python scripts/bootstrap_db.py [--drop]

Options:
    --drop    Drop and recreate the database before migrating.

Requires a running PostgreSQL 16 instance. Connection parameters are read from
environment variables or defaults:
    OPENCHART_DB_HOST     (default: localhost)
    OPENCHART_DB_PORT     (default: 5432)
    OPENCHART_DB_USER     (default: postgres)
    OPENCHART_DB_PASSWORD (default: postgres)
    OPENCHART_DB_NAME     (default: openchart)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_HOST = os.environ.get("OPENCHART_DB_HOST", "localhost")
DB_PORT = os.environ.get("OPENCHART_DB_PORT", "5432")
DB_USER = os.environ.get("OPENCHART_DB_USER", "postgres")
DB_PASSWORD = os.environ.get("OPENCHART_DB_PASSWORD", "postgres")
DB_NAME = os.environ.get("OPENCHART_DB_NAME", "openchart")

ADMIN_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"
DB_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def create_database(drop_first: bool = False) -> None:
    """Create the database if it doesn't exist."""
    engine = sa.create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            sa.text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": DB_NAME},
        ).scalar()

        if exists and drop_first:
            # Terminate existing connections
            conn.execute(sa.text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ), {"name": DB_NAME})
            conn.execute(sa.text(f'DROP DATABASE "{DB_NAME}"'))
            print(f"Dropped database '{DB_NAME}'.")
            exists = False

        if not exists:
            conn.execute(sa.text(f'CREATE DATABASE "{DB_NAME}"'))
            print(f"Created database '{DB_NAME}'.")
        else:
            print(f"Database '{DB_NAME}' already exists.")

    engine.dispose()


def run_migrations() -> None:
    """Run Alembic migrations to head."""
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", DB_URL)
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))

    command.upgrade(alembic_cfg, "head")
    print("Migrations complete.")


def verify_tables() -> None:
    """Verify all expected tables exist."""
    expected = {
        "pipeline_runs",
        "providers",
        "measures",
        "provider_measure_values",
        "provider_payment_adjustments",
        "provider_inspection_events",
        "provider_ownership",
        "provider_penalties",
        "alembic_version",
    }

    engine = sa.create_engine(DB_URL)
    inspector = sa.inspect(engine)
    actual = set(inspector.get_table_names())
    engine.dispose()

    missing = expected - actual
    if missing:
        print(f"MISSING TABLES: {missing}")
        sys.exit(1)

    print(f"Verified: {len(expected)} tables present.")

    # Also verify enum types
    engine = sa.create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(sa.text(
            "SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname"
        ))
        enums = [row[0] for row in result]
    engine.dispose()

    expected_enums = {
        "measure_direction",
        "measure_group",
        "payment_program",
        "provider_type",
        "reliability_flag",
        "ses_sensitivity",
    }
    actual_enums = set(enums)
    missing_enums = expected_enums - actual_enums
    if missing_enums:
        print(f"MISSING ENUMS: {missing_enums}")
        sys.exit(1)

    print(f"Verified: {len(expected_enums)} enum types present.")


def main() -> None:
    drop = "--drop" in sys.argv
    if drop:
        print("WARNING: --drop flag set. Database will be dropped and recreated.")

    create_database(drop_first=drop)
    run_migrations()
    verify_tables()
    print(f"\nDatabase ready at {DB_URL}")


if __name__ == "__main__":
    main()
