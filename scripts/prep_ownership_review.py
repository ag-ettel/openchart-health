"""
Prepare the ownership review workbook from clustering output.

Three outputs:
1. Auto-removes REITs/banks from clusters (modifies the main CSV)
2. Generates a global entity classification sheet (one row per entity across all clusters)
3. Generates a per-cluster decision batch sheet (grouped review items)

Usage:
    python scripts/prep_ownership_review.py

Inputs:  data/ownership_clusters_review.csv
         data/ownership_qa_data.json
Outputs: data/ownership_clusters_review.csv  (modified — REITs removed)
         data/review_entity_classifications.csv  (global entity sheet)
         data/review_cluster_decisions.csv  (per-cluster decision batches)
"""

from __future__ import annotations

import csv
import json
import logging
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Known REIT / financial entity patterns — auto-remove from operating clusters
REIT_BANK_PATTERNS = re.compile(
    r"\b(WELLTOWER|SABRA|OMEGA HEALTHCARE|VENTAS|HEALTHPEAK|"
    r"BANK OF AMERICA|TRUIST BANK|ZIONS BANK|CIBC BANK|"
    r"JPMORGAN|WELLS FARGO|FIFTH THIRD|REGIONS BANK|"
    r"NATIONAL HEALTH INVESTORS|MEDICAL PROPERTIES TRUST|"
    r"CARE TRUST|CARETRUST)\b",
    re.IGNORECASE,
)

# Broader patterns that suggest REIT/financial but need context
REIT_SUGGEST_PATTERNS = re.compile(
    r"\b(REALTY|REIT|MORTGAGE|BANCORP)\b",
    re.IGNORECASE,
)

LEGAL_SUFFIXES = re.compile(
    r"\b(LLC|INC|LP|LLP|CORP|CORPORATION|COMPANY|CO|LTD|LIMITED|"
    r"PARTNERSHIP|PARTNERS|HOLDINGS|HOLDING|GROUP|ENTERPRISES|"
    r"ASSOCIATES|ASSOCIATION|MANAGEMENT|MGMT|SERVICES|SVCS|"
    r"OPERATIONS|PROPERTIES|INVESTMENTS)\b",
    re.IGNORECASE,
)


