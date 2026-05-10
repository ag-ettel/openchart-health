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


# Postgres caps a query at 65,535 bind parameters. Multi-row INSERT uses
# one parameter per (column × row); pick a batch size that stays well under.
_PG_MAX_PARAMS = 65000


def _safe_batch_size(num_columns: int, target: int = 5000) -> int:
    """Largest safe batch size for `num_columns` per row."""
    if num_columns <= 0:
        return target
    return max(1, min(target, _PG_MAX_PARAMS // num_columns))


def upsert_measure_values(
    conn: Connection,
    rows: list[dict[str, Any]],
    provider_type: str = "HOSPITAL",
    batch_size: int = 5000,
    pipeline_run_id: Any = None,
) -> int:
    """Bulk upsert provider_measure_values rows.

    Upsert key: (provider_id, measure_id, period_label, stratification).
    Uses PostgreSQL multi-row INSERT ... ON CONFLICT DO UPDATE in batches of
    `batch_size`. Replaces per-row upsert which was the dominant pipeline
    bottleneck (~400 rows/sec → ~4,000+ rows/sec).

    `pipeline_run_id` (when supplied) is stamped on every row for audit trail.
    """
    if not rows:
        return 0

    table = _get_table(conn, "provider_measure_values")
    conflict_cols = ["provider_id", "measure_id", "period_label", "stratification"]

    # First pass: filter columns, defaults, drop rows missing the upsert key.
    prepared: list[dict[str, Any]] = []
    unknown_measures: set[str] = set()
    unknown_providers: set[str] = set()
    now = datetime.utcnow()

    for row in rows:
        data = _filter_columns(row, table)
        data.setdefault("provider_type", provider_type)
        data.setdefault("stratification", "")
        if not all(data.get(c) is not None for c in conflict_cols):
            logger.warning("Missing upsert key field in measure value: %s", data.get("measure_id"))
            continue
        data["updated_at"] = now
        if pipeline_run_id is not None:
            data["pipeline_run_id"] = pipeline_run_id
        prepared.append(data)
        unknown_measures.add(data["measure_id"])
        unknown_providers.add(data["provider_id"])

    if not prepared:
        return 0

    # Batch-register any new measures and providers before bulk insert (FK satisfaction).
    for mid in unknown_measures:
        ensure_measure_exists(conn, mid)
    for pid in unknown_providers:
        _ensure_provider_exists(conn, pid, provider_type)

    # Compute the union of keys across all rows; SQLAlchemy bulk values needs
    # every dict to have the same shape, with None for absent fields.
    all_keys = set()
    for d in prepared:
        all_keys.update(d.keys())
    for d in prepared:
        for k in all_keys:
            d.setdefault(k, None)

    update_keys = [
        k for k in all_keys
        if k not in conflict_cols and k not in ("created_at", "id")
    ]

    safe_size = _safe_batch_size(len(all_keys), batch_size)
    count = 0
    for i in range(0, len(prepared), safe_size):
        batch = prepared[i:i + safe_size]
        stmt = pg_insert(table).values(batch)
        set_ = {k: getattr(stmt.excluded, k) for k in update_keys}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_pmv_upsert_key",
            set_=set_,
        )
        conn.execute(stmt)
        count += len(batch)

    return count


def upsert_payment_adjustments(
    conn: Connection,
    rows: list[dict[str, Any]],
    batch_size: int = 5000,
    pipeline_run_id: Any = None,
) -> int:
    """Bulk upsert provider_payment_adjustments rows.

    Upsert key: (provider_id, program, program_year).
    Ensures provider exists before inserting (creates minimal stub if not).
    """
    if not rows:
        return 0

    table = _get_table(conn, "provider_payment_adjustments")
    conflict_cols = ["provider_id", "program", "program_year"]

    prepared: list[dict[str, Any]] = []
    needed_providers: set[str] = set()
    now = datetime.utcnow()

    for row in rows:
        data = _filter_columns(row, table)
        if not data.get("provider_id") or not data.get("program"):
            continue
        data["updated_at"] = now
        if pipeline_run_id is not None:
            data["pipeline_run_id"] = pipeline_run_id
        prepared.append(data)
        needed_providers.add(data["provider_id"])

    if not prepared:
        return 0

    # Ensure provider stubs exist for any payment-adjustment-only providers.
    for pid in needed_providers:
        _ensure_provider_exists(conn, pid, "HOSPITAL")

    all_keys = set()
    for d in prepared:
        all_keys.update(d.keys())
    for d in prepared:
        for k in all_keys:
            d.setdefault(k, None)

    update_keys = [
        k for k in all_keys
        if k not in conflict_cols and k not in ("created_at", "id")
    ]

    safe_size = _safe_batch_size(len(all_keys), batch_size)
    count = 0
    for i in range(0, len(prepared), safe_size):
        batch = prepared[i:i + safe_size]
        stmt = pg_insert(table).values(batch)
        set_ = {k: getattr(stmt.excluded, k) for k in update_keys}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_ppa_upsert_key",
            set_=set_,
        )
        conn.execute(stmt)
        count += len(batch)

    return count


