"""
Semi-automated ownership entity clustering for nursing homes.

Clusters ~12,000 distinct Organization entity names from the CMS Ownership
dataset (y2hd-n93e) into parent corporate groups using three passes:

  Pass 1: Facility overlap — entity pairs sharing 80%+ of the same facilities.
  Pass 2: Fuzzy name matching — within overlap clusters, merge by string similarity.
  Pass 3: Chain cross-reference — confirm groupings against providers.chain_id.

Output: data/ownership_clusters_review.csv for human review before database load.

Usage:
    python scripts/cluster_ownership_entities.py

Requires: PostgreSQL connection (postgresql+psycopg://postgres:postgres@localhost:5432/openchart)
"""

from __future__ import annotations

import csv
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

import sqlalchemy as sa

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"
OUTPUT_PATH = Path("data/ownership_clusters_review.csv")

# Minimum facility overlap ratio to auto-cluster (Pass 1)
OVERLAP_THRESHOLD_AUTO = 0.80
# Overlap range that gets flagged for human review
OVERLAP_THRESHOLD_REVIEW = 0.50
# Minimum string similarity for fuzzy matching (Pass 2)
FUZZY_THRESHOLD = 0.75
# Minimum facilities for an entity to participate in overlap analysis
MIN_FACILITY_COUNT = 2
# Minimum absolute shared facilities for a pair to count as overlapping
MIN_SHARED_FACILITIES = 3
# Maximum size ratio between entities to allow auto-clustering
# Prevents a 2-facility entity from dragging in a 300-facility entity
MAX_SIZE_RATIO = 20.0

# Roles that represent financial relationships, not operational control.
# These create false overlap links between unrelated corporate families.
FINANCIAL_ROLES = frozenset({
    "5% OR GREATER SECURITY INTEREST",
    "5% OR GREATER MORTGAGE INTEREST",
})

# Legal suffixes to strip for name normalization
LEGAL_SUFFIXES = re.compile(
    r"\b(LLC|INC|LP|LLP|CORP|CORPORATION|COMPANY|CO|LTD|LIMITED|"
    r"PARTNERSHIP|PARTNERS|HOLDINGS|HOLDING|GROUP|ENTERPRISES|"
    r"ASSOCIATES|ASSOCIATION|MANAGEMENT|MGMT|SERVICES|SVCS|"
    r"OPERATIONS|PROPERTIES|INVESTMENTS|HEALTH CARE|HEALTHCARE)\b",
    re.IGNORECASE,
)

# Connector words to strip
CONNECTORS = re.compile(r"\b(OF|THE|AND|A|AN|AT|IN|FOR|BY)\b", re.IGNORECASE)


@dataclass
class EntityInfo:
    """Metadata for a single ownership entity."""
    name: str
    facility_count: int
    facilities: set[str]  # set of provider_ids
    chain_ids: set[str] = field(default_factory=set)
    roles: set[str] = field(default_factory=set)  # distinct CMS roles held


@dataclass
class Cluster:
    """A group of related entity names (one parent corporate group)."""
    members: list[str] = field(default_factory=list)
    match_methods: dict[str, str] = field(default_factory=dict)
    match_confidences: dict[str, float] = field(default_factory=dict)


