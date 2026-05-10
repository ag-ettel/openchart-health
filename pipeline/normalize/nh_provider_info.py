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
    provider_id = _get(
        raw, "facility_id", "provnum",
        "cms_certification_number_(ccn)", "federal_provider_number",
    )
    if not provider_id:
        return None
    provider_id = provider_id.zfill(6)

    name = _get(raw, "facility_name", "provname", "provider_name")

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
        # Reported (raw PBJ hours)
        "reported_rn_hprd": parse_decimal(
            _get(raw, "reported_rn_staffing_hours_per_resident_per_day")),
        "reported_lpn_hprd": parse_decimal(
            _get(raw, "reported_lpn_staffing_hours_per_resident_per_day")),
        "reported_licensed_hprd": parse_decimal(
            _get(raw, "reported_licensed_staffing_hours_per_resident_per_day")),
        "reported_aide_hprd": parse_decimal(
            _get(raw, "reported_nurse_aide_staffing_hours_per_resident_per_day")),
        "reported_total_hprd": parse_decimal(
            _get(raw, "reported_total_nurse_staffing_hours_per_resident_per_day")),
        "weekend_rn_hprd": parse_decimal(
            _get(raw, "registered_nurse_hours_per_resident_per_day_on_the_weekend")),
        "weekend_total_hprd": parse_decimal(
            _get(raw, "total_number_of_nurse_staff_hours_per_resident_per_day_on_the_weekend")),
        "pt_hprd": parse_decimal(
            _get(raw, "reported_physical_therapist_staffing_hours_per_resident_per_day")),
        "nursing_casemix_index": parse_decimal(
            _get(raw, "nursing_case_mix_index", "nursing_casemix_index")),
        "nursing_casemix_index_ratio": parse_decimal(
            _get(raw, "nursing_case_mix_index_ratio", "nursing_casemix_index_ratio")),
        # Turnover
        "total_nursing_staff_turnover": parse_decimal(
            _get(raw, "total_nursing_staff_turnover")),
        "rn_turnover": parse_decimal(
            _get(raw, "registered_nurse_turnover")),
        "administrator_departures": parse_int(
            _get(raw, "number_of_administrators_who_have_left_the_nursing_home")),
        # Case-mix adjusted staffing
        "casemix_aide_hprd": parse_decimal(
            _get(raw, "case_mix_nurse_aide_staffing_hours_per_resident_per_day")),
        "casemix_lpn_hprd": parse_decimal(
            _get(raw, "case_mix_lpn_staffing_hours_per_resident_per_day")),
        "casemix_rn_hprd": parse_decimal(
            _get(raw, "case_mix_rn_staffing_hours_per_resident_per_day")),
        "casemix_licensed_hprd": parse_decimal(
            _get(raw, "case_mix_licensed_staffing_hours_per_resident_per_day")),
        "casemix_total_hprd": parse_decimal(
            _get(raw, "case_mix_total_nurse_staffing_hours_per_resident_per_day")),
        # Adjusted staffing (CMS adjusted for case-mix)
        "adjusted_aide_hprd": parse_decimal(
            _get(raw, "adjusted_nurse_aide_staffing_hours_per_resident_per_day")),
        "adjusted_lpn_hprd": parse_decimal(
            _get(raw, "adjusted_lpn_staffing_hours_per_resident_per_day")),
        "adjusted_rn_hprd": parse_decimal(
            _get(raw, "adjusted_rn_staffing_hours_per_resident_per_day")),
        "adjusted_licensed_hprd": parse_decimal(
            _get(raw, "adjusted_licensed_staffing_hours_per_resident_per_day")),
        "adjusted_total_hprd": parse_decimal(
            _get(raw, "adjusted_total_nurse_staffing_hours_per_resident_per_day")),
        "adjusted_weekend_total_hprd": parse_decimal(
            _get(raw, "adjusted_weekend_total_nurse_staffing_hours_per_resident_per_day")),
        "casemix_weekend_total_hprd": parse_decimal(
            _get(raw, "case_mix_weekend_total_nurse_staffing_hours_per_resident_per_day")),

        # Inspection scoring — cycle data
        "cycle_1_survey_date": _get(raw, "rating_cycle_1_standard_survey_health_date") or None,
        "cycle_1_total_health_deficiencies": parse_int(
            _get(raw, "rating_cycle_1_total_number_of_health_deficiencies")),
        "cycle_1_standard_health_deficiencies": parse_int(
            _get(raw, "rating_cycle_1_number_of_standard_health_deficiencies")),
        "cycle_1_complaint_health_deficiencies": parse_int(
            _get(raw, "rating_cycle_1_number_of_complaint_health_deficiencies")),
        "cycle_1_health_deficiency_score": parse_decimal(
            _get(raw, "rating_cycle_1_health_deficiency_score")),
        "cycle_1_health_revisits": parse_int(
            _get(raw, "rating_cycle_1_number_of_health_revisits")),
        "cycle_1_health_revisit_score": parse_decimal(
            _get(raw, "rating_cycle_1_health_revisit_score")),
        "cycle_1_total_health_score": parse_decimal(
            _get(raw, "rating_cycle_1_total_health_score")),
        "cycle_23_total_health_deficiencies": parse_int(
            _get(raw, "rating_cycle_2_3_total_number_of_health_deficiencies")),
        "cycle_23_health_deficiency_score": parse_decimal(
            _get(raw, "rating_cycle_2_3_health_deficiency_score")),

        # Chain average ratings
        "chain_average_overall_rating": parse_decimal(
            _get(raw, "chain_average_overall_5_star_rating")),
        "chain_average_health_inspection_rating": parse_decimal(
            _get(raw, "chain_average_health_inspection_rating")),
        "chain_average_staffing_rating": parse_decimal(
            _get(raw, "chain_average_staffing_rating")),
        "chain_average_qm_rating": parse_decimal(
            _get(raw, "chain_average_qm_rating")),

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


