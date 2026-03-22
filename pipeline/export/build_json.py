"""
JSON export builder — produces one JSON file per provider.

Reads from PostgreSQL (JOINing provider_measure_values to measures for metadata),
builds the schema defined in json-export.md, and writes to build/data_staging/.

Atomic export: all files written to staging, validated, then renamed to build/data/.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from pipeline.config import DATASET_NAMES

logger = logging.getLogger(__name__)


def _json_serial(obj: Any) -> Any:
    """JSON serializer for types not handled by default."""
    if isinstance(obj, Decimal):
        # Preserve precision: use float for JSON (JSON has no Decimal type)
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _build_trend(
    all_values: list[dict],
    measure_id: str,
) -> tuple[list[dict], bool, int]:
    """Build the trend array for a measure from all its period values.

    Returns (trend_array, trend_valid, trend_period_count).
    Rule 12: trend_valid=True only when 3+ periods available.
    """
    # Filter to this measure, sort by period_start
    measure_vals = sorted(
        [v for v in all_values if v["measure_id"] == measure_id],
        key=lambda v: v.get("period_start") or date.min,
    )

    # Deduplicate by period_label (same measure+period = same data point)
    seen_periods: set[str] = set()
    trend: list[dict] = []
    for v in measure_vals:
        pl = v["period_label"]
        if pl in seen_periods:
            continue
        seen_periods.add(pl)

        # Check for methodology change (footnote 29)
        fn_codes = v.get("footnote_codes") or []
        methodology_change = 29 in fn_codes

        trend.append({
            "period_label": pl,
            "numeric_value": v.get("numeric_value"),
            "suppressed": v.get("suppressed", False),
            "not_reported": v.get("not_reported", False),
            "methodology_change_flag": methodology_change,
        })

    period_count = len(trend)
    trend_valid = period_count >= 3

    return trend, trend_valid, period_count


def build_provider_json(
    conn: Connection,
    provider_id: str,
) -> dict[str, Any] | None:
    """Build the complete JSON export for one provider.

    JOINs provider_measure_values to measures for metadata (no denormalization).
    """
    metadata = sa.MetaData()
    metadata.reflect(bind=conn.engine)

    providers = metadata.tables["providers"]
    measures = metadata.tables["measures"]
    pmv = metadata.tables["provider_measure_values"]
    ppa = metadata.tables["provider_payment_adjustments"]

    # Load provider
    provider = conn.execute(
        sa.select(providers).where(providers.c.provider_id == provider_id)
    ).mappings().fetchone()

    if not provider:
        return None

    # Load all measure values with measure metadata via JOIN.
    # Use only columns that exist in the reflected schema — the database may
    # predate migrations that added cms_measure_definition, ci_source, etc.
    measure_cols = [
        measures.c.measure_name,
        measures.c.measure_plain_language,
        measures.c.measure_group,
        measures.c.direction,
        measures.c.unit,
        measures.c.tail_risk_flag,
        measures.c.ses_sensitivity,
        measures.c.dataset_id.label("measure_dataset_id"),
    ]
    for col_name in ("direction_source", "cms_measure_definition"):
        if hasattr(measures.c, col_name):
            measure_cols.append(getattr(measures.c, col_name))

    stmt = (
        sa.select(pmv, *measure_cols)
        .select_from(pmv.join(measures, pmv.c.measure_id == measures.c.measure_id))
        .where(pmv.c.provider_id == provider_id)
        .order_by(pmv.c.measure_id, pmv.c.period_start)
    )

    all_values = [dict(row) for row in conn.execute(stmt).mappings().fetchall()]

    # Group by measure_id for trend building, take latest period for primary display
    measure_ids = sorted(set(v["measure_id"] for v in all_values))

    measures_array: list[dict] = []
    for mid in measure_ids:
        mid_values = [v for v in all_values if v["measure_id"] == mid]
        # Latest period is the primary display value
        latest = max(mid_values, key=lambda v: v.get("period_start") or date.min)

        # Build trend
        trend, trend_valid, trend_count = _build_trend(all_values, mid)

        measure_entry = {
            "measure_id": mid,
            "measure_name": latest.get("measure_name"),
            "measure_plain_language": latest.get("measure_plain_language"),
            "cms_measure_definition": latest.get("cms_measure_definition"),
            "measure_group": latest.get("measure_group"),
            "source_dataset_id": latest.get("source_dataset_id") or latest.get("measure_dataset_id"),
            "source_dataset_name": DATASET_NAMES.get(
                latest.get("source_dataset_id") or latest.get("measure_dataset_id") or "", "CMS Provider Data"
            ),
            "direction": latest.get("direction"),
            "direction_source": latest.get("direction_source"),
            "unit": latest.get("unit"),
            "tail_risk_flag": latest.get("tail_risk_flag", False),
            "ses_sensitivity": latest.get("ses_sensitivity"),
            # Stratification: empty string → null per json-export.md
            "stratification": latest.get("stratification") or None,
            "numeric_value": latest.get("numeric_value"),
            "score_text": latest.get("score_text"),
            "confidence_interval_lower": latest.get("confidence_interval_lower"),
            "confidence_interval_upper": latest.get("confidence_interval_upper"),
            "ci_source": latest.get("ci_source"),
            "prior_source": latest.get("prior_source"),
            "compared_to_national": latest.get("compared_to_national"),
            "observed_value": latest.get("observed_value"),
            "expected_value": latest.get("expected_value"),
            "suppressed": latest.get("suppressed", False),
            "suppression_reason": latest.get("suppression_reason"),
            "not_reported": latest.get("not_reported", False),
            "not_reported_reason": latest.get("not_reported_reason"),
            "count_suppressed": latest.get("count_suppressed", False),
            "footnote_codes": latest.get("footnote_codes"),
            "footnote_text": latest.get("footnote_text"),
            "period_label": latest.get("period_label"),
            "period_start": latest.get("period_start"),
            "period_end": latest.get("period_end"),
            "sample_size": latest.get("sample_size"),
            "denominator": latest.get("denominator"),
            "reliability_flag": latest.get("reliability_flag"),
            "national_avg": latest.get("national_avg"),
            "national_avg_period": latest.get("national_avg_period"),
            "state_avg": latest.get("state_avg"),
            "state_avg_period": latest.get("state_avg_period"),
            # Trend data (longitudinal)
            "trend": trend if len(trend) > 1 else None,
            "trend_valid": trend_valid,
            "trend_period_count": trend_count,
        }
        measures_array.append(measure_entry)

    # Load payment adjustments
    pa_rows = conn.execute(
        sa.select(ppa).where(ppa.c.provider_id == provider_id)
        .order_by(ppa.c.program, ppa.c.program_year)
    ).mappings().fetchall()

    payment_adjustments = [
        {
            "program": row["program"],
            "program_year": row["program_year"],
            "penalty_flag": row["penalty_flag"],
            "payment_adjustment_pct": row["payment_adjustment_pct"],
            "total_score": row["total_score"],
            "score_percentile": row["score_percentile"],
        }
        for row in pa_rows
    ]

    # Build context objects
    ptype = provider["provider_type"]

    hospital_context = None
    if ptype == "HOSPITAL":
        hospital_context = {
            "is_critical_access": provider.get("is_critical_access"),
            "is_emergency_services": provider.get("is_emergency_services"),
            "birthing_friendly_designation": provider.get("birthing_friendly_designation"),
            "hospital_overall_rating": provider.get("hospital_overall_rating"),
            "hospital_overall_rating_footnote": provider.get("hospital_overall_rating_footnote"),
        }

    nursing_home_context = None
    if ptype == "NURSING_HOME":
        nursing_home_context = {
            "certified_beds": provider.get("certified_beds"),
            "average_daily_census": provider.get("average_daily_census"),
            "is_continuing_care_retirement_community": provider.get("is_continuing_care_retirement_community"),
            "is_special_focus_facility": provider.get("is_special_focus_facility"),
            "is_special_focus_facility_candidate": provider.get("is_special_focus_facility_candidate"),
            "is_hospital_based": provider.get("is_hospital_based"),
            "is_abuse_icon": provider.get("is_abuse_icon"),
            "is_urban": provider.get("is_urban"),
            "chain_name": provider.get("chain_name"),
            "chain_id": provider.get("chain_id"),
        }

    # Load inspection events (NH only)
    inspection_events = None
    if ptype == "NURSING_HOME" and "provider_inspection_events" in metadata.tables:
        pie = metadata.tables["provider_inspection_events"]
        ie_rows = conn.execute(
            sa.select(pie).where(pie.c.provider_id == provider_id)
            .order_by(pie.c.survey_date.desc(), pie.c.deficiency_tag)
        ).mappings().fetchall()

        inspection_events = []
        for row in ie_rows:
            event = {
                "survey_date": row["survey_date"],
                "survey_type": row.get("survey_type"),
                "deficiency_tag": row["deficiency_tag"],
                "deficiency_description": row.get("deficiency_description"),
                "deficiency_category": row.get("deficiency_category"),
                "scope_severity_code": row.get("scope_severity_code"),
                "is_immediate_jeopardy": row.get("is_immediate_jeopardy", False),
                "is_complaint_deficiency": row.get("is_complaint_deficiency", False),
                "correction_date": row.get("correction_date"),
                "inspection_cycle": row.get("inspection_cycle"),
                # DEC-028: contested citation transparency
                "is_contested": row.get("is_contested", False),
                "originally_published_scope_severity": row.get("originally_published_scope_severity"),
                "scope_severity_history": row.get("scope_severity_history"),
            }
            inspection_events.append(event)

    # Load penalties (NH only)
    penalties = None
    if ptype == "NURSING_HOME" and "provider_penalties" in metadata.tables:
        pp = metadata.tables["provider_penalties"]
        pen_rows = conn.execute(
            sa.select(pp).where(pp.c.provider_id == provider_id)
            .order_by(pp.c.penalty_date.desc())
        ).mappings().fetchall()

        penalties = []
        for row in pen_rows:
            penalty = {
                "penalty_date": row["penalty_date"],
                "penalty_type": row["penalty_type"],
                "fine_amount": row.get("fine_amount"),
                "payment_denial_start_date": row.get("payment_denial_start_date"),
                "payment_denial_length_days": row.get("payment_denial_length_days"),
                # DEC-028: penalty amount change transparency
                "originally_published_fine_amount": row.get("originally_published_fine_amount"),
                "fine_amount_changed": (
                    row.get("fine_amount") != row.get("originally_published_fine_amount")
                    if row.get("originally_published_fine_amount") is not None
                    else False
                ),
            }
            penalties.append(penalty)

    # Load ownership (NH only)
    ownership = None
    if ptype == "NURSING_HOME" and "provider_ownership" in metadata.tables:
        po = metadata.tables["provider_ownership"]
        own_rows = conn.execute(
            sa.select(po).where(po.c.provider_id == provider_id)
            .order_by(po.c.role, po.c.owner_name)
        ).mappings().fetchall()

        ownership = [
            {
                "owner_name": row["owner_name"],
                "owner_type": row.get("owner_type"),
                "role": row.get("role"),
                "ownership_percentage": row.get("ownership_percentage"),
                "ownership_percentage_not_provided": row.get("ownership_percentage_not_provided", False),
                "association_date": row.get("association_date"),
            }
            for row in own_rows
        ]

    # Build address
    address_raw = provider.get("address")
    if isinstance(address_raw, str):
        try:
            address = json.loads(address_raw)
        except (json.JSONDecodeError, TypeError):
            address = {"street": address_raw, "city": provider.get("city"), "state": provider.get("state"), "zip": provider.get("zip")}
    elif isinstance(address_raw, dict):
        address = address_raw
    else:
        address = {"street": None, "city": provider.get("city"), "state": provider.get("state"), "zip": provider.get("zip")}

    return {
        "provider_id": provider["provider_id"],
        "provider_type": ptype,
        "name": provider["name"],
        "is_active": provider.get("is_active", True),
        "phone": provider.get("phone"),
        "address": address,
        "provider_subtype": provider.get("provider_subtype"),
        "ownership_type": provider.get("ownership_type"),
        "last_updated": datetime.utcnow().isoformat(),
        "measures": measures_array,
        "payment_adjustments": payment_adjustments,
        "hospital_context": hospital_context,
        "nursing_home_context": nursing_home_context,
        "inspection_events": inspection_events,
        "penalties": penalties,
        "ownership": ownership,
    }


def export_all(
    db_url: str,
    output_dir: str | Path = "build/data_staging",
    final_dir: str | Path = "build/data",
) -> int:
    """Export JSON for all active providers. Returns count of files written.

    Writes to staging dir first, then atomic rename to final dir.
    """
    output_path = Path(output_dir)
    final_path = Path(final_dir)

    # Clean staging
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    engine = sa.create_engine(db_url)
    count = 0

    with engine.connect() as conn:
        # Get all active provider IDs
        metadata = sa.MetaData()
        metadata.reflect(bind=conn.engine, only=["providers"])
        providers = metadata.tables["providers"]

        provider_ids = [
            row[0] for row in conn.execute(
                sa.select(providers.c.provider_id)
                .where(providers.c.is_active == True)
                .order_by(providers.c.provider_id)
            ).fetchall()
        ]

        logger.info("Exporting %d providers to %s", len(provider_ids), output_path)

        for pid in provider_ids:
            data = build_provider_json(conn, pid)
            if data is None:
                continue

            filepath = output_path / f"{pid}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, default=_json_serial, ensure_ascii=False)

            count += 1
            if count % 500 == 0:
                logger.info("  Exported %d / %d providers", count, len(provider_ids))

    engine.dispose()

    logger.info("Exported %d provider JSON files to staging", count)

    # Atomic rename: staging → final
    if final_path.exists():
        backup = final_path.with_name("data_previous")
        if backup.exists():
            shutil.rmtree(backup)
        final_path.rename(backup)

    output_path.rename(final_path)
    logger.info("Staging renamed to %s", final_path)

    return count
