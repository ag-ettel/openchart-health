"""
Normalizer for Medicare Hospital Spending Per Patient dataset (rrqw-56er).

1 measure: MSPB-1 (Medicare Spending Per Beneficiary).
Phase 0 reference: docs/phase_0_findings.md §6

Simple dataset: OTHER risk adjustment (payment standardization + HCC), CMS
publishes CIs. Score is a ratio (1.0 = national average spending).

Key dataset-specific behaviors:
- 2019 uses MSPB-1 (with hyphen); current also uses MSPB-1 (consistent)
- No compared_to_national field
- No denominator field
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import normalize_measure_row

logger = logging.getLogger(__name__)

DATASET_ID = "rrqw-56er"

MEASURE_IDS = frozenset({"MSPB-1"})


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    measure_id = raw.get("measure_id", "").strip()
    if measure_id and measure_id not in MEASURE_IDS:
        logger.warning("Unknown measure_id in mspb: %r", measure_id)

    result = normalize_measure_row(
        raw,
        score_field="score",
        denominator_field=None,
        sample_field=None,
        lower_est_field=None,
        higher_est_field=None,
        compared_field=None,
        footnote_field="footnote",
    )
    result["source_dataset_id"] = DATASET_ID
    return result


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
