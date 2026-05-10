"""
Load reviewed ownership clusters CSV into the database.

Reads data/ownership_clusters_review.csv (after human review) and upserts
into ownership_parent_groups and ownership_entity_group_map tables.

Usage:
    python scripts/load_ownership_groups.py [--csv PATH] [--mark-verified]

Options:
    --csv PATH          Path to reviewed CSV (default: data/ownership_clusters_review.csv)
    --mark-verified     Set review_status to "human_verified" for all rows
                        (use after human review is complete). Default: "auto_matched".

Requires: PostgreSQL connection and migration 003 applied.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"


def load_csv(csv_path: Path) -> list[dict[str, str]]:
    """Read the review CSV and return rows as dicts."""
    if not csv_path.exists():
        logger.error("CSV file not found: %s", csv_path)
        sys.exit(1)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    logger.info("Read %d rows from %s", len(rows), csv_path)
    return rows


def upsert_groups(
    engine: sa.Engine,
    rows: list[dict[str, str]],
    review_status: str,
) -> tuple[int, int]:
    """Upsert parent groups and entity mappings.

    Returns (groups_upserted, mappings_upserted).
    """
    # Group rows by parent_group_id
    groups: dict[str, dict] = {}
    mappings: list[dict] = []

    for row in rows:
        pgid = row["parent_group_id"]
        if pgid not in groups:
            groups[pgid] = {
                "parent_group_id": pgid,
                "parent_group_name": row["parent_group_name"],
                "review_status": review_status,
            }

        mappings.append({
            "entity_name": row["entity_name"],
            "parent_group_id": pgid,
            "match_method": row["match_method"],
            "match_confidence": Decimal(row["match_confidence"]),
        })

    metadata = sa.MetaData()

    with engine.begin() as conn:
        metadata.reflect(bind=engine, only=[
            "ownership_parent_groups", "ownership_entity_group_map"
        ])

        pg_table = metadata.tables["ownership_parent_groups"]
        map_table = metadata.tables["ownership_entity_group_map"]

        # Upsert parent groups
        group_count = 0
        now = datetime.utcnow()

        for group_data in groups.values():
            group_data["updated_at"] = now
            stmt = pg_insert(pg_table).values(**group_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["parent_group_id"],
                set_={
                    "parent_group_name": group_data["parent_group_name"],
                    "review_status": group_data["review_status"],
                    "updated_at": now,
                },
            )
            conn.execute(stmt)
            group_count += 1

        logger.info("Upserted %d parent groups", group_count)

        # Upsert entity mappings
        map_count = 0
        for mapping in mappings:
            mapping["updated_at"] = now
            stmt = pg_insert(map_table).values(**mapping)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_oegm_entity_name",
                set_={
                    "parent_group_id": mapping["parent_group_id"],
                    "match_method": mapping["match_method"],
                    "match_confidence": mapping["match_confidence"],
                    "updated_at": now,
                },
            )
            conn.execute(stmt)
            map_count += 1

        logger.info("Upserted %d entity mappings", map_count)

    return group_count, map_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load reviewed ownership clusters into the database."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("data/ownership_clusters_review.csv"),
        help="Path to reviewed CSV file",
    )
    parser.add_argument(
        "--mark-verified",
        action="store_true",
        help="Set review_status to 'human_verified' (use after human review)",
    )
    args = parser.parse_args()

    review_status = "human_verified" if args.mark_verified else "auto_matched"
    logger.info("Review status will be set to: %s", review_status)

    rows = load_csv(args.csv)

    if not rows:
        logger.warning("No rows to load. Exiting.")
        return

    engine = sa.create_engine(DB_URL)
    groups, mappings = upsert_groups(engine, rows, review_status)
    engine.dispose()

    logger.info("Done. Loaded %d parent groups with %d entity mappings.", groups, mappings)


if __name__ == "__main__":
    main()
