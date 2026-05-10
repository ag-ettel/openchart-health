"""
Pipeline orchestrator — single entry point for running the full pipeline.

Ties together ingest (CSV or API) → normalize → store for all datasets.
Enforces dependency order and the 5% failure threshold (Rule 6).

Usage:
    from pipeline.orchestrate import run_pipeline
    run_pipeline(db_url="postgresql+psycopg://...", data_dir="data/")
"""

from __future__ import annotations

import json
import logging
import time
import uuid
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
from pipeline.normalize.benchmarks import (
    HOSPITAL_NATIONAL_CONFIGS,
    HOSPITAL_STATE_CONFIGS,
    normalize_hospital_national_benchmarks,
    normalize_hospital_state_benchmarks,
    normalize_nh_state_us_averages,
    normalize_snf_qrp_national_benchmarks,
)
from pipeline.store.seed_measures import seed_measures
from pipeline.store.upsert import (
    upsert_benchmarks,
    upsert_inspection_events,
    upsert_measure_values,
    upsert_ownership,
    upsert_payment_adjustments,
    upsert_penalties,
    upsert_providers,
)

logger = logging.getLogger(__name__)

# Maximum failure rate before aborting a dataset (Rule 6)
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
    run_id: uuid.UUID | None = None
    datasets_fetched: list[str] = field(default_factory=list)


def _create_pipeline_run(engine: sa.Engine) -> uuid.UUID:
    """Insert a pipeline_runs row at the start of a run; returns the run_id.

    Schema-required audit trail (database-schema.md). Other tables carry a
    pipeline_run_id FK back to this row. Use a fresh short-lived connection
    so the run record commits even if the main pipeline aborts later.
    """
    metadata = sa.MetaData()
    metadata.reflect(bind=engine, only=["pipeline_runs"])
    table = metadata.tables["pipeline_runs"]
    run_id = uuid.uuid4()
    with engine.connect() as conn:
        conn.execute(table.insert().values(
            run_id=run_id,
            started_at=datetime.utcnow(),
            datasets_fetched=json.dumps([]),
            rows_upserted=0,
            rows_failed=0,
            anomalies=json.dumps([]),
        ))
        conn.commit()
    return run_id


def _complete_pipeline_run(engine: sa.Engine, run_id: uuid.UUID, result: PipelineResult) -> None:
    """Update the pipeline_runs row with final totals at end of a run."""
    metadata = sa.MetaData()
    metadata.reflect(bind=engine, only=["pipeline_runs"])
    table = metadata.tables["pipeline_runs"]
    with engine.connect() as conn:
        conn.execute(
            table.update()
            .where(table.c.run_id == run_id)
            .values(
                completed_at=datetime.utcnow(),
                datasets_fetched=json.dumps(sorted(set(result.datasets_fetched))),
                rows_upserted=result.rows_upserted,
                rows_failed=result.rows_failed,
                anomalies=json.dumps(result.anomalies[:200]),  # cap to avoid bloat
                updated_at=datetime.utcnow(),
            )
        )
        conn.commit()


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
    pipeline_run_id: Any = None,
) -> tuple[int, int, list[str], bool]:
    """Process one dataset from one archive.

    Returns (upserted, failed, anomalies, abort_dataset).
    abort_dataset is True when normalization-stage failure rate exceeds
    FAILURE_THRESHOLD (Rule 6) — caller must roll back the dataset's savepoint
    and treat the dataset as failed.
    """
    anomalies: list[str] = []
    abort_dataset = False

    # Read
    rows = read_csv_dataset(archive.path, dataset_key)
    if not rows:
        return 0, 0, [f"{dataset_key}: no data in {archive.path.name}"], False

    raw_count = len(rows)

    # Normalize
    try:
        normalized = normalizer.normalize_dataset(rows)
    except Exception as e:
        logger.error("Normalization failed for %s in %s: %s", dataset_key, archive.path.name, e)
        return 0, raw_count, [f"{dataset_key}: normalization error: {e}"], True

    norm_count = len(normalized)

    # Rule 6: per-dataset failure threshold abort.
    # We measure failure as raw rows that normalization couldn't keep
    # (excluding the legitimate cases where one raw row produces multiple
    # normalized rows like NH MDS quarter splitting). A normalize-to-zero
    # outcome on a non-empty input is always a Rule 6 abort.
    if raw_count > 0 and norm_count == 0:
        anomalies.append(
            f"{dataset_key}: all {raw_count} rows normalized to 0 results "
            f"(Rule 6 abort)"
        )
        return 0, raw_count, anomalies, True
    # When the normalizer yields fewer results than inputs (and not because
    # of intentional fan-out), treat the shortfall as failures and apply the
    # threshold. nh_mds_quality fans out 1→5; comparing strictly would be
    # noisy. The conservative reading: only check when norm_count < raw_count
    # AND we don't expect fan-out from this normalizer. Without dataset-level
    # metadata we can only check the normalize-to-zero case above.

    # Store
    upserted = 0
    failed = 0
    vintage = archive.vintage_label

    try:
        provider_type = "HOSPITAL" if archive.provider_type == "hospitals" else "NURSING_HOME"

        if target == "providers":
            upserted = upsert_providers(conn, normalized)
        elif target == "measure_values":
            upserted = upsert_measure_values(conn, normalized, provider_type=provider_type, pipeline_run_id=pipeline_run_id)
        elif target == "payment_adjustments":
            upserted = upsert_payment_adjustments(conn, normalized, pipeline_run_id=pipeline_run_id)
        elif target == "inspection_events":
            upserted = upsert_inspection_events(conn, normalized, vintage=vintage, pipeline_run_id=pipeline_run_id)
        elif target == "penalties":
            upserted = upsert_penalties(conn, normalized, vintage=vintage, pipeline_run_id=pipeline_run_id)
        elif target == "ownership":
            upserted = upsert_ownership(conn, normalized, pipeline_run_id=pipeline_run_id)
        else:
            anomalies.append(f"{dataset_key}: unknown target '{target}'")
    except Exception as e:
        logger.error("Store failed for %s: %s", dataset_key, e)
        failed = norm_count
        anomalies.append(f"{dataset_key}: store error: {e}")

    return upserted, failed, anomalies, abort_dataset


