"""
Build QA review data JSON for the ownership entity resolution review tool.

Reads the clustering CSV and computes:
1. Per-cluster facility overlap matrices (top 15 members)
2. Cross-cluster edges (entities with high overlap to multiple clusters)

Output: data/ownership_qa_data.json (consumed by data/ownership_qa_review.html)

Usage:
    python scripts/build_qa_data.py
"""

from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict

import sqlalchemy as sa

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/openchart"


def main() -> None:
    # Load CSV
    with open("data/ownership_clusters_review.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    logger.info("Loaded %d rows from CSV", len(rows))

    # Build cluster data
    clusters: dict[str, dict] = {}
    for r in rows:
        gid = r["parent_group_id"]
        if gid not in clusters:
            clusters[gid] = {
                "parent_group_id": gid,
                "parent_group_name": r["parent_group_name"],
                "members": [],
            }
        clusters[gid]["members"].append({
            "entity_name": r["entity_name"],
            "match_method": r["match_method"],
            "match_confidence": float(r["match_confidence"]),
            "facility_count": int(r["facility_count"]),
            "roles": r.get("roles", ""),
            "needs_review": r["needs_review"] == "TRUE",
        })

    # Load entity facilities from DB
    logger.info("Loading entity facility data from database...")
    engine = sa.create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(sa.text("""
            SELECT owner_name, provider_id
            FROM provider_ownership
            WHERE owner_type = 'Organization'
        """)).fetchall()

    entity_facilities: dict[str, set[str]] = defaultdict(set)
    for name, pid in result:
        entity_facilities[name].add(pid)

    engine.dispose()
    logger.info("Loaded facility data for %d entities", len(entity_facilities))

    # Entity -> cluster mapping
    entity_to_cluster: dict[str, str] = {}
    for r in rows:
        entity_to_cluster[r["entity_name"]] = r["parent_group_id"]

    # Cluster seeds (entity with most facilities per cluster)
    cluster_seeds: dict[str, str] = {}
    for gid, c in clusters.items():
        seed = max(c["members"], key=lambda m: m["facility_count"])
        cluster_seeds[gid] = seed["entity_name"]

    # Cross-cluster edges
    logger.info("Computing cross-cluster edges...")
    cross_cluster_edges: list[dict] = []
    clustered_entities = set(entity_to_cluster.keys())

    for entity_name in clustered_entities:
        home_cluster = entity_to_cluster[entity_name]
        e_facs = entity_facilities.get(entity_name, set())
        if not e_facs:
            continue

        for other_gid, seed_name in cluster_seeds.items():
            if other_gid == home_cluster:
                continue
            seed_facs = entity_facilities.get(seed_name, set())
            if not seed_facs:
                continue
            shared = len(e_facs & seed_facs)
            smaller = min(len(e_facs), len(seed_facs))
            if smaller == 0:
                continue
            overlap = shared / smaller
            if overlap >= 0.5 and shared >= 3:
                cross_cluster_edges.append({
                    "entity_name": entity_name,
                    "home_cluster": home_cluster,
                    "other_cluster": other_gid,
                    "overlap_ratio": round(overlap, 3),
                    "shared_facilities": shared,
                })

    logger.info("Found %d cross-cluster edges across %d entities",
                len(cross_cluster_edges),
                len(set(e["entity_name"] for e in cross_cluster_edges)))

    # Per-cluster overlap matrices (top 15 members)
    logger.info("Computing overlap matrices...")
    cluster_overlaps: dict[str, dict] = {}
    for gid, c in clusters.items():
        members = sorted(c["members"], key=lambda m: -m["facility_count"])[:15]
        names = [m["entity_name"] for m in members]
        matrix: list[list[float]] = []
        for a in names:
            row_data: list[float] = []
            a_facs = entity_facilities.get(a, set())
            for b in names:
                b_facs = entity_facilities.get(b, set())
                if not a_facs or not b_facs:
                    row_data.append(0.0)
                else:
                    shared = len(a_facs & b_facs)
                    smaller = min(len(a_facs), len(b_facs))
                    row_data.append(round(shared / smaller, 3) if smaller > 0 else 0.0)
            matrix.append(row_data)
        cluster_overlaps[gid] = {
            "names": names,
            "matrix": matrix,
        }

    output = {
        "clusters": clusters,
        "cross_cluster_edges": cross_cluster_edges,
        "cluster_overlaps": cluster_overlaps,
        "stats": {
            "total_clusters": len(clusters),
            "total_entities": len(rows),
            "cross_cluster_edge_count": len(cross_cluster_edges),
            "entities_with_cross_edges": len(set(e["entity_name"] for e in cross_cluster_edges)),
        },
    }

    with open("data/ownership_qa_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    logger.info("Wrote data/ownership_qa_data.json")
    logger.info("  Clusters: %d", len(clusters))
    logger.info("  Cross-cluster edges: %d", len(cross_cluster_edges))
    logger.info("  Entities with cross-edges: %d",
                len(set(e["entity_name"] for e in cross_cluster_edges)))


if __name__ == "__main__":
    main()
