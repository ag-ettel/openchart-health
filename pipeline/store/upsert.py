"""
Database write layer — upsert logic for all tables.

All writes use SQLAlchemy Core (not ORM) per coding-conventions.md.
No business logic in this module — it receives validated, normalized data
and writes it.

Upsert strategy: INSERT ... ON CONFLICT DO UPDATE for all tables.
Running the pipeline twice must produce identical row counts (Rule 5).
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection

from pipeline.store.seed_measures import ensure_measure_exists

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Table metadata (loaded lazily from the database)
# ---------------------------------------------------------------------------

_metadata = sa.MetaData()


def _get_table(conn: Connection, name: str) -> sa.Table:
    """Reflect a table from the connected database."""
    if name not in _metadata.tables:
        _metadata.reflect(bind=conn.engine, only=[name])
    return _metadata.tables[name]


# ---------------------------------------------------------------------------
# Type coercion helpers
# ---------------------------------------------------------------------------

_known_providers: set[str] = set()


def _ensure_provider_exists(conn: Connection, provider_id: str, provider_type: str) -> None:
    """Ensure provider exists — create stub if not. Cached to avoid repeated lookups."""
    if provider_id in _known_providers:
        return

    table = _get_table(conn, "providers")
    exists = conn.execute(
        sa.select(table.c.provider_id).where(table.c.provider_id == provider_id)
    ).fetchone()

    if exists:
        _known_providers.add(provider_id)
        return

    conn.execute(table.insert().values(
        provider_id=provider_id,
        provider_type=provider_type,
        name=f"Provider {provider_id}",
        is_active=True,
    ))
    _known_providers.add(provider_id)


def _coerce_value(val: Any) -> Any:
    """Coerce Python types to PostgreSQL-compatible values."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (date, datetime)):
        return val
    if isinstance(val, UUID):
        return val
    if isinstance(val, (list, dict)):
        return json.dumps(val) if isinstance(val, dict) else val
    return val


def _filter_columns(data: dict[str, Any], table: sa.Table) -> dict[str, Any]:
    """Filter a dict to only include columns that exist in the table.

    Strips any keys starting with '_' (private/transient fields from normalizers).
    """
    table_cols = {c.name for c in table.columns}
    return {
        k: _coerce_value(v)
        for k, v in data.items()
        if k in table_cols and not k.startswith("_")
    }


# ---------------------------------------------------------------------------
# Upsert functions
# ---------------------------------------------------------------------------

def upsert_providers(conn: Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert provider rows. Returns count of rows affected."""
    if not rows:
        return 0

    table = _get_table(conn, "providers")
    count = 0

    for row in rows:
        data = _filter_columns(row, table)
        if "provider_id" not in data:
            continue

        # Convert address dict to jsonb
        if "address" in data and isinstance(data["address"], dict):
            data["address"] = json.dumps(data["address"])

        data.setdefault("is_active", True)
        now = datetime.utcnow()
        data["updated_at"] = now

        stmt = pg_insert(table).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["provider_id"],
            set_={k: v for k, v in data.items() if k != "provider_id" and k != "created_at"},
        )
        conn.execute(stmt)
        count += 1

    return count


def upsert_measures(conn: Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert measures reference table from MEASURE_REGISTRY."""
    if not rows:
        return 0

    table = _get_table(conn, "measures")
    count = 0

    for row in rows:
        data = _filter_columns(row, table)
        if "measure_id" not in data:
            continue

        now = datetime.utcnow()
        data["updated_at"] = now

        stmt = pg_insert(table).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["measure_id"],
            set_={k: v for k, v in data.items() if k != "measure_id" and k != "created_at"},
        )
        conn.execute(stmt)
        count += 1

    return count


def upsert_measure_values(
    conn: Connection,
    rows: list[dict[str, Any]],
    provider_type: str = "HOSPITAL",
) -> int:
    """Upsert provider_measure_values rows.

    Upsert key: (provider_id, measure_id, period_label, stratification)
    """
    if not rows:
        return 0

    table = _get_table(conn, "provider_measure_values")
    conflict_cols = ["provider_id", "measure_id", "period_label", "stratification"]
    count = 0

    for row in rows:
        data = _filter_columns(row, table)
        data.setdefault("provider_type", provider_type)
        if not all(data.get(c) is not None for c in conflict_cols):
            logger.warning("Missing upsert key field in measure value: %s", data.get("measure_id"))
            continue

        # Auto-register unknown measure IDs (retired measures from older archives)
        ensure_measure_exists(conn, data["measure_id"])

        # Ensure provider exists (older archives may have providers not yet loaded)
        _ensure_provider_exists(conn, data["provider_id"], data.get("provider_type", "HOSPITAL"))

        # Ensure stratification is empty string, not null
        data.setdefault("stratification", "")
        now = datetime.utcnow()
        data["updated_at"] = now

        stmt = pg_insert(table).values(**data)
        update_cols = {k: v for k, v in data.items()
                       if k not in conflict_cols and k != "created_at" and k != "id"}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_pmv_upsert_key",
            set_=update_cols,
        )
        conn.execute(stmt)
        count += 1

    return count


