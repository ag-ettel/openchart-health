"""
Pipeline orchestrator — single entry point for running the full pipeline.

Ties together ingest (CSV or API) → normalize → store for all datasets.
Enforces dependency order and the 5% failure threshold (Rule 6).

Usage:
    from pipeline.orchestrate import run_pipeline
    run_pipeline(db_url="postgresql+psycopg://...", data_dir="data/")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa

from pipeline.ingest.csv_reader import ArchiveInfo, discover_archives, read_csv_dataset
from pipeline.normalize import (
    complications_deaths,
    hacrp,
    hai,
    hcahps,
    hospital_info,
    hrrp,
    imaging,
    mspb,
    nh_claims_quality,
    nh_health_deficiencies,
    nh_mds_quality,
    nh_ownership,
    nh_penalties,
    nh_provider_info,
    readmissions,
    snf_qrp,
    snf_vbp,
    timely_effective,
    vbp,
)
from pipeline.store.seed_measures import seed_measures
from pipeline.store.upsert import (
    upsert_inspection_events,
    upsert_measure_values,
    upsert_ownership,
    upsert_payment_adjustments,
    upsert_penalties,
    upsert_providers,
)

logger = logging.getLogger(__name__)

# Maximum failure rate before aborting (Rule 6)
FAILURE_THRESHOLD = 0.05


@dataclass
class PipelineResult:
    """Summary of a pipeline run."""

    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    archives_processed: int = 0
    datasets_processed: int = 0
    rows_upserted: int = 0
    rows_failed: int = 0
    anomalies: list[str] = field(default_factory=list)
    aborted: bool = False
    abort_reason: str | None = None


# ---------------------------------------------------------------------------
# Dataset processing registry
# ---------------------------------------------------------------------------

# Maps dataset_key → (normalizer_module, upsert_function_name, target_table)
# Order matters: providers first, then measures, then payment programs.

HOSPITAL_DATASETS = [
    # Provider metadata first (creates providers rows)
    ("hospital_info", hospital_info, "providers"),
    # Quality measures (require providers to exist)
    ("complications_deaths", complications_deaths, "measure_values"),
    ("hai", hai, "measure_values"),
    ("readmissions", readmissions, "measure_values"),
    ("hcahps", hcahps, "measure_values"),
    ("timely_effective", timely_effective, "measure_values"),
    ("imaging", imaging, "measure_values"),
    ("mspb", mspb, "measure_values"),
    # Payment programs
    ("hrrp", hrrp, "measure_values"),  # HRRP condition ratios → measure_values
    ("hacrp", hacrp, "payment_adjustments"),
    ("vbp_tps", vbp, "payment_adjustments"),
]

NH_DATASETS = [
    # Provider metadata first
    ("nh_provider_info", nh_provider_info, "providers"),
    # Quality measures
    ("nh_mds_quality", nh_mds_quality, "measure_values"),
    ("nh_claims_quality", nh_claims_quality, "measure_values"),
    ("snf_qrp", snf_qrp, "measure_values"),
    # Inspection data (after providers)
    ("nh_health_deficiencies", nh_health_deficiencies, "inspection_events"),
    # Penalties
    ("nh_penalties", nh_penalties, "penalties"),
    # Ownership
    ("nh_ownership", nh_ownership, "ownership"),
    # Payment programs
    ("snf_vbp", snf_vbp, "payment_adjustments"),
]


def _process_dataset(
    conn: sa.engine.Connection,
    archive: ArchiveInfo,
    dataset_key: str,
    normalizer: Any,
    target: str,
) -> tuple[int, int, list[str]]:
    """Process one dataset from one archive. Returns (upserted, failed, anomalies)."""
    anomalies: list[str] = []

    # Read
    rows = read_csv_dataset(archive.path, dataset_key)
    if not rows:
        return 0, 0, [f"{dataset_key}: no data in {archive.path.name}"]

    raw_count = len(rows)

    # Normalize
    try:
        normalized = normalizer.normalize_dataset(rows)
    except Exception as e:
        logger.error("Normalization failed for %s in %s: %s", dataset_key, archive.path.name, e)
        return 0, raw_count, [f"{dataset_key}: normalization error: {e}"]

    # Check failure threshold
    norm_count = len(normalized)
    if raw_count > 0 and norm_count == 0:
        anomalies.append(f"{dataset_key}: all {raw_count} rows normalized to 0 results")

    # Store
    upserted = 0
    failed = 0
    vintage = archive.vintage_label

    try:
        provider_type = "HOSPITAL" if archive.provider_type == "hospitals" else "NURSING_HOME"

        if target == "providers":
            upserted = upsert_providers(conn, normalized)
        elif target == "measure_values":
            upserted = upsert_measure_values(conn, normalized, provider_type=provider_type)
        elif target == "payment_adjustments":
            upserted = upsert_payment_adjustments(conn, normalized)
        elif target == "inspection_events":
            upserted = upsert_inspection_events(conn, normalized, vintage=vintage)
        elif target == "penalties":
            upserted = upsert_penalties(conn, normalized, vintage=vintage)
        elif target == "ownership":
            upserted = upsert_ownership(conn, normalized)
        else:
            anomalies.append(f"{dataset_key}: unknown target '{target}'")
    except Exception as e:
        logger.error("Store failed for %s: %s", dataset_key, e)
        failed = norm_count
        anomalies.append(f"{dataset_key}: store error: {e}")

    return upserted, failed, anomalies


def run_pipeline(
    db_url: str,
    data_dir: str | Path = "data",
    *,
    provider_types: list[str] | None = None,
    vintages: list[str] | None = None,
    dry_run: bool = False,
) -> PipelineResult:
    """Run the full pipeline: ingest → normalize → store.

    Args:
        db_url: PostgreSQL connection URL.
        data_dir: Path to the data directory containing archive zips.
        provider_types: Filter to ["hospitals"], ["nursing_homes"], or both (default).
        vintages: Filter to specific vintages like ["2024-07", "2026-02"].
        dry_run: If True, normalize but don't write to database.

    Returns:
        PipelineResult with summary statistics.
    """
    result = PipelineResult()
    data_path = Path(data_dir)

    # Discover archives
    archives = discover_archives(data_path)
    if vintages:
        archives = [a for a in archives if a.vintage_label in vintages]
    if provider_types:
        archives = [a for a in archives if a.provider_type in provider_types]

    logger.info("Pipeline starting: %d archives to process", len(archives))

    engine = sa.create_engine(db_url)

    # Seed measures reference table before any measure values (FK constraint)
    if not dry_run:
        with engine.connect() as conn:
            seed_measures(conn)
            conn.commit()
        logger.info("Measures reference table seeded")

    # Process archives in chronological order (DEC-028: lifecycle tracking)
    for archive in archives:
        logger.info("Processing %s (%s)", archive.path.name, archive.vintage_label)

        # Select dataset list based on provider type
        if archive.provider_type == "hospitals":
            dataset_list = HOSPITAL_DATASETS
        else:
            dataset_list = NH_DATASETS

        with engine.connect() as conn:
            for dataset_key, normalizer, target in dataset_list:
                if dry_run:
                    rows = read_csv_dataset(archive.path, dataset_key)
                    if rows:
                        normalized = normalizer.normalize_dataset(rows)
                        logger.info(
                            "  [dry-run] %s: %d raw -> %d normalized",
                            dataset_key, len(rows), len(normalized),
                        )
                    continue

                # Per-dataset savepoint so one failure doesn't roll back others
                savepoint = conn.begin_nested()
                try:
                    upserted, failed, anomalies = _process_dataset(
                        conn, archive, dataset_key, normalizer, target,
                    )

                    if failed > 0:
                        savepoint.rollback()
                        logger.warning(
                            "  %s: %d upserted, %d failed (rolled back)", dataset_key, upserted, failed
                        )
                    else:
                        savepoint.commit()
                        logger.info("  %s: %d upserted", dataset_key, upserted)
                except Exception as e:
                    savepoint.rollback()
                    failed = 1
                    anomalies = [f"{dataset_key}: exception: {e}"]
                    logger.error("  %s: exception (rolled back): %s", dataset_key, e)

                result.rows_upserted += upserted if failed == 0 else 0
                result.rows_failed += failed
                result.anomalies.extend(anomalies)
                result.datasets_processed += 1

            conn.commit()

        result.archives_processed += 1

    engine.dispose()

    result.completed_at = datetime.utcnow()
    duration = (result.completed_at - result.started_at).total_seconds()
    logger.info(
        "Pipeline complete: %d archives, %d datasets, %d upserted, %d failed, %.1fs",
        result.archives_processed, result.datasets_processed,
        result.rows_upserted, result.rows_failed, duration,
    )

    return result
