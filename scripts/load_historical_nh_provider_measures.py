"""
Load historical NH Provider Info measures (staffing + inspection) from multiple
archive vintages to populate the `trend` array in the JSON export.

For each archive vintage, extracts the staffing/inspection/star-rating measure
values and upserts them into provider_measure_values with period_label =
processing_date. Running pipeline is idempotent per DEC-005.

Strategy: load one archive per quarter (Q1/Q2/Q3/Q4) for years 2020-2026.
~25 vintages = 25 periods per measure = enough for trend display (Rule 12: 3+ periods).
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa

from pipeline.normalize.nh_provider_info import (
    extract_provider_measures_dataset,
    extract_star_ratings_dataset,
)
from pipeline.store.upsert import upsert_measure_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"
ARCHIVE_ROOT = Path("data/nursing_homes")


def load_archive(engine: sa.Engine, zip_path: Path) -> int:
    """Load one archive vintage's staffing and inspection measures."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            provider_files = [n for n in zf.namelist() if "providerinfo" in n.lower().replace("_", "")]
            if not provider_files:
                provider_files = [n for n in zf.namelist() if "provider" in n.lower()]
            if not provider_files:
                logger.warning("  No provider file in %s", zip_path.name)
                return 0

            provider_file = provider_files[0]

            # Try UTF-8 first, fall back to latin-1 for older archives
            for encoding in ("utf-8-sig", "latin-1"):
                try:
                    with zf.open(provider_file) as f:
                        text = io.TextIOWrapper(f, encoding=encoding)
                        reader = csv.DictReader(text)
                        rows = [
                            {
                                k.lower().replace(" ", "_").replace("-", "_").replace("/", "_"): v
                                for k, v in raw.items()
                            }
                            for raw in reader
                        ]
                    break
                except UnicodeDecodeError:
                    continue
    except (zipfile.BadZipFile, KeyError) as e:
        logger.error("  Failed to read %s: %s", zip_path.name, e)
        return 0

    if not rows:
        return 0

    # Extract measures (staffing + inspection + star ratings)
    staff_insp_rows = extract_provider_measures_dataset(rows)
    star_rows = extract_star_ratings_dataset(rows)
    all_measure_rows = staff_insp_rows + star_rows

    with engine.begin() as conn:
        count = upsert_measure_values(conn, all_measure_rows, provider_type="NURSING_HOME")

    return count


def main() -> None:
    engine = sa.create_engine(DB_URL)

    # Select one archive per quarter across years — enough for trend display
    # Format: (year_dir, month) pairs
    target_archives = [
        ("nursing_homes_including_rehab_services_2020", "03"),
        ("nursing_homes_including_rehab_services_2020", "06"),
        ("nursing_homes_including_rehab_services_2020", "09"),
        ("nursing_homes_including_rehab_services_2020", "12"),
        ("nursing_homes_including_rehab_services_2021", "03"),
        ("nursing_homes_including_rehab_services_2021", "06"),
        ("nursing_homes_including_rehab_services_2021", "09"),
        ("nursing_homes_including_rehab_services_2021", "12"),
        ("nursing_homes_including_rehab_services_2022", "03"),
        ("nursing_homes_including_rehab_services_2022", "06"),
        ("nursing_homes_including_rehab_services_2022", "09"),
        ("nursing_homes_including_rehab_services_2022", "12"),
        ("nursing_homes_including_rehab_services_2023", "03"),
        ("nursing_homes_including_rehab_services_2023", "06"),
        ("nursing_homes_including_rehab_services_2023", "09"),
        ("nursing_homes_including_rehab_services_2023", "12"),
        ("nursing_homes_including_rehab_services_2024", "03"),
        ("nursing_homes_including_rehab_services_2024", "06"),
        ("nursing_homes_including_rehab_services_2024", "09"),
        ("nursing_homes_including_rehab_services_2024", "12"),
        ("nursing_homes_including_rehab_services_2025", "03"),
        ("nursing_homes_including_rehab_services_2025", "06"),
        ("nursing_homes_including_rehab_services_2025", "09"),
        ("nursing_homes_including_rehab_services_2025", "12"),
    ]

    total_loaded = 0
    for year_dir, month in target_archives:
        year = year_dir.split("_")[-1]
        # Archive naming: nursing_homes_including_rehab_services_MM_YYYY.zip
        zip_path = ARCHIVE_ROOT / year_dir / f"nursing_homes_including_rehab_services_{month}_{year}.zip"
        if not zip_path.exists():
            logger.info("Skipping (not found): %s", zip_path.name)
            continue

        logger.info("Loading %s...", zip_path.name)
        count = load_archive(engine, zip_path)
        logger.info("  Upserted %d rows", count)
        total_loaded += count

    logger.info("")
    logger.info("Total measure values upserted across all vintages: %d", total_loaded)

    engine.dispose()


if __name__ == "__main__":
    main()