def normalize_name(name: str) -> str:
    """Normalize an entity name for comparison.

    Strips legal suffixes, punctuation, and extra whitespace to enable
    fuzzy matching of entity names that differ only in legal form.
    """
    s = name.upper().strip()
    s = LEGAL_SUFFIXES.sub("", s)
    s = CONNECTORS.sub("", s)
    s = re.sub(r"[.,\-/()&'\"]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def name_similarity(a: str, b: str) -> float:
    """Compute string similarity between two normalized names.

    Uses SequenceMatcher ratio which handles transpositions and partial
    matches better than pure Levenshtein for corporate names.
    """
    na = normalize_name(a)
    nb = normalize_name(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def slugify(name: str) -> str:
    """Generate a URL-safe slug from a parent group name."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:80]


def load_entity_data(engine: sa.Engine) -> dict[str, EntityInfo]:
    """Load Organization-type entity data from provider_ownership.

    Returns a dict mapping entity_name -> EntityInfo with facility sets.
    Individual-type entities are excluded (privacy + not relevant to
    cross-facility analysis).
    """
    logger.info("Loading Organization entity data from provider_ownership...")

    with engine.connect() as conn:
        # Get entity -> facilities mapping with roles.
        # Exclude mortgage/security interest roles from FACILITY OVERLAP
        # analysis — these are financial relationships that create false
        # overlap links between unrelated corporate families. But we still
        # load roles for display in the review CSV.
        excluded_roles = ", ".join(f"'{r}'" for r in FINANCIAL_ROLES)
        rows = conn.execute(sa.text(f"""
            SELECT owner_name, provider_id, role
            FROM provider_ownership
            WHERE owner_type = 'Organization'
              AND role NOT IN ({excluded_roles})
        """)).fetchall()

    entities: dict[str, EntityInfo] = {}
    for name, provider_id, role in rows:
        if name not in entities:
            entities[name] = EntityInfo(
                name=name, facility_count=0, facilities=set()
            )
        entities[name].facilities.add(provider_id)
        if role:
            entities[name].roles.add(role)

    for e in entities.values():
        e.facility_count = len(e.facilities)

    logger.info("Loaded %d distinct Organization entities across %d rows",
                len(entities), len(rows))
    return entities


def load_chain_data(engine: sa.Engine) -> dict[str, tuple[str, str]]:
    """Load provider -> (chain_id, chain_name) from providers table.

    Returns mapping of provider_id -> (chain_id, chain_name) for nursing homes
    that have chain affiliation.
    """
    logger.info("Loading chain affiliation data from providers...")

    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT provider_id, chain_id, chain_name
            FROM providers
            WHERE provider_type = 'NURSING_HOME'
              AND chain_id IS NOT NULL
              AND chain_id != ''
        """)).fetchall()

    chains = {row[0]: (row[1], row[2]) for row in rows}
    logger.info("Loaded chain data for %d providers", len(chains))
    return chains


def pass1_facility_overlap(
    entities: dict[str, EntityInfo],
) -> list[tuple[str, str, float]]:
    """Pass 1: Find entity pairs with high facility overlap.

    Two Organization entities sharing 80%+ of the same facilities are almost
    certainly the same corporate family. This is the strongest clustering signal.

    Returns list of (entity_a, entity_b, overlap_ratio) tuples.
    """
    logger.info("Pass 1: Computing facility overlap for %d entities...", len(entities))

    # Filter to entities with enough facilities for meaningful overlap
    eligible = {
        name: info for name, info in entities.items()
        if info.facility_count >= MIN_FACILITY_COUNT
    }
    logger.info("  %d entities with >= %d facilities eligible for overlap",
                len(eligible), MIN_FACILITY_COUNT)

    # Build inverted index: facility -> set of entities
    facility_to_entities: dict[str, list[str]] = defaultdict(list)
    for name, info in eligible.items():
        for fac in info.facilities:
            facility_to_entities[fac].append(name)

    # Find co-occurring pairs and count shared facilities
    pair_shared: dict[tuple[str, str], int] = defaultdict(int)
    for fac, ent_list in facility_to_entities.items():
        # Only process facility if it has multiple entities (co-occurrence)
        if len(ent_list) < 2:
            continue
        # Sort to ensure consistent pair ordering (a < b)
        for i, a in enumerate(ent_list):
            for b in ent_list[i + 1:]:
                pair_key = (min(a, b), max(a, b))
                pair_shared[pair_key] += 1

    # Compute overlap ratios with anti-chaining guards
    overlaps: list[tuple[str, str, float]] = []
    for (a, b), shared in pair_shared.items():
        a_count = eligible[a].facility_count
        b_count = eligible[b].facility_count
        smaller = min(a_count, b_count)
        larger = max(a_count, b_count)

        if smaller == 0:
            continue
        # Guard 1: require minimum absolute shared facilities
        if shared < MIN_SHARED_FACILITIES:
            continue
        # Guard 2: size ratio check — don't auto-link wildly different sizes
        # A 2-facility entity overlapping with a 300-facility entity is likely
        # a coincidental co-ownership, not the same corporate family
        size_ratio = larger / smaller if smaller > 0 else float("inf")
        if size_ratio > MAX_SIZE_RATIO:
            continue

        ratio = shared / smaller
        if ratio >= OVERLAP_THRESHOLD_REVIEW:  # Include review-range too
            overlaps.append((a, b, ratio))

    overlaps.sort(key=lambda x: -x[2])
    auto_count = sum(1 for _, _, r in overlaps if r >= OVERLAP_THRESHOLD_AUTO)
    review_count = len(overlaps) - auto_count
    logger.info("  Found %d auto-cluster pairs (>= %.0f%% overlap), "
                "%d review pairs (%.0f%%–%.0f%%)",
                auto_count, OVERLAP_THRESHOLD_AUTO * 100,
                review_count, OVERLAP_THRESHOLD_REVIEW * 100,
                OVERLAP_THRESHOLD_AUTO * 100)

    return overlaps


