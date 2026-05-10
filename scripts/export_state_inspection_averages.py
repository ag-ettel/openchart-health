"""Compute per-state nursing-home inspection severity averages and emit JSON.

Aggregations use the same 120-day clustering as scripts/export_parent_group_stats.py
and the per-facility / compare InspectionSummary views: each facility contributes
one observation — the citation counts in its most recent inspection event, where
an "event" is the most-recent survey plus any survey within 120 days of it.

Output:
    {output_dir}/state_inspection_averages.json
        {
          "states": {
              "AL": {"ac": .., "df": .., "ghi": .., "jkl": .., "total": ..,
                     "facility_count": int, "pct_facilities_with_recent_ij": .. },
              ...
          },
          "national": { same shape, computed across all states },
          "computed_at": ISO8601,
          "method": "120-day clustering anchored at most recent date; one
                     observation per facility"
        }

Why state-level: nursing home inspection regimes vary substantially by state.
Some states cite at higher overall rates; others escalate to immediate jeopardy
more readily. Comparing a facility only to the national average can mislead
in either direction. The state row gives the contextual baseline. See
frontend/components/InspectionSummary.tsx and CompareInspectionSummary.tsx for
how the JSON is consumed.

Run independently:
    python -m scripts.export_state_inspection_averages

The function `build_state_inspection_averages(conn)` is also imported by
pipeline/export/build_json.py to produce the file as part of every export run.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)

# Same window used by the per-facility InspectionSummary, the compare view, and
# scripts/export_parent_group_stats.py. Must stay in sync.
CLUSTER_WINDOW_DAYS = 120


def _severity_bucket(code: str | None) -> str | None:
    if not code:
        return None
    if code in "ABC":
        return "ac"
    if code in "DEF":
        return "df"
    if code in "GHI":
        return "ghi"
    if code in "JKL":
        return "jkl"
    return None


def _most_recent_event_per_facility(
    events: list[tuple],
) -> tuple[dict[str, int], bool]:
    """Counts in the most recent inspection event for one facility, plus a
    boolean indicating whether that event included any J-L citation.

    Args:
        events: list of (date, scope_severity_code) tuples for one facility.

    Returns:
        (counts, has_ij) where counts has keys ac/df/ghi/jkl/total.
    """
    counts = {"ac": 0, "df": 0, "ghi": 0, "jkl": 0, "total": 0}
    if not events:
        return counts, False

    events_sorted = sorted(events, key=lambda x: x[0], reverse=True)
    most_recent_date = events_sorted[0][0]

    has_ij = False
    for d, code in events_sorted:
        if (most_recent_date - d).days > CLUSTER_WINDOW_DAYS:
            break
        b = _severity_bucket(code)
        if b is None:
            continue
        counts[b] += 1
        counts["total"] += 1
        if b == "jkl":
            has_ij = True
    return counts, has_ij


def build_state_inspection_averages(conn: Connection) -> dict[str, Any]:
    """Compute per-state and national inspection severity averages.

    Reads providers + provider_inspection_events. For each active nursing
    home, computes the citation counts in its most recent inspection event
    (120-day cluster), buckets by state, and averages.

    The national row is computed across the same set of facilities. It is
    NOT an unweighted average of state averages — it is each facility's own
    observation aggregated, so states with more facilities contribute more.
    """
    sql = """
        SELECT p.state, ie.provider_id, ie.survey_date, ie.scope_severity_code
        FROM providers p
        JOIN provider_inspection_events ie ON ie.provider_id = p.provider_id
        WHERE p.provider_type = 'NURSING_HOME'
          AND p.is_active = true
          AND ie.survey_date IS NOT NULL
          AND ie.scope_severity_code IS NOT NULL
    """
    rows = conn.execute(sa.text(sql)).fetchall()
    logger.info(
        "Loaded %d citation rows for state inspection averages", len(rows)
    )

    by_state_provider: dict[str, dict[str, list[tuple]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for state, pid, d, code in rows:
        if not state:
            continue
        by_state_provider[state][pid].append((d, code))

    states: dict[str, dict[str, Any]] = {}
    nat_sums = {"ac": 0.0, "df": 0.0, "ghi": 0.0, "jkl": 0.0, "total": 0.0}
    nat_facs = 0
    nat_ij = 0

    for state, providers in by_state_provider.items():
        sums = {"ac": 0.0, "df": 0.0, "ghi": 0.0, "jkl": 0.0, "total": 0.0}
        n_facs = 0
        n_with_ij = 0
        for evs in providers.values():
            counts, has_ij = _most_recent_event_per_facility(evs)
            if counts["total"] == 0 and not evs:
                continue
            for k in sums:
                sums[k] += counts[k]
            n_facs += 1
            if has_ij:
                n_with_ij += 1
            # National rolls up the same facility-level observations
            for k in nat_sums:
                nat_sums[k] += counts[k]
            nat_facs += 1
            if has_ij:
                nat_ij += 1
        if n_facs == 0:
            continue
        states[state] = {
            "ac": round(sums["ac"] / n_facs, 3),
            "df": round(sums["df"] / n_facs, 3),
            "ghi": round(sums["ghi"] / n_facs, 3),
            "jkl": round(sums["jkl"] / n_facs, 3),
            "total": round(sums["total"] / n_facs, 3),
            "facility_count": n_facs,
            "pct_facilities_with_recent_ij": round(n_with_ij / n_facs, 4),
        }

    if nat_facs == 0:
        national: dict[str, Any] = {
            "ac": 0.0, "df": 0.0, "ghi": 0.0, "jkl": 0.0, "total": 0.0,
            "facility_count": 0, "pct_facilities_with_recent_ij": 0.0,
        }
    else:
        national = {
            "ac": round(nat_sums["ac"] / nat_facs, 3),
            "df": round(nat_sums["df"] / nat_facs, 3),
            "ghi": round(nat_sums["ghi"] / nat_facs, 3),
            "jkl": round(nat_sums["jkl"] / nat_facs, 3),
            "total": round(nat_sums["total"] / nat_facs, 3),
            "facility_count": nat_facs,
            "pct_facilities_with_recent_ij": round(nat_ij / nat_facs, 4),
        }

    return {
        "states": states,
        "national": national,
        "computed_at": datetime.now().isoformat(),
        "method": (
            f"{CLUSTER_WINDOW_DAYS}-day clustering anchored at most recent "
            f"date; one observation per facility"
        ),
    }


def write_state_inspection_averages(
    conn: Connection, output_dir: str | Path
) -> Path:
    """Compute and write the JSON to output_dir/state_inspection_averages.json.

    Returns the path written.
    """
    payload = build_state_inspection_averages(conn)
    output_path = Path(output_dir) / "state_inspection_averages.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    logger.info(
        "Wrote state_inspection_averages.json (%d states, %d facilities national)",
        len(payload["states"]),
        payload["national"]["facility_count"],
    )
    return output_path


def main() -> None:
    """Standalone entrypoint: writes to build/data/."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    db_url = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"
    engine = sa.create_engine(db_url)
    with engine.connect() as conn:
        path = write_state_inspection_averages(conn, "build/data")
    print(f"Wrote {path}")
    engine.dispose()


if __name__ == "__main__":
    main()
