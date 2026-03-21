"""
Normalizer for Healthcare-Associated Infections dataset (77hc-ibv8).

6 HAI measures, each with 6 sub-measure rows in CMS data:
  HAI_n_SIR        — Standardized Infection Ratio (primary measure value)
  HAI_n_CILOWER    — Lower confidence interval bound
  HAI_n_CIUPPER    — Upper confidence interval bound
  HAI_n_DOPC       — Device/procedure days (denominator context)
  HAI_n_ELIGCASES  — Expected number of infections
  HAI_n_NUMERATOR  — Observed number of infections

The 6 sub-measures are folded into a single row per HAI per provider. Only
the SIR row becomes a provider_measure_values entry; the companion values
are attached as CI bounds and sample size fields.

Phase 0 reference: docs/phase_0_findings.md §3

Key dataset-specific behaviors:
- SIR-based risk adjustment with CMS-published CIs
- "N/A" on CILOWER means zero infections observed (CI lower bound undefined) —
  NOT suppression. The hospital WAS evaluated. Stored as null CI lower bound.
- "Not Available" means suppressed (not enough data to calculate)
- compared_to_national uses "Benchmark" phrasing (DEC-022)
- 2019 archives use hyphens (HAI-1-SIR) vs 2021+ underscores (HAI_1_SIR)
- 2019 footnotes include full text ("13 - Results cannot be calculated...")
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any

from pipeline.normalize.common import (
    detect_suppression_state,
    derive_period_label,
    footnote_texts,
    normalize_compared_to_national,
    parse_date,
    parse_decimal,
    parse_footnote_codes,
    parse_int,
)

logger = logging.getLogger(__name__)

DATASET_ID = "77hc-ibv8"

# The 6 primary HAI measure IDs (current naming convention)
HAI_MEASURE_IDS = frozenset({
    "HAI_1_SIR", "HAI_2_SIR", "HAI_3_SIR",
    "HAI_4_SIR", "HAI_5_SIR", "HAI_6_SIR",
})

# Sub-measure suffixes we fold into the SIR row
_SUFFIXES = {"SIR", "CILOWER", "CIUPPER", "DOPC", "ELIGCASES", "NUMERATOR",
             # 2019 variants
             "CI-LOWER", "CI-UPPER", "DOPC-DAYS"}


def _normalize_measure_id(raw_id: str) -> tuple[str, str]:
    """Parse a HAI measure ID into (base_id, suffix).

    Handles both eras:
      2019: "HAI-1-CI-LOWER" -> ("HAI_1", "CILOWER")
      2026: "HAI_1_CILOWER"  -> ("HAI_1", "CILOWER")

    Returns (base_id, suffix) where base_id is like "HAI_1" and suffix
    is one of: SIR, CILOWER, CIUPPER, DOPC, ELIGCASES, NUMERATOR.
    """
    # Normalize hyphens to underscores
    normalized = raw_id.replace("-", "_")

    # Match: HAI_n_SUFFIX
    match = re.match(r"^(HAI_\d)_(.+)$", normalized)
    if not match:
        return raw_id, ""

    base = match.group(1)
    suffix = match.group(2).upper()

    # Normalize 2019-era suffixes
    suffix_map = {
        "CI_LOWER": "CILOWER",
        "CI_UPPER": "CIUPPER",
        "DOPC_DAYS": "DOPC",
    }
    suffix = suffix_map.get(suffix, suffix)

    return base, suffix


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Normalize all rows from an HAI CSV/API response.

    Groups the 6 sub-measure rows per (provider, HAI type, period) and
    produces one output row per HAI measure with companion values folded in.
    """
    # Group rows by (provider_id, base_measure, start_date, end_date)
    groups: dict[tuple[str, str, str, str], dict[str, dict[str, str]]] = defaultdict(dict)

    for raw in rows:
        raw_mid = raw.get("measure_id", "").strip()
        base, suffix = _normalize_measure_id(raw_mid)
        if not suffix:
            logger.warning("Unrecognized HAI measure_id format: %r", raw_mid)
            continue

        provider_id = raw.get("facility_id", "").strip().zfill(6)
        start = raw.get("start_date", "")
        end = raw.get("end_date", "")
        key = (provider_id, base, start, end)
        groups[key][suffix] = raw

    # Build normalized rows from grouped sub-measures
    results: list[dict[str, Any]] = []

    for (provider_id, base, start_raw, end_raw), sub_rows in groups.items():
        sir_row = sub_rows.get("SIR")
        if sir_row is None:
            # No SIR row — can't produce a meaningful measure value
            continue

        sir_measure_id = f"{base}_SIR"
        score_raw = sir_row.get("score", "")
        footnote_raw = sir_row.get("footnote", "")
        compared_raw = sir_row.get("compared_to_national", "")

        # Parse dates
        start_date = parse_date(start_raw)
        end_date = parse_date(end_raw)
        period_label = derive_period_label(start_date, end_date)

        # Footnotes
        fn_codes = parse_footnote_codes(footnote_raw)
        fn_texts = footnote_texts(fn_codes)

        # Suppression
        suppressed, not_reported, suppression_reason = detect_suppression_state(
            score_raw, compared_raw, footnote_raw
        )

        # SIR value
        numeric_value = None if suppressed or not_reported else parse_decimal(score_raw)

        # Companion CI bounds from CILOWER/CIUPPER sub-rows
        ci_lower_row = sub_rows.get("CILOWER", {})
        ci_upper_row = sub_rows.get("CIUPPER", {})
        ci_lower_raw = ci_lower_row.get("score", "")
        ci_upper_raw = ci_upper_row.get("score", "")

        # "N/A" on CILOWER means zero infections — CI lower is undefined.
        # This is NOT suppression. Store as null CI, not as suppressed.
        ci_lower = None
        if ci_lower_raw.strip().upper() != "N/A":
            ci_lower = parse_decimal(ci_lower_raw)

        ci_upper = parse_decimal(ci_upper_raw)

        # Companion count fields
        numerator_row = sub_rows.get("NUMERATOR", {})
        eligcases_row = sub_rows.get("ELIGCASES", {})
        dopc_row = sub_rows.get("DOPC", {})

        numerator = parse_decimal(numerator_row.get("score", ""))
        expected = parse_decimal(eligcases_row.get("score", ""))
        sample_size = parse_int(dopc_row.get("score", ""))

        result: dict[str, Any] = {
            "provider_id": provider_id,
            "measure_id": sir_measure_id,
            "raw_value": score_raw,
            "numeric_value": numeric_value,
            "score_text": None,
            "confidence_interval_lower": ci_lower,
            "confidence_interval_upper": ci_upper,
            "observed_value": numerator,  # DEC-016 pattern: observed infections
            "expected_value": expected,   # Expected infections from SIR model
            "compared_to_national": normalize_compared_to_national(compared_raw),
            "suppressed": suppressed,
            "suppression_reason": suppression_reason,
            "not_reported": not_reported,
            "not_reported_reason": suppression_reason if not_reported else None,
            "count_suppressed": False,
            "footnote_codes": fn_codes if fn_codes else None,
            "footnote_text": fn_texts if fn_texts else None,
            "period_start": start_date,
            "period_end": end_date,
            "period_label": period_label,
            "sample_size": sample_size,  # Device/procedure days
            "denominator": None,  # SIR doesn't have a traditional denominator
            "stratification": "",
            "source_dataset_id": DATASET_ID,
        }

        results.append(result)

    return results
