"""
Normalizer for Timely and Effective Care dataset (yv7e-xc69).

30 current measures across sepsis bundles, ED wait times, eCQMs, immunization,
stroke, VTE, colonoscopy, and EDV volume classification.

Phase 0 reference: docs/phase_0_findings.md §4

Key dataset-specific behaviors:
- EDV: categorical score ("very high", "high", "medium", "low") stored in
  score_text, not numeric_value (DEC-024/AMB-5). direction=None.
- `_condition` field (leading underscore is API artifact; CSV uses "Condition")
- `sample` field (not `denominator`) carries case counts
- No compared_to_national field
- No lower_estimate / higher_estimate fields
- 2019 had different measure IDs (OP-18b not OP_18b, ED_1b not OP_18a, etc.)
- Many measures retired across eras (OP_1, OP_2, OP_3b, OP_4, OP_5, OP_20,
  OP_21, OP_30, OP_33, PC_01, VTE_6, ED_1b, ED_2b, IMM_2, HCP_COVID_19, etc.)
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import normalize_measure_row

logger = logging.getLogger(__name__)

DATASET_ID = "yv7e-xc69"

MEASURE_IDS = frozenset({
    "EDV",
    "OP_18a", "OP_18b", "OP_18c", "OP_18d",
    "OP_22", "OP_23", "OP_29", "OP_31", "OP_40",
    "SEP_1", "SEP_SH_3HR", "SEP_SH_6HR", "SEV_SEP_3HR", "SEV_SEP_6HR",
    "STK_02", "STK_03", "STK_05",
    "VTE_1", "VTE_2",
    "IMM_3",
    "HH_HYPER", "HH_HYPO", "HH_ORAE",
    "SAFE_USE_OF_OPIOIDS",
    "GMCS", "GMCS_Malnutrition_Screening", "GMCS_Malnutrition_Diagnosis_Documented",
    "GMCS_Nutrition_Assessment", "GMCS_Nutritional_Care_Plan",
})

# EDV categorical values (DEC-024)
EDV_CATEGORIES = frozenset({"very high", "high", "medium", "low"})

# Measures that existed in older archives but are now retired
RETIRED_MEASURE_IDS = frozenset({
    "OP_1", "OP_2", "OP_3b", "OP_4", "OP_5",
    "OP_20", "OP_21", "OP_30", "OP_33",
    "PC_01", "PC_05",
    "VTE_6",
    "ED_1b", "ED_2b",
    "ED_2_Strata_1", "ED_2_Strata_2",
    "IMM_2",
    "HCP_COVID_19",
    "HH_01", "HH_02",
    "STK_06",
})

# 2019-era measure ID aliases
MEASURE_ID_ALIASES: dict[str, str] = {
    "IMM_3_OP_27_FAC_ADHPCT": "IMM_3",
}


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    measure_id = raw.get("measure_id", "").strip()

    # Normalize aliases
    measure_id = MEASURE_ID_ALIASES.get(measure_id, measure_id)
    raw["measure_id"] = measure_id

    if measure_id in RETIRED_MEASURE_IDS:
        return None

    if measure_id and measure_id not in MEASURE_IDS:
        logger.warning("Unknown measure_id in timely_effective: %r", measure_id)

    # T&E uses `sample` not `denominator`
    result = normalize_measure_row(
        raw,
        score_field="score",
        denominator_field=None,
        sample_field="sample",
        lower_est_field=None,
        higher_est_field=None,
        compared_field=None,
        footnote_field="footnote",
    )

    # EDV: categorical score (DEC-024/AMB-5)
    if measure_id == "EDV":
        score_raw = raw.get("score", "").strip().lower()
        if score_raw in EDV_CATEGORIES:
            result["score_text"] = score_raw
            result["numeric_value"] = None  # Not numeric
        # If "Not Available", normal suppression handling applies (already set)

    result["source_dataset_id"] = DATASET_ID
    return result


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
