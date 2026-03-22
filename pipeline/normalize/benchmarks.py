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
# Maps the verbose column names in NH_StateUSAverages to our measure_ids.
# Only quality measures relevant for benchmarking are included.

NH_STATE_AVG_COLUMN_MAP: dict[str, str] = {
    # Long-stay MDS quality measures
    "percentage_of_long_stay_residents_whose_need_for_help_with_daily_activities_has_increased": "401",
    "percentage_of_long_stay_residents_who_lose_too_much_weight": "402",
    "percentage_of_low_risk_long_stay_residents_who_lose_control_of_their_bowels_or_bladder": "403",
    "percentage_of_long_stay_residents_with_a_catheter_inserted_and_left_in_their_bladder": "404",
    "percentage_of_long_stay_residents_with_a_urinary_tract_infection": "405",
    "percentage_of_long_stay_residents_who_have_depressive_symptoms": "406",
    "percentage_of_long_stay_residents_who_were_physically_restrained": "407",
    "percentage_of_long_stay_residents_experiencing_one_or_more_falls_with_major_injury": "408",
    "percentage_of_long_stay_residents_assessed_and_appropriately_given_the_pneumococcal_vaccine": "409",
    "percentage_of_long_stay_residents_who_received_an_antipsychotic_medication": "410",
    "percentage_of_long_stay_residents_whose_ability_to_move_independently_worsened": "411",
    "percentage_of_long_stay_residents_who_received_an_antianxiety_or_hypnotic_medication": "419",
    "percentage_of_high_risk_long_stay_residents_with_pressure_ulcers": "451",
    "percentage_of_long_stay_residents_assessed_and_appropriately_given_the_seasonal_influenza_vaccine": "425",
    # Short-stay MDS quality measures
    "percentage_of_short_stay_residents_assessed_and_appropriately_given_the_pneumococcal_vaccine": "409S",
    "percentage_of_short_stay_residents_who_newly_received_an_antipsychotic_medication": "410S",
    "percentage_of_short_stay_residents_who_made_improvements_in_function": "424",
    "percentage_of_short_stay_residents_who_were_assessed_and_appropriately_given_the_seasonal_influenza_vaccine": "425S",
    "percentage_of_short_stay_residents_who_were_rehospitalized_after_a_nursing_home_admission": "471",
    "percentage_of_short_stay_residents_who_had_an_outpatient_emergency_department_visit": "472",
    # Claims-based measures
    "number_of_hospitalizations_per_1000_long-stay_resident_days": "521",
    "number_of_outpatient_emergency_department_visits_per_1000_long-stay_resident_days": "522",
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
        measure_code = raw.get("measure_code", "").strip()
        if not measure_code:
            continue

        # SNF QRP national rows have CCN = "NATION"
        ccn = raw.get("cms_certification_number_(ccn)", raw.get("ccn", ""))
        if ccn.strip().upper() != "NATION":
            continue

        score = parse_decimal(raw.get("score", ""))
        if score is None:
            continue

        start_date = parse_date(raw.get("start_date"))
        end_date = parse_date(raw.get("end_date"))
        period_label = derive_period_label(start_date, end_date)

        results.append({
            "measure_id": measure_code,
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
