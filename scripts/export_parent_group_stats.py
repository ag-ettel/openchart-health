"""Compute parent group aggregate stats and add to provider JSON exports.

Aggregations use the same 120-day clustering logic as the per-facility
InspectionSummary view: each facility's most recent inspection event is the
unit of comparison, where an "event" is a standard survey plus any follow-up
revisits or complaint inspections within 120 days.
"""

import json
from collections import defaultdict
from pathlib import Path

import sqlalchemy as sa

from pipeline.config import NH_MIN_RN_HPRD, NH_MIN_TOTAL_NURSE_HPRD
from pipeline.export.build_json import _json_serial

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"

# National averages — most recent inspection event per facility
# (computed across 15,129 facilities from CMS Health Deficiencies, Feb 2026)
NAT_AVG_PER_EVENT = {
    "ac": 0.17,
    "df": 7.44,
    "ghi": 0.31,
    "jkl": 0.24,
    "total": 8.15,
}
# 1,605 of 15,129 facilities had at least one J-L citation in their most recent
# inspection event (CMS Health Deficiencies, Feb 2026 snapshot).
NAT_PCT_FACILITIES_WITH_IJ_RECENT = 0.106

CLUSTER_WINDOW_DAYS = 120


def _severity_bucket(code: str | None) -> str | None:
    if not code:
        return None
    if code in "ABC":
        return "ac"
    if code in "DEF":
        return "df"
    if code in "GHI":
        return "ghi"
    if code in "JKL":
        return "jkl"
    return None


def _most_recent_event_per_facility(events: list[tuple]) -> dict[str, int]:
    """Given a list of (date, severity_code) for one facility, return the
    citation counts for the most recent inspection event (cluster of surveys
    within CLUSTER_WINDOW_DAYS of the most recent date)."""
    counts = {"ac": 0, "df": 0, "ghi": 0, "jkl": 0, "total": 0}
    if not events:
        return counts

    events_sorted = sorted(events, key=lambda x: x[0], reverse=True)
    most_recent_date = events_sorted[0][0]

    for d, code in events_sorted:
        if (most_recent_date - d).days > CLUSTER_WINDOW_DAYS:
            break
        b = _severity_bucket(code)
        if b is None:
            continue
        counts[b] += 1
        counts["total"] += 1
    return counts


def compute_inspection_aggregates(conn, provider_ids: list[str]) -> dict:
    """Aggregate most-recent-event citation counts across a set of facilities."""
    rows = conn.execute(
        sa.text(
            "SELECT provider_id, survey_date, scope_severity_code "
            "FROM provider_inspection_events "
            "WHERE provider_id = ANY(:pids) AND survey_date IS NOT NULL"
        ),
        {"pids": provider_ids},
    ).fetchall()

    by_provider = defaultdict(list)
    for pid, d, code in rows:
        if code:
            by_provider[pid].append((d, code))

    totals = {"ac": 0, "df": 0, "ghi": 0, "jkl": 0, "total": 0}
    n_with_ij = 0
    n_facs = 0

    for events in by_provider.values():
        if not events:
            continue
        n_facs += 1
        mr = _most_recent_event_per_facility(events)
        for k in totals:
            totals[k] += mr[k]
        if mr["jkl"] > 0:
            n_with_ij += 1

    if n_facs == 0:
        return {"facilities_with_inspections": 0}

    return {
        "facilities_with_inspections": n_facs,
        "avg_citations_per_event": totals["total"] / n_facs,
        "avg_jkl_per_event": totals["jkl"] / n_facs,
        "avg_ghi_per_event": totals["ghi"] / n_facs,
        "avg_df_per_event": totals["df"] / n_facs,
        "avg_ac_per_event": totals["ac"] / n_facs,
        "facilities_with_recent_ij": n_with_ij,
        "pct_facilities_with_recent_ij": n_with_ij / n_facs,
    }