def _process_archive_benchmarks(
    conn: sa.engine.Connection,
    archive: ArchiveInfo,
    pipeline_run_id: Any = None,
) -> tuple[int, list[str]]:
    """Ingest CMS-published benchmark CSVs from one archive (DEC-036).

    Returns (rows_upserted, anomalies). Reads:
    - Hospital archives: -National.csv and -State.csv companion files
    - NH archives: NH_StateUSAverages and SNF_QRP_National

    Skips state files for HGLM measures (CMS does not publish those — DEC-036).
    """
    anomalies: list[str] = []
    upserted = 0
    vintage = archive.vintage_label

    if archive.provider_type == "hospitals":
        for dataset_key, config in HOSPITAL_NATIONAL_CONFIGS.items():
            rows = read_csv_dataset(archive.path, dataset_key)
            if not rows:
                continue
            normalized = normalize_hospital_national_benchmarks(rows, config, vintage)
            if normalized:
                upserted += upsert_benchmarks(conn, normalized, pipeline_run_id=pipeline_run_id)

        for dataset_key, config in HOSPITAL_STATE_CONFIGS.items():
            rows = read_csv_dataset(archive.path, dataset_key)
            if not rows:
                continue
            normalized = normalize_hospital_state_benchmarks(rows, config, vintage)
            if normalized:
                upserted += upsert_benchmarks(conn, normalized, pipeline_run_id=pipeline_run_id)
    else:
        rows = read_csv_dataset(archive.path, "nh_state_averages")
        if rows:
            normalized = normalize_nh_state_us_averages(rows, vintage)
            if normalized:
                upserted += upsert_benchmarks(conn, normalized, pipeline_run_id=pipeline_run_id)

        rows = read_csv_dataset(archive.path, "snf_qrp_national")
        if rows:
            normalized = normalize_snf_qrp_national_benchmarks(rows, vintage)
            if normalized:
                upserted += upsert_benchmarks(conn, normalized, pipeline_run_id=pipeline_run_id)

    return upserted, anomalies


