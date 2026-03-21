"""
Normalizer for Hospital General Information dataset (xubh-q36u).

Provider metadata, not quality measures. One row per hospital.
Output: dict shaped for the `providers` table upsert.

Phase 0 reference: docs/phase_0_findings.md §1
DEC-009: group summary fields — store footnotes + facility counts, discard rest.
DEC-013: hospital_type and hospital_ownership stored as varchar.
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import parse_int

logger = logging.getLogger(__name__)

DATASET_ID = "xubh-q36u"


def _parse_bool_yn(raw: str | None, yes_val: str = "Yes") -> bool | None:
    """Parse Y/N or Yes/No CMS boolean strings."""
    if not raw or not raw.strip():
        return None
    val = raw.strip()
    if val in (yes_val, "Y"):
        return True
    if val in ("No", "N"):
        return False
    return None


def normalize_row(raw: dict[str, str]) -> dict[str, Any]:
    """Normalize a single Hospital General Info row for providers table."""
    provider_id = raw.get("facility_id", "").strip().zfill(6)
    hospital_type = raw.get("hospital_type", "").strip()

    # Star rating: string "1"-"5" or "Not Available"
    rating_raw = raw.get("hospital_overall_rating", "").strip()
    try:
        hospital_overall_rating = int(rating_raw) if rating_raw and rating_raw.isdigit() else None
    except ValueError:
        hospital_overall_rating = None

    return {
        "provider_id": provider_id,
        "provider_type": "HOSPITAL",
        "name": raw.get("facility_name", "").strip(),
        "address": {
            "street": raw.get("address", "").strip(),
            "city": raw.get("city_town", raw.get("citytown", "")).strip(),
            "state": raw.get("state", "").strip(),
            "zip": raw.get("zip_code", "").strip(),
        },
        "city": raw.get("city_town", raw.get("citytown", "")).strip(),
        "state": raw.get("state", "").strip(),
        "zip": raw.get("zip_code", "").strip(),
        "phone": raw.get("telephone_number", "").strip() or None,
        "provider_subtype": hospital_type or None,
        "ownership_type": raw.get("hospital_ownership", "").strip() or None,
        "ownership_type_raw": raw.get("hospital_ownership", "").strip() or None,
        "is_critical_access": hospital_type == "Critical Access Hospitals",
        "is_emergency_services": _parse_bool_yn(raw.get("emergency_services")),
        "birthing_friendly_designation": _parse_bool_yn(
            raw.get("meets_criteria_for_birthing_friendly_designation"), yes_val="Y"
        ),
        "hospital_overall_rating": hospital_overall_rating,
        "hospital_overall_rating_footnote": raw.get("hospital_overall_rating_footnote", "").strip() or None,
        # Group measure counts (DEC-009)
        "count_of_facility_mort_measures": parse_int(raw.get("count_of_facility_mort_measures")),
        "count_of_facility_readm_measures": parse_int(raw.get("count_of_facility_readm_measures")),
        "count_of_facility_safety_measures": parse_int(raw.get("count_of_facility_safety_measures")),
        "count_of_facility_pt_exp_measures": parse_int(raw.get("count_of_facility_pt_exp_measures")),
        "count_of_facility_te_measures": parse_int(raw.get("count_of_facility_te_measures")),
        # Group footnotes (DEC-009)
        "mort_group_footnote": raw.get("mort_group_footnote", "").strip() or None,
        "readm_group_footnote": raw.get("readm_group_footnote", "").strip() or None,
        "safety_group_footnote": raw.get("safety_group_footnote", "").strip() or None,
        "pt_exp_group_footnote": raw.get("pt_exp_group_footnote", "").strip() or None,
        "te_group_footnote": raw.get("te_group_footnote", "").strip() or None,
        "source_dataset_id": DATASET_ID,
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [normalize_row(raw) for raw in rows]