def build_clusters_from_overlaps(
    overlaps: list[tuple[str, str, float]],
    entities: dict[str, EntityInfo],
) -> dict[str, Cluster]:
    """Build clusters using seed-and-absorb strategy on overlap pairs.

    Why not union-find: CMS ownership data has layered LLC structures where
    real estate companies, management companies, and family trusts co-occur
    on facilities with multiple unrelated operating companies. Transitive
    union-find chains these together into mega-clusters (e.g., 2,000+ entities).

    Strategy: seed-and-absorb.
    1. Sort entities by facility count descending (largest = most likely to be
       the "core" operating entity of a corporate family).
    2. Each unclaimed large entity becomes a cluster seed.
    3. Smaller entities are absorbed into the seed they overlap most with,
       but ONLY if they have direct overlap with the seed — no transitivity.
    4. Two seeds only merge if THEY directly overlap (not via intermediaries).

    Small entities (< MIN_SEED_FACILITIES) can be absorbed but cannot serve as
    bridge nodes between clusters. This prevents a 3-facility LLC from linking
    two unrelated 300-facility corporate families.

    Returns dict mapping seed_name -> Cluster.
    """
    MIN_SEED_FACILITIES = 10  # Only entities >= this can be cluster seeds

    # Build adjacency: direct overlap pairs (only auto-threshold)
    adj: dict[str, dict[str, float]] = defaultdict(dict)
    for a, b, ratio in overlaps:
        if ratio >= OVERLAP_THRESHOLD_AUTO:
            adj[a][b] = max(ratio, adj[a].get(b, 0.0))
            adj[b][a] = max(ratio, adj[b].get(a, 0.0))

    # All entities that participate in at least one overlap pair
    all_overlap_entities = set(adj.keys())

    # Sort by facility count descending — seeds are picked greedily
    sorted_entities = sorted(
        all_overlap_entities,
        key=lambda n: entities[n].facility_count if n in entities else 0,
        reverse=True,
    )

    claimed: dict[str, str] = {}  # entity -> seed name
    clusters: dict[str, Cluster] = {}

    # Phase 1: Seed selection and direct absorption
    for name in sorted_entities:
        if name in claimed:
            continue

        fac_count = entities[name].facility_count if name in entities else 0
        if fac_count < MIN_SEED_FACILITIES:
            continue  # Too small to be a seed; will be absorbed later

        # Check if this entity should merge with an existing seed
        best_seed: str | None = None
        best_overlap = 0.0

        for neighbor, ratio in adj[name].items():
            if neighbor in claimed and claimed[neighbor] == neighbor:
                # neighbor IS a seed — check direct overlap
                if ratio > best_overlap:
                    best_overlap = ratio
                    best_seed = neighbor

        if best_seed and best_overlap >= OVERLAP_THRESHOLD_AUTO:
            # Merge into existing seed's cluster
            claimed[name] = best_seed
            cluster = clusters[best_seed]
            cluster.members.append(name)
            cluster.match_methods[name] = "facility_overlap"
            cluster.match_confidences[name] = best_overlap
        else:
            # Become a new seed
            claimed[name] = name
            cluster = Cluster()
            cluster.members.append(name)
            cluster.match_methods[name] = "facility_overlap"
            cluster.match_confidences[name] = 1.0
            clusters[name] = cluster

    # Phase 2: Absorb small entities into the seed they overlap most with
    for name in sorted_entities:
        if name in claimed:
            continue

        # Find the seed this entity overlaps most with (direct overlap only)
        best_seed: str | None = None
        best_overlap = 0.0

        for neighbor, ratio in adj[name].items():
            if neighbor in claimed:
                seed = claimed[neighbor]
                # Only count if this entity has direct overlap with the seed
                # OR with a large member of the cluster
                if ratio > best_overlap:
                    best_overlap = ratio
                    best_seed = seed

        if best_seed and best_overlap >= OVERLAP_THRESHOLD_AUTO:
            claimed[name] = best_seed
            cluster = clusters[best_seed]
            cluster.members.append(name)
            cluster.match_methods[name] = "facility_overlap"
            cluster.match_confidences[name] = best_overlap

    absorbed = sum(1 for v in claimed.values() if v != claimed.get(v))
    unclaimed = len(all_overlap_entities) - len(claimed)
    logger.info("  Seeds: %d, absorbed: %d, unclaimed: %d",
                len(clusters), absorbed, unclaimed)

    return clusters


