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

# Path to ZCTA centroid file (US Census Bureau 2020 Gazetteer, public domain).
ZCTA_CENTROIDS_PATH = Path("data/reference/zcta_centroids.tsv")


def _load_zcta_centroids(path: Path | None = None) -> dict[str, tuple[float, float]]:
    """Load zip → (lat, lon) mapping from ZCTA Gazetteer centroids TSV.

    The file has three tab-separated columns: GEOID, INTPTLAT, INTPTLONG.
    No header row (pre-processed from Census Gazetteer).

    Returns:
        Dict mapping 5-digit zip string to (latitude, longitude) tuple.
    """
    centroids: dict[str, tuple[float, float]] = {}
    filepath = path or ZCTA_CENTROIDS_PATH
    if not filepath.exists():
        logger.warning("ZCTA centroids file not found at %s; hospital coordinates will be null", filepath)
        return centroids

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                zip_code = parts[0].strip().zfill(5)
                try:
                    lat = float(parts[1].strip())
                    lon = float(parts[2].strip())
                    centroids[zip_code] = (lat, lon)
                except (ValueError, IndexError):
                    continue

    logger.info("Loaded %d ZCTA centroids", len(centroids))
    return centroids


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
    grouped: dict[str, list[dict]] | None = None,
) -> tuple[list[dict], bool, int]:
    """Build the trend array for a measure from all its period values.

    Returns (trend_array, trend_valid, trend_period_count).
    Rule 12: trend_valid=True only when 3+ periods available.

    `grouped` is an optional pre-grouped dict measure_id -> [rows]. Passing it
    avoids re-iterating `all_values` per measure (O(N²) → O(N)).
    """
    if grouped is not None:
        rows_for_measure = grouped.get(measure_id, [])
    else:
        rows_for_measure = [v for v in all_values if v["measure_id"] == measure_id]

    # Drop "unknown" period_labels from the trend — they don't represent a real
    # observation point and would corrupt the trend ordering / count.
    rows_for_measure = [
        v for v in rows_for_measure if v.get("period_label") != "unknown"
    ]

    measure_vals = sorted(
        rows_for_measure,
        key=lambda v: (
            v.get("period_start") or date.min,
            v.get("period_label") or "",
        ),
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
            "sample_size": v.get("sample_size"),
            "ci_lower": v.get("confidence_interval_lower"),
            "ci_upper": v.get("confidence_interval_upper"),
            "compared_to_national": v.get("compared_to_national"),
            "footnote_codes": fn_codes if fn_codes else None,
        })

    period_count = len(trend)
    trend_valid = period_count >= 3

    return trend, trend_valid, period_count


def _load_benchmark_lookup(
    conn: Connection,
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    """Load all measure_benchmarks rows into an in-memory lookup.

    Key: (measure_id, geography_type, geography_code, period_label)
    Value: dict with avg_value and period_label.

    This is loaded once per export run and reused for all providers. For a
    lookup that supports fast nearest-period fallback, use
    _build_benchmark_index() to create a secondary index keyed by
    (measure_id, geo_type, geo_code) -> [(period_label, avg_value), ...].
    """
    metadata = sa.MetaData()
    metadata.reflect(bind=conn.engine, only=["measure_benchmarks"])
    bench = metadata.tables["measure_benchmarks"]

    rows = conn.execute(
        sa.select(
            bench.c.measure_id,
            bench.c.geography_type,
            bench.c.geography_code,
            bench.c.period_label,
            bench.c.avg_value,
        )
    ).fetchall()

    lookup: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row.measure_id, row.geography_type, row.geography_code, row.period_label)
        lookup[key] = {
            "avg_value": row.avg_value,
            "period_label": row.period_label,
        }
    return lookup


