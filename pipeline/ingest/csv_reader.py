"""
CSV archive reader — reads CMS bulk CSV downloads from zip archives.

Produces list[dict] with snake_case keys, the same interface as client.py.
Normalizers are shared between API and CSV data sources.

Handles three CMS archive eras:
  - 2019-2020: different filenames (e.g., "ProviderInfo_Download.csv",
    "Complications and Deaths - Hospital.csv") — spaces not underscores
  - 2022-2023: files nested in a subdirectory within the zip
  - 2021, 2024+: flat zip with underscore filenames

Usage:
    from pipeline.ingest.csv_reader import read_csv_dataset, discover_archives

    # Discover all available archives
    archives = discover_archives("e:/openchart-health/data/hospitals")

    # Read a specific dataset from a specific archive
    rows = read_csv_dataset(archive_path, "complications_deaths")
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# Column name conversion
# ---------------------------------------------------------------------------

# Special cases where mechanical conversion doesn't match API convention.
# Older CMS archives (2019-2020) used different column names than current.
# These overrides normalize all eras to the current API convention.
_COLUMN_OVERRIDES: dict[str, str] = {
    "condition": "_condition",  # T&E: CSV "Condition" -> API "_condition"
    "cms_certification_number_ccn": "facility_id",  # NH CCN field -> facility_id
    # 2019-2020 hospital archives used different column names
    "provider_id": "facility_id",
    "hospital_name": "facility_name",
    "city": "citytown",
    "county_name": "countyparish",
    "phone_number": "telephone_number",
    "zip": "zip_code",
    "measure_start_date": "start_date",
    "measure_end_date": "end_date",
    # 2019-2020 NH archives (column names differ significantly)
    "federal_provider_number": "facility_id",
    "provnum": "facility_id",
    "provname": "facility_name",
    "provider_name": "facility_name",
    "provider_address": "facility_address",
    "provider_city": "citytown",
    "provider_state": "state",
    "provider_zip_code": "zip_code",
    # 2019 NH MDS quality
    "msr_cd": "measure_code",
    "msr_descr": "measure_description",
    "stay_type": "resident_type",
    "q1_measure_fn": "footnote_for_q1_measure_score",
    "q2_measure_fn": "footnote_for_q2_measure_score",
    "q3_measure_fn": "footnote_for_q3_measure_score",
    "q4_measure_fn": "footnote_for_q4_measure_score",
    "measure_score_4qtr_avg": "four_quarter_average_score",
    "score4qtr_fn": "footnote_for_four_quarter_average_score",
    "five_star_msr": "used_in_quality_measure_five_star_rating",
    "filedate": "processing_date",
    # 2019 NH claims quality
    "score_adjusted": "adjusted_score",
    "score_observed": "observed_score",
    "score_expected": "expected_score",
    "score_fn": "footnote_for_score",
    # 2019 NH health deficiencies
    "survey_date_output": "survey_date",
    "surveytype": "survey_type",
    "defpref": "deficiency_prefix",
    "tag": "deficiency_tag_number",
    "tag_desc": "deficiency_description",
    "scope": "scope_severity_code",
    "defstat": "deficiency_corrected",
    "statdate": "correction_date",
    "cycle": "inspection_cycle",
    "standard": "standard_deficiency",
    "complaint": "complaint_deficiency",
    "hlthsrvy_post20171128": "deficiency_category",
    # 2019 NH penalties
    "pnlty_date": "penalty_date",
    "pnlty_type": "penalty_type",
    "fine_amt": "fine_amount",
    "payden_strt_dt": "payment_denial_start_date",
    "payden_days": "payment_denial_length_in_days",
    # 2019 NH ownership
    "role_desc": "role_played_by_owner_or_manager_in_facility",
    "owner_percentage": "ownership_percentage",
}


def csv_header_to_snake(header: str) -> str:
    """Convert a CSV Title Case header to snake_case matching API field names.

    Examples:
        "Facility ID"                    -> "facility_id"
        "CMS Certification Number (CCN)" -> "cms_certification_number_ccn"
        "City/Town"                      -> "city_town"
        "Start Date"                     -> "start_date"
        "Rating Cycle 2/3 Total ..."     -> "rating_cycle_2_3_total_..."
    """
    s = header.strip()
    # Remove parentheses but keep content: "(CCN)" -> "CCN"
    s = s.replace("(", "").replace(")", "")
    # Replace slashes and hyphens with spaces for uniform splitting
    s = s.replace("/", " ").replace("-", " ")
    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    # Lowercase and replace spaces with underscores
    s = s.lower().replace(" ", "_")

    # Apply special-case overrides
    return _COLUMN_OVERRIDES.get(s, s)


# ---------------------------------------------------------------------------
# Dataset file matching
# ---------------------------------------------------------------------------

# Maps our internal dataset keys to filename patterns across archive eras.
# Each entry is a list of regex patterns tried in order against zip member names.
# The FIRST match wins. Patterns are case-insensitive.

HOSPITAL_FILE_PATTERNS: dict[str, list[str]] = {
    "complications_deaths": [
        r"Complications[ _]and[ _]Deaths[ _-]+Hospital\.csv$",
    ],
    "hai": [
        r"Healthcare[ _]Associated[ _]Infections[ _-]+Hospital\.csv$",
    ],
    "readmissions": [
        r"(?<!REH_)Unplanned[ _]Hospital[ _]Visits[ _-]+Hospital\.csv$",
    ],
    "hcahps": [
        r"HCAHPS[ _-]+Hospital\.csv$",
    ],
    "timely_effective": [
        r"(?<!REH_)Timely[ _]and[ _]Effective[ _]Care[ _-]+Hospital\.csv$",
    ],
    "imaging": [
        r"(?<!REH_)Outpatient[ _]Imaging[ _]Efficiency[ _-]+Hospital\.csv$",
    ],
    "mspb": [
        r"Medicare[ _]Hospital[ _]Spending.*Hospital\.csv$",
        r"HOSPITAL_QUARTERLY_MSPB.*\.csv$",
    ],
    "hospital_info": [
        r"Hospital[ _]General[ _]Information\.csv$",
    ],
    "hrrp": [
        r"FY[_ ]?\d{4}.*Hospital[_ ]Readmissions[_ ]Reduction.*Hospital\.csv$",
        r"HOSPITAL_QUARTERLY_QUALITYMEASURE_RRP_HOSPITAL\.csv$",
    ],
    "hacrp": [
        r"FY[_ ]?\d{4}.*HAC[_ ]Reduction.*Hospital\.csv$",
        r"HOSPITAL_QUARTERY_HAC_DOMAIN_HOSPITAL\.csv$",
    ],
    "vbp_tps": [
        r"hvbp_tps[_\.].*\.csv$",
        r"hvbp_tps\.csv$",
    ],
    "measure_dates": [
        r"^Measure[_ ]Dates\.csv$",
    ],
    # National/state average files
    "complications_deaths_national": [
        r"Complications[ _]and[ _]Deaths[ _-]+National\.csv$",
    ],
    "complications_deaths_state": [
        r"Complications[ _]and[ _]Deaths[ _-]+State\.csv$",
    ],
    "hai_national": [
        r"Healthcare[ _]Associated[ _]Infections[ _-]+National\.csv$",
    ],
    "hai_state": [
        r"Healthcare[ _]Associated[ _]Infections[ _-]+State\.csv$",
    ],
    "timely_effective_national": [
        r"Timely[ _]and[ _]Effective[ _]Care[ _-]+National\.csv$",
    ],
    "timely_effective_state": [
        r"Timely[ _]and[ _]Effective[ _]Care[ _-]+State\.csv$",
    ],
    "readmissions_national": [
        r"Unplanned[ _]Hospital[ _]Visits[ _-]+National\.csv$",
    ],
    "hcahps_national": [
        r"HCAHPS[ _-]+National\.csv$",
    ],
    "hcahps_state": [
        r"HCAHPS[ _-]+State\.csv$",
    ],
}

NH_FILE_PATTERNS: dict[str, list[str]] = {
    "nh_provider_info": [
        r"ProviderInfo_Download\.csv$",
        r"NH_ProviderInfo_\w+\.csv$",
    ],
    "nh_mds_quality": [
        r"QualityMsrMDS_Download\.csv$",
        r"NH_QualityMsr_MDS_\w+\.csv$",
    ],
    "nh_claims_quality": [
        r"QualityMsrClaims_Download\.csv$",
        r"NH_QualityMsr_Claims_\w+\.csv$",
    ],
    "nh_health_deficiencies": [
        r"HealthDeficiencies_Download\.csv$",
        r"NH_HealthCitations_\w+\.csv$",
    ],
    "nh_fire_safety": [
        r"FireSafetyDeficiencies_Download\.csv$",
        r"NH_FireSafetyCitations_\w+\.csv$",
    ],
    "nh_penalties": [
        r"Penalties_Download\.csv$",
        r"NH_Penalties_\w+\.csv$",
    ],
    "nh_ownership": [
        r"Ownership_Download\.csv$",
        r"NH_Ownership_\w+\.csv$",
    ],
    "nh_survey_summary": [
        r"SurveySummary_Download\.csv$",
        r"NH_SurveySummary_\w+\.csv$",
    ],
    "nh_survey_dates": [
        r"NH_SurveyDates_\w+\.csv$",
    ],
    "nh_state_averages": [
        r"StateAverages_Download\.csv$",
        r"NH_StateUSAverages_\w+\.csv$",
    ],
    "snf_qrp": [
        r"Skilled.Nursing.Facility.Quality.Reporting.*Provider.data\.csv$",
        r"Skilled_Nursing_Facility_Quality_Reporting.*Provider_Data_\w+\.csv$",
    ],
    "snf_vbp": [
        r"SNF.VBP.Facility.Performance\.csv$",
        r"FY_\d{4}_SNF_VBP_Facility_Performance\.csv$",
    ],
}

ALL_FILE_PATTERNS: dict[str, list[str]] = {**HOSPITAL_FILE_PATTERNS, **NH_FILE_PATTERNS}


def _find_csv_in_zip(zf: zipfile.ZipFile, dataset_key: str) -> str | None:
    """Find the matching CSV filename inside a zip archive."""
    patterns = ALL_FILE_PATTERNS.get(dataset_key, [])
    members = zf.namelist()

    for pattern in patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        for member in members:
            # Match against the basename (handles nested dirs inside zip)
            basename = member.rsplit("/", 1)[-1] if "/" in member else member
            if regex.search(basename) or regex.search(member):
                return member
    return None


# ---------------------------------------------------------------------------
# Archive discovery
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ArchiveInfo:
    """Metadata about a discovered CMS archive zip file."""

    path: Path
    provider_type: str  # "hospitals" or "nursing_homes"
    vintage: str  # e.g., "2024-07", "2019-01"
    year: int
    month: int

    @property
    def vintage_label(self) -> str:
        """Human-readable label like '2024-07'."""
        return f"{self.year}-{self.month:02d}"


def discover_archives(data_dir: str | Path) -> list[ArchiveInfo]:
    """Discover all CMS archive zip files under a data directory.

    Scans recursively for .zip files and extracts vintage metadata from
    directory/filename patterns.

    Returns archives sorted chronologically.
    """
    data_path = Path(data_dir)
    archives: list[ArchiveInfo] = []

    for zip_path in sorted(data_path.rglob("*.zip")):
        # Determine provider type from path
        rel = zip_path.relative_to(data_path)
        parts_str = str(rel).replace("\\", "/").lower()

        if "hospital" in parts_str:
            provider_type = "hospitals"
        elif "nursing_home" in parts_str or "nh_archive" in parts_str:
            provider_type = "nursing_homes"
        else:
            continue

        # Extract month/year from filename
        # Patterns: hospitals_07_2024.zip, nh_archive_01_2019.zip,
        #           nursing_homes_including_rehab_services_01_2024.zip,
        #           hos_revised_flatfiles_archive_03_2019.zip
        match = re.search(r"(\d{2})_(\d{4})\.zip$", zip_path.name)
        if not match:
            continue

        month = int(match.group(1))
        year = int(match.group(2))

        archives.append(ArchiveInfo(
            path=zip_path,
            provider_type=provider_type,
            vintage=f"{year}-{month:02d}",
            year=year,
            month=month,
        ))

    return sorted(archives, key=lambda a: (a.provider_type, a.year, a.month))


# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------

def _open_csv_in_zip(
    zf: zipfile.ZipFile,
    member: str,
) -> io.TextIOWrapper:
    """Open a CSV file inside a zip with robust encoding handling.

    Uses utf-8-sig (handles BOM) with errors='replace' so that the rare
    non-UTF-8 byte in older CMS archives (e.g., 0x96 en-dash in latin-1
    address fields) doesn't crash the pipeline. The replacement character
    only affects display strings (addresses, names), never measure values.
    """
    raw = zf.open(member)
    return io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")


def read_csv_dataset(
    archive_path: str | Path,
    dataset_key: str,
) -> list[dict[str, str]]:
    """Read a dataset from a CMS archive zip, returning rows as snake_case dicts.

    Args:
        archive_path: Path to the zip file.
        dataset_key: Key from HOSPITAL_FILE_PATTERNS or NH_FILE_PATTERNS.

    Returns:
        List of dicts with snake_case keys matching API field names.
        Empty list if the dataset is not found in the archive.

    Raises:
        FileNotFoundError: If the zip file doesn't exist.
    """
    archive_path = Path(archive_path)
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with zipfile.ZipFile(archive_path) as zf:
        member = _find_csv_in_zip(zf, dataset_key)
        if member is None:
            return []

        text = _open_csv_in_zip(zf, member)
        reader = csv.DictReader(text)
        if reader.fieldnames is None:
            return []

        col_map = {h: csv_header_to_snake(h) for h in reader.fieldnames}

        return [
            {col_map[k]: v for k, v in row.items() if k in col_map}
            for row in reader
        ]


def iter_csv_dataset(
    archive_path: str | Path,
    dataset_key: str,
) -> Iterator[dict[str, str]]:
    """Streaming version of read_csv_dataset for large files.

    Yields one dict per row. Use this for datasets over ~100K rows
    (NH Health Citations, HCAHPS, etc.) to avoid loading everything into memory.
    """
    archive_path = Path(archive_path)
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    with zipfile.ZipFile(archive_path) as zf:
        member = _find_csv_in_zip(zf, dataset_key)
        if member is None:
            return

        text = _open_csv_in_zip(zf, member)
        reader = csv.DictReader(text)
        if reader.fieldnames is None:
            return

        col_map = {h: csv_header_to_snake(h) for h in reader.fieldnames}

        for row in reader:
            yield {col_map[k]: v for k, v in row.items() if k in col_map}


def get_csv_headers(
    archive_path: str | Path,
    dataset_key: str,
) -> list[str] | None:
    """Return the snake_case column headers for a dataset in an archive.

    Returns None if the dataset is not found.
    """
    archive_path = Path(archive_path)
    with zipfile.ZipFile(archive_path) as zf:
        member = _find_csv_in_zip(zf, dataset_key)
        if member is None:
            return None

        with zf.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig")
            reader = csv.DictReader(text)
            if reader.fieldnames is None:
                return None
            return [csv_header_to_snake(h) for h in reader.fieldnames]


def list_datasets_in_archive(archive_path: str | Path) -> list[str]:
    """Return which dataset keys are available in an archive zip."""
    archive_path = Path(archive_path)
    found: list[str] = []
    with zipfile.ZipFile(archive_path) as zf:
        for key in ALL_FILE_PATTERNS:
            if _find_csv_in_zip(zf, key) is not None:
                found.append(key)
    return sorted(found)
