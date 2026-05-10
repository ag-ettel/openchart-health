"""
Normalizer for Unplanned Hospital Visits / Readmissions dataset (632h-zaca).

14 measures (current): 6 READM_30, 3 EDAC_30, Hybrid_HWR, OP_32, OP_35_ADM,
OP_35_ED, OP_36.

Phase 0 reference: docs/phase_0_findings.md §7

Key dataset-specific behaviors:
- HGLM risk-adjusted with CMS-published CIs for READM/Hybrid/OP_32/OP_35
- EDAC measures use "Days" phrasing for compared_to_national (DEC-022)
- OP_36 uses "expected" phrasing for compared_to_national (DEC-022)
- EDAC compared_to_national is "Not Available" in some archives (no CI)
- CMS inconsistent capitalization: "Number of Cases Too Small" vs
  "Number of cases too small" in the same snapshot (AMB-3)
- number_of_patients / number_of_patients_returned fields (2021+ only)
- 2019 uses OP-32 (hyphen) not OP_32 (underscore)
- 2019 has READM_30_HOSP_WIDE and READM_30_STK (retired in current)
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import normalize_measure_row, parse_int

logger = logging.getLogger(__name__)

DATASET_ID = "632h-zaca"

MEASURE_IDS = frozenset({
    "READM_30_AMI", "READM_30_CABG", "READM_30_COPD",
    "READM_30_HF", "READM_30_HIP_KNEE", "READM_30_PN",
    "EDAC_30_AMI", "EDAC_30_HF", "EDAC_30_PN",
    "Hybrid_HWR",
    "OP_32", "OP_35_ADM", "OP_35_ED", "OP_36",
})

# Measures from older archives that were retired or renamed
RETIRED_MEASURE_IDS = frozenset({
    "READM_30_HOSP_WIDE",  # Renamed to Hybrid_HWR
    "READM_30_STK",        # Retired
})

# 2019-era measure ID aliases (hyphens to underscores)
MEASURE_ID_ALIASES: dict[str, str] = {
    "OP-32": "OP_32",
    "OP-35-ADM": "OP_35_ADM",
    "OP-35-ED": "OP_35_ED",
    "OP-36": "OP_36",
}


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    """Normalize a single Readmissions row."""
    measure_id = raw.get("measure_id", "").strip()

    # Normalize 2019-era measure IDs
    measure_id = MEASURE_ID_ALIASES.get(measure_id, measure_id)
    raw["measure_id"] = measure_id

    if measure_id in RETIRED_MEASURE_IDS:
        return None

    if measure_id and measure_id not in MEASURE_IDS:
        logger.warning(
            "Unknown measure_id in readmissions: %r (provider=%s)",
            measure_id, raw.get("facility_id", "?"),
        )

    # Determine which fields carry sample size data.
    # number_of_patients / number_of_patients_returned exist in 2021+ only.
    # denominator exists in all eras.
    sample_field = None
    if raw.get("number_of_patients", ""):
        sample_field = "number_of_patients"

    result = normalize_measure_row(
        raw,
        measure_id_field="measure_id",
        score_field="score",
        denominator_field="denominator",
        sample_field=sample_field,
        lower_est_field="lower_estimate",
        higher_est_field="higher_estimate",
        compared_field="compared_to_national",
        footnote_field="footnote",
    )

    # number_of_patients_returned is an additional count field (not in common)
    num_returned = parse_int(raw.get("number_of_patients_returned"))
    # Store in raw_value context — the display layer may surface this
    if num_returned is not None:
        result["_number_of_patients_returned"] = num_returned

    result["source_dataset_id"] = DATASET_ID
    return result


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Normalize all rows from a Readmissions CSV/API response."""
    results: list[dict[str, Any]] = []
    for raw in rows:
        normalized = normalize_row(raw)
        if normalized is not None:
            results.append(normalized)
    return results
