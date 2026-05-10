"""
Normalizer for Nursing Home Claims Quality Measures dataset (ijh5-nb2v).

4 measures (codes 521, 522, 551, 552). observed/expected/adjusted triplet (DEC-016).
Phase 0 reference: docs/phase_0_findings.md §14
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import (
    footnote_texts,
    is_suppressed,
    parse_decimal,
    parse_footnote_codes,
)

logger = logging.getLogger(__name__)

DATASET_ID = "ijh5-nb2v"


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    measure_code = raw.get("measure_code", "").strip()
    if not measure_code:
        return None

    provider_id = raw.get("facility_id", "").strip().zfill(6)
    score_raw = raw.get("adjusted_score", "").strip()
    fn_raw = raw.get("footnote_for_score", "").strip()
    fn_codes = parse_footnote_codes(fn_raw)
    fn_texts = footnote_texts(fn_codes, provider_type="NURSING_HOME")

    suppressed = False
    not_reported = False
    if 5 in fn_codes:
        not_reported = True
    elif is_suppressed(score_raw) or not score_raw:
        suppressed = True

    numeric_value = None if suppressed or not_reported else parse_decimal(score_raw)

    return {
        "provider_id": provider_id,
        "measure_id": f"NH_CLAIMS_{measure_code}",
        "raw_value": score_raw,
        "numeric_value": numeric_value,
        "score_text": None,
        "confidence_interval_lower": None,
        "confidence_interval_upper": None,
        "observed_value": parse_decimal(raw.get("observed_score")),
        "expected_value": parse_decimal(raw.get("expected_score")),
        "compared_to_national": None,
        "suppressed": suppressed,
        "suppression_reason": "Data not available" if suppressed else None,
        "not_reported": not_reported,
        "not_reported_reason": "Results not available" if not_reported else None,
        "count_suppressed": False,
        "footnote_codes": fn_codes if fn_codes else None,
        "footnote_text": fn_texts if fn_texts else None,
        "period_start": None,
        "period_end": None,
        "period_label": raw.get("measure_period", "").strip() or "unknown",
        "sample_size": None,
        "denominator": None,
        "stratification": "",
        "source_dataset_id": DATASET_ID,
        "_resident_type": raw.get("resident_type", "").strip(),
        "_five_star_measure": raw.get("used_in_quality_measure_five_star_rating", "").strip(),
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