def _build_benchmark_index(
    lookup: dict[tuple[str, str, str, str], dict[str, Any]],
) -> dict[tuple[str, str, str], list[tuple[str, Any]]]:
    """Index benchmarks by (measure_id, geo_type, geo_code).

    Each value is a list of (period_label, avg_value) sorted by period_label
    descending so [0] is the most recent. Lets _resolve_benchmark find the
    fallback in O(1) instead of scanning all benchmarks per call.
    """
    index: dict[tuple[str, str, str], list[tuple[str, Any]]] = {}
    for (measure_id, geo_type, geo_code, period_label), entry in lookup.items():
        key = (measure_id, geo_type, geo_code)
        index.setdefault(key, []).append((period_label, entry["avg_value"]))

    # Sort each list by period_label descending so [0] is the most recent.
    for periods in index.values():
        periods.sort(key=lambda p: p[0], reverse=True)

    return index


def _resolve_benchmark(
    lookup: dict[tuple[str, str, str, str], dict[str, Any]],
    measure_id: str,
    geo_type: str,
    geo_code: str,
    period_label: str,
    index: dict[tuple[str, str, str], list[tuple[str, Any]]] | None = None,
) -> tuple[Any, str | None]:
    """Resolve a benchmark value with same-measure fallback to nearest period.

    Returns (avg_value, benchmark_period_label) — both null when no benchmark exists.

    Tries exact match on period_label first. If that misses, falls back to the
    most recent benchmark for this (measure_id, geo_type, geo_code) — matches
    the display intent: show CMS's most recently published average even if its
    period doesn't perfectly align with the provider's period.

    When `index` is supplied, the fallback is O(1). When omitted, falls back
    to a linear scan (kept for backwards compatibility with tests).
    """
    # Exact match
    key = (measure_id, geo_type, geo_code, period_label)
    if key in lookup:
        entry = lookup[key]
        return entry["avg_value"], entry["period_label"]

    if index is not None:
        candidates = index.get((measure_id, geo_type, geo_code))
        if not candidates:
            return None, None
        # candidates is sorted by period_label descending; [0] is most recent
        period_label_recent, avg_value = candidates[0]
        return avg_value, period_label_recent

    # Linear-scan fallback (used when no index provided — tests, ad-hoc calls)
    candidates_pairs = [
        (k, v) for k, v in lookup.items()
        if k[0] == measure_id and k[1] == geo_type and k[2] == geo_code
    ]
    if not candidates_pairs:
        return None, None
    candidates_pairs.sort(key=lambda item: item[0][3], reverse=True)
    _, entry = candidates_pairs[0]
    return entry["avg_value"], entry["period_label"]


def _compute_overlap_flag(
    ci_lower: Any,
    ci_upper: Any,
    national_avg: Any,
) -> bool | None:
    """Compute overlap_flag at export time (DEC-029, json-export.md).

    True when ci_lower <= national_avg <= ci_upper. Null when any input is null.
    """
    if ci_lower is None or ci_upper is None or national_avg is None:
        return None
    try:
        return Decimal(str(ci_lower)) <= Decimal(str(national_avg)) <= Decimal(str(ci_upper))
    except (TypeError, ValueError):
        return None


def _load_entity_facility_counts(
    conn: Connection,
) -> tuple[dict[str, int], dict[str, int]]:
    """Pre-compute facility counts for ownership entities and parent groups.

    Used by per-provider ownership enrichment. Computing these once per export
    instead of per provider eliminates an N+1 problem on ~16K NH providers.
    Returns:
      (entity_to_count, parent_group_id_to_count)
    """
    metadata = sa.MetaData()
    metadata.reflect(bind=conn.engine, only=["provider_ownership"])
    po = metadata.tables["provider_ownership"]

    rows = conn.execute(
        sa.select(
            po.c.owner_name,
            sa.func.count(sa.distinct(po.c.provider_id)).label("n"),
        )
        .where(po.c.owner_type == "Organization")
        .group_by(po.c.owner_name)
    ).fetchall()
    entity_counts = {row.owner_name: row.n for row in rows}

    parent_group_counts: dict[str, int] = {}
    insp = sa.inspect(conn.engine)
    if (
        "ownership_entity_group_map" in insp.get_table_names()
        and "ownership_parent_groups" in insp.get_table_names()
    ):
        meta2 = sa.MetaData()
        meta2.reflect(bind=conn.engine, only=["ownership_entity_group_map", "provider_ownership"])
        oegm = meta2.tables["ownership_entity_group_map"]
        po2 = meta2.tables["provider_ownership"]
        rows = conn.execute(
            sa.select(
                oegm.c.parent_group_id,
                sa.func.count(sa.distinct(po2.c.provider_id)).label("n"),
            )
            .select_from(po2.join(oegm, po2.c.owner_name == oegm.c.entity_name))
            .where(po2.c.owner_type == "Organization")
            .group_by(oegm.c.parent_group_id)
        ).fetchall()
        parent_group_counts = {row.parent_group_id: row.n for row in rows}

    return entity_counts, parent_group_counts


