"""Build national reporting rates for each hospital measure.

Outputs build/data/reporting_rates.json with the percentage of hospitals
that report each measure. Used by the frontend NotReportedCard component
to give context on whether non-reporting is common or unusual.

Usage:
    python scripts/build_reporting_rates.py

Reads from provider_measure_values and providers tables. No migration needed.
"""

import json
from pathlib import Path

import sqlalchemy as sa

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"
OUTPUT_PATH = Path("build/data/reporting_rates.json")


def main() -> None:
    engine = sa.create_engine(DB_URL)
    rates: dict[str, dict[str, object]] = {}

    with engine.connect() as conn:
        # Total hospital count (active hospitals with at least one measure)
        total_result = conn.execute(sa.text("""
            SELECT COUNT(DISTINCT p.provider_id)
            FROM providers p
            JOIN provider_measure_values pmv ON p.provider_id = pmv.provider_id
            WHERE p.provider_type = 'HOSPITAL'
        """))
        total_hospitals = total_result.scalar() or 0

        if total_hospitals == 0:
            print("No hospitals found. Exiting.")
            return

        # Per-measure reporting counts for the most recent period per measure
        rows = conn.execute(sa.text("""
            WITH latest_periods AS (
                SELECT measure_id, MAX(period_label) AS period_label
                FROM provider_measure_values pmv
                JOIN providers p ON pmv.provider_id = p.provider_id
                WHERE p.provider_type = 'HOSPITAL'
                  AND pmv.stratification = ''
                GROUP BY measure_id
            )
            SELECT
                pmv.measure_id,
                lp.period_label,
                COUNT(*) AS total_rows,
                COUNT(*) FILTER (
                    WHERE pmv.numeric_value IS NOT NULL
                      AND pmv.suppressed = false
                      AND pmv.not_reported = false
                ) AS reported_count,
                COUNT(*) FILTER (
                    WHERE pmv.suppressed = true
                ) AS suppressed_count,
                COUNT(*) FILTER (
                    WHERE pmv.not_reported = true
                ) AS not_reported_count
            FROM provider_measure_values pmv
            JOIN providers p ON pmv.provider_id = p.provider_id
            JOIN latest_periods lp
              ON pmv.measure_id = lp.measure_id
             AND pmv.period_label = lp.period_label
            WHERE p.provider_type = 'HOSPITAL'
              AND pmv.stratification = ''
            GROUP BY pmv.measure_id, lp.period_label
        """))

        for row in rows:
            measure_id: str = row[0]
            period_label: str = row[1]
            total_rows: int = row[2]
            reported: int = row[3]
            suppressed: int = row[4]
            not_reported_count: int = row[5]

            # Denominator = hospitals where CMS has a row for this measure
            # (reported + suppressed + not_reported). This excludes hospital types
            # that don't participate in a given measure program (VA, psychiatric, etc.)
            eligible = total_rows
            pct = round((reported / eligible) * 100, 1) if eligible > 0 else 0.0

            rates[measure_id] = {
                "reported": reported,
                "suppressed": suppressed,
                "not_reported": not_reported_count,
                "eligible_hospitals": eligible,
                "pct_reported": pct,
                "period_label": period_label,
            }

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(rates, f)

    print(
        f"Built reporting rates for {len(rates)} measures "
        f"({total_hospitals} hospitals in database) -> {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
