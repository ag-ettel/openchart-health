# Nursing Home Ownership Entity Resolution

## Problem

CMS publishes nursing home ownership data with entity names as free-text strings.
The same corporate family operates through dozens of distinct legal entities:

- "GENESIS HEALTHCARE LLC" — 324 facilities
- "GENESIS HEALTHCARE INC" — 317 facilities
- "GENESIS HOLDINGS LLC" — 290 facilities
- "SENIOR CARE GENESIS LLC" — 289 facilities
- "GENESIS OPERATIONS LLC" — 116 facilities
- ... 28 more Genesis-related entities

These are the same corporate family but CMS treats them as unrelated strings.
Researchers and consumers cannot answer "how many facilities does Genesis operate?"
without manually resolving entity names to parent groups.

This is high-value curation that makes the researcher subscription defensible.

## Current Data

| Table | Rows | Source |
|---|---|---|
| `provider_ownership` | 378,567 | CMS Ownership dataset (y2hd-n93e) |
| Organization-type records | 81,531 | Entities eligible for cross-facility analysis |
| Individual-type records | 297,036 | Per-provider only (privacy) |
| Distinct entity names (Org) | ~12,000 | Estimated from unique owner_name values |
| Facilities with ownership data | 15,154 | |
| Monthly snapshots available | 82 | 2019-2026, for ownership change detection |

15 distinct roles observed: direct/indirect ownership, mortgage/security interests,
general/limited partnerships, operational/managerial control, managing employees,
corporate officers/directors.

## Feature: Parent Group Resolution

### Schema

New reference table: `ownership_parent_groups`

```
ownership_parent_groups
├── id UUID PK
├── parent_group_id varchar unique (e.g., "genesis_healthcare")
├── parent_group_name varchar (display: "Genesis Healthcare")
├── entity_type varchar (e.g., "chain_operator", "pe_backed", "nonprofit_system")
├── notes text null (human reviewer notes)
├── review_status varchar ("auto_matched", "human_verified", "disputed")
├── created_at timestamptz
└── updated_at timestamptz
```

New mapping table: `ownership_entity_group_map`

```
ownership_entity_group_map
├── id UUID PK
├── entity_name varchar (exact match to provider_ownership.owner_name)
├── parent_group_id varchar FK ownership_parent_groups
├── match_method varchar ("exact", "fuzzy", "facility_overlap", "manual")
├── match_confidence decimal(3,2) (0.00-1.00)
├── reviewed_by varchar null
├── created_at timestamptz
└── updated_at timestamptz
```

### Clustering Algorithm (Semi-Automated First Pass)

**Step 1: Facility overlap clustering.**
Two Organization entities that share 80%+ of the same facilities are almost
certainly the same corporate family. This is the strongest signal.

```sql
-- Find entity pairs with high facility overlap
SELECT a.owner_name, b.owner_name,
       COUNT(DISTINCT a.provider_id) AS shared_facilities,
       COUNT(DISTINCT a.provider_id)::float /
         LEAST(a_total, b_total) AS overlap_ratio
FROM provider_ownership a
JOIN provider_ownership b ON a.provider_id = b.provider_id
  AND a.owner_name < b.owner_name
WHERE a.owner_type = 'Organization' AND b.owner_type = 'Organization'
GROUP BY a.owner_name, b.owner_name, a_total, b_total
HAVING overlap_ratio > 0.8
```

**Step 2: Fuzzy name matching within clusters.**
Within facility-overlap clusters, use string similarity (trigram, Levenshtein)
to confirm related entities. "GENESIS HEALTHCARE LLC" and "GENESIS HEALTHCARE INC"
have high string similarity AND high facility overlap — strong match.

**Step 3: Chain affiliation cross-reference.**
The `providers.chain_id` and `providers.chain_name` from Provider Info provide a
CMS-published grouping signal. If all facilities of entity X share the same
chain_id, that confirms the cluster. If they don't, the entity may span multiple
chains (holding company above chain level).

**Step 4: Human review.**
Flag clusters for review where:
- Overlap ratio is 0.5-0.8 (ambiguous)
- Name similarity is low but facility overlap is high (different brand, same parent)
- Small entities (< 5 facilities) that could be unrelated namesakes
- Entities with "HEALTH SYSTEM" in the name (could be hospital systems)

### Ownership Change Detection (From Monthly Snapshots)

We have 82 monthly NH snapshots (2019-2026). The `provider_ownership` table
currently stores the latest snapshot. To detect changes:

**Option A: Diff at query time.**
Load a second snapshot's ownership data into a temp table, compare against
current. Entities present in month N but absent in N-1 = new ownership.
Entities absent in N but present in N-1 = divestiture.

**Option B: Store all snapshots with vintage.**
Add `snapshot_vintage varchar` to `provider_ownership` (or a separate
`provider_ownership_history` table). Load each monthly snapshot as a distinct
set. This enables temporal queries: "When did Genesis acquire facility X?"

Option B is more expensive (378K × 82 = ~31M rows) but enables the richest
analysis. Option A is cheaper and sufficient for detecting changes between
adjacent months.

**Recommendation:** Option B for the researcher tier. The storage cost is modest
(~3 GB) and the temporal ownership data is the unique selling point.

### Consumer Display

For the public consumer profile page:
- Show current ownership entities with roles and percentages (already built)
- Show parent group name when resolved: "Part of Genesis Healthcare (324 facilities)"
- Link to the parent group's facility list in filter-explore

For the researcher tier:
- Ownership change timeline: "Acquired by Genesis Healthcare LLC on 2019-03-15"
- Cross-facility aggregation by parent group
- Downloadable datasets grouped by operator

## Relationship to Existing Architecture

- `provider_ownership` table — already populated (378K rows)
- `ownership_entity_index.json` — defined in json-export.md for filter-explore
  feature, Organization-type entities only. The parent group resolution enriches
  this index with parent_group_id and aggregate stats.
- `legal-compliance.md` — ownership display has strict legal constraints. NO
  causal language connecting ownership to quality. The entity resolution and
  rollup features display factual ownership structure, not quality assertions.
- `display-philosophy.md` NH rules — ownership group browsing in filter-explore
  is "factual ordering, not a leaderboard."

## Implementation Priority

1. Build clustering script (semi-automated, output to review CSV)
2. Human review of top ~200 parent groups (covers 80%+ of facilities)
3. Create schema + migration for parent group tables
4. Wire into export layer (parent_group_name on ownership records)
5. Build filter-explore ownership group browsing
6. Ownership change detection (Option B: historical snapshots)

## Not In Scope

- Hospital ownership entity resolution (CMS doesn't publish hospital ownership
  entity names — only broad categories. Requires external data sources.)
- PE identification (CMS confirms PE identification from ownership data alone
  is unreliable — GAO finding. Do not attempt.)
- Ownership-quality causal claims (legal-compliance.md: strictly prohibited)
