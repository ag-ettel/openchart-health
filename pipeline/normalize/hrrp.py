"""
Normalizer for Hospital Readmissions Reduction Program dataset (9n3s-kdb3).

Payment adjustment program, not a quality measure dataset. Each row is one
condition-specific excess readmission ratio per hospital per program year.

Phase 0 reference: docs/phase_0_findings.md §9

Key dataset-specific behaviors:
- Uses `measure_name` (not `measure_id`) as the measure identifier
- 2019 uses underscores (READM_30_AMI_HRRP), 2026 uses hyphens (READM-30-AMI-HRRP)
- Three-way suppression state (DEC-023):
  1. Normal: all fields populated
  2. Count-suppressed: number_of_readmissions="Too Few to Report",
     number_of_discharges="N/A", but excess_readmission_ratio IS populated
  3. Full suppression: all measure fields "N/A"
- No address fields in this dataset
- CCN may not be zero-padded in older archives
- No compared_to_national field
- No lower_estimate / higher_estimate fields
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import (
    derive_period_label,
    footnote_texts,
    is_count_suppressed,
    is_suppressed,
    parse_date,
    parse_decimal,
    parse_footnote_codes,
    parse_int,
)

logger = logging.getLogger(__name__)

DATASET_ID = "9n3s-kdb3"

# Normalize the HRRP measure_name to a stable measure_id.
# HRRP uses measure_name as the row identifier, not measure_id.
# The name format varies across eras (hyphens vs underscores).
_MEASURE_NAME_TO_ID: dict[str, str] = {
    # Current era (hyphens)
    "readm-30-ami-hrrp": "HRRP_AMI",
    "readm-30-cabg-hrrp": "HRRP_CABG",
    "readm-30-copd-hrrp": "HRRP_COPD",
    "readm-30-hf-hrrp": "HRRP_HF",
    "readm-30-hip-knee-hrrp": "HRRP_HIP_KNEE",
    "readm-30-pn-hrrp": "HRRP_PN",
    # 2019 era (underscores)
    "readm_30_ami_hrrp": "HRRP_AMI",
    "readm_30_cabg_hrrp": "HRRP_CABG",
    "readm_30_copd_hrrp": "HRRP_COPD",
    "readm_30_hf_hrrp": "HRRP_HF",
    "readm_30_hip_knee_hrrp": "HRRP_HIP_KNEE",
    "readm_30_pn_hrrp": "HRRP_PN",
}


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    """Normalize a single HRRP row.

    Returns a dict shaped for provider_payment_adjustments upsert,
    NOT provider_measure_values. HRRP condition-specific ratios are
    payment program data, not quality measures. The program-level
    payment adjustment outcome is what goes in provider_payment_adjustments.
    Individual condition ratios go in provider_measure_values for display.
    """
    # HRRP uses measure_name as identifier
    measure_name = raw.get("measure_name", "").strip()
    measure_id = _MEASURE_NAME_TO_ID.get(measure_name.lower())
    if measure_id is None:
        logger.warning("Unknown HRRP measure_name: %r", measure_name)
        measure_id = measure_name.upper().replace("-", "_")

    provider_id = raw.get("facility_id", "").strip().zfill(6)

    # Parse dates
    start_date = parse_date(raw.get("start_date"))
    end_date = parse_date(raw.get("end_date"))
    period_label = derive_period_label(start_date, end_date)

    # Footnotes
    fn_raw = raw.get("footnote", "")
    fn_codes = parse_footnote_codes(fn_raw)
    fn_texts = footnote_texts(fn_codes)

    # Three-way suppression detection (DEC-023)
    ratio_raw = raw.get("excess_readmission_ratio", "").strip()
    readmissions_raw = raw.get("number_of_readmissions", "").strip()
    discharges_raw = raw.get("number_of_discharges", "").strip()

    if 5 in fn_codes:
        # Not-reported takes priority (same as common.py logic)
        suppressed = False
        not_reported = True
        count_suppressed = False
        numeric_value = None
    elif is_suppressed(ratio_raw):
        # State 3: Full suppression — no ratio calculated
        suppressed = True
        not_reported = False
        count_suppressed = False
        numeric_value = None
    elif is_count_suppressed(readmissions_raw):
        # State 2: Count-suppressed — ratio exists but counts hidden
        suppressed = False
        not_reported = False
        count_suppressed = True
        numeric_value = parse_decimal(ratio_raw)
    else:
        # State 1: Normal
        suppressed = False
        not_reported = False
        count_suppressed = False
        numeric_value = parse_decimal(ratio_raw)

    return {
        "provider_id": provider_id,
        "measure_id": measure_id,
        "raw_value": ratio_raw,
        "numeric_value": numeric_value,
        "score_text": None,
        "confidence_interval_lower": None,
        "confidence_interval_upper": None,
        "compared_to_national": None,
        "suppressed": suppressed,
        "suppression_reason": "All fields N/A" if suppressed else None,
        "not_reported": not_reported,
        "not_reported_reason": "Results are not available for this reporting period" if not_reported else None,
        "count_suppressed": count_suppressed,
        "footnote_codes": fn_codes if fn_codes else None,
        "footnote_text": fn_texts if fn_texts else None,
        "period_start": start_date,
        "period_end": end_date,
        "period_label": period_label,
        "sample_size": parse_int(discharges_raw) if not is_count_suppressed(discharges_raw) else None,
        "denominator": parse_int(discharges_raw) if not is_count_suppressed(discharges_raw) else None,
        "stratification": "",
        "source_dataset_id": DATASET_ID,
        # HRRP-specific fields for provider_measure_values
        "predicted_readmission_rate": parse_decimal(raw.get("predicted_readmission_rate")),
        "expected_readmission_rate": parse_decimal(raw.get("expected_readmission_rate")),
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