def build_provider_json(
    conn: Connection,
    provider_id: str,
    benchmark_lookup: dict[tuple[str, str, str, str], dict[str, Any]] | None = None,
    metadata: sa.MetaData | None = None,
    entity_facility_counts: dict[str, int] | None = None,
    parent_group_facility_counts: dict[str, int] | None = None,
    benchmark_index: dict[tuple[str, str, str], list[tuple[str, Any]]] | None = None,
) -> dict[str, Any] | None:
    """Build the complete JSON export for one provider.

    JOINs provider_measure_values to measures for metadata (no denormalization).
    Benchmarks (national_avg, state_avg) are resolved from `measure_benchmarks`
    via the in-memory `benchmark_lookup` (DEC-036). When `benchmark_lookup` is
    None, the function loads it on demand — but the export driver should pass
    it in for efficiency.

    `metadata` (reflected) and the facility-count dicts can be passed in to
    avoid re-reflecting and re-computing per provider — the export driver does
    this once for all providers.
    """
    if metadata is None:
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

    if benchmark_lookup is None:
        benchmark_lookup = _load_benchmark_lookup(conn)

    provider_state = (provider.get("state") or "").upper() or None

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

    # Filter out is_active=false measures — these are retired or auto-registered
    # unknowns from older archives that we don't surface anywhere on the site.
    # See seed_measures.ensure_measure_exists for how these get inserted.
    stmt = (
        sa.select(pmv, *measure_cols)
        .select_from(pmv.join(measures, pmv.c.measure_id == measures.c.measure_id))
        .where(pmv.c.provider_id == provider_id)
        .where(measures.c.is_active == True)  # noqa: E712
        .order_by(pmv.c.measure_id, pmv.c.period_start)
    )

    all_values = [dict(row) for row in conn.execute(stmt).mappings().fetchall()]

    # Group by measure_id once so per-measure work is O(1) instead of O(N).
    grouped_by_measure: dict[str, list[dict]] = {}
    for v in all_values:
        grouped_by_measure.setdefault(v["measure_id"], []).append(v)

    measure_ids = sorted(grouped_by_measure)

    measures_array: list[dict] = []
    for mid in measure_ids:
        mid_values = grouped_by_measure[mid]
        # Latest period is the primary display value.
        # Prefer period_start when populated; fall back to period_label (ISO date
        # strings like "2026-02-01" sort correctly as strings) for measures
        # without structured dates. Rows with period_label="unknown" are sorted
        # last regardless — the normalizer emits this fallback when the CSV
        # didn't provide a parseable period, and we should never let those
        # rows shadow real period data when picking "latest".
        latest = max(
            mid_values,
            key=lambda v: (
                v.get("period_label") != "unknown",
                v.get("period_start") or date.min,
                v.get("period_label") or "",
            ),
        )

        # Build trend (uses pre-grouped dict for O(1) per-measure lookup)
        trend, trend_valid, trend_count = _build_trend(all_values, mid, grouped_by_measure)

        # Resolve benchmarks from measure_benchmarks lookup (DEC-036).
        # National: (measure_id, "national", "US", period_label).
        # State: (measure_id, "state", provider_state, period_label).
        period_label = latest.get("period_label") or ""
        national_avg, national_avg_period = _resolve_benchmark(
            benchmark_lookup, mid, "national", "US", period_label,
            index=benchmark_index,
        )
        state_avg = None
        state_avg_period = None
        if provider_state:
            state_avg, state_avg_period = _resolve_benchmark(
                benchmark_lookup, mid, "state", provider_state, period_label,
                index=benchmark_index,
            )

        # Compute overlap_flag and ci_level at export time (DEC-029).
        ci_lower = latest.get("confidence_interval_lower")
        ci_upper = latest.get("confidence_interval_upper")
        ci_level = "95%" if (ci_lower is not None and ci_upper is not None) else None
        overlap_flag = _compute_overlap_flag(ci_lower, ci_upper, national_avg)

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
            "confidence_interval_lower": ci_lower,
            "confidence_interval_upper": ci_upper,
            "ci_source": latest.get("ci_source"),
            "prior_source": latest.get("prior_source"),
            "ci_level": ci_level,
            "overlap_flag": overlap_flag,
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
            "national_avg": national_avg,
            "national_avg_period": national_avg_period,
            "state_avg": state_avg,
            "state_avg_period": state_avg_period,
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
            # Staffing context (DEC-018)
            "reported_rn_hprd": provider.get("reported_rn_hprd"),
            "reported_total_hprd": provider.get("reported_total_hprd"),
            "adjusted_total_hprd": provider.get("adjusted_total_hprd"),
            "adjusted_rn_hprd": provider.get("adjusted_rn_hprd"),
            "casemix_total_hprd": provider.get("casemix_total_hprd"),
            "casemix_rn_hprd": provider.get("casemix_rn_hprd"),
            "weekend_rn_hprd": provider.get("weekend_rn_hprd"),
            "reported_aide_hprd": provider.get("reported_aide_hprd"),
            "reported_lpn_hprd": provider.get("reported_lpn_hprd"),
            "adjusted_aide_hprd": provider.get("adjusted_aide_hprd"),
            "adjusted_lpn_hprd": provider.get("adjusted_lpn_hprd"),
            "weekend_total_hprd": provider.get("weekend_total_hprd"),
            "pt_hprd": provider.get("pt_hprd"),
            "nursing_casemix_index": provider.get("nursing_casemix_index"),
            "total_turnover": provider.get("total_nursing_staff_turnover"),
            "rn_turnover": provider.get("rn_turnover"),
            "administrator_departures": provider.get("administrator_departures"),
            "total_weighted_health_survey_score": provider.get("total_weighted_health_survey_score"),
            "cycle_1_total_health_deficiencies": provider.get("cycle_1_total_health_deficiencies"),
            "cycle_1_health_deficiency_score": provider.get("cycle_1_health_deficiency_score"),
            "staffing_rating": None,
            # Staffing trend is built from archive vintages at export time
            # (not from DB — requires multi-vintage archive processing)
            "staffing_trend": None,
            # Standard survey dates from Rating Cycle fields in Provider Info.
            # Includes dates of inspections that may have found 0 deficiencies.
            "standard_survey_dates": None,  # populated from provider context
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

    # Load ownership (NH only), enriched with parent group when available.
    # Facility counts come from pre-computed dicts (passed by caller) instead
    # of per-provider subqueries — eliminates an N+1 over 16K NH providers.
    ownership = None
    if ptype == "NURSING_HOME" and "provider_ownership" in metadata.tables:
        po = metadata.tables["provider_ownership"]
        has_group_tables = (
            "ownership_entity_group_map" in metadata.tables
            and "ownership_parent_groups" in metadata.tables
        )

        if has_group_tables:
            oegm = metadata.tables["ownership_entity_group_map"]
            opg = metadata.tables["ownership_parent_groups"]
            join_from = (
                po.outerjoin(oegm, po.c.owner_name == oegm.c.entity_name)
                .outerjoin(opg, oegm.c.parent_group_id == opg.c.parent_group_id)
            )
            own_stmt = (
                sa.select(po, opg.c.parent_group_id, opg.c.parent_group_name)
                .select_from(join_from)
                .where(po.c.provider_id == provider_id)
                .order_by(po.c.role, po.c.owner_name)
            )
        else:
            own_stmt = (
                sa.select(po)
                .where(po.c.provider_id == provider_id)
                .order_by(po.c.role, po.c.owner_name)
            )

        own_rows = conn.execute(own_stmt).mappings().fetchall()

        entity_counts = entity_facility_counts or {}
        pg_counts = parent_group_facility_counts or {}

        ownership = []
        for row in own_rows:
            owner_name = row["owner_name"]
            pg_id = row.get("parent_group_id") if has_group_tables else None
            entry: dict[str, Any] = {
                "owner_name": owner_name,
                "owner_type": row.get("owner_type"),
                "role": row.get("role"),
                "ownership_percentage": row.get("ownership_percentage"),
                "ownership_percentage_not_provided": row.get("ownership_percentage_not_provided", False),
                "association_date": row.get("association_date"),
                "parent_group_id": pg_id,
                "parent_group_name": row.get("parent_group_name") if has_group_tables else None,
                "entity_facility_count": entity_counts.get(owner_name),
                "parent_group_facility_count": pg_counts.get(pg_id) if pg_id else None,
            }
            ownership.append(entry)

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


