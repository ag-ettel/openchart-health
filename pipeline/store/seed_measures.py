"""
Seed the `measures` reference table from MEASURE_REGISTRY, and auto-register
unknown measure IDs encountered during pipeline runs.

Must run before any provider_measure_values are written (FK constraint).
"""

from __future__ import annotations

import logging

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection

from pipeline.cms_definitions import CMS_MEASURE_DEFINITIONS
from pipeline.config import DATASET_DIRECTION_SOURCE, MEASURE_REGISTRY

logger = logging.getLogger(__name__)

# Cache of measure_ids known to exist in the measures table (avoids repeated lookups)
_registered_ids: set[str] = set()


def seed_measures(conn: Connection) -> int:
    """Upsert all MEASURE_REGISTRY entries into the measures table.

    Returns count of rows upserted.
    """
    metadata = sa.MetaData()
    metadata.reflect(bind=conn.engine, only=["measures"])
    table = metadata.tables["measures"]
    count = 0

    for entry in MEASURE_REGISTRY.values():
        data = {
            "measure_id": entry.measure_id,
            "measure_name": entry.name,
            "measure_plain_language": entry.plain_language,
            # DEC-037: CMS definition from the definitions mapping, with
            # MeasureEntry field as override if set directly.
            "cms_measure_definition": (
                entry.cms_measure_definition
                or CMS_MEASURE_DEFINITIONS.get(entry.measure_id)
            ),
            "measure_group": entry.group,
            "direction": entry.direction,
            "direction_source": DATASET_DIRECTION_SOURCE.get(entry.dataset_id),
            "unit": entry.unit,
            "tail_risk_flag": entry.tail_risk_flag,
            "ses_sensitivity": entry.ses_sensitivity,
            "dataset_id": entry.dataset_id,
            "is_active": True,
        }

        stmt = pg_insert(table).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["measure_id"],
            set_={k: v for k, v in data.items() if k != "measure_id"},
        )
        conn.execute(stmt)
        _registered_ids.add(entry.measure_id)
        count += 1

    logger.info("Seeded %d measures into measures table", count)
    return count


def ensure_measure_exists(conn: Connection, measure_id: str) -> None:
    """Ensure a measure_id exists in the measures table.

    If the measure is not in MEASURE_REGISTRY (e.g., retired CMS measure from an
    older archive), insert a minimal stub with is_active=False. This prevents FK
    violations while preserving historical data.

    This is the antifragile path: store unknown values rather than rejecting them.
    A retired measure stored with is_active=False is recoverable. A rejected row
    from a historical archive is data loss.
    """
    if measure_id in _registered_ids:
        return

    # Check database
    metadata = sa.MetaData()
    metadata.reflect(bind=conn.engine, only=["measures"])
    table = metadata.tables["measures"]

    exists = conn.execute(
        sa.select(table.c.measure_id).where(table.c.measure_id == measure_id)
    ).fetchone()

    if exists:
        _registered_ids.add(measure_id)
        return

    # Insert minimal stub for unknown/retired measure
    # Use SPENDING as a safe default group (least assumptions)
    # The measure will be flagged is_active=False for review
    logger.warning(
        "Auto-registering unknown measure_id: %r (not in MEASURE_REGISTRY — likely retired)",
        measure_id,
    )
    conn.execute(table.insert().values(
        measure_id=measure_id,
        measure_name=f"[Retired/Unknown] {measure_id}",
        measure_group="SPENDING",  # Safe default — will be corrected if needed
        tail_risk_flag=False,
        ses_sensitivity="UNKNOWN",
        is_active=False,
    ))
    _registered_ids.add(measure_id)
