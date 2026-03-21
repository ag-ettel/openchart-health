"""
Normalizer for Nursing Home Provider Information dataset (4pq5-n9py).

Provider metadata — one row per nursing home. Output → providers table.
Phase 0 reference: docs/phase_0_findings.md §12
DEC-018: Staffing context fields in providers table.
DEC-026: Schema changes across archive vintages.
"""

from __future__ import annotations

import logging
from typing import Any

from pipeline.normalize.common import parse_decimal, parse_int

logger = logging.getLogger(__name__)

DATASET_ID = "4pq5-n9py"


def _parse_bool_yn(val: str | None) -> bool | None:
    if not val or not val.strip():
        return None
    v = val.strip().upper()
    if v in ("Y", "YES"):
        return True
    if v in ("N", "NO"):
        return False
    return None


def _get(raw: dict[str, str], *keys: str) -> str:
    """Get first non-empty value from multiple possible column names."""
    for k in keys:
        v = raw.get(k, "").strip()
        if v:
            return v
    return ""


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    provider_id = _get(raw, "facility_id", "provnum")
    if not provider_id:
        return None
    provider_id = provider_id.zfill(6)

    name = _get(raw, "facility_name", "provname")

    # Special Focus Facility status
    sff_raw = _get(raw, "special_focus_status")
    is_sff = sff_raw == "SFF"
    is_sff_candidate = sff_raw == "SFF Candidate"

    # Overall rating
    rating_raw = _get(raw, "overall_rating")
    try:
        overall_rating = int(rating_raw) if rating_raw and rating_raw.isdigit() else None
    except ValueError:
        overall_rating = None

    result: dict[str, Any] = {
        "provider_id": provider_id,
        "provider_type": "NURSING_HOME",
        "name": name,
        "address": {
            "street": _get(raw, "facility_address", "provider_address", "address"),
            "city": _get(raw, "city_town", "citytown"),
            "state": _get(raw, "state"),
            "zip": _get(raw, "zip_code"),
        },
        "city": _get(raw, "city_town", "citytown"),
        "state": _get(raw, "state"),
        "zip": _get(raw, "zip_code"),
        "phone": _get(raw, "telephone_number") or None,
        "provider_subtype": _get(raw, "provider_type") or None,
        "ownership_type": _get(raw, "ownership_type") or None,
        "ownership_type_raw": _get(raw, "ownership_type") or None,

        # NH-specific metadata
        "certified_beds": parse_int(_get(raw, "number_of_certified_beds")),
        "average_daily_census": parse_decimal(_get(raw, "average_number_of_residents_per_day")),
        "is_continuing_care_retirement_community": _parse_bool_yn(
            _get(raw, "continuing_care_retirement_community")),
        "is_special_focus_facility": is_sff,
        "is_special_focus_facility_candidate": is_sff_candidate,
        "is_hospital_based": _parse_bool_yn(_get(raw, "provider_resides_in_hospital")),
        "is_abuse_icon": _parse_bool_yn(_get(raw, "abuse_icon")),
        "is_urban": _parse_bool_yn(_get(raw, "urban")),  # Only in current era
        "chain_name": _get(raw, "chain_name") or None,
        "chain_id": _get(raw, "chain_id") or None,
        "ownership_changed_recently": _parse_bool_yn(
            _get(raw, "provider_changed_ownership_in_last_12_months")),
        "inspection_overdue": _parse_bool_yn(
            _get(raw, "most_recent_health_inspection_more_than_2_years_ago")),
        "resident_family_council": _get(raw, "with_a_resident_and_family_council") or None,
        "sprinkler_status": _get(raw, "automatic_sprinkler_systems_in_all_required_areas") or None,

        # Staffing context (DEC-018)
        "reported_lpn_hprd": parse_decimal(
            _get(raw, "reported_lpn_staffing_hours_per_resident_per_day")),
        "reported_licensed_hprd": parse_decimal(
            _get(raw, "reported_licensed_staffing_hours_per_resident_per_day")),
        "pt_hprd": parse_decimal(
            _get(raw, "reported_physical_therapist_staffing_hours_per_resident_per_day")),
        "nursing_casemix_index": parse_decimal(_get(raw, "nursing_casemix_index")),

        # Penalty summary
        "number_of_fines": parse_int(_get(raw, "number_of_fines")),
        "total_amount_of_fines_dollars": parse_decimal(
            _get(raw, "total_amount_of_fines_in_dollars")),
        "number_of_payment_denials": parse_int(_get(raw, "number_of_payment_denials")),
        "total_number_of_penalties": parse_int(_get(raw, "total_number_of_penalties")),

        # Inspection scoring
        "total_weighted_health_survey_score": parse_decimal(
            _get(raw, "total_weighted_health_survey_score")),

        "source_dataset_id": DATASET_ID,
    }

    return result


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