def build_ownership_entity_index(conn: Connection) -> dict[str, Any]:
    """Build the ownership_entity_index.json for filter-explore.

    Contains Organization-type entities only (not Individual, for privacy).
    Enriched with parent_group_id/parent_group_name when entity resolution
    tables exist. Also includes chain browsing data.

    Schema defined in json-export.md § Ownership Entity Index.
    """
    metadata = sa.MetaData()
    metadata.reflect(bind=conn.engine)

    po = metadata.tables["provider_ownership"]
    providers = metadata.tables["providers"]

    has_group_tables = (
        "ownership_entity_group_map" in metadata.tables
        and "ownership_parent_groups" in metadata.tables
    )

    # Build entity index: Organization-type only
    if has_group_tables:
        oegm = metadata.tables["ownership_entity_group_map"]
        opg = metadata.tables["ownership_parent_groups"]

        entity_stmt = (
            sa.select(
                po.c.owner_name,
                po.c.provider_id,
                po.c.role,
                po.c.association_date,
                po.c.ownership_percentage,
                po.c.ownership_percentage_not_provided,
                providers.c.state,
                opg.c.parent_group_id,
                opg.c.parent_group_name,
            )
            .select_from(
                po.join(providers, po.c.provider_id == providers.c.provider_id)
                .outerjoin(oegm, po.c.owner_name == oegm.c.entity_name)
                .outerjoin(opg, oegm.c.parent_group_id == opg.c.parent_group_id)
            )
            .where(po.c.owner_type == "Organization")
            .order_by(po.c.owner_name, po.c.provider_id)
        )
    else:
        entity_stmt = (
            sa.select(
                po.c.owner_name,
                po.c.provider_id,
                po.c.role,
                po.c.association_date,
                po.c.ownership_percentage,
                po.c.ownership_percentage_not_provided,
                providers.c.state,
            )
            .select_from(
                po.join(providers, po.c.provider_id == providers.c.provider_id)
            )
            .where(po.c.owner_type == "Organization")
            .order_by(po.c.owner_name, po.c.provider_id)
        )

    rows = conn.execute(entity_stmt).mappings().fetchall()

    # Aggregate per entity
    entity_data: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row["owner_name"]
        if name not in entity_data:
            entity_data[name] = {
                "entity_name": name,
                "roles": set(),
                "states": set(),
                "facilities": [],
                "parent_group_id": row.get("parent_group_id") if has_group_tables else None,
                "parent_group_name": row.get("parent_group_name") if has_group_tables else None,
            }

        entry = entity_data[name]
        if row.get("role"):
            entry["roles"].add(row["role"])
        if row.get("state"):
            entry["states"].add(row["state"])
        entry["facilities"].append({
            "provider_id": row["provider_id"],
            "role": row.get("role"),
            "association_date": row.get("association_date"),
            "ownership_percentage": row.get("ownership_percentage"),
            "ownership_percentage_not_provided": row.get("ownership_percentage_not_provided", False),
        })

    entities_list: list[dict[str, Any]] = []
    for entry in entity_data.values():
        entity_out: dict[str, Any] = {
            "entity_name": entry["entity_name"],
            "roles": sorted(entry["roles"]),
            "facility_count": len(entry["facilities"]),
            "states": sorted(entry["states"]),
            "facilities": entry["facilities"],
        }
        if entry.get("parent_group_id"):
            entity_out["parent_group_id"] = entry["parent_group_id"]
            entity_out["parent_group_name"] = entry["parent_group_name"]
        entities_list.append(entity_out)

    # Sort by facility count descending
    entities_list.sort(key=lambda e: -e["facility_count"])

    # Build chain index
    chain_stmt = (
        sa.select(
            providers.c.chain_id,
            providers.c.chain_name,
            providers.c.provider_id,
            providers.c.state,
        )
        .where(providers.c.provider_type == "NURSING_HOME")
        .where(providers.c.chain_id.isnot(None))
        .where(providers.c.chain_id != "")
        .order_by(providers.c.chain_id)
    )
    chain_rows = conn.execute(chain_stmt).mappings().fetchall()

    chain_data: dict[str, dict[str, Any]] = {}
    for row in chain_rows:
        cid = row["chain_id"]
        if cid not in chain_data:
            chain_data[cid] = {
                "chain_id": cid,
                "chain_name": row.get("chain_name"),
                "facilities": [],
                "states": set(),
            }
        chain_data[cid]["facilities"].append(row["provider_id"])
        if row.get("state"):
            chain_data[cid]["states"].add(row["state"])

    chains_list = [
        {
            "chain_id": c["chain_id"],
            "chain_name": c["chain_name"],
            "facility_count": len(c["facilities"]),
            "chain_avg_overall": None,
            "chain_avg_health_inspection": None,
            "chain_avg_staffing": None,
            "chain_avg_qm": None,
            "states": sorted(c["states"]),
            "facilities": c["facilities"],
        }
        for c in chain_data.values()
    ]
    chains_list.sort(key=lambda c: -c["facility_count"])

    return {
        "entities": entities_list,
        "chains": chains_list,
        "processing_date": date.today().isoformat(),
        "source_datasets": {
            "ownership": "y2hd-n93e",
            "provider_info": "4pq5-n9py",
        },
    }


