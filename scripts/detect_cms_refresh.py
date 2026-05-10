"""Detect newly published CMS dataset vintages.

Polls the DKAN metastore for each tracked dataset and compares the
`modified` timestamp against the most recent timestamp recorded in
`pipeline_runs.datasets_fetched` (the audit trail per database-schema.md).

Output:
    logs/cms_refresh_check_YYYY-MM-DD.json — JSON report describing each
    dataset's current published vintage, last-ingested vintage, and whether
    a refresh is recommended.

Exit codes:
    0 — Up-to-date (no refresh needed) OR refresh available (caller checks
        the JSON report). The "refresh available" case is intentionally
        exit 0 so cron-style scheduling does not flag detection as a
        failure when CMS publishes new data.
    2 — Configuration / database connectivity error
    3 — CMS API error (one or more datasets could not be queried)

Usage:
    python scripts/detect_cms_refresh.py
    python scripts/detect_cms_refresh.py --db-url postgresql+psycopg://...
    python scripts/detect_cms_refresh.py --output logs/custom-report.json
    python scripts/detect_cms_refresh.py --provider-types hospitals
    python scripts/detect_cms_refresh.py --no-db  # local-only check, skips state lookup

Constraints:
    - All CMS API calls go through pipeline.ingest.client (coding-conventions.md).
    - Decimal precision rules do not apply here (no rate values handled).
    - Failures raise/log with full context (Rule 6).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow running as a top-level script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pipeline.config import (  # noqa: E402
    DATASET_NAMES,
    HOSPITAL_DATASET_IDS,
    NH_DATASET_IDS,
)
from pipeline.ingest.client import CMSAPIError, get_dataset_metadata  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default DB URL — same fallback as scripts/check_ownership_changes.py
# ---------------------------------------------------------------------------

DEFAULT_DB_URL = os.environ.get(
    "OPENCHART_DB_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/openchart",
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class DatasetStatus:
    """Refresh status for a single CMS dataset."""

    dataset_id: str
    dataset_name: str
    provider_type: str  # "hospitals" or "nursing_homes"
    cms_modified: str | None
    cms_released: str | None
    cms_title: str | None
    last_ingested_at: str | None
    last_ingested_run_id: str | None
    refresh_available: bool
    download_urls: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class RefreshReport:
    """Top-level report aggregating all dataset statuses."""

    generated_at: str
    db_url_present: bool
    datasets: list[DatasetStatus] = field(default_factory=list)
    api_errors: int = 0
    refresh_count: int = 0


# ---------------------------------------------------------------------------
# Last-ingested lookup
# ---------------------------------------------------------------------------

def _build_dataset_to_runs_map(db_url: str) -> dict[str, dict[str, str]]:
    """Return {dataset_key: {"completed_at": iso, "run_id": uuid}} for the most
    recent successful pipeline run that fetched each dataset.

    Reads `pipeline_runs.datasets_fetched` which the orchestrator populates
    with the dataset *keys* (e.g. "hospital_info", "nh_provider_info"), NOT
    the Socrata IDs. We map back via HOSPITAL_DATASET_IDS / NH_DATASET_IDS.
    """
    try:
        import sqlalchemy as sa
    except ImportError:
        logger.error("sqlalchemy not importable; cannot read pipeline_runs.")
        raise

    engine = sa.create_engine(db_url)
    out: dict[str, dict[str, str]] = {}
    try:
        with engine.connect() as conn:
            metadata = sa.MetaData()
            metadata.reflect(bind=conn.engine, only=["pipeline_runs"])
            runs = metadata.tables["pipeline_runs"]
            rows = conn.execute(
                sa.select(runs.c.run_id, runs.c.completed_at, runs.c.datasets_fetched)
                .where(runs.c.completed_at.isnot(None))
                .order_by(runs.c.completed_at.desc())
            ).fetchall()
        for row in rows:
            datasets = row.datasets_fetched
            if isinstance(datasets, str):
                try:
                    datasets = json.loads(datasets)
                except json.JSONDecodeError:
                    datasets = []
            if not datasets:
                continue
            iso = row.completed_at.astimezone(timezone.utc).isoformat() if row.completed_at else None
            run_id = str(row.run_id)
            for ds_key in datasets:
                # The first time we see a dataset key (rows are DESC by completed_at)
                # is the most recent successful run.
                if ds_key not in out:
                    out[ds_key] = {"completed_at": iso or "", "run_id": run_id}
    finally:
        engine.dispose()
    return out


# ---------------------------------------------------------------------------
# Refresh determination
# ---------------------------------------------------------------------------

def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    if not s:
        return None
    # CMS sometimes returns "YYYY-MM-DD" without time; normalize.
    try:
        if "T" not in s and len(s) == 10:
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        # Replace trailing Z with +00:00 for fromisoformat compatibility
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _is_refresh_available(cms_modified: str | None, last_ingested_at: str | None) -> bool:
    """Return True when CMS has published more recently than our last ingest.

    Conservative: when either timestamp is missing, we report refresh
    available (assume update needed). This biases toward checking again
    rather than missing data — antifragile.
    """
    cms_dt = _parse_iso(cms_modified)
    last_dt = _parse_iso(last_ingested_at)
    if cms_dt is None:
        # CMS metadata missing — we can't tell, default to "refresh available"
        # so the caller investigates.
        return True
    if last_dt is None:
        # Never ingested — refresh trivially available.
        return True
    return cms_dt > last_dt


def _extract_download_urls(metadata: dict[str, Any]) -> list[str]:
    """Pull `distribution[].downloadURL` (or data.downloadURL) entries.

    DKAN distributions vary in shape: some embed `downloadURL` directly,
    others wrap it under `data`. We try both.
    """
    urls: list[str] = []
    distributions = metadata.get("distribution") or []
    if not isinstance(distributions, list):
        return urls
    for dist in distributions:
        if not isinstance(dist, dict):
            continue
        url = dist.get("downloadURL")
        if not url and isinstance(dist.get("data"), dict):
            url = dist["data"].get("downloadURL")
        if isinstance(url, str) and url:
            urls.append(url)
    return urls


# ---------------------------------------------------------------------------
# Tracked dataset list
# ---------------------------------------------------------------------------

def _tracked_datasets(provider_types: list[str] | None) -> list[tuple[str, str, str]]:
    """Return [(dataset_key, dataset_id, provider_type), ...].

    Filters by provider_types when supplied. Includes only datasets we
    actively ingest in `pipeline/orchestrate.py`. The reference / lookup
    tables in NH_DATASET_IDS (data collection, citation lookup, cutpoints)
    are not refresh-monitored — they are static reference data.
    """
    pt_filter = set(provider_types) if provider_types else None
    out: list[tuple[str, str, str]] = []
    if pt_filter is None or "hospitals" in pt_filter:
        for key, ds_id in HOSPITAL_DATASET_IDS.items():
            out.append((key, ds_id, "hospitals"))
    if pt_filter is None or "nursing_homes" in pt_filter:
        skip_keys = {"nh_data_collection", "nh_citation_lookup", "nh_inspection_cutpoints"}
        for key, ds_id in NH_DATASET_IDS.items():
            if key in skip_keys:
                continue
            out.append((key, ds_id, "nursing_homes"))
    return out


# ---------------------------------------------------------------------------
# Main detection
# ---------------------------------------------------------------------------

def detect_refreshes(
    db_url: str | None,
    provider_types: list[str] | None = None,
) -> RefreshReport:
    """Run the full detection sweep across all tracked datasets.

    `db_url=None` skips the pipeline_runs lookup; every dataset is then
    reported as refresh_available=True (useful for first-run smoke tests).
    """
    last_ingested: dict[str, dict[str, str]] = {}
    if db_url:
        try:
            last_ingested = _build_dataset_to_runs_map(db_url)
        except Exception as exc:
            # Surface but don't pretend datasets are up-to-date on DB error.
            logger.error("Failed to read pipeline_runs from %s: %s", db_url, exc)
            raise

    report = RefreshReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        db_url_present=bool(db_url),
    )

    for ds_key, ds_id, provider_type in _tracked_datasets(provider_types):
        cms_meta_modified: str | None = None
        cms_meta_released: str | None = None
        cms_title: str | None = None
        download_urls: list[str] = []
        error: str | None = None
        try:
            metadata = get_dataset_metadata(ds_id)
            cms_meta_modified = metadata.get("modified")
            cms_meta_released = metadata.get("released")
            cms_title = metadata.get("title")
            download_urls = _extract_download_urls(metadata)
        except CMSAPIError as exc:
            logger.error("CMS API error for %s (%s): %s", ds_key, ds_id, exc)
            error = str(exc)
            report.api_errors += 1
        except Exception as exc:  # noqa: BLE001 — log full context (Rule 6)
            logger.error("Unexpected error for %s (%s): %s", ds_key, ds_id, exc)
            error = f"unexpected: {exc}"
            report.api_errors += 1

        last_run = last_ingested.get(ds_key) or {}
        last_at = last_run.get("completed_at") or None
        last_run_id = last_run.get("run_id") or None

        # When the API call errored we cannot determine refresh state.
        # Mark refresh_available=True so an operator investigates.
        refresh_available = (
            True if error else _is_refresh_available(cms_meta_modified, last_at)
        )
        if refresh_available:
            report.refresh_count += 1

        report.datasets.append(
            DatasetStatus(
                dataset_id=ds_id,
                dataset_name=DATASET_NAMES.get(ds_id, ds_key),
                provider_type=provider_type,
                cms_modified=cms_meta_modified,
                cms_released=cms_meta_released,
                cms_title=cms_title,
                last_ingested_at=last_at,
                last_ingested_run_id=last_run_id,
                refresh_available=refresh_available,
                download_urls=download_urls,
                error=error,
            )
        )

    return report


def write_report(report: RefreshReport, output_path: Path) -> None:
    """Write the report to disk as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "generated_at": report.generated_at,
        "db_url_present": report.db_url_present,
        "api_errors": report.api_errors,
        "refresh_count": report.refresh_count,
        "datasets": [asdict(d) for d in report.datasets],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("Wrote refresh report to %s", output_path)


