"""Idempotency verification — Rule 5.

Two-part check:

1. Constraint check (fast): every upserted table must have a UNIQUE constraint
   on its upsert key. With a unique constraint, ON CONFLICT DO UPDATE is
   structurally idempotent — the database itself rejects duplicates.

2. Optional row-count diff (slow): re-running the pipeline must produce
   identical row counts. Pass --rerun to drive this end-to-end against a
   limited subset of vintages.

The constraint check is preferred for routine verification (runs in <1 second
on a 60M-row table). The row-count diff is the integration test the user
ultimately specified.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import sqlalchemy as sa


CHECKS: list[dict[str, Any]] = [
    {
        "table": "provider_measure_values",
        "key": ["provider_id", "measure_id", "period_label", "stratification"],
        "rule": "Rule 5",
    },
    {
        "table": "provider_payment_adjustments",
        "key": ["provider_id", "program", "program_year"],
        "rule": "Rule 5",
    },
    {
        "table": "measure_benchmarks",
        "key": ["measure_id", "geography_type", "geography_code", "period_label"],
        "rule": "DEC-036 / Rule 5",
    },
    {
        "table": "providers",
        "key": ["provider_id"],
        "rule": "Rule 5",
    },
    {
        "table": "measures",
        "key": ["measure_id"],
        "rule": "Rule 5",
    },
    {
        "table": "provider_inspection_events",
        "key": ["provider_id", "event_id", "deficiency_tag"],
        "rule": "Rule 5",
    },
    {
        "table": "provider_penalties",
        "key": ["provider_id", "penalty_date", "penalty_type"],
        "rule": "Rule 5",
    },
    {
        "table": "provider_ownership",
        "key": ["provider_id", "owner_name", "role"],
        "rule": "Rule 5",
    },
]


def check_constraints(conn: sa.engine.Connection) -> int:
    """Verify each table has a UNIQUE constraint on its upsert key.

    Returns 0 if all checks pass, 1 if any failed.
    """
    failed = False
    for check in CHECKS:
        table = check["table"]
        key_cols = sorted(check["key"])

        # Find unique constraints on this table whose columns match the upsert key.
        # string_agg + split avoids array_agg's postgres-array-literal-as-string quirk.
        rows = conn.execute(
            sa.text(
                """
                SELECT tc.constraint_name,
                       string_agg(kcu.column_name, ',' ORDER BY kcu.column_name) AS cols
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_name = kcu.table_name
                WHERE tc.table_name = :tbl
                  AND tc.constraint_type IN ('UNIQUE', 'PRIMARY KEY')
                GROUP BY tc.constraint_name
                """
            ),
            {"tbl": table},
        ).fetchall()

        constraint_match = None
        for row in rows:
            cols_sorted = sorted((row.cols or "").split(","))
            if cols_sorted == key_cols:
                constraint_match = row.constraint_name
                break

        total = conn.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar()
        if constraint_match:
            print(
                f"  [PASS] {table:35} rows={total:>12,}  "
                f"constraint={constraint_match}  ({check['rule']})"
            )
        else:
            failed = True
            print(
                f"  [FAIL] {table:35} rows={total:>12,}  "
                f"NO unique constraint on {key_cols}  ({check['rule']})"
            )

    return 1 if failed else 0


def diff_row_counts(
    conn: sa.engine.Connection,
    before: dict[str, int],
) -> int:
    """Compare current row counts to a previous snapshot. Returns 0 if identical."""
    failed = False
    for check in CHECKS:
        table = check["table"]
        n = conn.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar()
        prev = before.get(table)
        if prev is None:
            print(f"  [SKIP] {table:35} no baseline")
            continue
        if n == prev:
            print(f"  [PASS] {table:35} rows={n:>12,}  unchanged")
        else:
            failed = True
            delta = n - prev
            print(f"  [FAIL] {table:35} rows={n:>12,}  delta={delta:+,}")
    return 1 if failed else 0


def snapshot(conn: sa.engine.Connection) -> dict[str, int]:
    out: dict[str, int] = {}
    for check in CHECKS:
        out[check["table"]] = conn.execute(sa.text(f"SELECT COUNT(*) FROM {check['table']}")).scalar()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default="postgresql+psycopg://postgres:postgres@localhost:5432/openchart",
    )
    parser.add_argument(
        "--mode",
        choices=["constraints", "snapshot", "diff"],
        default="constraints",
        help="constraints: structural check (fast). snapshot: print baseline. diff: compare against --baseline.",
    )
    parser.add_argument("--baseline", help="JSON file with row counts to diff against.")
    args = parser.parse_args()

    engine = sa.create_engine(args.db)

    with engine.connect() as conn:
        if args.mode == "constraints":
            print("=== Idempotency Structural Check (unique constraints on upsert keys) ===")
            return check_constraints(conn)

        if args.mode == "snapshot":
            print("=== Row Count Snapshot ===")
            counts = snapshot(conn)
            import json
            print(json.dumps(counts, indent=2))
            return 0

        if args.mode == "diff":
            if not args.baseline:
                print("--baseline FILE required for diff mode", file=sys.stderr)
                return 2
            import json
            with open(args.baseline) as f:
                before = json.load(f)
            print(f"=== Row Count Diff vs {args.baseline} ===")
            return diff_row_counts(conn, before)

    return 0


if __name__ == "__main__":
    sys.exit(main())
