"""
Normalizer for Nursing Home MDS Quality Measures dataset (djen-97ju).

17 measures (10 long-stay + 7 short-stay). Each row carries Q1-Q4 scores
plus a 4-quarter average, each with its own footnote. Per DEC-015, each
quarter becomes a separate row in provider_measure_values.

Phase 0 reference: docs/phase_0_findings.md §13
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import (
    footnote_texts,
    parse_decimal,
    parse_footnote_codes,
    is_suppressed,
)

logger = logging.getLogger(__name__)

DATASET_ID = "djen-97ju"

# Quarter columns: (score_field, footnote_field, quarter_label_field_or_none)
_QUARTER_FIELDS = [
    ("q1_measure_score", "footnote_for_q1_measure_score", "Q1"),
    ("q2_measure_score", "footnote_for_q2_measure_score", "Q2"),
    ("q3_measure_score", "footnote_for_q3_measure_score", "Q3"),
    ("q4_measure_score", "footnote_for_q4_measure_score", "Q4"),
    ("four_quarter_average_score", "footnote_for_four_quarter_average_score", "AVG"),
]


def _derive_measure_period(raw: dict[str, str]) -> str:
    """Reconstruct measure_period when CMS doesn't supply it directly.

    Modern archives (2019-06+) ship `measure_period` like "2024Q4-2025Q3".
    The 2019-01 archive omits that field but provides per-quarter labels
    (`q1_quarter` ... `q4_quarter`); we derive the range from the earliest
    and latest of those.
    """
    explicit = (raw.get("measure_period") or "").strip()
    if explicit:
        return explicit

    quarters = [
        (raw.get(f"{q.lower()}_quarter") or "").strip()
        for q in ("Q1", "Q2", "Q3", "Q4")
    ]
    quarters = [q for q in quarters if q]
    if not quarters:
        return ""
    sorted_q = sorted(quarters)
    if sorted_q[0] == sorted_q[-1]:
        return sorted_q[0]
    return f"{sorted_q[0]}-{sorted_q[-1]}"


def normalize_row(raw: dict[str, str]) -> list[dict[str, Any]]:
    """Normalize one MDS row into up to 5 provider_measure_values rows (DEC-015).

    Returns a list of dicts — one per quarter with data, plus the 4-quarter average.
    """
    provider_id = raw.get("facility_id", "").strip().zfill(6)
    measure_code = raw.get("measure_code", "").strip()
    measure_period = _derive_measure_period(raw)

    if not measure_code:
        return []

    results: list[dict[str, Any]] = []

    for score_field, fn_field, q_label in _QUARTER_FIELDS:
        score_raw = raw.get(score_field, "").strip()
        fn_raw = raw.get(fn_field, "").strip()

        # Skip entirely empty quarters
        if not score_raw and not fn_raw:
            continue

        fn_codes = parse_footnote_codes(fn_raw)
        fn_texts = footnote_texts(fn_codes, provider_type="NURSING_HOME")

        suppressed = False
        not_reported = False
        if 5 in fn_codes:
            not_reported = True
        elif is_suppressed(score_raw) or not score_raw:
            suppressed = True

        numeric_value = None
        if not suppressed and not not_reported:
            numeric_value = parse_decimal(score_raw)

        # Period label: for individual quarters use "2025Q1" format;
        # for the average, use the full measure_period range.
        # Falls back to processing_date when CMS provides nothing parseable.
        if q_label == "AVG":
            period_label = measure_period or (raw.get("processing_date") or "").strip() or "unknown"
        else:
            quarter_field = raw.get(f"{q_label.lower()}_quarter", "").strip()
            if quarter_field:
                period_label = quarter_field
            elif measure_period:
                period_label = f"{measure_period}_{q_label}"
            else:
                period_label = (raw.get("processing_date") or "").strip() or "unknown"

        results.append({
            "provider_id": provider_id,
            "measure_id": f"NH_MDS_{measure_code}",
            "raw_value": score_raw,
            "numeric_value": numeric_value,
            "score_text": None,
            "confidence_interval_lower": None,
            "confidence_interval_upper": None,
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
            "period_label": period_label,
            "sample_size": None,
            "denominator": None,
            "stratification": "",
            "source_dataset_id": DATASET_ID,
            # NH-specific context
            "_resident_type": raw.get("resident_type", "").strip(),
            "_five_star_measure": raw.get("used_in_quality_measure_five_star_rating", "").strip(),
        })

    return results


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for raw in rows:
        results.extend(normalize_row(raw))
    return results