def default_output_path() -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _REPO_ROOT / "logs" / f"cms_refresh_check_{today}.json"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help="Postgres SQLAlchemy URL for pipeline_runs lookup. "
             "Set to '' or use --no-db to skip.",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip pipeline_runs lookup; treat all datasets as refresh_available=True.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Default: logs/cms_refresh_check_YYYY-MM-DD.json",
    )
    parser.add_argument(
        "--provider-types",
        nargs="+",
        choices=["hospitals", "nursing_homes"],
        default=None,
        help="Limit to specific provider types.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational stdout summary.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    db_url = None if args.no_db or not args.db_url else args.db_url
    output = args.output or default_output_path()

    try:
        report = detect_refreshes(
            db_url=db_url,
            provider_types=args.provider_types,
        )
    except Exception as exc:  # noqa: BLE001 — Rule 6: log with context
        logger.error("Refresh detection failed: %s", exc, exc_info=True)
        return 2

    write_report(report, output)

    if not args.quiet:
        print(f"Datasets checked: {len(report.datasets)}")
        print(f"Refresh available: {report.refresh_count}")
        print(f"API errors: {report.api_errors}")
        for ds in report.datasets:
            tag = "REFRESH" if ds.refresh_available else "current"
            err = f" ERROR={ds.error}" if ds.error else ""
            print(f"  [{tag:7}] {ds.provider_type:14} {ds.dataset_id:10} {ds.dataset_name}{err}")
        print(f"Report written to: {output}")

    if report.api_errors:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
