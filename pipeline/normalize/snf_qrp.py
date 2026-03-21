"""
Normalizer for SNF Quality Reporting Program dataset (fykj-qjee).

15 base measures, each with multiple sub-code rows (DEC-020).
Sub-codes carry CI bounds, observed/expected rates, comparison, and volume.

Phase 0 reference: docs/phase_0_findings.md §22
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any

from pipeline.normalize.common import (
    derive_period_label,
    footnote_texts,
    is_suppressed,
    normalize_compared_to_national,
    parse_date,
    parse_decimal,
    parse_footnote_codes,
    parse_int,
)

logger = logging.getLogger(__name__)

DATASET_ID = "fykj-qjee"

# Sub-code suffix → target field mapping
_SUFFIX_MAP = {
    "RSRR": "numeric_value",           # Risk-standardized rate (primary)
    "RS_RATE": "numeric_value",         # Risk-standardized rate variant
    "ADJ_RATE": "numeric_value",        # Adjusted rate variant
    "SCORE": "numeric_value",           # MSPB score
    "OBS_RATE": "observed_value",       # Observed rate
    "OBS": "observed_value",            # Observed value variant
    "OBS_READM": "_observed_count",     # Observed readmission count
    "RSRR_2_5": "ci_lower",            # CI lower bound
    "RS_RATE_2_5": "ci_lower",
    "RSRR_97_5": "ci_upper",           # CI upper bound
    "RS_RATE_97_5": "ci_upper",
    "COMP_PERF": "compared",           # Compared to national performance
    "VOLUME": "sample_size",
    "NUMB": "sample_size",
    "NUMBER": "sample_size",
    "DENOMINATOR": "denominator",
    "NUMERATOR": "numerator",
}


def _parse_measure_code(raw_code: str) -> tuple[str, str]:
    """Parse compound measure_code into (base, suffix).

    S_004_01_PPR_PD_RSRR → (S_004_01, RSRR)
    S_005_02_DTC_COMP_PERF → (S_005_02, COMP_PERF)
    S_006_01_MSPB_SCORE → (S_006_01, SCORE)
    S_007_02_DENOMINATOR → (S_007_02, DENOMINATOR)
    """
    # Match base: S_NNN_NN then middle descriptor then suffix
    # Strategy: try known suffixes from longest to shortest
    for suffix in sorted(_SUFFIX_MAP.keys(), key=len, reverse=True):
        if raw_code.upper().endswith(f"_{suffix}"):
            base = raw_code[:-(len(suffix) + 1)]
            # Strip middle descriptor (PPR_PD_, DTC_, MSPB_, etc.)
            # Base should be S_NNN_NN format
            base_match = re.match(r"^(S_\d{3}_\d{2})", base)
            if base_match:
                return base_match.group(1), suffix
    return raw_code, ""


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Normalize all SNF QRP rows, grouping sub-codes into single measure rows."""

    # Group by (provider_id, base_measure, start_date, end_date)
    groups: dict[tuple, dict[str, dict[str, str]]] = defaultdict(dict)

    for raw in rows:
        raw_code = raw.get("measure_code", "").strip()
        base, suffix = _parse_measure_code(raw_code)
        if not suffix:
            logger.warning("Unrecognized SNF QRP measure_code: %r", raw_code)
            continue

        provider_id = raw.get("facility_id", "").strip().zfill(6)
        start = raw.get("start_date", "")
        end = raw.get("end_date", "")
        key = (provider_id, base, start, end)
        groups[key][suffix] = raw

    results: list[dict[str, Any]] = []

    for (provider_id, base, start_raw, end_raw), sub_rows in groups.items():
        # Find the primary value row
        primary_suffix = None
        for s in ("RSRR", "RS_RATE", "ADJ_RATE", "SCORE", "OBS_RATE"):
            if s in sub_rows:
                primary_suffix = s
                break

        primary_row = sub_rows.get(primary_suffix, {}) if primary_suffix else {}
        if not primary_row:
            # No primary value — use any sub-row for metadata
            primary_row = next(iter(sub_rows.values()), {})

        score_raw = primary_row.get("score", "").strip()
        fn_raw = primary_row.get("footnote", "").strip()
        # SNF QRP uses "-" for no footnote
        if fn_raw == "-":
            fn_raw = ""

        fn_codes = parse_footnote_codes(fn_raw)
        fn_texts = footnote_texts(fn_codes, provider_type="NURSING_HOME")

        suppressed = False
        not_reported = False
        if 5 in fn_codes:
            not_reported = True
        elif is_suppressed(score_raw) or not score_raw:
            suppressed = True

        numeric_value = None if suppressed or not_reported else parse_decimal(score_raw)

        # CI bounds from sub-rows
        ci_lower_row = sub_rows.get("RSRR_2_5") or sub_rows.get("RS_RATE_2_5") or {}
        ci_upper_row = sub_rows.get("RSRR_97_5") or sub_rows.get("RS_RATE_97_5") or {}
        ci_lower = parse_decimal(ci_lower_row.get("score"))
        ci_upper = parse_decimal(ci_upper_row.get("score"))

        # Observed/expected from sub-rows
        obs_row = sub_rows.get("OBS_RATE") or sub_rows.get("OBS") or {}
        observed_value = parse_decimal(obs_row.get("score"))

        # Comparison
        comp_row = sub_rows.get("COMP_PERF", {})
        compared_raw = comp_row.get("score", "")
        compared = normalize_compared_to_national(compared_raw) if compared_raw else None

        # Volume/counts
        vol_row = sub_rows.get("VOLUME") or sub_rows.get("NUMB") or sub_rows.get("NUMBER") or {}
        sample_size = parse_int(vol_row.get("score"))

        denom_row = sub_rows.get("DENOMINATOR", {})
        denominator = parse_int(denom_row.get("score"))

        numer_row = sub_rows.get("NUMERATOR", {})
        numerator = parse_int(numer_row.get("score"))

        start_date = parse_date(start_raw)
        end_date = parse_date(end_raw)

        results.append({
            "provider_id": provider_id,
            "measure_id": base,
            "raw_value": score_raw,
            "numeric_value": numeric_value,
            "score_text": None,
            "confidence_interval_lower": ci_lower,
            "confidence_interval_upper": ci_upper,
            "observed_value": observed_value,
            "expected_value": None,  # SNF QRP doesn't publish expected separately
            "compared_to_national": compared,
            "suppressed": suppressed,
            "suppression_reason": "Data not available" if suppressed else None,
            "not_reported": not_reported,
            "not_reported_reason": "Results not available" if not_reported else None,
            "count_suppressed": False,
            "footnote_codes": fn_codes if fn_codes else None,
            "footnote_text": fn_texts if fn_texts else None,
            "period_start": start_date,
            "period_end": end_date,
            "period_label": derive_period_label(start_date, end_date),
            "sample_size": sample_size,
            "denominator": denominator,
            "stratification": "",
            "source_dataset_id": DATASET_ID,
            "_numerator": numerator,
        })

    return results
