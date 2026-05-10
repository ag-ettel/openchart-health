"""
Classify ownership parent groups by structural profile.

Applies deterministic rules to CMS-published entity names and role data
to produce a structural classification for each parent group. Rules are
transparent and publishable in /methodology.

Two outputs per parent group:
  - ownership_structure_type: composite label (e.g., "family_investment_layered")
  - structural_tags: array of individual signals detected

This does NOT classify entities as PE/non-PE. It describes the SHAPE of
the ownership structure using patterns in CMS-published data. A researcher
or journalist applies their own interpretation to the structural facts.

Decision logic (publishable in methodology):

  SIMPLE_OPERATOR
    Rule: <= 3 entities, all classified as OPERATOR.
    Meaning: single organization operates its own facilities.

  NONPROFIT_AFFILIATED
    Rule: any entity name contains a religious denomination, "nonprofit",
    "charitable", "foundation", "ministry", or "diocese".
    Meaning: ownership chain includes a nonprofit or religious organization.

  GOVERNMENT_AFFILIATED
    Rule: any entity name contains "hospital district", "county hospital",
    "hospital authority", "health district", or "state of" / "city of".
    Meaning: ownership chain includes a government entity.

  FAMILY_CONTROLLED
    Rule: at least one entity is classified as FAMILY_TRUST (name contains
    "trust", "family", "irrevocable", "revocable", "grantor", "dynasty",
    "estate", or similar legal trust language).
    Meaning: ownership chain includes family trust vehicles.

  INVESTMENT_FUND_PRESENCE
    Rule: any entity name contains institutional investment patterns:
    "opportunity fund", "capital partners", "growth partners",
    "equity holdings", "investors holdings", "fund LP/LLC",
    or "advisors LP". Excludes casual use of "ventures" or "investors"
    in family-owned LLCs (e.g., "TACK FAMILY VENTURES LLC" does not
    trigger this tag).
    Meaning: ownership chain includes entities with institutional
    investment fund naming conventions. This is a structural observation
    about entity names published by CMS, not a classification of
    investment strategy.

  LAYERED_HOLDING_STRUCTURE
    Rule: 5 or more entities classified as HOLDING_CO.
    Meaning: multiple layers of holding companies between the operating
    entity and ultimate owners.

  MULTI_ENTITY
    Rule: more than 10 entities in the parent group.
    Meaning: complex corporate family with many distinct legal entities.

  REIT_IN_CHAIN
    Rule: any entity name matches a known publicly traded healthcare REIT
    (Welltower, Sabra, Omega Healthcare, Ventas, Healthpeak, NHI,
    Medical Properties Trust, CareTrust).
    Meaning: a real estate investment trust owns property in this group's
    facilities. The REIT is a landlord, not an operator.

Composite type derivation:
  Tags are combined into a human-readable composite label using priority
  rules. The composite is a convenience label; the tag array is the
  authoritative structural data.

Usage:
    python scripts/classify_ownership_structures.py

Requires: data/review_entity_classifications.csv (from prep_ownership_review.py)
Outputs:  data/ownership_structure_profiles.csv
          Updates ownership_parent_groups.entity_type in database (if --write-db)
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structural detection rules
# ---------------------------------------------------------------------------

NONPROFIT_WORDS = frozenset([
    "NONPROFIT", "NON-PROFIT", "LUTHERAN", "METHODIST", "BAPTIST",
    "CATHOLIC", "PRESBYTERIAN", "ADVENTIST", "SAMARITAN", "MENNONITE",
    "CHURCH", "DIOCESE", "MINISTRY", "CHARITABLE", "FOUNDATION",
    "COVENANT", "QUAKER", "BRETHREN", "EVANGELICAL",
])

GOVERNMENT_WORDS = frozenset([
    "HOSPITAL DISTRICT", "COUNTY HOSPITAL", "HOSPITAL AUTHORITY",
    "HEALTH DISTRICT", "VETERANS", "STATE OF ", "CITY OF ",
    "COUNTY OF ", "TOWNSHIP", "MUNICIPALITY",
])

# Investment fund patterns — must be specific enough to avoid matching
# family-owned LLCs that use "Ventures" or "Investors" casually.
# "TACK FAMILY VENTURES LLC" is a family business, not an institutional fund.
# "COLUMBIA PACIFIC OPPORTUNITY FUND" is an institutional fund.
FUND_WORDS = frozenset([
    "OPPORTUNITY FUND",
    "CAPITAL PARTNERS",
    "GROWTH PARTNERS",
    "EQUITY HOLDINGS",
    "INVESTORS HOLDINGS",
    " FUND ",         # space-bounded to avoid "REFUND" etc.
    " FUND,",
    "FUND LP",
    "FUND LLC",
    "FUND L.P.",
    "ADVISORS LP",
    "ADVISORS, LP",
])

REIT_NAMES = frozenset([
    "WELLTOWER", "SABRA", "OMEGA HEALTHCARE", "VENTAS", "HEALTHPEAK",
    "NATIONAL HEALTH INVESTORS", "MEDICAL PROPERTIES TRUST", "CARETRUST",
])

TRUST_WORDS = frozenset([
    "TRUST", "FAMILY TR", "FAM TR", "IRREV", "IRRV",
    "REVOCABLE", "GRANTOR", "DYNASTY", "ESTATE",
    "U/A/D", "U/W", "TTEE", "TRUSTEE",
])


def classify_entity_type(name: str, roles: str) -> str:
    """Classify a single entity by its name and roles."""
    upper = name.upper()
    role_set = set(roles.split("|")) - {""}

    if "OPERATOR" in role_set or "OPERATIONAL/MANAGERIAL CONTROL" in role_set:
        return "OPERATOR"
    if any(w in upper for w in TRUST_WORDS):
        return "FAMILY_TRUST"
    if any(w in upper for w in ["HOLDINGS", "HOLDCO", "HOLDING"]):
        return "HOLDING_CO"
    if any(w in upper for w in FUND_WORDS):
        return "INVESTMENT_VEHICLE"
    if any(w in upper for w in ["MANAGEMENT", "MGMT", "CONSULTING"]):
        return "MANAGEMENT_CO"
    if "DIRECT" in role_set:
        return "HOLDING_CO"
    return "OTHER"


def detect_structural_tags(members: list[dict]) -> set[str]:
    """Apply deterministic rules to detect structural tags for a parent group."""
    tags: set[str] = set()
    names_upper = [m["entity_name"].upper() for m in members]
    all_text = " ".join(names_upper)

    # Count entity types
    type_counts = Counter(m.get("entity_type_local", "OTHER") for m in members)
    total = len(members)

    # Simple operator
    if total <= 3 and type_counts.get("OPERATOR", 0) >= total - 1:
        tags.add("SIMPLE_OPERATOR")

    # Multi-entity
    if total > 10:
        tags.add("MULTI_ENTITY")

    # Nonprofit
    if any(w in all_text for w in NONPROFIT_WORDS):
        tags.add("NONPROFIT_AFFILIATED")

    # Government
    if any(w in all_text for w in GOVERNMENT_WORDS):
        tags.add("GOVERNMENT_AFFILIATED")

    # Family controlled
    if type_counts.get("FAMILY_TRUST", 0) >= 1:
        tags.add("FAMILY_CONTROLLED")

    # Investment fund presence
    if any(w in all_text for w in FUND_WORDS):
        tags.add("INVESTMENT_FUND_PRESENCE")

    # Layered holding structure
    if type_counts.get("HOLDING_CO", 0) >= 5:
        tags.add("LAYERED_HOLDING_STRUCTURE")

    # REIT in chain
    if any(w in all_text for w in REIT_NAMES):
        tags.add("REIT_IN_CHAIN")

    return tags


def derive_composite_type(tags: set[str]) -> str:
    """Derive a human-readable composite type from structural tags.

    Priority-based: the most specific combination wins.
    """
    if "SIMPLE_OPERATOR" in tags:
        if "NONPROFIT_AFFILIATED" in tags:
            return "nonprofit_operator"
        if "GOVERNMENT_AFFILIATED" in tags:
            return "government_operator"
        return "independent_operator"

    parts: list[str] = []

    if "GOVERNMENT_AFFILIATED" in tags:
        return "government_affiliated"
    if "NONPROFIT_AFFILIATED" in tags:
        parts.append("nonprofit")

    if "FAMILY_CONTROLLED" in tags:
        parts.append("family")
    if "INVESTMENT_FUND_PRESENCE" in tags:
        parts.append("investment")
    if "LAYERED_HOLDING_STRUCTURE" in tags:
        parts.append("layered")
    if "REIT_IN_CHAIN" in tags:
        parts.append("reit_involved")

    if not parts:
        if "MULTI_ENTITY" in tags:
            return "multi_entity_operator"
        return "unclassified"

    return "_".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-db", action="store_true",
                        help="Update entity_type in ownership_parent_groups table")
    args = parser.parse_args()

    # Load entity data
    ent_path = Path("data/review_entity_classifications.csv")
    with open(ent_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    logger.info("Loaded %d entities", len(rows))

    # Group by cluster and classify
    clusters: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        r["entity_type_local"] = classify_entity_type(
            r["entity_name"], r.get("roles", "")
        )
        clusters[r["home_cluster_name"]].append(r)

    # Build profiles
    profiles: list[dict] = []
    for cluster_name, members in clusters.items():
        tags = detect_structural_tags(members)
        composite = derive_composite_type(tags)

        max_fac = max(int(m["facility_count"]) for m in members)
        type_counts = Counter(m["entity_type_local"] for m in members)

        profiles.append({
            "cluster_name": cluster_name,
            "entity_count": len(members),
            "max_facility_count": max_fac,
            "ownership_structure_type": composite,
            "structural_tags": "|".join(sorted(tags)),
            "entity_type_breakdown": "; ".join(
                f"{t}:{c}" for t, c in type_counts.most_common()
            ),
        })

    profiles.sort(key=lambda p: -p["max_facility_count"])

    # Write profiles
    out_path = Path("data/ownership_structure_profiles.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "cluster_name", "entity_count", "max_facility_count",
            "ownership_structure_type", "structural_tags", "entity_type_breakdown",
        ])
        writer.writeheader()
        writer.writerows(profiles)

    logger.info("Wrote %s: %d profiles", out_path, len(profiles))

    # Summary
    type_dist = Counter(p["ownership_structure_type"] for p in profiles)
    logger.info("")
    logger.info("OWNERSHIP STRUCTURE TYPE DISTRIBUTION:")
    for t, c in type_dist.most_common():
        logger.info("  %-40s %4d groups", t, c)

    # Write to database if requested
    if args.write_db:
        import sqlalchemy as sa
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"
        engine = sa.create_engine(DB_URL)
        metadata = sa.MetaData()

        with engine.begin() as conn:
            metadata.reflect(bind=engine, only=["ownership_parent_groups"])
            table = metadata.tables["ownership_parent_groups"]

            updated = 0
            for p in profiles:
                # Match by parent_group_name since we don't have the slug here
                conn.execute(
                    table.update()
                    .where(table.c.parent_group_name == p["cluster_name"])
                    .values(entity_type=p["ownership_structure_type"])
                )
                updated += 1

            logger.info("Updated entity_type for %d parent groups in database", updated)

        engine.dispose()


if __name__ == "__main__":
    main()