def build_provider_directory(conn: Connection) -> list[dict[str, Any]]:
    """Build lightweight provider directory for client-side nearby search.

    Returns a list of directory entries with short keys for minimal file size.
    Hospitals get coordinates from ZCTA zip centroids; nursing homes use
    CMS-published latitude/longitude from the providers table.

    Schema per entry:
        id:  CCN
        n:   name
        c:   city (nullable)
        s:   state (nullable, 2-char)
        z:   zip (nullable, 5-char)
        t:   provider_type ("HOSPITAL" | "NURSING_HOME")
        lat: latitude (nullable)
        lon: longitude (nullable)
    """
    metadata = sa.MetaData()
    metadata.reflect(bind=conn.engine, only=["providers"])
    providers = metadata.tables["providers"]

    rows = conn.execute(
        sa.select(
            providers.c.provider_id,
            providers.c.name,
            providers.c.city,
            providers.c.state,
            providers.c.zip,
            providers.c.provider_type,
            providers.c.latitude,
            providers.c.longitude,
        )
        .where(providers.c.is_active == True)  # noqa: E712
        .order_by(providers.c.provider_id)
    ).mappings().fetchall()

    # Load ZCTA centroids for hospital zip-based coordinates
    zcta = _load_zcta_centroids()

    directory: list[dict[str, Any]] = []
    for row in rows:
        ptype = row["provider_type"]
        zip_code = row.get("zip")
        zip5 = zip_code[:5] if zip_code and len(zip_code) >= 5 else zip_code

        # Nursing homes: use CMS-published lat/lon.
        # Hospitals: use ZCTA zip centroid lookup.
        lat: float | None = None
        lon: float | None = None
        if ptype == "NURSING_HOME":
            db_lat = row.get("latitude")
            db_lon = row.get("longitude")
            if db_lat is not None and db_lon is not None:
                lat = float(db_lat)
                lon = float(db_lon)
        if lat is None and zip5 and zip5 in zcta:
            lat, lon = zcta[zip5]

        entry: dict[str, Any] = {
            "id": row["provider_id"],
            "n": row["name"],
            "c": row.get("city"),
            "s": row.get("state"),
            "z": zip5,
            "t": ptype,
            "lat": round(lat, 6) if lat is not None else None,
            "lon": round(lon, 6) if lon is not None else None,
        }
        directory.append(entry)

    logger.info("Built provider directory with %d entries", len(directory))
    return directory


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

        # Build all per-export lookups once and reuse across all providers.
        # This eliminates N+1 patterns that dominated runtime when each
        # build_provider_json call recomputed entity_facility_count subqueries.
        full_metadata = sa.MetaData()
        full_metadata.reflect(bind=conn.engine)

        benchmark_lookup = _load_benchmark_lookup(conn)
        benchmark_index = _build_benchmark_index(benchmark_lookup)
        logger.info(
            "Loaded %d benchmark rows / %d unique (measure,geo) keys",
            len(benchmark_lookup), len(benchmark_index),
        )

        entity_counts, pg_counts = _load_entity_facility_counts(conn)
        logger.info(
            "Loaded %d entity / %d parent group facility counts",
            len(entity_counts), len(pg_counts),
        )

        for pid in provider_ids:
            data = build_provider_json(
                conn, pid,
                benchmark_lookup=benchmark_lookup,
                metadata=full_metadata,
                entity_facility_counts=entity_counts,
                parent_group_facility_counts=pg_counts,
                benchmark_index=benchmark_index,
            )
            if data is None:
                continue

            filepath = output_path / f"{pid}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, default=_json_serial, ensure_ascii=False)

            count += 1
            if count % 500 == 0:
                logger.info("  Exported %d / %d providers", count, len(provider_ids))

        # Build ownership entity index (NH only)
        if "provider_ownership" in sa.MetaData().tables or True:
            try:
                entity_index = build_ownership_entity_index(conn)
                index_path = output_path / "ownership_entity_index.json"
                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(entity_index, f, default=_json_serial, ensure_ascii=False)
                logger.info("Wrote ownership_entity_index.json (%d entities, %d chains)",
                            len(entity_index.get("entities", [])),
                            len(entity_index.get("chains", [])))
            except Exception:
                logger.warning("Could not build ownership_entity_index.json "
                               "(tables may not exist yet)", exc_info=True)

        # Build provider directory for client-side nearby search
        try:
            directory = build_provider_directory(conn)
            dir_path = output_path / "provider_directory.json"
            with open(dir_path, "w", encoding="utf-8") as f:
                json.dump(directory, f, default=_json_serial, ensure_ascii=False)
            logger.info("Wrote provider_directory.json (%d entries)", len(directory))
        except Exception:
            logger.warning("Could not build provider_directory.json", exc_info=True)

        # Build per-state inspection severity averages (state-baseline context
        # for the InspectionSummary / CompareInspectionSummary panels). Same
        # 120-day clustering as the per-facility view.
        try:
            from scripts.export_state_inspection_averages import (
                write_state_inspection_averages,
            )
            write_state_inspection_averages(conn, output_path)
        except Exception:
            logger.warning(
                "Could not build state_inspection_averages.json "
                "(tables may not exist yet)", exc_info=True
            )

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
