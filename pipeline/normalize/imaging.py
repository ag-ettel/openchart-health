"""
Normalizer for Outpatient Imaging Efficiency dataset (wkfw-kthe).

4 current measures: OP-8, OP-10, OP-13, OP-39.
Phase 0 reference: docs/phase_0_findings.md §8

Simple dataset: no risk adjustment (NONE), no CIs published, no
compared_to_national field. Numerator/denominator published — Bayesian
credible intervals calculable in transform layer.

Key dataset-specific behaviors:
- 2019 uses hyphens (OP-8), current uses mixed (OP-8, OP-10, OP-13, OP-39)
- 2019 had additional measures (OP-9, OP-11, OP-14) now retired
- No compared_to_national field
- No lower_estimate / higher_estimate fields
- score field is numeric percentage
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import normalize_measure_row

logger = logging.getLogger(__name__)

DATASET_ID = "wkfw-kthe"

MEASURE_IDS = frozenset({"OP-8", "OP-10", "OP-13", "OP-39"})

RETIRED_MEASURE_IDS = frozenset({"OP-9", "OP-11", "OP-14"})

MEASURE_ID_ALIASES: dict[str, str] = {}  # No aliasing needed — hyphens preserved


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    measure_id = raw.get("measure_id", "").strip()
    if measure_id in RETIRED_MEASURE_IDS:
        return None
    if measure_id and measure_id not in MEASURE_IDS:
        logger.warning("Unknown measure_id in imaging: %r", measure_id)

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
    results: list[dict[str, Any]] = []
    for raw in rows:
        normalized = normalize_row(raw)
        if normalized is not None:
            results.append(normalized)
    return results
