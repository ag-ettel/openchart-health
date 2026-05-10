"""
Normalizer for Nursing Home Health Deficiencies dataset (r5ix-sfxw).

One row per deficiency citation. Output → provider_inspection_events table.
Phase 0 reference: docs/phase_0_findings.md §15
DEC-028: Citation lifecycle preservation.
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import parse_date

logger = logging.getLogger(__name__)

DATASET_ID = "r5ix-sfxw"

IJ_CODES = frozenset({"J", "K", "L"})


def _parse_bool_yn(val: str | None) -> bool:
    """Parse Y/N to bool, defaulting to False."""
    return val is not None and val.strip().upper() == "Y"


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    """Normalize one deficiency citation for provider_inspection_events."""
    provider_id = raw.get("facility_id", "").strip().zfill(6)
    if not provider_id or provider_id == "000000":
        return None

    tag = raw.get("deficiency_tag_number", "").strip()
    if not tag:
        return None

    scope_severity = raw.get("scope_severity_code", "").strip().upper()
    # Some 2019 rows have empty scope — log but store
    if scope_severity and scope_severity not in "ABCDEFGHIJKL":
        logger.warning("Unknown scope_severity_code: %r (provider=%s, tag=%s)",
                       scope_severity, provider_id, tag)

    survey_date = parse_date(raw.get("survey_date"))

    return {
        "provider_id": provider_id,
        "provider_type": "NURSING_HOME",
        "event_id": f"{provider_id}_{raw.get('survey_date', '')}_{raw.get('survey_type', '')}",
        "survey_date": survey_date,
        "survey_type": raw.get("survey_type", "").strip() or None,
        "deficiency_tag": tag,
        "deficiency_description": raw.get("deficiency_description", "").strip() or None,
        "deficiency_category": raw.get("deficiency_category", "").strip() or None,
        "scope_severity_code": scope_severity or None,
        "is_immediate_jeopardy": scope_severity in IJ_CODES,
        "is_complaint_deficiency": _parse_bool_yn(raw.get("complaint_deficiency")),
        "correction_date": parse_date(raw.get("correction_date")),
        "inspection_cycle": int(raw.get("inspection_cycle", "0").strip() or "0") or None,
        "source_dataset_id": DATASET_ID,
        # DEC-028 lifecycle fields — set by the store layer during chronological load
        "originally_published_scope_severity": None,
        "is_contested": False,
        "scope_severity_history": None,
        "originally_published_vintage": None,
        "last_seen_vintage": None,
        # Context for derived measures (DEC-034)
        "_standard_deficiency": _parse_bool_yn(raw.get("standard_deficiency")),
        "_infection_control": _parse_bool_yn(raw.get("infection_control_inspection_deficiency")),
        "_citation_under_idr": _parse_bool_yn(raw.get("citation_under_idr")),
        "_citation_under_iidr": _parse_bool_yn(raw.get("citation_under_iidr")),
        "_deficiency_corrected": raw.get("deficiency_corrected", "").strip() or None,
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
