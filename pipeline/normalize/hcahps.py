"""
Normalizer for HCAHPS Patient Survey dataset (dgck-syfz).

68 measures. One row per measure per hospital.
Phase 0 reference: docs/phase_0_findings.md §4

Key dataset-specific behaviors:
- Uses `hcahps_measure_id` (not `measure_id`) as the measure identifier
- Primary score: `hcahps_answer_percent` (percentage)
- Companion fields: `patient_survey_star_rating`, `hcahps_linear_mean_value` —
  both "Not Applicable" on most rows (individual answer rows vs summary rows)
- Multiple footnote companion fields per value column
- PATIENT_MIX_ADJUSTMENT risk model — no CIs available, no num/denom
- `number_of_completed_surveys` is the sample size (shared across all measures
  for a given hospital)
- `survey_response_rate_percent` provides response rate context
- DEC-010: hcahps_linear_mean_value discarded (not stored)
- No compared_to_national field
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import (
    derive_period_label,
    footnote_texts,
    is_suppressed,
    parse_date,
    parse_decimal,
    parse_footnote_codes,
    parse_int,
)

logger = logging.getLogger(__name__)

DATASET_ID = "dgck-syfz"


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    measure_id = raw.get("hcahps_measure_id", "").strip()
    if not measure_id:
        return None

    provider_id = raw.get("facility_id", "").strip().zfill(6)
    score_raw = raw.get("hcahps_answer_percent", "").strip()

    # Parse dates
    start_date = parse_date(raw.get("start_date"))
    end_date = parse_date(raw.get("end_date"))
    period_label = derive_period_label(start_date, end_date)

    # Primary footnote is on the answer percent field
    fn_raw = raw.get("hcahps_answer_percent_footnote", "").strip()
    fn_codes = parse_footnote_codes(fn_raw)
    fn_texts = footnote_texts(fn_codes)

    # "Not Applicable" in HCAHPS means this field type doesn't apply to this
    # row (e.g., answer percent on a star rating row). It's structural, not
    # suppression. "Not Available" means the data was expected but missing.
    is_not_applicable = score_raw.lower() == "not applicable"
    suppressed = False
    not_reported = False

    if 5 in fn_codes:
        not_reported = True
    elif not is_not_applicable and is_suppressed(score_raw):
        suppressed = True

    numeric_value = None
    if not suppressed and not not_reported and not is_not_applicable:
        numeric_value = parse_decimal(score_raw)

    # Sample size from completed surveys
    sample_size = parse_int(raw.get("number_of_completed_surveys"))

    return {
        "provider_id": provider_id,
        "measure_id": measure_id,
        "raw_value": score_raw,
        "numeric_value": numeric_value,
        "score_text": None,
        "confidence_interval_lower": None,  # HCAHPS has no CIs
        "confidence_interval_upper": None,
        "compared_to_national": None,  # No compared_to_national field
        "suppressed": suppressed,
        "suppression_reason": "Data not available" if suppressed else None,
        "not_reported": not_reported,
        "not_reported_reason": "Results are not available for this reporting period" if not_reported else None,
        "count_suppressed": False,
        "footnote_codes": fn_codes if fn_codes else None,
        "footnote_text": fn_texts if fn_texts else None,
        "period_start": start_date,
        "period_end": end_date,
        "period_label": period_label,
        "sample_size": sample_size,
        "denominator": sample_size,
        "stratification": "",
        "source_dataset_id": DATASET_ID,
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