def normalize(s: str) -> str:
    s = LEGAL_SUFFIXES.sub("", s.upper()).strip()
    s = re.sub(r"[.,\-/()&\"']+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def classify_entity(name: str, roles: str) -> str:
    """Auto-classify entity based on name and role patterns.

    Returns one of:
      REIT, BANK, OPERATOR, HOLDING_CO, MANAGEMENT_CO,
      FAMILY_TRUST, INVESTMENT_VEHICLE, (empty = needs human classification)
    """
    upper = name.upper()
    role_set = set(roles.split("|")) - {""}

    # Definite REIT
    if REIT_BANK_PATTERNS.search(name):
        if any(w in upper for w in ["BANK", "BANCORP", "TRUIST", "ZIONS", "CIBC",
                                     "JPMORGAN", "WELLS FARGO", "FIFTH THIRD", "REGIONS"]):
            return "BANK"
        return "REIT"

    # Probable REIT
    if REIT_SUGGEST_PATTERNS.search(name) and "OPERATOR" not in role_set:
        return "REIT"

    # Has OPERATOR role
    if "OPERATOR" in role_set:
        return "OPERATOR"

    # Family trust patterns
    trust_words = ["TRUST", "FAMILY TR", "FAM TR", "IRREV", "IRRV",
                   "REVOCABLE", "GRANTOR", "DYNASTY", "ESTATE",
                   "U/A/D", "U/W", "TTEE", "TRUSTEE"]
    if any(w in upper for w in trust_words):
        return "FAMILY_TRUST"

    # Management company
    if "MANAGEMENT" in upper or "MGMT" in upper or "CONSULTING" in upper:
        if "OPERATIONAL/MANAGERIAL CONTROL" in role_set or "OPERATOR" in role_set:
            return "MANAGEMENT_CO"

    # Investment vehicle
    invest_words = ["INVESTMENT", "INVESTOR", "CAPITAL", "FUND", "VENTURES",
                    "EQUITY", "PARTNERS LP", "ADVISORS"]
    if any(w in upper for w in invest_words):
        return "INVESTMENT_VEHICLE"

    # Holding company
    if "HOLDINGS" in upper or "HOLDCO" in upper or "HOLDING" in upper:
        return "HOLDING_CO"

    # Operating company (has DIRECT ownership, typical of facility-level LLCs)
    if "DIRECT" in role_set and len(role_set) <= 2:
        return "HOLDING_CO"

    return ""  # Needs human classification


def main() -> None:
    csv_path = Path("data/ownership_clusters_review.csv")
    qa_path = Path("data/ownership_qa_data.json")

    # Load data
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    logger.info("Loaded %d rows from clustering CSV", len(rows))

    with open(qa_path, encoding="utf-8") as f:
        qa_data = json.load(f)

    # Build cross-cluster edge lookup
    entity_cross: dict[str, list[dict]] = defaultdict(list)
    for e in qa_data["cross_cluster_edges"]:
        entity_cross[e["entity_name"]].append(e)

    # ---------------------------------------------------------------
    # Step 1: Auto-remove definite REITs/banks from clusters
    # ---------------------------------------------------------------
    auto_removed: list[dict] = []
    kept: list[dict] = []

    for row in rows:
        if REIT_BANK_PATTERNS.search(row["entity_name"]):
            auto_removed.append(row)
        else:
            kept.append(row)

    logger.info("Auto-removed %d REIT/bank entities from clusters", len(auto_removed))

    # Write back the cleaned CSV
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)
    logger.info("Wrote cleaned CSV with %d rows", len(kept))

    # ---------------------------------------------------------------
    # Step 2: Global entity classification sheet
    # ---------------------------------------------------------------
    # One row per unique entity across all clusters.
    # If an entity appears in cluster A and also has cross-links to B and C,
    # show all of them so the reviewer sees the full picture.

    entity_info: dict[str, dict] = {}
    for row in kept:
        name = row["entity_name"]
        if name not in entity_info:
            entity_info[name] = {
                "entity_name": name,
                "home_cluster_id": row["parent_group_id"],
                "home_cluster_name": row["parent_group_name"],
                "facility_count": int(row["facility_count"]),
                "roles": row.get("roles", ""),
                "match_method": row["match_method"],
                "match_confidence": row["match_confidence"],
                "cross_cluster_names": [],
                "max_cross_overlap": 0.0,
            }

        # Add cross-cluster info
        cross = entity_cross.get(name, [])
        other_names = set()
        max_overlap = 0.0
        for edge in cross:
            other_gid = (edge["other_cluster"]
                         if edge["home_cluster"] == row["parent_group_id"]
                         else edge["home_cluster"])
            other_name = qa_data["clusters"].get(other_gid, {}).get(
                "parent_group_name", other_gid
            )
            other_names.add(other_name)
            max_overlap = max(max_overlap, edge["overlap_ratio"])

        entity_info[name]["cross_cluster_names"] = sorted(other_names)
        entity_info[name]["max_cross_overlap"] = max_overlap

    # Auto-classify
    for info in entity_info.values():
        info["auto_classification"] = classify_entity(
            info["entity_name"], info["roles"]
        )

    # Determine review priority
    for info in entity_info.values():
        priority = "CONFIRMED"  # default: no action needed

        has_cross = len(info["cross_cluster_names"]) > 0
        has_classification = info["auto_classification"] != ""
        is_operator = info["auto_classification"] == "OPERATOR"

        if not has_classification and has_cross:
            priority = "HIGH"
        elif not has_classification:
            priority = "MEDIUM"
        elif has_cross and not is_operator:
            priority = "LOW"
        elif has_cross and is_operator:
            priority = "CONFIRMED"

        info["review_priority"] = priority

    # Sort: HIGH first, then MEDIUM, LOW, CONFIRMED
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "CONFIRMED": 3}
    sorted_entities = sorted(
        entity_info.values(),
        key=lambda x: (priority_order.get(x["review_priority"], 9), -x["facility_count"]),
    )

    # Write entity classification sheet
    ent_path = Path("data/review_entity_classifications.csv")
    with open(ent_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "review_priority",
            "entity_name",
            "home_cluster_name",
            "facility_count",
            "roles",
            "auto_classification",
            "YOUR_CLASSIFICATION",  # human fills this in
            "cross_clusters",
            "max_cross_overlap",
            "YOUR_ACTION",  # KEEP / REMOVE / MOVE_TO:xxx
            "YOUR_NOTES",
        ])

        for info in sorted_entities:
            cross_str = " | ".join(info["cross_cluster_names"]) if info["cross_cluster_names"] else ""
            cross_pct = f"{info['max_cross_overlap']:.0%}" if info["max_cross_overlap"] > 0 else ""
            writer.writerow([
                info["review_priority"],
                info["entity_name"],
                info["home_cluster_name"],
                info["facility_count"],
                info["roles"],
                info["auto_classification"],
                "",  # YOUR_CLASSIFICATION
                cross_str,
                cross_pct,
                "",  # YOUR_ACTION
                "",  # YOUR_NOTES
            ])

    counts = defaultdict(int)
    for info in sorted_entities:
        counts[info["review_priority"]] += 1

    logger.info("Wrote %s: %d entities", ent_path, len(sorted_entities))
    logger.info("  HIGH priority: %d (unclassified + cross-linked)", counts["HIGH"])
    logger.info("  MEDIUM priority: %d (unclassified, no cross-links)", counts["MEDIUM"])
    logger.info("  LOW priority: %d (auto-classified but cross-linked)", counts["LOW"])
    logger.info("  CONFIRMED: %d (auto-classified, no issues)", counts["CONFIRMED"])

    # ---------------------------------------------------------------
    # Step 3: Per-cluster decision batch sheet
    # ---------------------------------------------------------------
    # Groups entities within each cluster by auto_classification,
    # so the reviewer sees "these 8 are all HOLDING_COs — keep or remove as batch"

    batch_path = Path("data/review_cluster_decisions.csv")
    with open(batch_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "cluster_name",
            "cluster_id",
            "batch_classification",
            "batch_size",
            "entity_names",
            "facility_counts",
            "any_cross_linked",
            "BATCH_ACTION",  # human fills: KEEP_ALL / REMOVE_ALL / REVIEW_INDIVIDUALLY
        ])

        for gid, cluster in sorted(
            qa_data["clusters"].items(),
            key=lambda x: -max(m["facility_count"] for m in x[1]["members"]),
        ):
            # Group members by classification
            batches: dict[str, list[dict]] = defaultdict(list)
            for m in cluster["members"]:
                name = m["entity_name"]
                if name in entity_info:
                    cls = entity_info[name]["auto_classification"] or "UNCLASSIFIED"
                else:
                    cls = "AUTO_REMOVED"
                batches[cls].append(m)

            for cls, members in sorted(batches.items()):
                if cls == "AUTO_REMOVED":
                    continue
                names = [m["entity_name"] for m in sorted(members, key=lambda x: -x["facility_count"])]
                facs = [str(m["facility_count"]) for m in sorted(members, key=lambda x: -x["facility_count"])]
                any_cross = any(entity_cross.get(m["entity_name"]) for m in members)

                writer.writerow([
                    cluster["parent_group_name"],
                    gid,
                    cls,
                    len(members),
                    " | ".join(names[:10]) + ("..." if len(names) > 10 else ""),
                    " | ".join(facs[:10]) + ("..." if len(facs) > 10 else ""),
                    "YES" if any_cross else "",
                    "",  # BATCH_ACTION
                ])

    logger.info("Wrote %s", batch_path)
    logger.info("")
    logger.info("REVIEW WORKFLOW:")
    logger.info("  1. Open review_entity_classifications.csv in a spreadsheet")
    logger.info("  2. Work through HIGH priority rows first (~%d entities)", counts["HIGH"])
    logger.info("  3. Fill YOUR_CLASSIFICATION and YOUR_ACTION columns")
    logger.info("  4. When you classify an entity (e.g. WELLTOWER = REIT),")
    logger.info("     filter the sheet by entity name — it appears once,")
    logger.info("     and YOUR_ACTION applies everywhere it's clustered.")
    logger.info("  5. Use review_cluster_decisions.csv for batch decisions")
    logger.info("     (e.g. 'all HOLDING_COs in Genesis: KEEP_ALL')")


if __name__ == "__main__":
    main()
