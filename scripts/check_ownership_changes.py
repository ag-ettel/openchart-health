"""Detect nursing home ownership changes between two CMS archive vintages.

Compares the Ownership dataset (y2hd-n93e) across two archive snapshots and
emits a triaged report of facility-level ownership changes worth investigating.
Optionally verifies high-signal changes via Claude API web search.

Why two CSV vintages and not the database:
  `provider_ownership` upsert is destructive — when a row drops out of a CMS
  snapshot, the upsert layer doesn't track that. The CSV-to-CSV diff is the
  authoritative source for "what actually changed between snapshots".

What counts as a high-signal change:
  - **NEW operational control** — entity newly appears as OPERATIONAL/MANAGERIAL
    CONTROL or 5% DIRECT INTEREST. Strongest single acquisition signal.
  - **REMOVED operational control** — entity drops from those roles. Strongest
    divestiture signal.
  - **PERCENTAGE shift > 25pp** for direct or indirect ownership. Suggests a
    capital structure change without a formal handoff.

Lower-signal changes (also reported, but not prioritized for web search):
  - New/removed officers, directors, managing employees (high churn, low signal)
  - New 5% mortgage/security interests (financing changes, not control changes)

Usage:
    # Detect only (no web search)
    python scripts/check_ownership_changes.py --previous 2026-01 --current 2026-04

    # Detect + verify high-signal changes via Claude web search
    ANTHROPIC_API_KEY=sk-... \\
      python scripts/check_ownership_changes.py \\
        --previous 2026-01 --current 2026-04 --verify-web

    # Verify only, reading a saved detection report
    python scripts/check_ownership_changes.py --verify-existing report.json

Output:
    docs/ownership_changes_<from>_to_<to>.md  — human-readable report
    docs/ownership_changes_<from>_to_<to>.json — machine-readable detail
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Use the same csv_reader as the pipeline so we get identical normalization
sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline.ingest.csv_reader import discover_archives, read_csv_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — change classification
# ---------------------------------------------------------------------------

HIGH_SIGNAL_ROLES = frozenset({
    "OPERATIONAL/MANAGERIAL CONTROL",
    "5% OR GREATER DIRECT OWNERSHIP INTEREST",
    "5% OR GREATER INDIRECT OWNERSHIP INTEREST",
})

# Roles that turn over frequently and rarely indicate a real ownership change.
LOW_SIGNAL_ROLES = frozenset({
    "DIRECTOR",
    "OFFICER",
    "CORPORATE DIRECTOR",
    "CORPORATE OFFICER",
    "MANAGING EMPLOYEE",
    "W-2 MANAGING EMPLOYEE",
    "CONTRACTED MANAGING EMPLOYEE",
})

# Significance threshold for percentage shifts on the same (provider, owner, role)
PERCENTAGE_SHIFT_THRESHOLD = 25  # percentage points


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OwnershipKey:
    provider_id: str
    owner_name: str
    role: str


@dataclass
class ChangeRecord:
    provider_id: str
    facility_name: str | None
    facility_state: str | None
    change_type: str  # "ADDED" | "REMOVED" | "PERCENTAGE_SHIFT"
    role: str
    owner_name: str
    owner_type: str | None
    high_signal: bool
    previous_percentage: int | None = None
    current_percentage: int | None = None
    previous_association_date: str | None = None
    current_association_date: str | None = None
    parent_group_name: str | None = None
    verification: dict[str, Any] | None = None  # filled by web-search verifier

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "facility_name": self.facility_name,
            "facility_state": self.facility_state,
            "change_type": self.change_type,
            "role": self.role,
            "owner_name": self.owner_name,
            "owner_type": self.owner_type,
            "high_signal": self.high_signal,
            "previous_percentage": self.previous_percentage,
            "current_percentage": self.current_percentage,
            "previous_association_date": self.previous_association_date,
            "current_association_date": self.current_association_date,
            "parent_group_name": self.parent_group_name,
            "verification": self.verification,
        }


# ---------------------------------------------------------------------------
# Reading and indexing ownership data
# ---------------------------------------------------------------------------

def _parse_pct(raw: str) -> int | None:
    if not raw:
        return None
    cleaned = raw.strip().rstrip("%").strip()
    if not cleaned or cleaned.upper() in ("NOT APPLICABLE", "NO PERCENTAGE PROVIDED", "N/A"):
        return None
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return None


def _index_by_key(rows: list[dict[str, str]]) -> dict[OwnershipKey, dict[str, Any]]:
    """Index ownership rows by (provider_id, owner_name, role).

    Returns dict[key -> {percentage, owner_type, association_date_raw}].
    """
    index: dict[OwnershipKey, dict[str, Any]] = {}
    for r in rows:
        raw_pid = (r.get("facility_id") or "").strip()
        owner_name = (r.get("owner_name") or "").strip()
        role = (
            r.get("role_played_by_owner_or_manager_in_facility")
            or r.get("ownership_role")
            or r.get("role")
            or ""
        ).strip().upper()
        if not raw_pid or not owner_name or not role:
            continue
        provider_id = raw_pid.zfill(6)
        key = OwnershipKey(provider_id, owner_name, role)
        index[key] = {
            "percentage": _parse_pct(r.get("ownership_percentage", "")),
            "owner_type": (r.get("owner_type") or "").strip() or None,
            "association_date_raw": (r.get("association_date") or "").strip() or None,
        }
    return index


def _facility_metadata_from_provider_info(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Build a lookup of facility name and state keyed by provider_id."""
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        pid = (r.get("facility_id") or "").strip().zfill(6)
        if not pid:
            continue
        out[pid] = {
            "name": (r.get("facility_name") or "").strip(),
            "state": (r.get("state") or "").strip(),
        }
    return out


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def diff_ownership(
    previous: dict[OwnershipKey, dict[str, Any]],
    current: dict[OwnershipKey, dict[str, Any]],
    facility_meta: dict[str, dict[str, str]],
    parent_groups: dict[str, str] | None = None,
) -> list[ChangeRecord]:
    """Compare two indexed ownership snapshots and return change records."""
    parent_groups = parent_groups or {}
    changes: list[ChangeRecord] = []

    prev_keys = set(previous)
    curr_keys = set(current)

    added = curr_keys - prev_keys
    removed = prev_keys - curr_keys
    common = prev_keys & curr_keys

    for key in added:
        meta = current[key]
        fac = facility_meta.get(key.provider_id, {})
        changes.append(ChangeRecord(
            provider_id=key.provider_id,
            facility_name=fac.get("name"),
            facility_state=fac.get("state"),
            change_type="ADDED",
            role=key.role,
            owner_name=key.owner_name,
            owner_type=meta.get("owner_type"),
            high_signal=key.role in HIGH_SIGNAL_ROLES,
            current_percentage=meta.get("percentage"),
            current_association_date=meta.get("association_date_raw"),
            parent_group_name=parent_groups.get(key.owner_name),
        ))

    for key in removed:
        meta = previous[key]
        fac = facility_meta.get(key.provider_id, {})
        changes.append(ChangeRecord(
            provider_id=key.provider_id,
            facility_name=fac.get("name"),
            facility_state=fac.get("state"),
            change_type="REMOVED",
            role=key.role,
            owner_name=key.owner_name,
            owner_type=meta.get("owner_type"),
            high_signal=key.role in HIGH_SIGNAL_ROLES,
            previous_percentage=meta.get("percentage"),
            previous_association_date=meta.get("association_date_raw"),
            parent_group_name=parent_groups.get(key.owner_name),
        ))

    for key in common:
        prev_pct = previous[key].get("percentage")
        curr_pct = current[key].get("percentage")
        if prev_pct is None or curr_pct is None:
            continue
        if abs(curr_pct - prev_pct) < PERCENTAGE_SHIFT_THRESHOLD:
            continue
        fac = facility_meta.get(key.provider_id, {})
        changes.append(ChangeRecord(
            provider_id=key.provider_id,
            facility_name=fac.get("name"),
            facility_state=fac.get("state"),
            change_type="PERCENTAGE_SHIFT",
            role=key.role,
            owner_name=key.owner_name,
            owner_type=current[key].get("owner_type"),
            high_signal=key.role in HIGH_SIGNAL_ROLES,
            previous_percentage=prev_pct,
            current_percentage=curr_pct,
            previous_association_date=previous[key].get("association_date_raw"),
            current_association_date=current[key].get("association_date_raw"),
            parent_group_name=parent_groups.get(key.owner_name),
        ))

    return changes


