"""
Normalizer for Nursing Home Penalties dataset (g6vv-u9sr).

One row per penalty event. Output → provider_penalties table.
Phase 0 reference: docs/phase_0_findings.md §19
DEC-028 pattern: lifecycle tracking for fine amount changes.
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import parse_date, parse_decimal, parse_int

logger = logging.getLogger(__name__)

DATASET_ID = "g6vv-u9sr"


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    provider_id = raw.get("facility_id", "").strip().zfill(6)
    if not provider_id or provider_id == "000000":
        return None

    penalty_type = raw.get("penalty_type", "").strip()
    if not penalty_type:
        return None

    return {
        "provider_id": provider_id,
        "provider_type": "NURSING_HOME",
        "penalty_date": parse_date(raw.get("penalty_date")),
        "penalty_type": penalty_type,
        "fine_amount": parse_decimal(raw.get("fine_amount")),
        "payment_denial_start_date": parse_date(raw.get("payment_denial_start_date")),
        "payment_denial_length_days": parse_int(raw.get("payment_denial_length_in_days")),
        "source_dataset_id": DATASET_ID,
        # DEC-028 lifecycle fields — set by store layer during chronological load
        "originally_published_fine_amount": None,
        "originally_published_vintage": None,
        "last_seen_vintage": None,
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