def compute_parent_group_stats(conn, parent_group_id: str) -> dict:
    """Compute aggregate stats for a parent group."""
    fac_ids = conn.execute(
        sa.text(
            "SELECT DISTINCT po.provider_id "
            "FROM provider_ownership po "
            "JOIN ownership_entity_group_map oegm ON po.owner_name = oegm.entity_name "
            "WHERE oegm.parent_group_id = :pgid AND po.owner_type = 'Organization'"
        ),
        {"pgid": parent_group_id},
    ).fetchall()

    pids = [r[0] for r in fac_ids]
    if not pids:
        return {}

    name_row = conn.execute(
        sa.text(
            "SELECT parent_group_name FROM ownership_parent_groups WHERE parent_group_id = :pgid"
        ),
        {"pgid": parent_group_id},
    ).fetchone()

    # Provider-level aggregates: fines, penalties, SFF, abuse icon, beds, and
    # the share of group facilities reporting below the CMS minimum staffing
    # thresholds (NH_MIN_TOTAL_NURSE_HPRD, NH_MIN_RN_HPRD). Threshold-based
    # signals are more interpretable than raw HPRD averages because they map
    # to a CMS-defined floor (text-templates.md sub-type 2c).
    #
    # Denominator is facilities WITH reported staffing — facilities whose
    # reported_*_hprd is null (suppression / no PBJ submission) are excluded
    # from both numerator and denominator. Surfacing the denominator keeps
    # the percentage honest: a small group with mostly-null staffing data
    # would otherwise produce a misleading "0% below threshold."
    grp = conn.execute(
        sa.text(
            "SELECT "
            "  COUNT(*) as cnt, "
            "  AVG(total_amount_of_fines_dollars) as fines, "
            "  AVG(total_number_of_penalties) as penalties, "
            "  SUM(CASE WHEN is_special_focus_facility THEN 1 ELSE 0 END) as sff, "
            "  SUM(CASE WHEN is_abuse_icon THEN 1 ELSE 0 END) as abuse, "
            "  AVG(certified_beds) as beds, "
            "  COUNT(reported_total_hprd) as cnt_total_hprd, "
            "  SUM(CASE WHEN reported_total_hprd IS NOT NULL "
            "    AND reported_total_hprd < :tot_thr THEN 1 ELSE 0 END) as below_total, "
            "  COUNT(reported_rn_hprd) as cnt_rn_hprd, "
            "  SUM(CASE WHEN reported_rn_hprd IS NOT NULL "
            "    AND reported_rn_hprd < :rn_thr THEN 1 ELSE 0 END) as below_rn "
            "FROM providers "
            "WHERE provider_id = ANY(:pids) AND is_active = true"
        ),
        {
            "pids": pids,
            "tot_thr": NH_MIN_TOTAL_NURSE_HPRD,
            "rn_thr": NH_MIN_RN_HPRD,
        },
    ).fetchone()

    nat = conn.execute(
        sa.text(
            "SELECT "
            "  AVG(total_amount_of_fines_dollars) as fines, "
            "  AVG(total_number_of_penalties) as penalties, "
            "  SUM(CASE WHEN is_special_focus_facility THEN 1 ELSE 0 END)::float / COUNT(*) as sff_pct, "
            "  SUM(CASE WHEN is_abuse_icon THEN 1 ELSE 0 END)::float / COUNT(*) as abuse_pct, "
            "  SUM(CASE WHEN reported_total_hprd IS NOT NULL "
            "    AND reported_total_hprd < :tot_thr THEN 1 ELSE 0 END)::float "
            "    / NULLIF(COUNT(reported_total_hprd), 0) as below_total_pct, "
            "  SUM(CASE WHEN reported_rn_hprd IS NOT NULL "
            "    AND reported_rn_hprd < :rn_thr THEN 1 ELSE 0 END)::float "
            "    / NULLIF(COUNT(reported_rn_hprd), 0) as below_rn_pct "
            "FROM providers "
            "WHERE provider_type = 'NURSING_HOME' AND is_active = true"
        ),
        {
            "tot_thr": NH_MIN_TOTAL_NURSE_HPRD,
            "rn_thr": NH_MIN_RN_HPRD,
        },
    ).fetchone()

    # Inspection aggregates with 120-day clustering
    insp = compute_inspection_aggregates(conn, pids)

    return {
        "parent_group_id": parent_group_id,
        "parent_group_name": name_row[0] if name_row else parent_group_id,
        "facility_count": grp[0],
        # Inspection averages per most recent event
        "avg_citations_per_event": insp.get("avg_citations_per_event"),
        "avg_jkl_per_event": insp.get("avg_jkl_per_event"),
        "avg_ghi_per_event": insp.get("avg_ghi_per_event"),
        "avg_df_per_event": insp.get("avg_df_per_event"),
        "avg_ac_per_event": insp.get("avg_ac_per_event"),
        "facilities_with_recent_ij": insp.get("facilities_with_recent_ij"),
        "pct_facilities_with_recent_ij": insp.get("pct_facilities_with_recent_ij"),
        # National reference values
        "nat_avg_citations_per_event": NAT_AVG_PER_EVENT["total"],
        "nat_avg_jkl_per_event": NAT_AVG_PER_EVENT["jkl"],
        "nat_avg_ghi_per_event": NAT_AVG_PER_EVENT["ghi"],
        "nat_avg_df_per_event": NAT_AVG_PER_EVENT["df"],
        "nat_avg_ac_per_event": NAT_AVG_PER_EVENT["ac"],
        "nat_pct_facilities_with_recent_ij": NAT_PCT_FACILITIES_WITH_IJ_RECENT,
        # Provider-level aggregates
        "avg_fines": float(grp[1]) if grp[1] else None,
        "nat_avg_fines": float(nat[0]) if nat[0] else None,
        "avg_penalties": float(grp[2]) if grp[2] else None,
        "nat_avg_penalties": float(nat[1]) if nat[1] else None,
        "sff_count": grp[3],
        "abuse_icon_count": grp[4],
        "nat_pct_sff": float(nat[2]) if nat[2] else None,
        "nat_pct_abuse": float(nat[3]) if nat[3] else None,
        "avg_beds": float(grp[5]) if grp[5] else None,
        # Staffing threshold rollups (DEC-pending). Numerator = facilities
        # reporting below the CMS minimum HPRD; denominator = facilities with
        # a reported value (NULL-staffing facilities excluded).
        "facilities_with_reported_total_hprd": int(grp[6]) if grp[6] is not None else 0,
        "facilities_below_total_nurse_threshold": int(grp[7]) if grp[7] is not None else 0,
        "pct_below_total_nurse_threshold": (
            float(grp[7]) / float(grp[6]) if grp[6] else None
        ),
        "facilities_with_reported_rn_hprd": int(grp[8]) if grp[8] is not None else 0,
        "facilities_below_rn_threshold": int(grp[9]) if grp[9] is not None else 0,
        "pct_below_rn_threshold": (
            float(grp[9]) / float(grp[8]) if grp[8] else None
        ),
        "nat_pct_below_total_nurse_threshold": float(nat[4]) if nat[4] is not None else None,
        "nat_pct_below_rn_threshold": float(nat[5]) if nat[5] is not None else None,
        "min_total_nurse_hprd_threshold": NH_MIN_TOTAL_NURSE_HPRD,
        "min_rn_hprd_threshold": NH_MIN_RN_HPRD,
    }


def main() -> None:
    engine = sa.create_engine(DB_URL)

    with engine.connect() as conn:
        stats = compute_parent_group_stats(conn, "genesis")
        print(json.dumps(stats, indent=2, default=str))

        p = Path("build/data/015019.json")
        with open(p, encoding="utf-8") as f:
            data = json.load(f)

        pg_id = None
        for o in data.get("ownership", []):
            if o.get("parent_group_id"):
                pg_id = o["parent_group_id"]
                break

        if pg_id:
            data["parent_group_stats"] = compute_parent_group_stats(conn, pg_id)

        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, default=_json_serial, ensure_ascii=False)

        print(f"\nWrote parent_group_stats to {p}")

    engine.dispose()


if __name__ == "__main__":
    main()