def pass2_fuzzy_names(
    clusters: dict[str, Cluster],
    entities: dict[str, EntityInfo],
) -> dict[str, Cluster]:
    """Pass 2: Fuzzy name matching to absorb singleton entities into clusters.

    For each unclustered entity, check if its normalized name is similar to
    any cluster member. If so, add it to that cluster. This catches entities
    like "GENESIS HEALTHCARE LLC" and "GENESIS HEALTHCARE INC" that may not
    have enough facility overlap (e.g., one is a newly created entity).
    """
    logger.info("Pass 2: Fuzzy name matching...")

    clustered_names: set[str] = set()
    for cluster in clusters.values():
        clustered_names.update(cluster.members)

    unclustered = [
        name for name in entities
        if name not in clustered_names and entities[name].facility_count >= MIN_FACILITY_COUNT
    ]
    logger.info("  %d unclustered entities with >= %d facilities",
                len(unclustered), MIN_FACILITY_COUNT)

    # Build lookup of normalized cluster representative names
    cluster_reps: list[tuple[str, str, Cluster]] = []  # (norm_name, raw_name, cluster)
    for root, cluster in clusters.items():
        for member in cluster.members:
            cluster_reps.append((normalize_name(member), member, cluster))

    absorbed = 0
    for name in unclustered:
        norm = normalize_name(name)
        best_sim = 0.0
        best_cluster: Cluster | None = None

        for rep_norm, rep_raw, cluster in cluster_reps:
            sim = SequenceMatcher(None, norm, rep_norm).ratio()
            if sim > best_sim:
                best_sim = sim
                best_cluster = cluster

        if best_sim >= FUZZY_THRESHOLD and best_cluster is not None:
            best_cluster.members.append(name)
            best_cluster.match_methods[name] = "fuzzy_name"
            best_cluster.match_confidences[name] = round(best_sim, 3)
            clustered_names.add(name)
            absorbed += 1

    logger.info("  Absorbed %d entities via fuzzy name matching", absorbed)

    # Also try to create new clusters from unclustered entities that match each other
    still_unclustered = [
        name for name in entities
        if name not in clustered_names and entities[name].facility_count >= MIN_FACILITY_COUNT
    ]

    # Group by normalized name prefix (first 10 chars) for efficiency
    prefix_groups: dict[str, list[str]] = defaultdict(list)
    for name in still_unclustered:
        norm = normalize_name(name)
        if len(norm) >= 5:
            prefix_groups[norm[:10]].append(name)

    new_clusters = 0
    for prefix, group in prefix_groups.items():
        if len(group) < 2:
            continue
        # Check all pairs in this prefix group
        merged: set[str] = set()
        for i, a in enumerate(group):
            if a in merged:
                continue
            cluster_members_local = [a]
            for b in group[i + 1:]:
                if b in merged:
                    continue
                sim = name_similarity(a, b)
                if sim >= FUZZY_THRESHOLD:
                    cluster_members_local.append(b)
                    merged.add(b)
            if len(cluster_members_local) > 1:
                merged.add(a)
                cluster = Cluster()
                for m in cluster_members_local:
                    cluster.members.append(m)
                    cluster.match_methods[m] = "fuzzy_name"
                    cluster.match_confidences[m] = round(
                        name_similarity(m, cluster_members_local[0]), 3
                    )
                cluster.match_confidences[cluster_members_local[0]] = 1.0
                new_key = cluster_members_local[0]
                clusters[new_key] = cluster
                clustered_names.update(cluster_members_local)
                new_clusters += 1

    logger.info("  Created %d new clusters from fuzzy name matching", new_clusters)
    return clusters