def upsert_payment_adjustments(conn: Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert provider_payment_adjustments rows.

    Upsert key: (provider_id, program, program_year)

    Ensures provider exists before inserting (creates minimal stub if not).
    """
    if not rows:
        return 0

    table = _get_table(conn, "provider_payment_adjustments")
    providers_table = _get_table(conn, "providers")
    count = 0

    for row in rows:
        data = _filter_columns(row, table)
        if not data.get("provider_id") or not data.get("program"):
            continue

        # Ensure provider exists (VBP/HACRP may reference providers not in General Info)
        provider_exists = conn.execute(
            sa.select(providers_table.c.provider_id)
            .where(providers_table.c.provider_id == data["provider_id"])
        ).fetchone()

        if not provider_exists:
            conn.execute(providers_table.insert().values(
                provider_id=data["provider_id"],
                provider_type="HOSPITAL",
                name=f"Provider {data['provider_id']}",
                is_active=True,
            ))

        now = datetime.utcnow()
        data["updated_at"] = now

        stmt = pg_insert(table).values(**data)
        update_cols = {k: v for k, v in data.items()
                       if k not in ("provider_id", "program", "program_year", "created_at", "id")}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_ppa_upsert_key",
            set_=update_cols,
        )
        conn.execute(stmt)
        count += 1

    return count


def upsert_inspection_events(
    conn: Connection,
    rows: list[dict[str, Any]],
    vintage: str | None = None,
) -> int:
    """Upsert provider_inspection_events rows with DEC-028 lifecycle tracking.

    Upsert key: (provider_id, event_id, deficiency_tag)

    On INSERT: sets originally_published_scope_severity and originally_published_vintage.
    On UPDATE: if scope_severity_code changed, sets is_contested=True and appends
    to scope_severity_history.
    """
    if not rows:
        return 0

    table = _get_table(conn, "provider_inspection_events")
    count = 0

    for row in rows:
        data = _filter_columns(row, table)
        if not data.get("provider_id") or not data.get("deficiency_tag"):
            continue

        # Preserve private fields for DEC-028 IDR tracking before they're stripped
        idr_flag = row.get("_citation_under_idr", False)

        now = datetime.utcnow()
        data["updated_at"] = now
        data["last_seen_vintage"] = vintage

        # Check if row already exists
        existing = conn.execute(
            sa.select(table.c.id, table.c.scope_severity_code, table.c.scope_severity_history)
            .where(table.c.provider_id == data["provider_id"])
            .where(table.c.event_id == data.get("event_id"))
            .where(table.c.deficiency_tag == data["deficiency_tag"])
        ).fetchone()

        if existing is None:
            # INSERT: first time seeing this citation
            data["originally_published_scope_severity"] = data.get("scope_severity_code")
            data["originally_published_vintage"] = vintage
            data["is_contested"] = False
            conn.execute(table.insert().values(**data))
        else:
            # UPDATE: citation already exists
            old_ss = existing.scope_severity_code
            new_ss = data.get("scope_severity_code")

            update_data = {k: v for k, v in data.items()
                           if k not in ("provider_id", "event_id", "deficiency_tag",
                                        "created_at", "id", "originally_published_scope_severity",
                                        "originally_published_vintage")}

            # DEC-028: detect scope/severity change
            if old_ss and new_ss and old_ss != new_ss:
                update_data["is_contested"] = True
                history = existing.scope_severity_history or []
                if isinstance(history, str):
                    history = json.loads(history)
                history.append({
                    "code": new_ss,
                    "vintage": vintage,
                    "previous": old_ss,
                    "idr": bool(idr_flag),
                })
                update_data["scope_severity_history"] = history

            conn.execute(
                table.update()
                .where(table.c.id == existing.id)
                .values(**update_data)
            )

        count += 1

    return count


def upsert_penalties(
    conn: Connection,
    rows: list[dict[str, Any]],
    vintage: str | None = None,
) -> int:
    """Upsert provider_penalties rows with DEC-028 lifecycle tracking.

    Upsert key: (provider_id, penalty_date, penalty_type)

    On INSERT: sets originally_published_fine_amount and originally_published_vintage.
    On UPDATE: updates current fine_amount (changes are normal per DEC-028 findings).
    """
    if not rows:
        return 0

    table = _get_table(conn, "provider_penalties")
    count = 0

    for row in rows:
        data = _filter_columns(row, table)
        if not data.get("provider_id") or not data.get("penalty_type"):
            continue

        now = datetime.utcnow()
        data["updated_at"] = now
        data["last_seen_vintage"] = vintage

        # Check if row exists
        existing = conn.execute(
            sa.select(table.c.id)
            .where(table.c.provider_id == data["provider_id"])
            .where(table.c.penalty_date == data.get("penalty_date"))
            .where(table.c.penalty_type == data["penalty_type"])
        ).fetchone()

        if existing is None:
            data["originally_published_fine_amount"] = data.get("fine_amount")
            data["originally_published_vintage"] = vintage
            conn.execute(table.insert().values(**data))
        else:
            update_data = {k: v for k, v in data.items()
                           if k not in ("provider_id", "penalty_date", "penalty_type",
                                        "created_at", "id", "originally_published_fine_amount",
                                        "originally_published_vintage")}
            conn.execute(
                table.update()
                .where(table.c.id == existing.id)
                .values(**update_data)
            )

        count += 1

    return count


def upsert_ownership(conn: Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert provider_ownership rows.

    Upsert key: (provider_id, owner_name, role)
    """
    if not rows:
        return 0

    table = _get_table(conn, "provider_ownership")
    count = 0

    for row in rows:
        data = _filter_columns(row, table)
        if not data.get("provider_id") or not data.get("owner_name"):
            continue

        now = datetime.utcnow()
        data["updated_at"] = now

        stmt = pg_insert(table).values(**data)
        update_cols = {k: v for k, v in data.items()
                       if k not in ("provider_id", "owner_name", "role", "created_at", "id")}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_po_upsert_key",
            set_=update_cols,
        )
        conn.execute(stmt)
        count += 1

    return count