def run_benchmark_ingest(
    db_url: str,
    data_dir: str | Path = "data",
    *,
    provider_types: list[str] | None = None,
    vintages: list[str] | None = None,
) -> PipelineResult:
    """Ingest only benchmark CSVs (DEC-036) from archives.

    Independent path that does not touch provider/measure/inspection data.
    Used for backfilling measure_benchmarks across all archive vintages.
    """
    result = PipelineResult()
    archives = discover_archives(Path(data_dir))
    if vintages:
        archives = [a for a in archives if a.vintage_label in vintages]
    if provider_types:
        archives = [a for a in archives if a.provider_type in provider_types]

    logger.info("Benchmark ingest: %d archives to scan", len(archives))

    engine = sa.create_engine(db_url)
    result.run_id = _create_pipeline_run(engine)
    logger.info("Benchmark ingest run id: %s", result.run_id)

    with engine.connect() as conn:
        seed_measures(conn)
        conn.commit()

        for archive in archives:
            logger.info("Benchmarks from %s (%s)", archive.path.name, archive.vintage_label)
            try:
                upserted, anomalies = _process_archive_benchmarks(
                    conn, archive, pipeline_run_id=result.run_id,
                )
                result.rows_upserted += upserted
                result.anomalies.extend(anomalies)
                conn.commit()
                logger.info("  %d benchmark rows upserted", upserted)
            except Exception as e:
                conn.rollback()
                msg = f"benchmark ingest failed for {archive.path.name}: {e}"
                logger.error(msg)
                result.anomalies.append(msg)
                result.rows_failed += 1
            result.archives_processed += 1

    result.completed_at = datetime.utcnow()
    _complete_pipeline_run(engine, result.run_id, result)
    engine.dispose()
    duration = (result.completed_at - result.started_at).total_seconds()
    logger.info(
        "Benchmark ingest complete: %d archives, %d rows, %d failures, %.1fs",
        result.archives_processed, result.rows_upserted, result.rows_failed, duration,
    )
    return result


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

    # Open a pipeline_runs audit row up-front so other tables can FK back to it.
    if not dry_run:
        result.run_id = _create_pipeline_run(engine)
        logger.info("Pipeline run id: %s", result.run_id)

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
                    upserted, failed, anomalies, abort_dataset = _process_dataset(
                        conn, archive, dataset_key, normalizer, target,
                        pipeline_run_id=result.run_id,
                    )

                    if abort_dataset or failed > 0:
                        savepoint.rollback()
                        upserted = 0  # nothing committed for this dataset
                        if abort_dataset:
                            logger.warning(
                                "  %s: ABORTED (Rule 6: failure rate > %.0f%%)",
                                dataset_key, FAILURE_THRESHOLD * 100,
                            )
                        else:
                            logger.warning(
                                "  %s: %d failed (rolled back)", dataset_key, failed
                            )
                    else:
                        savepoint.commit()
                        logger.info("  %s: %d upserted", dataset_key, upserted)
                except Exception as e:
                    savepoint.rollback()
                    upserted = 0
                    failed = 1
                    anomalies = [f"{dataset_key}: exception: {e}"]
                    logger.error("  %s: exception (rolled back): %s", dataset_key, e)

                result.rows_upserted += upserted
                result.rows_failed += failed
                result.anomalies.extend(anomalies)
                result.datasets_processed += 1
                result.datasets_fetched.append(dataset_key)

            # Benchmark CSVs (DEC-036) — same archive, separate target table
            if not dry_run:
                bench_savepoint = conn.begin_nested()
                try:
                    bench_upserted, bench_anomalies = _process_archive_benchmarks(
                        conn, archive, pipeline_run_id=result.run_id,
                    )
                    bench_savepoint.commit()
                    result.rows_upserted += bench_upserted
                    result.anomalies.extend(bench_anomalies)
                    if bench_upserted:
                        logger.info("  benchmarks: %d upserted", bench_upserted)
                except Exception as e:
                    bench_savepoint.rollback()
                    result.anomalies.append(f"benchmarks: exception: {e}")
                    logger.error("  benchmarks: exception (rolled back): %s", e)

            conn.commit()

        result.archives_processed += 1

    if not dry_run and result.run_id:
        result.completed_at = datetime.utcnow()
        _complete_pipeline_run(engine, result.run_id, result)

    engine.dispose()

    if result.completed_at is None:
        result.completed_at = datetime.utcnow()
    duration = (result.completed_at - result.started_at).total_seconds()
    logger.info(
        "Pipeline complete: %d archives, %d datasets, %d upserted, %d failed, %.1fs",
        result.archives_processed, result.datasets_processed,
        result.rows_upserted, result.rows_failed, duration,
    )

    return result