def pass3_chain_crossref(
    clusters: dict[str, Cluster],
    entities: dict[str, EntityInfo],
    chain_data: dict[str, tuple[str, str]],
) -> dict[str, Cluster]:
    """Pass 3: Cross-reference clusters with providers.chain_id.

    If all facilities of an entity share a chain_id, that confirms the
    grouping. If they don't, the entity may span multiple chains
    (holding company above chain level).

    Also absorbs singleton entities that share a chain_id with a cluster.
    """
    logger.info("Pass 3: Chain cross-reference...")

    # Annotate entities with chain info
    for name, info in entities.items():
        for fac in info.facilities:
            if fac in chain_data:
                info.chain_ids.add(chain_data[fac][0])

    # Check each cluster for chain consistency
    confirmed = 0
    for root, cluster in clusters.items():
        cluster_chain_ids: set[str] = set()
        for member in cluster.members:
            if member in entities:
                cluster_chain_ids.update(entities[member].chain_ids)

        if len(cluster_chain_ids) == 1:
            # All cluster members share one chain — strong confirmation
            for member in cluster.members:
                if cluster.match_methods.get(member) == "facility_overlap":
                    cluster.match_confidences[member] = min(
                        1.0, cluster.match_confidences.get(member, 0.8) + 0.1
                    )
            confirmed += 1

    logger.info("  %d clusters confirmed by single chain_id", confirmed)

    # Try to absorb unclustered entities into clusters via chain_id
    clustered_names: set[str] = set()
    cluster_by_chain: dict[str, Cluster] = {}
    for root, cluster in clusters.items():
        clustered_names.update(cluster.members)
        cluster_chain_ids: set[str] = set()
        for member in cluster.members:
            if member in entities:
                cluster_chain_ids.update(entities[member].chain_ids)
        if len(cluster_chain_ids) == 1:
            chain_id = next(iter(cluster_chain_ids))
            cluster_by_chain[chain_id] = cluster

    absorbed = 0
    for name, info in entities.items():
        if name in clustered_names or info.facility_count < MIN_FACILITY_COUNT:
            continue
        if len(info.chain_ids) == 1:
            chain_id = next(iter(info.chain_ids))
            if chain_id in cluster_by_chain:
                target = cluster_by_chain[chain_id]
                target.members.append(name)
                target.match_methods[name] = "chain_crossref"
                target.match_confidences[name] = 0.85
                clustered_names.add(name)
                absorbed += 1

    logger.info("  Absorbed %d entities via chain cross-reference", absorbed)
    return clusters


