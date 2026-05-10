"""
Normalizer for Hospital-Acquired Condition Reduction Program dataset (yq43-i98g).

One row per hospital per fiscal year. Wide format — SIR values for each HAI
type plus PSI_90, total HAC score, and payment reduction flag.

Phase 0 reference: docs/phase_0_findings.md §10
DEC-012: Winsorized Z-score fields discarded (not stored).

Output: one dict per row shaped for provider_payment_adjustments upsert.
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import parse_decimal, parse_int

logger = logging.getLogger(__name__)

DATASET_ID = "yq43-i98g"


def normalize_row(raw: dict[str, str]) -> dict[str, Any]:
    """Normalize a single HACRP row for provider_payment_adjustments."""
    provider_id = raw.get("facility_id", "").strip().zfill(6)
    fiscal_year = parse_int(raw.get("fiscal_year")) or 0

    # Payment reduction: Yes/No/N/A
    pr_raw = raw.get("payment_reduction", "").strip()
    if pr_raw.lower() == "yes":
        penalty_flag = True
    elif pr_raw.lower() == "no":
        penalty_flag = False
    else:
        penalty_flag = None  # N/A — excluded from program

    return {
        "provider_id": provider_id,
        "program": "HACRP",
        "program_year": fiscal_year,
        "penalty_flag": penalty_flag,
        "payment_adjustment_pct": None,  # HACRP uses binary reduction, not a percentage
        "total_score": parse_decimal(raw.get("total_hac_score")),
        "score_percentile": None,
        "total_hac_score": parse_decimal(raw.get("total_hac_score")),
        "payment_reduction": penalty_flag,
        "source_dataset_id": DATASET_ID,
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [normalize_row(raw) for raw in rows]
