"""Compute Bayesian credible intervals for HCAHPS primary response measures.

Reads HCAHPS rows from provider_measure_values, derives numerator from
the adjusted percentage × survey count, computes Beta-Binomial CIs using
state/national average priors from measure_benchmarks, and updates the DB.

Then re-exports affected provider JSON files.

Usage:
    python scripts/compute_hcahps_ci.py

Requires PostgreSQL running. See DEC-039 for methodology.
"""

import logging
from decimal import Decimal

import sqlalchemy as sa

from pipeline.config import MEASURE_REGISTRY
from pipeline.transform.credible_intervals import (
    calculate_credible_interval,
    is_ci_calculable,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"

# Primary HCAHPS measure IDs eligible for CI (DEC-039)
PRIMARY_HCAHPS = [
    mid for mid, entry in MEASURE_REGISTRY.items()
    if entry.risk_adjustment_model == "PATIENT_MIX_ADJUSTMENT"
    and entry.numerator_denominator_published is True
    and is_ci_calculable(
        entry.risk_adjustment_model,
        entry.cms_ci_published,
        entry.numerator_denominator_published,
    )
]


def main() -> None:
    engine = sa.create_engine(DB_URL)
    logger.info("CI-eligible HCAHPS measures: %d", len(PRIMARY_HCAHPS))
    logger.info("Measures: %s", ", ".join(sorted(PRIMARY_HCAHPS)))

    updated = 0
    affected_providers: set[str] = set()

    with engine.begin() as conn:
        # Check if ci_source column exists (may not if migration hasn't run)
        col_check = conn.execute(sa.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'provider_measure_values'
              AND column_name = 'ci_source'
        """))
        has_ci_source = col_check.fetchone() is not None

        # Fetch all eligible rows: need numeric_value, sample_size, and
        # state_avg/national_avg (denormalized on the row in current schema)
        rows = conn.execute(sa.text("""
            SELECT pmv.id, pmv.provider_id, pmv.measure_id, pmv.period_label,
                   pmv.numeric_value, pmv.sample_size,
                   pmv.state_avg, pmv.national_avg
            FROM provider_measure_values pmv
            WHERE pmv.measure_id = ANY(:measure_ids)
              AND pmv.stratification = ''
              AND pmv.numeric_value IS NOT NULL
              AND pmv.sample_size IS NOT NULL
              AND pmv.sample_size > 0
              AND pmv.suppressed = false
              AND pmv.not_reported = false
              AND pmv.confidence_interval_lower IS NULL
        """), {"measure_ids": PRIMARY_HCAHPS})

        all_rows = rows.fetchall()
        logger.info("Rows to process: %d", len(all_rows))

        for row in all_rows:
            row_id, provider_id, _, _, numeric_value, sample_size, state_avg, national_avg = row

            # Derive numerator from adjusted percentage × survey count
            pct = float(numeric_value)
            numerator = round(pct * sample_size / 100.0)
            denominator = sample_size

            ci = calculate_credible_interval(
                numerator=numerator,
                denominator=denominator,
                state_avg=state_avg,
                national_avg=national_avg,
            )

            if ci is None:
                continue

            # CI values are on 0-1 scale; HCAHPS values are 0-100 percentages.
            # Scale CI bounds to match.
            ci_lower = (ci.lower * 100).quantize(Decimal("0.0001"))
            ci_upper = (ci.upper * 100).quantize(Decimal("0.0001"))

            if has_ci_source:
                conn.execute(sa.text("""
                    UPDATE provider_measure_values
                    SET confidence_interval_lower = :ci_lower,
                        confidence_interval_upper = :ci_upper,
                        ci_source = :ci_source,
                        prior_source = :prior_source
                    WHERE id = :row_id
                """), {
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper,
                    "ci_source": ci.ci_source,
                    "prior_source": ci.prior_source,
                    "row_id": row_id,
                })
            else:
                conn.execute(sa.text("""
                    UPDATE provider_measure_values
                    SET confidence_interval_lower = :ci_lower,
                        confidence_interval_upper = :ci_upper
                    WHERE id = :row_id
                """), {
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper,
                    "row_id": row_id,
                })
            updated += 1
            affected_providers.add(provider_id)

    logger.info(
        "Updated %d rows across %d providers",
        updated, len(affected_providers),
    )

    # Re-export affected providers
    if affected_providers:
        import json
        from pathlib import Path
        from pipeline.export.build_json import build_provider_json, _json_serial

        output_dir = Path("build/data")
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Re-exporting %d provider JSON files...", len(affected_providers))
        engine2 = sa.create_engine(DB_URL)
        with engine2.connect() as conn:
            exported = 0
            for pid in sorted(affected_providers):
                try:
                    data = build_provider_json(conn, pid)
                    if data:
                        out_path = output_dir / f"{pid}.json"
                        with open(out_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, default=_json_serial, ensure_ascii=False)
                        exported += 1
                except Exception as e:
                    logger.error("Failed to export %s: %s", pid, e)
            logger.info("Exported %d provider files to %s", exported, output_dir)


if __name__ == "__main__":
    main()
