"""Build national distribution histograms for each measure.

Outputs build/data/distributions.json with 25-bin histograms for every
(measure_id, period_label) pair. Used by the frontend histogram component.

Usage:
    python scripts/build_distributions.py

Reads from provider_measure_values in the database. No migration needed.
"""

import json
import math
from pathlib import Path

import numpy as np
import sqlalchemy as sa

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"
OUTPUT_PATH = Path("build/data/distributions.json")
NUM_BINS = 25


def compute_histogram(
    values: list[float], num_bins: int = NUM_BINS
) -> dict:
    """Compute a histogram with fixed bin count."""
    arr = np.array(values)
    # Use numpy histogram with auto-range
    counts, bin_edges = np.histogram(arr, bins=num_bins)
    return {
        "counts": counts.tolist(),
        "bin_edges": [round(float(e), 4) for e in bin_edges],
        "total": len(values),
        "mean": round(float(arr.mean()), 4),
        "median": round(float(np.median(arr)), 4),
        "p5": round(float(np.percentile(arr, 5)), 4),
        "p25": round(float(np.percentile(arr, 25)), 4),
        "p75": round(float(np.percentile(arr, 75)), 4),
        "p95": round(float(np.percentile(arr, 95)), 4),
    }


def main() -> None:
    engine = sa.create_engine(DB_URL)
    distributions: dict[str, dict] = {}

    with engine.connect() as conn:
        # Get all measure/period pairs with enough data for a meaningful histogram
        pairs = conn.execute(sa.text("""
            SELECT pmv.measure_id, pmv.period_label,
                   array_agg(pmv.numeric_value ORDER BY pmv.numeric_value) as values
            FROM provider_measure_values pmv
            JOIN providers p ON pmv.provider_id = p.provider_id
            WHERE pmv.numeric_value IS NOT NULL
              AND pmv.suppressed = false
              AND pmv.not_reported = false
              AND pmv.stratification = ''
              AND p.provider_type = 'HOSPITAL'
            GROUP BY pmv.measure_id, pmv.period_label
            HAVING COUNT(*) >= 30
        """))

        for row in pairs:
            measure_id = row[0]
            period_label = row[1]
            values = [float(v) for v in row[2]]

            hist = compute_histogram(values)
            key = f"{measure_id}|{period_label}"
            distributions[key] = hist

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(distributions, f)

    print(f"Built distributions for {len(distributions)} measure/period pairs -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