def upsert_inspection_events(
    conn: Connection,
    rows: list[dict[str, Any]],
    vintage: str | None = None,
    pipeline_run_id: Any = None,
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
    now = datetime.utcnow()

    # Filter once and gather all keys we'll need to look up.
    prepared: list[tuple[dict[str, Any], bool]] = []  # (data, idr_flag)
    keys_needed: set[tuple[str, str | None, str]] = set()
    for row in rows:
        data = _filter_columns(row, table)
        if not data.get("provider_id") or not data.get("deficiency_tag"):
            continue
        idr_flag = row.get("_citation_under_idr", False)
        data["updated_at"] = now
        data["last_seen_vintage"] = vintage
        if pipeline_run_id is not None:
            data["pipeline_run_id"] = pipeline_run_id
        prepared.append((data, idr_flag))
        keys_needed.add((data["provider_id"], data.get("event_id"), data["deficiency_tag"]))

    if not prepared:
        return 0

    # Pre-fetch existing rows in batches — one round-trip per ~5K keys instead
    # of one per row. Cuts inspection_events upsert from O(N) round-trips to
    # O(N/batch_size) round-trips for the lookup phase.
    existing_by_key: dict[tuple[str, str | None, str], Any] = {}
    keys_list = list(keys_needed)
    LOOKUP_BATCH = 5000
    for i in range(0, len(keys_list), LOOKUP_BATCH):
        chunk = keys_list[i:i + LOOKUP_BATCH]
        rows_existing = conn.execute(
            sa.select(
                table.c.id,
                table.c.provider_id,
                table.c.event_id,
                table.c.deficiency_tag,
                table.c.scope_severity_code,
                table.c.scope_severity_history,
            ).where(
                sa.tuple_(table.c.provider_id, table.c.event_id, table.c.deficiency_tag).in_(
                    [(p, e, d) for p, e, d in chunk]
                )
            )
        ).fetchall()
        for r in rows_existing:
            existing_by_key[(r.provider_id, r.event_id, r.deficiency_tag)] = r

    count = 0
    inserts: list[dict[str, Any]] = []
    for data, idr_flag in prepared:
        key = (data["provider_id"], data.get("event_id"), data["deficiency_tag"])
        existing = existing_by_key.get(key)

        if existing is None:
            # INSERT: first time seeing this citation
            data["originally_published_scope_severity"] = data.get("scope_severity_code")
            data["originally_published_vintage"] = vintage
            data["is_contested"] = False
            inserts.append(data)
        else:
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

    # Bulk INSERT new rows. INSERT-only (no ON CONFLICT) since the pre-fetch
    # already proved these don't exist; the unique constraint will still
    # protect against concurrent ingest if it ever happens.
    if inserts:
        # Normalize shape: union of keys, None defaults
        all_keys = set()
        for d in inserts:
            all_keys.update(d.keys())
        for d in inserts:
            for k in all_keys:
                d.setdefault(k, None)
        safe_size = _safe_batch_size(len(all_keys))
        for i in range(0, len(inserts), safe_size):
            batch = inserts[i:i + safe_size]
            conn.execute(table.insert().values(batch))
            count += len(batch)

    return count


def upsert_penalties(
    conn: Connection,
    rows: list[dict[str, Any]],
    vintage: str | None = None,
    pipeline_run_id: Any = None,
) -> int:
    """Upsert provider_penalties rows with DEC-028 lifecycle tracking.

    Upsert key: (provider_id, penalty_date, penalty_type)

    On INSERT: sets originally_published_fine_amount and originally_published_vintage.
    On UPDATE: updates current fine_amount (changes are normal per DEC-028 findings).
    """
    if not rows:
        return 0

    table = _get_table(conn, "provider_penalties")
    now = datetime.utcnow()

    prepared: list[dict[str, Any]] = []
    keys_needed: set[tuple[str, Any, str]] = set()
    for row in rows:
        data = _filter_columns(row, table)
        if not data.get("provider_id") or not data.get("penalty_type"):
            continue
        data["updated_at"] = now
        data["last_seen_vintage"] = vintage
        if pipeline_run_id is not None:
            data["pipeline_run_id"] = pipeline_run_id
        prepared.append(data)
        keys_needed.add((data["provider_id"], data.get("penalty_date"), data["penalty_type"]))

    if not prepared:
        return 0

    # Pre-fetch existing keys (same pattern as upsert_inspection_events)
    existing_ids: dict[tuple[str, Any, str], Any] = {}
    LOOKUP_BATCH = 5000
    keys_list = list(keys_needed)
    for i in range(0, len(keys_list), LOOKUP_BATCH):
        chunk = keys_list[i:i + LOOKUP_BATCH]
        rows_existing = conn.execute(
            sa.select(
                table.c.id,
                table.c.provider_id,
                table.c.penalty_date,
                table.c.penalty_type,
            ).where(
                sa.tuple_(table.c.provider_id, table.c.penalty_date, table.c.penalty_type).in_(chunk)
            )
        ).fetchall()
        for r in rows_existing:
            existing_ids[(r.provider_id, r.penalty_date, r.penalty_type)] = r.id

    count = 0
    inserts: list[dict[str, Any]] = []
    for data in prepared:
        key = (data["provider_id"], data.get("penalty_date"), data["penalty_type"])
        existing_id = existing_ids.get(key)

        if existing_id is None:
            data["originally_published_fine_amount"] = data.get("fine_amount")
            data["originally_published_vintage"] = vintage
            inserts.append(data)
        else:
            update_data = {k: v for k, v in data.items()
                           if k not in ("provider_id", "penalty_date", "penalty_type",
                                        "created_at", "id", "originally_published_fine_amount",
                                        "originally_published_vintage")}
            conn.execute(
                table.update()
                .where(table.c.id == existing_id)
                .values(**update_data)
            )
            count += 1

    if inserts:
        all_keys = set()
        for d in inserts:
            all_keys.update(d.keys())
        for d in inserts:
            for k in all_keys:
                d.setdefault(k, None)
        safe_size = _safe_batch_size(len(all_keys))
        for i in range(0, len(inserts), safe_size):
            batch = inserts[i:i + safe_size]
            conn.execute(table.insert().values(batch))
            count += len(batch)
    return count


def upsert_benchmarks(conn: Connection, rows: list[dict[str, Any]], pipeline_run_id: Any = None) -> int:
    """Upsert measure_benchmarks rows.

    Upsert key: (measure_id, geography_type, geography_code, period_label).

    DEC-036: only stores CMS-published averages. The pipeline must never compute
    a benchmark from provider data. Skips rows whose measure_id is not in the
    `measures` reference table (e.g., HCAHPS columns CMS publishes but we don't
    register, retired measure codes).
    """
    if not rows:
        return 0

    table = _get_table(conn, "measure_benchmarks")
    measures_table = _get_table(conn, "measures")
    count = 0
    skipped_unknown = 0

    # Cache known measure_ids for this run.
    known_ids: set[str] = {
        r[0] for r in conn.execute(sa.select(measures_table.c.measure_id)).fetchall()
    }

    for row in rows:
        data = _filter_columns(row, table)
        mid = data.get("measure_id")
        geo_type = data.get("geography_type")
        geo_code = data.get("geography_code")
        period = data.get("period_label")
        if not (mid and geo_type and geo_code and period):
            continue

        if mid not in known_ids:
            skipped_unknown += 1
            continue

        now = datetime.utcnow()
        data["updated_at"] = now
        if pipeline_run_id is not None:
            data["pipeline_run_id"] = pipeline_run_id

        stmt = pg_insert(table).values(**data)
        update_cols = {
            k: v for k, v in data.items()
            if k not in ("measure_id", "geography_type", "geography_code",
                         "period_label", "created_at", "id")
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_measure_benchmarks_upsert",
            set_=update_cols,
        )
        conn.execute(stmt)
        count += 1

    if skipped_unknown:
        logger.info("Skipped %d benchmark rows whose measure_id is not in measures table", skipped_unknown)

    return count


def upsert_ownership(
    conn: Connection,
    rows: list[dict[str, Any]],
    batch_size: int = 5000,
    pipeline_run_id: Any = None,
) -> int:
    """Bulk upsert provider_ownership rows.

    Upsert key: (provider_id, owner_name, role).
    """
    if not rows:
        return 0

    table = _get_table(conn, "provider_ownership")
    conflict_cols = ["provider_id", "owner_name", "role"]

    prepared: list[dict[str, Any]] = []
    now = datetime.utcnow()

    for row in rows:
        data = _filter_columns(row, table)
        if not data.get("provider_id") or not data.get("owner_name"):
            continue
        data["updated_at"] = now
        if pipeline_run_id is not None:
            data["pipeline_run_id"] = pipeline_run_id
        prepared.append(data)

    if not prepared:
        return 0

    all_keys = set()
    for d in prepared:
        all_keys.update(d.keys())
    for d in prepared:
        for k in all_keys:
            d.setdefault(k, None)

    update_keys = [
        k for k in all_keys
        if k not in conflict_cols and k not in ("created_at", "id")
    ]

    safe_size = _safe_batch_size(len(all_keys), batch_size)
    count = 0
    for i in range(0, len(prepared), safe_size):
        batch = prepared[i:i + safe_size]
        stmt = pg_insert(table).values(batch)
        set_ = {k: getattr(stmt.excluded, k) for k in update_keys}
        stmt = stmt.on_conflict_do_update(
            constraint="uq_po_upsert_key",
            set_=set_,
        )
        conn.execute(stmt)
        count += len(batch)

    return count