# ---------------------------------------------------------------------------
# Five-Star sub-rating measure rows (→ provider_measure_values)
# ---------------------------------------------------------------------------

_STAR_RATING_MAP: list[tuple[str, tuple[str, ...], str | None]] = [
    # (measure_id, CSV column name(s), footnote column)
    ("NH_STAR_OVERALL", ("overall_rating",), "overall_rating_footnote"),
    ("NH_STAR_HEALTH_INSP", ("health_inspection_rating",), "health_inspection_rating_footnote"),
    ("NH_STAR_QM", ("qm_rating",), "qm_rating_footnote"),
    ("NH_STAR_STAFFING", ("staffing_rating",), "staffing_rating_footnote"),
    ("NH_STAR_LS_QM", ("long_stay_qm_rating",), "long_stay_qm_rating_footnote"),
    ("NH_STAR_SS_QM", ("short_stay_qm_rating",), "short_stay_qm_rating_footnote"),
]


def extract_star_rating_measures(raw: dict[str, str]) -> list[dict[str, Any]]:
    """Extract Five-Star sub-ratings as measure value rows.

    These are stored in provider_measure_values alongside quality measures,
    enabling the dashboard to render them uniformly.
    """
    provider_id = _get(
        raw, "facility_id", "provnum",
        "cms_certification_number_(ccn)", "federal_provider_number",
    )
    if not provider_id:
        return []
    provider_id = provider_id.zfill(6)

    processing_date = _get(raw, "processing_date")
    period_label = processing_date or "current"

    results: list[dict[str, Any]] = []
    for measure_id, col_names, fn_col in _STAR_RATING_MAP:
        val_str = _get(raw, *col_names)
        footnote_str = _get(raw, fn_col) if fn_col else ""

        numeric_value = None
        suppressed = False
        not_reported = False

        if val_str and val_str.isdigit():
            numeric_value = int(val_str)
        elif not val_str or val_str.upper() in ("", "N/A", "NOT AVAILABLE"):
            not_reported = True

        footnote_codes = None
        footnote_text = None
        if footnote_str:
            try:
                codes = [int(c.strip()) for c in footnote_str.split(",") if c.strip().isdigit()]
                if codes:
                    footnote_codes = codes
            except ValueError:
                pass

        results.append({
            "provider_id": provider_id,
            "provider_type": "NURSING_HOME",
            "measure_id": measure_id,
            "source_dataset_id": DATASET_ID,
            "numeric_value": numeric_value,
            "raw_value": val_str,
            "suppressed": suppressed,
            "not_reported": not_reported,
            "footnote_codes": footnote_codes,
            "footnote_text": footnote_text,
            "period_label": period_label,
            "stratification": "",
        })

    return results


