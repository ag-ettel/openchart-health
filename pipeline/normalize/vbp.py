"""
Normalizer for Hospital Value-Based Purchasing Program dataset (ypbt-wvdk / hvbp_tps).

One row per hospital per fiscal year with domain scores and total performance score.

Phase 0 reference: docs/phase_0_findings.md §11
DEC-011: VBP domain score column naming.

Output: one dict per row shaped for provider_payment_adjustments upsert.
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import parse_decimal, parse_int

logger = logging.getLogger(__name__)

DATASET_ID = "ypbt-wvdk"


def normalize_row(raw: dict[str, str]) -> dict[str, Any]:
    """Normalize a single VBP TPS row for provider_payment_adjustments."""
    provider_id = raw.get("facility_id", "").strip().zfill(6)
    fiscal_year = parse_int(raw.get("fiscal_year")) or 0

    tps = parse_decimal(raw.get("total_performance_score"))

    return {
        "provider_id": provider_id,
        "program": "VBP",
        "program_year": fiscal_year,
        "penalty_flag": None,  # VBP is bonus/penalty, determined by TPS vs threshold
        "payment_adjustment_pct": None,  # Not in this file — in FY payment tables
        "total_score": tps,
        "total_performance_score": tps,
        "score_percentile": None,
        # Domain scores (DEC-011 column naming)
        "unweighted_normalized_clinical_outcomes_domain_score":
            parse_decimal(raw.get("unweighted_normalized_clinical_outcomes_domain_score")),
        "weighted_normalized_clinical_outcomes_domain_score":
            parse_decimal(raw.get("weighted_normalized_clinical_outcomes_domain_score")),
        "unweighted_person_and_community_engagement_domain_score":
            parse_decimal(raw.get("unweighted_person_and_community_engagement_domain_score")),
        "weighted_person_and_community_engagement_domain_score":
            parse_decimal(raw.get("weighted_person_and_community_engagement_domain_score")),
        "unweighted_normalized_safety_domain_score":
            parse_decimal(raw.get("unweighted_normalized_safety_domain_score")),
        "weighted_safety_domain_score":
            parse_decimal(raw.get("weighted_safety_domain_score")),
        "unweighted_efficiency_and_cost_reduction_domain_score":
            parse_decimal(raw.get("unweighted_normalized_efficiency_and_cost_reduction_domain_score")),
        "weighted_efficiency_and_cost_reduction_domain_score":
            parse_decimal(raw.get("weighted_efficiency_and_cost_reduction_domain_score")),
        "source_dataset_id": DATASET_ID,
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [normalize_row(raw) for raw in rows]