# ---------------------------------------------------------------------------
# Per-facility roll-up
# ---------------------------------------------------------------------------

def roll_up_by_facility(changes: list[ChangeRecord]) -> dict[str, list[ChangeRecord]]:
    """Group changes by provider_id; sort each group with high_signal first."""
    by_facility: dict[str, list[ChangeRecord]] = defaultdict(list)
    for c in changes:
        by_facility[c.provider_id].append(c)
    for pid, recs in by_facility.items():
        recs.sort(key=lambda r: (not r.high_signal, r.change_type, r.role, r.owner_name))
    return by_facility


# ---------------------------------------------------------------------------
# Web search verification (optional)
# ---------------------------------------------------------------------------

def verify_via_web_search(
    facility_name: str,
    facility_state: str | None,
    owner_name: str,
    change_type: str,
    api_key: str,
    model: str = "claude-haiku-4-5-20251001",
) -> dict[str, Any]:
    """Use Claude API web search tool to look for confirmation of an ownership change.

    Returns a dict with:
      - confidence: "VERIFIED" | "PARTIAL" | "UNVERIFIED"
      - summary: short text from search result
      - sources: list of URLs cited

    Cost note: each call uses Anthropic's web_search tool (~$0.01/call). At 100
    high-signal changes per snapshot, that's ~$1/run. The verifier only runs
    on high_signal=True records and only when --verify-web is set.
    """
    try:
        import anthropic
    except ImportError:
        return {"confidence": "SKIPPED", "summary": "anthropic SDK not installed", "sources": []}

    client = anthropic.Anthropic(api_key=api_key)
    state_clause = f" in {facility_state}" if facility_state else ""
    direction = {
        "ADDED": "acquired",
        "REMOVED": "divested or sold",
        "PERCENTAGE_SHIFT": "ownership stake changed",
    }.get(change_type, "ownership change")

    query_prompt = (
        f"Search the web for recent news about whether {owner_name} {direction} "
        f"{facility_name}{state_clause}, a nursing home / skilled nursing facility. "
        f"Look for press releases, news articles, regulatory filings, or industry publications "
        f"from the past 18 months. "
        f"Reply with: (1) a single word — VERIFIED, PARTIAL, or UNVERIFIED — on the first line; "
        f"(2) a 1-sentence summary of what you found (or 'No corroborating news found.'); "
        f"(3) up to 3 source URLs, one per line, prefixed with 'SOURCE: '."
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=600,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            messages=[{"role": "user", "content": query_prompt}],
        )
    except Exception as e:
        return {"confidence": "ERROR", "summary": f"API call failed: {e}", "sources": []}

    # Extract the assistant's final text
    final_text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            final_text += block.text

    # Parse the response
    lines = [ln.strip() for ln in final_text.strip().splitlines() if ln.strip()]
    confidence = "UNVERIFIED"
    summary = ""
    sources: list[str] = []
    for ln in lines:
        upper = ln.upper()
        if upper in ("VERIFIED", "PARTIAL", "UNVERIFIED"):
            confidence = upper
        elif ln.upper().startswith("SOURCE:"):
            sources.append(ln.split(":", 1)[1].strip())
        else:
            summary += (" " if summary else "") + ln

    return {
        "confidence": confidence,
        "summary": summary[:500],
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _summarize_clusters(
    changes: list[ChangeRecord],
    min_size: int = 3,
) -> list[dict[str, Any]]:
    """Group high-signal changes by (entity or parent_group, change_type).

    A cluster is a group of changes touching the same entity (or, when
    available, the same resolved parent group) and all in the same direction
    (all ADDED or all REMOVED). Clusters spanning many facilities are
    near-certain M&A signals — Welltower REIT-style indirect-interest churn,
    a family trust restructuring, a chain acquisition, etc. This is the
    single highest-leverage thing to surface to a reviewer.

    `min_size` is the minimum facility count for a cluster to be reported.
    Default 3 strikes the right balance — 2-facility patterns are usually
    just two unrelated changes that happen to share a name.
    """
    grouped: dict[tuple[str, str, str], list[ChangeRecord]] = defaultdict(list)
    for c in changes:
        if not c.high_signal:
            continue
        # Prefer the parent group label so all entities under the same parent
        # group fold into one cluster. Fall back to the raw owner name.
        cluster_key = c.parent_group_name or c.owner_name
        grouped[(cluster_key, c.change_type, c.role)].append(c)

    clusters: list[dict[str, Any]] = []
    for (cluster_key, change_type, role), recs in grouped.items():
        if len(recs) < min_size:
            continue
        states = sorted({r.facility_state for r in recs if r.facility_state})
        clusters.append({
            "label": cluster_key,
            "change_type": change_type,
            "role": role,
            "facility_count": len({r.provider_id for r in recs}),
            "states": states,
            "sample_facilities": [
                {
                    "ccn": r.provider_id,
                    "name": r.facility_name,
                    "state": r.facility_state,
                    "owner": r.owner_name,
                }
                for r in recs[:5]
            ],
        })
    clusters.sort(key=lambda c: -c["facility_count"])
    return clusters


def write_markdown_report(
    changes: list[ChangeRecord],
    by_facility: dict[str, list[ChangeRecord]],
    previous_vintage: str,
    current_vintage: str,
    output_path: Path,
    min_cluster_size: int = 3,
) -> None:
    high_signal = [c for c in changes if c.high_signal]
    n_facilities_high = len({c.provider_id for c in high_signal})
    clusters = _summarize_clusters(changes, min_size=min_cluster_size)

    lines = [
        f"# Nursing home ownership changes: {previous_vintage} → {current_vintage}",
        "",
        f"_Generated {datetime.now().isoformat(timespec='minutes')}_",
        "",
        "## Summary",
        "",
        f"- **Total facility-level change records:** {len(changes):,}",
        f"- **High-signal changes** (operational control / 5% direct/indirect): {len(high_signal):,}",
        f"- **Facilities with at least one high-signal change:** {n_facilities_high:,}",
        f"- **Facilities with any change:** {len(by_facility):,}",
        f"- **Multi-facility clusters** (same entity/parent across 3+ facilities, same direction): {len(clusters):,}",
        "",
        "Roles considered high-signal: " + ", ".join(sorted(HIGH_SIGNAL_ROLES)),
        "",
        "## Multi-facility clusters",
        "",
        "Same entity (or resolved parent group) appearing across multiple facilities in",
        "the same direction. Real M&A and REIT restructurings concentrate here — start",
        "the review at the top of this list.",
        "",
    ]
    if not clusters:
        lines.append("_No multi-facility clusters detected._")
        lines.append("")
    else:
        lines.append("| Direction | Role | Entity / Parent Group | Facilities | States |")
        lines.append("|---|---|---|---|---|")
        for cl in clusters[:50]:
            states_label = ", ".join(cl["states"][:8])
            if len(cl["states"]) > 8:
                states_label += f" (+{len(cl['states']) - 8} more)"
            lines.append(
                f"| {cl['change_type']} | {cl['role']} | {cl['label']} | "
                f"{cl['facility_count']} | {states_label} |"
            )
        if len(clusters) > 50:
            lines.append(f"")
            lines.append(f"_... and {len(clusters) - 50} smaller clusters omitted._")
        lines.append("")

    lines.extend([
        "## High-signal changes (per facility)",
        "",
        "All facility-level high-signal changes, including those that didn't form clusters.",
        "",
    ])

    if not high_signal:
        lines.append("_No high-signal changes detected._")
        lines.append("")
    else:
        # Group high-signal changes by facility for narrative cohesion
        hs_by_facility: dict[str, list[ChangeRecord]] = defaultdict(list)
        for c in high_signal:
            hs_by_facility[c.provider_id].append(c)
        for pid in sorted(hs_by_facility):
            recs = hs_by_facility[pid]
            facility_label = recs[0].facility_name or pid
            state_label = f" ({recs[0].facility_state})" if recs[0].facility_state else ""
            lines.append(f"### {facility_label}{state_label} — CCN {pid}")
            lines.append("")
            lines.append("| Change | Role | Entity | Detail |")
            lines.append("|---|---|---|---|")
            for r in recs:
                detail_parts = []
                if r.previous_percentage is not None or r.current_percentage is not None:
                    detail_parts.append(
                        f"{r.previous_percentage if r.previous_percentage is not None else '-'}%"
                        f" → "
                        f"{r.current_percentage if r.current_percentage is not None else '-'}%"
                    )
                if r.current_association_date:
                    detail_parts.append(f"assoc {r.current_association_date}")
                if r.parent_group_name:
                    detail_parts.append(f"parent: {r.parent_group_name}")
                detail = "; ".join(detail_parts) or "-"
                lines.append(
                    f"| {r.change_type} | {r.role} | {r.owner_name} | {detail} |"
                )
            # Verification block, when present
            verified = [r for r in recs if r.verification]
            if verified:
                lines.append("")
                lines.append("**Web verification:**")
                for r in verified:
                    v = r.verification or {}
                    conf = v.get("confidence", "UNVERIFIED")
                    summary = v.get("summary", "")
                    sources = v.get("sources", []) or []
                    lines.append(f"- _{r.owner_name}_ — **{conf}**: {summary}")
                    for src in sources[:3]:
                        lines.append(f"  - {src}")
            lines.append("")

    lines.append("## Lower-signal changes (officers, directors, managing employees)")
    lines.append("")
    lower_signal = [c for c in changes if not c.high_signal]
    lines.append(
        f"_{len(lower_signal):,} records — typically high churn that does not "
        f"indicate ownership change. Surfaced here for reference only._"
    )
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote %s", output_path)


def write_json_report(
    changes: list[ChangeRecord],
    previous_vintage: str,
    current_vintage: str,
    output_path: Path,
) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(),
        "previous_vintage": previous_vintage,
        "current_vintage": current_vintage,
        "n_changes": len(changes),
        "n_high_signal": sum(1 for c in changes if c.high_signal),
        "changes": [c.to_dict() for c in changes],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_archive_ownership(
    data_dir: Path,
    vintage: str,
) -> tuple[dict[OwnershipKey, dict[str, Any]], dict[str, dict[str, str]]]:
    archives = [
        a for a in discover_archives(data_dir)
        if a.provider_type == "nursing_homes" and a.vintage_label == vintage
    ]
    if not archives:
        sys.exit(f"Archive not found for vintage {vintage} in {data_dir}")
    archive = archives[0]
    own_rows = read_csv_dataset(archive.path, "nh_ownership")
    info_rows = read_csv_dataset(archive.path, "nh_provider_info")
    return _index_by_key(own_rows), _facility_metadata_from_provider_info(info_rows)


def _load_parent_groups_from_db(db_url: str) -> dict[str, str]:
    """owner_name -> parent_group_name from the resolved entity tables.

    Returns empty dict when the resolution tables don't exist.
    """
    try:
        import sqlalchemy as sa
        engine = sa.create_engine(db_url)
        with engine.connect() as conn:
            insp = sa.inspect(engine)
            tables = set(insp.get_table_names())
            if "ownership_entity_group_map" not in tables or "ownership_parent_groups" not in tables:
                return {}
            rows = conn.execute(sa.text(
                "SELECT m.entity_name, g.parent_group_name "
                "FROM ownership_entity_group_map m "
                "JOIN ownership_parent_groups g ON m.parent_group_id = g.parent_group_id"
            )).fetchall()
            return {r.entity_name: r.parent_group_name for r in rows}
    except Exception as e:
        logger.warning("Could not load parent groups: %s", e)
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect NH ownership changes between two CMS archive vintages.")
    parser.add_argument("--previous", required=True, help="Previous vintage label, e.g. 2026-01")
    parser.add_argument("--current", required=True, help="Current vintage label, e.g. 2026-04")
    parser.add_argument("--data-dir", default="data", help="Path to data/ root containing archive zips")
    parser.add_argument("--db-url", default="postgresql+psycopg://postgres:postgres@localhost:5432/openchart",
                        help="DB URL for parent-group resolution lookup")
    parser.add_argument("--verify-web", action="store_true",
                        help="Verify high-signal changes via Claude API web search")
    parser.add_argument("--max-verify", type=int, default=50,
                        help="Cap on web-search verifications per run (cost control)")
    parser.add_argument("--min-cluster-size", type=int, default=3,
                        help="Minimum facility count for a multi-facility cluster to be reported")
    parser.add_argument("--output-dir", default="docs",
                        help="Directory for the markdown and JSON reports")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading previous vintage %s ...", args.previous)
    prev_index, prev_facility_meta = _load_archive_ownership(data_dir, args.previous)
    logger.info("  %d ownership rows from %s", len(prev_index), args.previous)

    logger.info("Loading current vintage %s ...", args.current)
    curr_index, curr_facility_meta = _load_archive_ownership(data_dir, args.current)
    logger.info("  %d ownership rows from %s", len(curr_index), args.current)

    facility_meta = {**prev_facility_meta, **curr_facility_meta}
    parent_groups = _load_parent_groups_from_db(args.db_url)
    logger.info("Loaded %d parent group mappings from DB", len(parent_groups))

    changes = diff_ownership(prev_index, curr_index, facility_meta, parent_groups)
    by_facility = roll_up_by_facility(changes)
    high_signal = [c for c in changes if c.high_signal]
    logger.info(
        "Detected %d total changes (%d high-signal) across %d facilities",
        len(changes), len(high_signal), len(by_facility),
    )

    if args.verify_web:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("--verify-web requires ANTHROPIC_API_KEY env var")
            return 2
        verify_targets = [c for c in high_signal if c.facility_name][: args.max_verify]
        logger.info("Running web search verification on %d records ...", len(verify_targets))
        for i, c in enumerate(verify_targets, 1):
            logger.info("  [%d/%d] %s — %s — %s",
                        i, len(verify_targets), c.facility_name, c.change_type, c.owner_name)
            c.verification = verify_via_web_search(
                c.facility_name or "",
                c.facility_state,
                c.owner_name,
                c.change_type,
                api_key,
            )

    md_path = output_dir / f"ownership_changes_{args.previous}_to_{args.current}.md"
    json_path = output_dir / f"ownership_changes_{args.previous}_to_{args.current}.json"
    write_markdown_report(
        changes, by_facility, args.previous, args.current, md_path,
        min_cluster_size=args.min_cluster_size,
    )
    write_json_report(changes, args.previous, args.current, json_path)

    print()
    print(f"Report: {md_path}")
    print(f"JSON:   {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
