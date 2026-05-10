"""
Normalizer for SNF Value-Based Purchasing dataset (284v-j9fz).

One row per facility per fiscal year. Wide-format with measure-specific
columns (achievement, improvement, measure scores) plus an incentive
payment multiplier.

Output → provider_payment_adjustments table.
Phase 0 reference: docs/phase_0_findings.md §23

Column names embed fiscal years and vary across eras (22 cols in FY2019,
49 cols in FY2026). We extract the stable program-level fields and let
the variable measure-level fields be stored in raw_row jsonb.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pipeline.normalize.common import parse_decimal, parse_int

logger = logging.getLogger(__name__)

DATASET_ID = "284v-j9fz"


def _find_field(raw: dict[str, str], patterns: list[str]) -> str | None:
    """Find a field value by trying multiple column name patterns."""
    for pattern in patterns:
        for key, val in raw.items():
            if re.search(pattern, key, re.IGNORECASE):
                return val.strip() if val else None
    return None


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    # Provider ID: 2019 uses "provider_number_ccn", 2026 uses "facility_id"
    provider_id = (
        raw.get("facility_id", "").strip()
        or raw.get("provider_number_ccn", "").strip()
    )
    if not provider_id:
        return None
    provider_id = provider_id.zfill(6)

    # Incentive payment multiplier — the key program outcome
    ipm = _find_field(raw, [r"incentive_payment_multiplier"])

    # Performance standard score
    perf_score = _find_field(raw, [r"performance_standards_score"])

    # Program ranking
    ranking = _find_field(raw, [r"snf_vbp.*ranking"])

    # Baseline and performance rates (SNFRM readmission rate)
    baseline_rate = _find_field(raw, [r"baseline.*risk_standardized_readmission_rate$"])
    performance_rate = _find_field(raw, [r"performance.*risk_standardized_readmission_rate$"])

    # Achievement/improvement scores
    achievement = _find_field(raw, [r"snfrm_achievement_score"])
    improvement = _find_field(raw, [r"snfrm_improvement_score"])
    measure_score = _find_field(raw, [r"snfrm_measure_score"])

    return {
        "provider_id": provider_id,
        "program": "SNF_VBP",
        "program_year": 0,  # Determined from the archive vintage / filename
        "penalty_flag": None,
        "payment_adjustment_pct": None,
        "total_score": parse_decimal(perf_score),
        "score_percentile": None,
        "incentive_payment_multiplier": parse_decimal(ipm),
        "baseline_rate": parse_decimal(baseline_rate),
        "performance_rate": parse_decimal(performance_rate),
        "achievement_score": parse_decimal(achievement),
        "improvement_score": parse_decimal(improvement),
        "measure_score": parse_decimal(measure_score),
        "source_dataset_id": DATASET_ID,
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
