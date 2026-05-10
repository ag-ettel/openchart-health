"""
Normalizer for Complications and Deaths dataset (ynj2-r877).

20 measures: 7 mortality, 1 complication (COMP_HIP_KNEE), 12 PSI.
Phase 0 reference: docs/phase_0_findings.md §5

Key dataset-specific behaviors:
- HGLM risk-adjusted with CMS-published CIs (lower_estimate / higher_estimate)
- compared_to_national dual phrasing: "Rate" for individual measures,
  "Value" for PSI_90 composite (DEC-022)
- PSI_90 denominator = "Not Applicable" (not suppression — composite has no
  single patient-count denominator). Store as null denominator, not suppressed.
- Footnote codes observed: 1, 5, 7, 13, 19, 23, 28, 29
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import normalize_measure_row

logger = logging.getLogger(__name__)

# Dataset identifier for provenance tracking
DATASET_ID = "ynj2-r877"

# All measure IDs in this dataset (confirmed Phase 0, full-population CSV scan)
MEASURE_IDS = frozenset({
    # Mortality (7)
    "MORT_30_AMI", "MORT_30_CABG", "MORT_30_COPD",
    "MORT_30_HF", "MORT_30_PN", "MORT_30_STK",
    "Hybrid_HWM",
    # Complication (1)
    "COMP_HIP_KNEE",
    # Patient Safety Indicators (12)
    "PSI_03", "PSI_04", "PSI_06", "PSI_08", "PSI_09", "PSI_10",
    "PSI_11", "PSI_12", "PSI_13", "PSI_14", "PSI_15", "PSI_90",
})

# Measures that existed in older archives but were retired/renamed
RETIRED_MEASURE_IDS = frozenset({
    "READM_30_HOSP_WIDE",  # Renamed to Hybrid_HWR (readmissions dataset)
})

# CMS changed PSI measure IDs between 2019 and 2021. Map old -> current.
MEASURE_ID_ALIASES: dict[str, str] = {
    "PSI_3_ULCER": "PSI_03",
    "PSI_4_SURG_COMP": "PSI_04",
    "PSI_6_IAT_PTX": "PSI_06",
    "PSI_8_POST_HIP": "PSI_08",
    "PSI_9_POST_HEM": "PSI_09",
    "PSI_10_POST_KIDNEY": "PSI_10",
    "PSI_11_POST_RESP": "PSI_11",
    "PSI_12_POSTOP_PULMEMB_DVT": "PSI_12",
    "PSI_13_POST_SEPSIS": "PSI_13",
    "PSI_14_POSTOP_DEHIS": "PSI_14",
    "PSI_15_ACC_LAC": "PSI_15",
    "PSI_90_SAFETY": "PSI_90",
}


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    """Normalize a single Complications and Deaths row.

    Args:
        raw: Dict with snake_case keys (from csv_reader or API client).

    Returns:
        Normalized dict ready for validation and upsert, or None if the row
        should be skipped (e.g., unrecognized measure_id from a retired measure).
    """
    measure_id = raw.get("measure_id", "").strip()

    # Normalize old-era measure IDs to current convention
    measure_id = MEASURE_ID_ALIASES.get(measure_id, measure_id)
    raw["measure_id"] = measure_id

    # Skip retired measures from older archives
    if measure_id in RETIRED_MEASURE_IDS:
        return None

    # Log unknown measure IDs but don't reject — store them
    if measure_id and measure_id not in MEASURE_IDS:
        logger.warning(
            "Unknown measure_id in complications_deaths: %r (provider=%s)",
            measure_id,
            raw.get("facility_id", "?"),
        )

    # Base normalization (shared infrastructure)
    result = normalize_measure_row(
        raw,
        measure_id_field="measure_id",
        score_field="score",
        denominator_field="denominator",
        lower_est_field="lower_estimate",
        higher_est_field="higher_estimate",
        compared_field="compared_to_national",
        footnote_field="footnote",
    )

    # Dataset-specific: PSI_90 denominator = "Not Applicable" is not suppression.
    # It's a composite index with no single patient-count denominator.
    denom_raw = raw.get("denominator", "").strip()
    if denom_raw.lower() == "not applicable":
        result["denominator"] = None
        result["sample_size"] = None
        # Don't set suppressed — the score IS populated for PSI_90

    # Attach dataset provenance
    result["source_dataset_id"] = DATASET_ID

    return result


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Normalize all rows from a Complications and Deaths CSV/API response.

    Args:
        rows: List of raw dicts from csv_reader or API client.

    Returns:
        List of normalized dicts. Skipped rows (retired measures) are excluded.
    """
    results: list[dict[str, Any]] = []
    for raw in rows:
        normalized = normalize_row(raw)
        if normalized is not None:
            results.append(normalized)
    return results