def extract_star_ratings_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Extract Five-Star rating measure rows from all provider rows."""
    results: list[dict[str, Any]] = []
    for raw in rows:
        results.extend(extract_star_rating_measures(raw))
    return results


# ---------------------------------------------------------------------------
# Staffing + inspection provider-level measures (→ provider_measure_values)
# ---------------------------------------------------------------------------

# (measure_id, CSV column name(s), unit for formatting, footnote column or None)
_PROVIDER_MEASURE_MAP: list[tuple[str, tuple[str, ...], str | None]] = [
    # Staffing
    ("NH_STAFF_REPORTED_TOTAL_HPRD", ("reported_total_nurse_staffing_hours_per_resident_per_day",), "reported_staffing_footnote"),
    ("NH_STAFF_REPORTED_RN_HPRD", ("reported_rn_staffing_hours_per_resident_per_day",), "reported_staffing_footnote"),
    ("NH_STAFF_REPORTED_AIDE_HPRD", ("reported_nurse_aide_staffing_hours_per_resident_per_day",), None),
    ("NH_STAFF_ADJ_TOTAL_HPRD", ("adjusted_total_nurse_staffing_hours_per_resident_per_day",), None),
    ("NH_STAFF_ADJ_RN_HPRD", ("adjusted_rn_staffing_hours_per_resident_per_day",), None),
    ("NH_STAFF_ADJ_WEEKEND_HPRD", ("adjusted_weekend_total_nurse_staffing_hours_per_resident_per_day",), None),
    ("NH_STAFF_TOTAL_TURNOVER", ("total_nursing_staff_turnover",), "total_nursing_staff_turnover_footnote"),
    ("NH_STAFF_RN_TURNOVER", ("registered_nurse_turnover",), "registered_nurse_turnover_footnote"),
    ("NH_STAFF_ADMIN_DEPARTURES", ("number_of_administrators_who_have_left_the_nursing_home",), "administrator_turnover_footnote"),
    # Inspection
    ("NH_INSP_WEIGHTED_SCORE", ("total_weighted_health_survey_score",), None),
    ("NH_INSP_TOTAL_HEALTH_DEF", ("rating_cycle_1_total_number_of_health_deficiencies",), None),
]


def extract_provider_measures(raw: dict[str, str]) -> list[dict[str, Any]]:
    """Extract staffing and inspection metrics as measure value rows."""
    provider_id = _get(
        raw, "facility_id", "provnum",
        "cms_certification_number_(ccn)", "federal_provider_number",
    )
    if not provider_id:
        return []
    provider_id = provider_id.zfill(6)

    processing_date = _get(raw, "processing_date")
    period_label = processing_date or "current"

    results: list[dict[str, Any]] = []
    for measure_id, col_names, fn_col in _PROVIDER_MEASURE_MAP:
        val_str = _get(raw, *col_names)

        numeric_value = None
        suppressed = False
        not_reported = False

        if val_str:
            try:
                numeric_value = parse_decimal(val_str)
            except Exception:
                not_reported = True
        else:
            not_reported = True

        footnote_codes = None
        if fn_col:
            fn_str = _get(raw, fn_col)
            if fn_str:
                try:
                    codes = [int(c.strip()) for c in fn_str.split(",") if c.strip().isdigit()]
                    if codes:
                        footnote_codes = codes
                except ValueError:
                    pass

        results.append({
            "provider_id": provider_id,
            "provider_type": "NURSING_HOME",
            "measure_id": measure_id,
            "source_dataset_id": DATASET_ID,
            "numeric_value": numeric_value,
            "raw_value": val_str,
            "suppressed": suppressed,
            "not_reported": not_reported,
            "footnote_codes": footnote_codes,
            "period_label": period_label,
            "stratification": "",
        })

    return results


def extract_provider_measures_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Extract staffing + inspection measure rows from all provider rows."""
    results: list[dict[str, Any]] = []
    for raw in rows:
        results.extend(extract_provider_measures(raw))
    return results
