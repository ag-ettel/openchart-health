"""
Shared normalizer infrastructure — suppression detection, footnote parsing,
period extraction, value conversion.

All per-dataset normalizers import from this module. Do not duplicate these
functions in individual normalizers — if you find yourself copying logic, it
belongs here.

Design principle (Phase 1 ethos): log and store unknown values rather than
rejecting them. An unknown value stored with an anomaly log entry is
recoverable. A rejected row is data loss.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from pipeline.config import COMPARED_TO_NATIONAL_MAPPING

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Suppression detection
# ---------------------------------------------------------------------------

# CMS uses inconsistent strings across datasets to indicate suppressed values.
# All comparisons are case-insensitive.
SUPPRESSION_SENTINELS: frozenset[str] = frozenset({
    "not available",
    "not applicable",
    "n/a",
    "--",  # 2019-era HAI archives
})

# Values that indicate count-level suppression (DEC-023: the primary measure
# value IS populated, but count fields are suppressed for privacy).
COUNT_SUPPRESSION_SENTINELS: frozenset[str] = frozenset({
    "too few to report",
    "n/a",
})


def is_suppressed(value: str) -> bool:
    """Check if a raw CMS string represents a suppressed value."""
    return value.strip().lower() in SUPPRESSION_SENTINELS


def is_count_suppressed(value: str) -> bool:
    """Check if a raw CMS count field is suppressed for privacy (DEC-023)."""
    return value.strip().lower() in COUNT_SUPPRESSION_SENTINELS


def detect_suppression_state(
    score: str,
    compared_to_national: str | None = None,
    footnote: str | None = None,
) -> tuple[bool, bool, str | None]:
    """Determine suppression and not-reported state from raw CMS fields.

    Returns:
        (suppressed, not_reported, reason)

    Rules:
    - suppressed=True when CMS could not calculate the measure (too few cases,
      not enough data). The primary indicator is score being a suppression sentinel.
    - not_reported=True when the hospital did not submit data for this measure
      (footnote 5 = "Results are not available for this reporting period").
    - Both can be False (normal reported value).
    - Both should not be True simultaneously.
    """
    score_lower = score.strip().lower() if score else ""

    # Not-reported check FIRST — footnote 5 means hospital didn't report.
    # This takes priority over suppression because the distinction matters:
    # suppressed = CMS tried to calculate but couldn't (too few cases).
    # not_reported = hospital didn't submit data at all.
    fn_codes = parse_footnote_codes(footnote) if footnote else []
    if 5 in fn_codes:
        return False, True, "Results are not available for this reporting period"

    # Suppressed: score is a sentinel value
    if score_lower in SUPPRESSION_SENTINELS:
        # Try to determine reason from compared_to_national or footnote
        reason = _suppression_reason(compared_to_national, footnote)
        return True, False, reason

    return False, False, None


def _suppression_reason(
    compared_to_national: str | None,
    footnote: str | None,
) -> str | None:
    """Derive a human-readable suppression reason from CMS context fields."""
    if compared_to_national:
        ctn_lower = compared_to_national.strip().lower()
        if "too small" in ctn_lower or "too few" in ctn_lower:
            return "Number of cases too small"

    if footnote:
        codes = parse_footnote_codes(footnote)
        if 1 in codes:
            return "Number of cases too small"
        if 13 in codes:
            return "Results cannot be calculated for this reporting period"
        if 12 in codes:
            return "Measure does not apply to this hospital for this reporting period"
        if 4 in codes:
            return "Data suppressed by CMS for one or more quarters"

    return "Data not available"


# ---------------------------------------------------------------------------
# Footnote parsing
# ---------------------------------------------------------------------------

# Hospital footnote crosswalk — source of truth: docs/Footnote_Crosswalk.csv
HOSPITAL_FOOTNOTE_TEXT: dict[int, str] = {
    1: "The number of cases/patients is too few to report.",
    2: "Data submitted were based on a sample of cases/patients.",
    3: "Results are based on a shorter time period than required.",
    4: "Data suppressed by CMS for one or more quarters.",
    5: "Results are not available for this reporting period.",
    6: "Fewer than 100 patients completed the CAHPS survey.",
    7: "No cases met the criteria for this measure.",
    8: "The lower limit of the confidence interval cannot be calculated if the number of observed infections equals zero.",
    9: "No data are available from the state/territory for this reporting period.",
    10: "Very few patients were eligible for the CAHPS survey.",
    11: "There were discrepancies in the data collection process.",
    12: "This measure does not apply to this hospital for this reporting period.",
    13: "Results cannot be calculated for this reporting period.",
    14: "The results for this state are combined with nearby states to protect confidentiality.",
    15: "The number of cases/patients is too few to report a star rating.",
    16: "There are too few measures or measure groups reported to calculate a star rating.",
    17: "This hospital's star rating only includes data reported on inpatient services.",
    18: "This result is not based on performance data.",
    19: "Data are shown only for hospitals that participate in the IQR and OQR programs.",
    20: "State and national averages do not include VHA hospital data.",
    21: "Patient survey results for VHA hospitals are not official HCAHPS results.",
    22: "Overall star ratings are not calculated for DoD hospitals.",
    23: "Data are based on claims; the hospital has reported discrepancies.",
    24: "Results for this VHA hospital are combined with the administrative parent hospital.",
    25: "State and national averages include VHA hospital data.",
    26: "State and national averages include DoD hospital data.",
    27: "Retired.",
    28: "Results are based on data submitted with a CMS-approved Extraordinary Circumstances Exception.",
    29: "This measure was calculated using partial performance period data.",
}


# Nursing home footnote codes — distinct from hospital codes.
# Source: NH Data Dictionary Table 15, confirmed Phase 0.
NH_FOOTNOTE_TEXT: dict[int, str] = {
    1: "Newly certified nursing home with less than 12-15 months of data or less than 6 months open.",
    2: "Not enough data available to calculate a star rating.",
    6: "Data did not meet criteria for this staffing measure.",
    7: "CMS determined the percentage is not accurate or data has been suppressed.",
    9: "Number of residents or stays is too small to report.",
    10: "Data is missing or was not submitted.",
    13: "Results are based on a shorter time period than required.",
    14: "Not required to submit SNF QRP data.",
    18: "Not rated due to Special Focus Facility program.",
    20: "Accuracy of data for this rating could not be validated.",
    21: "Accuracy of data for this measure could not be validated.",
    22: "Street address could not be matched; latitude/longitude based on ZIP code.",
    23: "Facility did not submit staffing data.",
    24: "Facility reported a high number of days without an RN onsite.",
    25: "Accuracy of staffing data could not be validated.",
    26: "No staffing data or invalid data for turnover; receives minimum points.",
    27: "Staffing data did not meet criteria for turnover; excluded from rating.",
    28: "Annual measure; quarterly data is not available.",
}


def parse_footnote_codes(raw: str) -> list[int]:
    """Parse CMS footnote field into a list of integer codes.

    CMS uses comma-space-separated codes: "1, 28" -> [1, 28].
    Empty string or whitespace returns [].
    Non-integer tokens are logged and skipped.
    """
    if not raw or not raw.strip():
        return []

    codes: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            codes.append(int(token))
        except ValueError:
            # 2019-era footnotes include full text: "13 - Results cannot..."
            # Extract the leading integer.
            match = re.match(r"^(\d+)\s*[-–]", token)
            if match:
                codes.append(int(match.group(1)))
            else:
                # Non-integer footnotes (e.g., "a", "*", "**" in HACRP)
                logger.debug("Non-integer footnote code: %r in raw=%r", token, raw)
    return codes


def footnote_texts(
    codes: list[int],
    provider_type: str = "HOSPITAL",
) -> list[str]:
    """Look up human-readable text for a list of footnote codes.

    Uses hospital or nursing home lookup table based on provider_type.
    Unknown codes produce a generic message and are logged.
    """
    lookup = NH_FOOTNOTE_TEXT if provider_type == "NURSING_HOME" else HOSPITAL_FOOTNOTE_TEXT
    texts: list[str] = []
    for code in codes:
        text = lookup.get(code)
        if text:
            texts.append(text)
        else:
            logger.warning("Unknown footnote code: %d (provider_type=%s)", code, provider_type)
            texts.append(f"Footnote {code} (see CMS documentation).")
    return texts


# ---------------------------------------------------------------------------
# compared_to_national mapping
# ---------------------------------------------------------------------------

def normalize_compared_to_national(raw: str | None) -> str | None:
    """Map CMS compared_to_national string to canonical value (DEC-022).

    Case-insensitive. Returns None if input is empty/None.
    Logs and returns the raw value (uppercased) if no mapping found —
    stores the unknown value rather than discarding it.
    """
    if not raw or not raw.strip():
        return None

    canonical = COMPARED_TO_NATIONAL_MAPPING.get(raw.strip().lower())
    if canonical:
        return canonical

    logger.warning(
        "Unknown compared_to_national value: %r — storing as-is", raw
    )
    return raw.strip().upper()


# ---------------------------------------------------------------------------
# Period parsing
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    (re.compile(r"^(\d{2})/(\d{2})/(\d{4})$"), "%m/%d/%Y"),  # MM/DD/YYYY
    (re.compile(r"^(\d{4})-(\d{2})-(\d{2})$"), "%Y-%m-%d"),  # YYYY-MM-DD
]


def parse_date(raw: str | None) -> date | None:
    """Parse a CMS date string to a Python date.

    Handles MM/DD/YYYY (CSV) and YYYY-MM-DD (API) formats.
    Returns None for empty/unparseable values.
    """
    if not raw or not raw.strip():
        return None

    raw = raw.strip()
    for pattern, fmt in _DATE_PATTERNS:
        if pattern.match(raw):
            try:
                parts = raw.split("/" if "/" in raw else "-")
                if fmt == "%m/%d/%Y":
                    return date(int(parts[2]), int(parts[0]), int(parts[1]))
                else:
                    return date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                pass

    logger.warning("Unparseable date: %r", raw)
    return None


def derive_period_label(
    start_date: date | None,
    end_date: date | None,
    raw_period: str | None = None,
) -> str:
    """Derive a period_label string for the upsert key.

    Uses the raw period string if provided (e.g., "2024Q4-2025Q3" for MDS).
    Otherwise derives from start/end dates: "2022-07 to 2024-06".
    Falls back to "unknown" if nothing is available.
    """
    if raw_period and raw_period.strip():
        return raw_period.strip()

    if start_date and end_date:
        return f"{start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}"

    return "unknown"


# ---------------------------------------------------------------------------
# Value conversion
# ---------------------------------------------------------------------------

def parse_decimal(raw: str | None) -> Decimal | None:
    """Parse a CMS numeric string to Decimal (Rule 10: never use float).

    Returns None for empty/suppressed values.
    """
    if not raw or not raw.strip():
        return None

    cleaned = raw.strip()
    if cleaned.lower() in SUPPRESSION_SENTINELS:
        return None

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        # EDV categorical scores ("very high", "high", "medium", "low") and other
        # CMS string values flow through here legitimately and are stored as
        # score_text. Demote to debug so they don't flood the ingest log.
        logger.debug("Non-numeric value for parse_decimal: %r", raw)
        return None


def parse_int(raw: str | None) -> int | None:
    """Parse a CMS integer string. Returns None for empty/suppressed values."""
    if not raw or not raw.strip():
        return None

    cleaned = raw.strip()
    if cleaned.lower() in SUPPRESSION_SENTINELS:
        return None

    try:
        # Handle "1,234" formatted numbers
        return int(cleaned.replace(",", ""))
    except ValueError:
        logger.warning("Unparseable integer: %r", raw)
        return None


# ---------------------------------------------------------------------------
# Row-level normalization output
# ---------------------------------------------------------------------------

def normalize_measure_row(
    raw: dict[str, str],
    *,
    measure_id_field: str = "measure_id",
    score_field: str = "score",
    denominator_field: str | None = "denominator",
    sample_field: str | None = None,
    lower_est_field: str | None = "lower_estimate",
    higher_est_field: str | None = "higher_estimate",
    compared_field: str | None = "compared_to_national",
    footnote_field: str = "footnote",
    start_date_field: str = "start_date",
    end_date_field: str = "end_date",
    provider_id_field: str = "facility_id",
) -> dict[str, Any]:
    """Normalize a single CMS measure row into pipeline-standard fields.

    This is the shared normalization pass. Per-dataset normalizers call this
    and then apply dataset-specific logic on top (e.g., EDV score_text,
    HRRP count-suppression, HAI sub-measure handling).

    Returns a BASE dict. Per-dataset normalizers must add:
      - source_dataset_id (which CMS dataset this came from)
    The store layer adds before upsert:
      - provider_type (from providers table lookup)
      - pipeline_run_id (from current pipeline run)
    The transform layer adds:
      - reliability_flag (computed from sample_size)
      - confidence_interval_lower/upper, ci_source, prior_source (for calculable measures)
    Benchmark values (national_avg, state_avg) live in measure_benchmarks table (DEC-036).
    """
    # Raw value preservation (Rule 7)
    score_raw = raw.get(score_field, "")
    raw_value = score_raw

    # Parse dates
    start_date = parse_date(raw.get(start_date_field))
    end_date = parse_date(raw.get(end_date_field))
    period_label = derive_period_label(start_date, end_date)

    # Footnotes
    footnote_raw = raw.get(footnote_field, "")
    fn_codes = parse_footnote_codes(footnote_raw)
    fn_texts = footnote_texts(fn_codes)

    # Suppression detection
    compared_raw = raw.get(compared_field, "") if compared_field else ""
    suppressed, not_reported, suppression_reason = detect_suppression_state(
        score_raw, compared_raw, footnote_raw
    )

    # Numeric value
    numeric_value = None if suppressed or not_reported else parse_decimal(score_raw)

    # Confidence intervals
    ci_lower = parse_decimal(raw.get(lower_est_field, "")) if lower_est_field else None
    ci_upper = parse_decimal(raw.get(higher_est_field, "")) if higher_est_field else None

    # Sample size / denominator
    denominator = parse_int(raw.get(denominator_field, "")) if denominator_field else None
    sample_size = parse_int(raw.get(sample_field, "")) if sample_field else denominator

    # compared_to_national canonical mapping
    compared_canonical = normalize_compared_to_national(compared_raw) if compared_field else None

    return {
        "provider_id": raw.get(provider_id_field, "").strip().zfill(6),
        "measure_id": raw.get(measure_id_field, "").strip(),
        "raw_value": raw_value,
        "numeric_value": numeric_value,
        "score_text": None,  # Set by per-dataset normalizer for categorical measures
        "confidence_interval_lower": ci_lower,
        "confidence_interval_upper": ci_upper,
        # ci_source / prior_source: set by normalize for CMS-published intervals,
        # overwritten by transform layer for calculated intervals (DEC-029).
        "ci_source": "cms_published" if (ci_lower is not None or ci_upper is not None) else None,
        "prior_source": None,  # Only populated when ci_source == "calculated"
        "compared_to_national": compared_canonical,
        "suppressed": suppressed,
        "suppression_reason": suppression_reason if suppressed else None,
        "not_reported": not_reported,
        "not_reported_reason": suppression_reason if not_reported else None,
        "count_suppressed": False,  # Set by per-dataset normalizer (HRRP)
        "footnote_codes": fn_codes if fn_codes else None,
        "footnote_text": fn_texts if fn_texts else None,
        "period_start": start_date,
        "period_end": end_date,
        "period_label": period_label,
        "sample_size": sample_size,
        "denominator": denominator,
        "stratification": "",  # Non-stratified default
    }