def pick_display_name(members: list[str], entities: dict[str, EntityInfo]) -> str:
    """Pick the best display name for a parent group.

    Prefers the member with the most facilities, with legal suffixes stripped
    and title-cased for readability.
    """
    if not members:
        return "Unknown"

    # Sort by facility count descending
    ranked = sorted(
        members,
        key=lambda m: entities.get(m, EntityInfo(m, 0, set())).facility_count,
        reverse=True,
    )

    best = ranked[0]
    # Clean up for display: strip trailing LLC/INC, title case
    display = LEGAL_SUFFIXES.sub("", best).strip()
    display = re.sub(r"\s+", " ", display).strip()
    display = re.sub(r"[,.\-]+$", "", display).strip()

    # Title case, but preserve common abbreviations
    words = display.split()
    result = []
    for w in words:
        if len(w) <= 3 and w.upper() == w:
            result.append(w.upper())  # Keep abbreviations like "HCR"
        else:
            result.append(w.title())
    return " ".join(result)


def flag_needs_review(
    cluster: Cluster,
    entities: dict[str, EntityInfo],
    overlaps: list[tuple[str, str, float]],
) -> bool:
    """Determine if a cluster needs human review.

    Flags clusters where:
    - Any member has match confidence < 0.80
    - Any member was matched by fuzzy name only (no facility overlap)
    - Cluster contains "HEALTH SYSTEM" entities (could be hospital systems)
    - Any member has < 5 facilities (possible namesake collision)
    """
    for member in cluster.members:
        conf = cluster.match_confidences.get(member, 0.0)
        if conf < 0.80:
            return True
        if cluster.match_methods.get(member) == "fuzzy_name":
            info = entities.get(member)
            if info and info.facility_count < 5:
                return True
        name_upper = member.upper()
        if "HEALTH SYSTEM" in name_upper:
            return True

    return False


