"""
Benchmark normalizer — parses CMS companion National/State CSV files into
measure_benchmarks rows.

CMS publishes `-National.csv` and `-State.csv` files alongside each
`-Hospital.csv` dataset. Nursing home archives include `NH_StateUSAverages`
(state + national in one file) and `SNF_QRP_National_Data`.

These files are the authoritative source for benchmark values. The pipeline
must NOT compute averages from provider data (DEC-036).

Key constraint: if CMS does not publish a state average for a measure
(e.g., HGLM outcome measures), the pipeline must not fabricate one.
Missing CMS state files for a dataset = no state benchmark rows for
those measures.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from pipeline.normalize.common import derive_period_label, parse_date, parse_decimal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hospital benchmark file configurations
# ---------------------------------------------------------------------------
# Maps csv_reader dataset keys to their benchmark extraction config.
# score_field: the CSV column (snake_cased) containing the average value.
# measure_id_field: the CSV column containing the CMS measure ID.
# state_field: for state files, the column containing the state abbreviation.

# CMS benchmark CSVs use underscores in some imaging/MSPB measure IDs while the
# registry stores them with hyphens (matching the per-provider data files).
# Map CSV-form → registry-form here so benchmarks JOIN cleanly to measures.
HOSPITAL_BENCHMARK_MEASURE_ID_REMAP: dict[str, str] = {
    "OP_8": "OP-8",
    "OP_10": "OP-10",
    "OP_13": "OP-13",
    "OP_39": "OP-39",
    "MSPB_1": "MSPB-1",
}


HOSPITAL_NATIONAL_CONFIGS: dict[str, dict[str, str]] = {
    "timely_effective_national": {
        "score_field": "score",
        "measure_id_field": "measure_id",
        "source": "Timely_and_Effective_Care-National",
    },
    "imaging_national": {
        "score_field": "score",
        "measure_id_field": "measure_id",
        "source": "Outpatient_Imaging_Efficiency-National",
    },
    "complications_deaths_national": {
        "score_field": "national_rate",
        "measure_id_field": "measure_id",
        "source": "Complications_and_Deaths-National",
    },
    "readmissions_national": {
        "score_field": "national_rate",
        "measure_id_field": "measure_id",
        "source": "Unplanned_Hospital_Visits-National",
    },
    "hai_national": {
        "score_field": "score",
        "measure_id_field": "measure_id",
        "source": "Healthcare_Associated_Infections-National",
    },
    "hcahps_national": {
        "score_field": "hcahps_answer_percent",
        "measure_id_field": "hcahps_measure_id",
        "source": "HCAHPS-National",
    },
    "mspb_national": {
        "score_field": "score",
        "measure_id_field": "measure_id",
        "source": "Medicare_Hospital_Spending_Per_Patient-National",
    },
}

HOSPITAL_STATE_CONFIGS: dict[str, dict[str, str]] = {
    "timely_effective_state": {
        "score_field": "score",
        "measure_id_field": "measure_id",
        "state_field": "state",
        "source": "Timely_and_Effective_Care-State",
    },
    "imaging_state": {
        "score_field": "score",
        "measure_id_field": "measure_id",
        "state_field": "state",
        "source": "Outpatient_Imaging_Efficiency-State",
    },
    # NOTE: Complications-State and Readmissions-State do NOT have a score column.
    # CMS does not publish state averages for HGLM outcome measures.
    # DO NOT add them here. See DEC-036.
    "hai_state": {
        "score_field": "score",
        "measure_id_field": "measure_id",
        "state_field": "state",
        "source": "Healthcare_Associated_Infections-State",
    },
    "hcahps_state": {
        "score_field": "hcahps_answer_percent",
        "measure_id_field": "hcahps_measure_id",
        "state_field": "state",
        "source": "HCAHPS-State",
    },
    "mspb_state": {
        "score_field": "score",
        "measure_id_field": "measure_id",
        "state_field": "state",
        "source": "Medicare_Hospital_Spending_Per_Patient-State",
    },
}


# ---------------------------------------------------------------------------
# NH State/US Averages column-to-measure_id mapping
# ---------------------------------------------------------------------------
# The NH_StateUSAverages CSV is wide-format (one column per measure), so unlike
# the hospital benchmark files (where measure_id is a row field) we have to map
# each column header to its measure_id by hand. The mapping below was verified
# against the actual CMS column headers in NH_StateUSAverages_Apr2026.csv and
# the names in MEASURE_REGISTRY (pipeline/config.py).
#
# Snake-case rule: csv_reader replaces hyphens AND slashes with spaces, then
# lowercases and converts all spaces to underscores. So both "long stay" and
# "long-stay" in CMS column headers normalize to "long_stay" — the keys here
# always use underscores, never hyphens.
#
# CSV columns NOT mapped (intentional — measure not in MEASURE_REGISTRY):
#   - "Percentage of short stay residents who made improvements in function"
#     (NH_QM_456 — not currently tracked)
NH_STATE_AVG_COLUMN_MAP: dict[str, str] = {
    # Long-stay MDS quality measures
    "percentage_of_long_stay_residents_whose_need_for_help_with_daily_activities_has_increased": "NH_MDS_401",
    "percentage_of_long_stay_residents_who_lose_too_much_weight": "NH_MDS_404",
    "percentage_of_long_stay_residents_with_a_catheter_inserted_and_left_in_their_bladder": "NH_MDS_406",
    "percentage_of_long_stay_residents_with_a_urinary_tract_infection": "NH_MDS_407",
    "percentage_of_long_stay_residents_who_have_depressive_symptoms": "NH_MDS_408",
    "percentage_of_long_stay_residents_who_were_physically_restrained": "NH_MDS_409",
    "percentage_of_long_stay_residents_experiencing_one_or_more_falls_with_major_injury": "NH_MDS_410",
    "percentage_of_long_stay_residents_assessed_and_appropriately_given_the_pneumococcal_vaccine": "NH_MDS_415",
    "percentage_of_long_stay_residents_whose_ability_to_walk_independently_worsened": "NH_MDS_451",
    "percentage_of_long_stay_residents_who_received_an_antianxiety_or_hypnotic_medication": "NH_MDS_452",
    "percentage_of_long_stay_residents_assessed_and_appropriately_given_the_seasonal_influenza_vaccine": "NH_MDS_454",
    "percentage_of_long_stay_residents_with_pressure_ulcers": "NH_MDS_479",
    "percentage_of_long_stay_residents_with_new_or_worsened_bowel_or_bladder_incontinence": "NH_MDS_480",
    "percentage_of_long_stay_residents_who_received_an_antipsychotic_medication": "NH_MDS_481",
    # Short-stay MDS quality measures
    "percentage_of_short_stay_residents_assessed_and_appropriately_given_the_pneumococcal_vaccine": "NH_MDS_430",
    "percentage_of_short_stay_residents_who_newly_received_an_antipsychotic_medication": "NH_MDS_434",
    "percentage_of_short_stay_residents_who_were_assessed_and_appropriately_given_the_seasonal_influenza_vaccine": "NH_MDS_472",
    # Claims-based measures (NH_CLAIMS_521/522 are short-stay rehospitalization
    # / outpatient ED. NH_CLAIMS_551/552 are the per-1000-resident-days rates.)
    "percentage_of_short_stay_residents_who_were_rehospitalized_after_a_nursing_home_admission": "NH_CLAIMS_521",
    "percentage_of_short_stay_residents_who_had_an_outpatient_emergency_department_visit": "NH_CLAIMS_522",
    "number_of_hospitalizations_per_1000_long_stay_resident_days": "NH_CLAIMS_551",
    "number_of_outpatient_emergency_department_visits_per_1000_long_stay_resident_days": "NH_CLAIMS_552",
}


def normalize_hospital_national_benchmarks(
    rows: list[dict[str, str]],
    config: dict[str, str],
    vintage: str,
) -> list[dict[str, Any]]:
    """Normalize a hospital -National.csv file into measure_benchmarks rows.

    Parameters
    ----------
    rows : list[dict[str, str]]
        Raw rows from csv_reader (snake_case keys).
    config : dict
        Entry from HOSPITAL_NATIONAL_CONFIGS.
    vintage : str
        Archive vintage label (e.g., "2025-11").

    Returns
    -------
    list[dict] ready for upsert into measure_benchmarks.
    """
    results: list[dict[str, Any]] = []
    score_field = config["score_field"]
    measure_id_field = config["measure_id_field"]
    source = config["source"]

    for raw in rows:
        measure_id = raw.get(measure_id_field, "").strip()
        if not measure_id:
            continue
        measure_id = HOSPITAL_BENCHMARK_MEASURE_ID_REMAP.get(measure_id, measure_id)

        score = parse_decimal(raw.get(score_field, ""))
        if score is None:
            logger.debug(
                "Skipping benchmark for %s: unparseable score '%s'",
                measure_id, raw.get(score_field, ""),
            )
            continue

        start_date = parse_date(raw.get("start_date"))
        end_date = parse_date(raw.get("end_date"))
        period_label = derive_period_label(start_date, end_date)

        results.append({
            "measure_id": measure_id,
            "geography_type": "national",
            "geography_code": "US",
            "period_label": period_label,
            "avg_value": score,
            "sample_size": None,
            "source": source,
            "source_vintage": vintage,
        })

    logger.info(
        "Normalized %d national benchmarks from %s (vintage %s)",
        len(results), source, vintage,
    )
    return results


def normalize_hospital_state_benchmarks(
    rows: list[dict[str, str]],
    config: dict[str, str],
    vintage: str,
) -> list[dict[str, Any]]:
    """Normalize a hospital -State.csv file into measure_benchmarks rows.

    Parameters
    ----------
    rows : list[dict[str, str]]
        Raw rows from csv_reader (snake_case keys).
    config : dict
        Entry from HOSPITAL_STATE_CONFIGS.
    vintage : str
        Archive vintage label (e.g., "2025-11").

    Returns
    -------
    list[dict] ready for upsert into measure_benchmarks.
    """
    results: list[dict[str, Any]] = []
    score_field = config["score_field"]
    measure_id_field = config["measure_id_field"]
    state_field = config["state_field"]
    source = config["source"]

    for raw in rows:
        state = raw.get(state_field, "").strip().upper()
        measure_id = raw.get(measure_id_field, "").strip()
        if not state or not measure_id:
            continue
        measure_id = HOSPITAL_BENCHMARK_MEASURE_ID_REMAP.get(measure_id, measure_id)

        score = parse_decimal(raw.get(score_field, ""))
        if score is None:
            continue

        start_date = parse_date(raw.get("start_date"))
        end_date = parse_date(raw.get("end_date"))
        period_label = derive_period_label(start_date, end_date)

        results.append({
            "measure_id": measure_id,
            "geography_type": "state",
            "geography_code": state,
            "period_label": period_label,
            "avg_value": score,
            "sample_size": None,
            "source": source,
            "source_vintage": vintage,
        })

    logger.info(
        "Normalized %d state benchmarks from %s (vintage %s)",
        len(results), source, vintage,
    )
    return results


def normalize_nh_state_us_averages(
    rows: list[dict[str, str]],
    vintage: str,
) -> list[dict[str, Any]]:
    """Normalize NH_StateUSAverages CSV into measure_benchmarks rows.

    This file has one row per geography (53 states + NATION) with measure
    values as columns. The column-to-measure_id mapping is defined in
    NH_STATE_AVG_COLUMN_MAP.

    Parameters
    ----------
    rows : list[dict[str, str]]
        Raw rows from csv_reader (snake_case keys).
    vintage : str
        Archive vintage label (e.g., "2023-01").

    Returns
    -------
    list[dict] ready for upsert into measure_benchmarks.
    """
    results: list[dict[str, Any]] = []

    for raw in rows:
        geo_raw = raw.get("state_or_nation", "").strip().upper()
        if not geo_raw:
            continue

        if geo_raw == "NATION":
            geography_type = "national"
            geography_code = "US"
        else:
            geography_type = "state"
            geography_code = geo_raw

        # Processing date serves as period anchor for NH state averages.
        processing_date = raw.get("processing_date", "")
        period_label = processing_date if processing_date else f"vintage_{vintage}"

        for col_name, measure_id in NH_STATE_AVG_COLUMN_MAP.items():
            value = parse_decimal(raw.get(col_name, ""))
            if value is None:
                continue

            results.append({
                "measure_id": measure_id,
                "geography_type": geography_type,
                "geography_code": geography_code,
                "period_label": period_label,
                "avg_value": value,
                "sample_size": None,
                "source": "NH_StateUSAverages",
                "source_vintage": vintage,
            })

    logger.info(
        "Normalized %d NH state/US benchmarks (vintage %s)",
        len(results), vintage,
    )
    return results


def normalize_snf_qrp_national_benchmarks(
    rows: list[dict[str, str]],
    vintage: str,
) -> list[dict[str, Any]]:
    """Normalize SNF QRP National Data CSV into measure_benchmarks rows.

    The SNF QRP national file uses compound measure_code values per DEC-020.
    Each base measure has multiple sub-codes:
      - `<MID>_NAT_UNADJUST_AVG` / `<MID>_NAT_OBS_RATE` / `<MID>_NATL_OBS_RATE`
        / `<MID>_MSPB_SCORE_NATL`  → the national average we want
      - `<MID>_N_BETTER_NAT` / `_N_NO_DIFF_NAT` / `_N_TOO_SMALL` / `_N_WORSE_NAT`
        → comparison counts (not benchmarks)

    The base measure_id is the leading 3-segment prefix (e.g., `S_004_01`)
    that matches the registry. CCN is in `facility_id` not `cms_certification_...`.
    """
    avg_suffixes = (
        "_NAT_UNADJUST_AVG",
        "_NAT_OBS_RATE",
        "_NATL_OBS_RATE",
        "_MSPB_SCORE_NATL",
    )

    results: list[dict[str, Any]] = []

    for raw in rows:
        measure_code = raw.get("measure_code", "").strip()
        if not measure_code:
            continue

        # SNF QRP national rows have facility_id = "NATION".
        # Older snapshots may use cms_certification_number_(ccn).
        ccn = raw.get("facility_id") or raw.get("cms_certification_number_(ccn)") or raw.get("ccn") or ""
        if ccn.strip().upper() != "NATION":
            continue

        # Decompose compound measure_code: keep only rows that are the average.
        matched_suffix = None
        for suffix in avg_suffixes:
            if measure_code.endswith(suffix):
                matched_suffix = suffix
                break
        if matched_suffix is None:
            continue

        # Base measure_id is the part before the matched suffix, with any trailing
        # measure-domain segment stripped. Registry IDs are 3 segments (S_NNN_NN).
        base_with_domain = measure_code[: -len(matched_suffix)]
        # Strip trailing domain like _PPR_PD, _DTC, _HAI — keep only first 3 parts.
        parts = base_with_domain.split("_")
        if len(parts) < 3:
            continue
        base_measure_id = "_".join(parts[:3])

        score = parse_decimal(raw.get("score", ""))
        if score is None:
            continue

        start_date = parse_date(raw.get("start_date"))
        end_date = parse_date(raw.get("end_date"))
        period_label = derive_period_label(start_date, end_date)

        results.append({
            "measure_id": base_measure_id,
            "geography_type": "national",
            "geography_code": "US",
            "period_label": period_label,
            "avg_value": score,
            "sample_size": None,
            "source": "SNF_QRP_National",
            "source_vintage": vintage,
        })

    logger.info(
        "Normalized %d SNF QRP national benchmarks (vintage %s)",
        len(results), vintage,
    )
    return results