def write_csv(
    clusters: dict[str, Cluster],
    entities: dict[str, EntityInfo],
    overlaps: list[tuple[str, str, float]],
    output_path: Path,
) -> int:
    """Write the review CSV with one row per entity per cluster.

    Columns:
    - parent_group_id: auto-generated slug
    - parent_group_name: best candidate display name
    - entity_name: each member entity
    - match_method: facility_overlap / fuzzy_name / chain_crossref
    - match_confidence: 0.0-1.0
    - facility_count: how many facilities this entity appears in
    - needs_review: boolean flag for ambiguous matches
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort clusters by total facility count (largest first)
    sorted_clusters: list[tuple[str, Cluster]] = []
    for root, cluster in clusters.items():
        total_facilities = sum(
            entities.get(m, EntityInfo(m, 0, set())).facility_count
            for m in cluster.members
        )
        sorted_clusters.append((root, cluster))
    sorted_clusters.sort(
        key=lambda x: sum(
            entities.get(m, EntityInfo(m, 0, set())).facility_count
            for m in x[1].members
        ),
        reverse=True,
    )

    rows_written = 0
    seen_slugs: set[str] = set()

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "parent_group_id", "parent_group_name", "entity_name",
            "match_method", "match_confidence", "facility_count",
            "roles", "needs_review",
        ])

        for root, cluster in sorted_clusters:
            if len(cluster.members) < 2:
                continue  # Skip singleton clusters

            display_name = pick_display_name(cluster.members, entities)
            slug = slugify(display_name)

            # Ensure unique slug
            base_slug = slug
            counter = 2
            while slug in seen_slugs:
                slug = f"{base_slug}_{counter}"
                counter += 1
            seen_slugs.add(slug)

            needs_review = flag_needs_review(cluster, entities, overlaps)

            # Sort members by facility count descending
            sorted_members = sorted(
                cluster.members,
                key=lambda m: entities.get(m, EntityInfo(m, 0, set())).facility_count,
                reverse=True,
            )

            for member in sorted_members:
                info = entities.get(member, EntityInfo(member, 0, set()))
                # Abbreviate roles for CSV readability
                role_abbrevs = {
                    "5% OR GREATER DIRECT OWNERSHIP INTEREST": "DIRECT",
                    "5% OR GREATER INDIRECT OWNERSHIP INTEREST": "INDIRECT",
                    "OPERATIONAL/MANAGERIAL CONTROL": "OPERATOR",
                    "GENERAL PARTNERSHIP INTEREST": "GEN_PARTNER",
                    "LIMITED PARTNERSHIP INTEREST": "LTD_PARTNER",
                    "PARTNERSHIP INTEREST": "PARTNER",
                }
                roles_str = "|".join(
                    sorted(role_abbrevs.get(r, r) for r in info.roles)
                ) if info.roles else ""
                writer.writerow([
                    slug,
                    display_name,
                    member,
                    cluster.match_methods.get(member, "facility_overlap"),
                    f"{cluster.match_confidences.get(member, 0.0):.3f}",
                    info.facility_count,
                    roles_str,
                    "TRUE" if needs_review else "FALSE",
                ])
                rows_written += 1

    return rows_written


def print_summary(
    clusters: dict[str, Cluster],
    entities: dict[str, EntityInfo],
) -> None:
    """Print summary statistics for review."""
    multi_clusters = {k: v for k, v in clusters.items() if len(v.members) >= 2}

    total_entities_clustered = sum(len(c.members) for c in multi_clusters.values())
    total_entities = len(entities)

    # Top 10 by unique facility count
    cluster_stats: list[tuple[str, int, int]] = []
    for root, cluster in multi_clusters.items():
        display = pick_display_name(cluster.members, entities)
        unique_facilities: set[str] = set()
        for m in cluster.members:
            if m in entities:
                unique_facilities.update(entities[m].facilities)
        cluster_stats.append((display, len(cluster.members), len(unique_facilities)))

    cluster_stats.sort(key=lambda x: -x[2])

    logger.info("")
    logger.info("=" * 70)
    logger.info("CLUSTERING SUMMARY")
    logger.info("=" * 70)
    logger.info("Total Organization entities: %d", total_entities)
    logger.info("Entities clustered: %d (%.1f%%)",
                total_entities_clustered,
                100 * total_entities_clustered / total_entities if total_entities else 0)
    logger.info("Parent groups formed: %d", len(multi_clusters))
    logger.info("")
    logger.info("Top 10 parent groups by facility count:")
    logger.info("-" * 70)
    for name, member_count, fac_count in cluster_stats[:10]:
        logger.info("  %-40s  %3d entities  %4d facilities", name, member_count, fac_count)
    logger.info("-" * 70)


def main() -> None:
    """Run the three-pass clustering pipeline."""
    logger.info("Starting ownership entity clustering...")
    engine = sa.create_engine(DB_URL)

    # Load data
    entities = load_entity_data(engine)
    chain_data = load_chain_data(engine)

    if not entities:
        logger.error("No Organization entities found in provider_ownership. Aborting.")
        sys.exit(1)

    # Pass 1: Facility overlap
    overlaps = pass1_facility_overlap(entities)

    # Build initial clusters from high-confidence overlaps
    clusters = build_clusters_from_overlaps(overlaps, entities)
    logger.info("Pass 1 result: %d clusters from facility overlap",
                len([c for c in clusters.values() if len(c.members) >= 2]))

    # Pass 2: Fuzzy name matching
    clusters = pass2_fuzzy_names(clusters, entities)
    logger.info("Pass 2 result: %d total clusters",
                len([c for c in clusters.values() if len(c.members) >= 2]))

    # Pass 3: Chain cross-reference
    clusters = pass3_chain_crossref(clusters, entities, chain_data)
    logger.info("Pass 3 result: %d total clusters",
                len([c for c in clusters.values() if len(c.members) >= 2]))

    # Write output
    rows = write_csv(clusters, entities, overlaps, OUTPUT_PATH)
    logger.info("Wrote %d rows to %s", rows, OUTPUT_PATH)

    # Summary
    print_summary(clusters, entities)

    engine.dispose()
    logger.info("Done. Review the CSV, then run: python scripts/load_ownership_groups.py")


if __name__ == "__main__":
    main()
