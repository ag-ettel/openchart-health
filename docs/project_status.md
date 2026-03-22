# Project Status — 2026-03-21

## Where We Are

The pipeline is operational. CMS data flows from 9 years of CSV archives through
18 normalizers into PostgreSQL, with longitudinal data for trend display. The full
backfill is running — 113 archives (31 hospital quarterly snapshots + 82 nursing
home monthly snapshots, 2019–2026). When complete, the database will contain the
richest longitudinal CMS quality dataset any consumer tool has assembled.

The JSON export layer is built. The frontend TypeScript contract is synchronized.
The contested citation lifecycle tracking (DEC-028) preserves every scope/severity
revision and fine amount change across monthly CMS snapshots — information no
existing consumer tool surfaces.

---

## What Has Been Built

### Phase 0 (Complete — 2026-03-20)

All 27 gate criteria satisfied. Produced:
- 213 MEASURE_REGISTRY entries across 13 CMS datasets (143 hospital + 64 NH + 6 HRRP)
- 28 pipeline decisions (DEC-001 through DEC-028)
- Complete phase_0_findings.md, data_dictionary.md, csv_findings.md
- Alembic migration: 8 tables, 6 PostgreSQL enums
- 22 fixture files from live CMS API responses
- Full-population CSV audit across 4 archive vintages

### Phase 1A: Pipeline Core (Complete)

**Ingest layer:**
- `pipeline/ingest/csv_reader.py` — reads 113 CMS archive zips directly, handles
  3 naming eras (2019 legacy, 2022 nested, 2024+ current), column name normalization
  across all eras, encoding fallback for non-UTF-8 bytes in older archives
- `pipeline/ingest/client.py` — CMS DKAN API client (scaffolded, not yet needed —
  CSV archives are the primary data source for historical backfill)

**Normalize layer (18 normalizers, 331 tests):**

| Normalizer | Dataset | Rows (current) | Key Feature |
|---|---|---|---|
| `complications_deaths` | ynj2-r877 | 95,780 | HGLM CIs, 2019 PSI ID aliases |
| `hai` | 77hc-ibv8 | 28,734 | 6:1 sub-measure grouping, N/A≠suppressed |
| `readmissions` | 632h-zaca | 67,046 | EDAC/OP_36 phrasing, count-suppression |
| `hcahps` | dgck-syfz | 325,652 | Not Applicable≠suppressed |
| `timely_effective` | yv7e-xc69 | 138,129 | EDV categorical score_text |
| `imaging` | wkfw-kthe | 18,500 | Straightforward |
| `mspb` | rrqw-56er | 4,625 | Single measure |
| `hospital_info` | xubh-q36u | 5,426 | Provider metadata → providers table |
| `hrrp` | 9n3s-kdb3 | 18,330 | Three-way count-suppression (DEC-023) |
| `hacrp` | yq43-i98g | 3,055 | Payment reduction Yes/No/N/A |
| `vbp` | ypbt-wvdk | 2,455 | Domain scores (DEC-011) |
| `nh_provider_info` | 4pq5-n9py | 14,713 | NH metadata, Five-Star, staffing |
| `nh_mds_quality` | djen-97ju | 1,250,605 | Quarterly score expansion (DEC-015) |
| `nh_claims_quality` | ijh5-nb2v | 58,852 | O/E/adjusted triplet (DEC-016) |
| `nh_health_deficiencies` | r5ix-sfxw | 417,571 | Scope/severity, IDR, complaint flags |
| `nh_penalties` | g6vv-u9sr | 18,467 | Fine/payment denial lifecycle |
| `nh_ownership` | y2hd-n93e | 154,095 | Percentage parsing, association dates |
| `snf_qrp` | fykj-qjee | 220,695 | Compound code decomposition (DEC-020) |
| `snf_vbp` | 284v-j9fz | 13,900 | Fuzzy column matching across FY eras |

**Store layer:**
- `pipeline/store/upsert.py` — idempotent upserts for all 8 tables, per-dataset
  savepoints, DEC-028 citation lifecycle tracking (scope/severity history with IDR
  flag), penalty amount change tracking, auto-registration of unknown measures and
  providers
- `pipeline/store/seed_measures.py` — seeds measures reference table from
  MEASURE_REGISTRY, auto-registers retired/unknown measures as is_active=False

**Export layer:**
- `pipeline/export/build_json.py` — builds one JSON per provider, JOINs to measures
  table (no denormalization), builds trend arrays from all historical periods,
  Rule 12 trend validity, footnote 29 methodology change detection, contested
  citation transparency, penalty amount change transparency, atomic staging→production
  rename

**Orchestrator:**
- `pipeline/orchestrate.py` — single entry point, chronological archive processing
  (DEC-028), per-dataset savepoints, anomaly logging

**Infrastructure:**
- `scripts/bootstrap_db.py` — database creation + Alembic migration
- `scripts/csv_audit.py` — cross-vintage CSV audit tool
- PostgreSQL 17 running locally via conda-forge
- 331 tests passing in ~1 second

### Frontend Component Rebuild (Complete — 2026-03-21)

Full audit and rebuild of all 16 components in `frontend/components/`, both files in
`frontend/lib/`, and `frontend/types/provider.ts`. Every component was audited against
display-philosophy.md, text-templates.md, json-export.md, legal-compliance.md,
ses-context.md, and all relevant pipeline decisions (DEC-009/022/023/024/028/030/031/032).

**Architectural contract files:**
- `frontend/types/provider.ts` — TypeScript contract synchronized with export layer,
  includes InspectionEvent, Penalty, Ownership, ScopeSeverityChange types, DirectionSource
- `frontend/lib/constants.ts` — all verbatim template strings, DIRECTION_NOTE,
  EXPLICIT_DIRECTION_SOURCES, MEASURE_GROUP_DISPLAY_NAMES, METHODOLOGY_CHANGE_FOOTNOTE_TEXT
- `frontend/lib/utils.ts` — 5 authoritative functions (formatValue, formatAttribution,
  hasSESSensitivity, groupByMeasureId, consecutivePenalties). Stale functions removed
  (compareToAverage, compareProviders, findSummary, ComparisonResult/Summary imports)
- `tests/pipeline/test_export_contract.py` — validates provider.ts against canonical
  schema on every test run, DirectionSource enum added

**Rebuilt components (from stub or fundamentally redesigned):**

| Component | Key Changes |
|---|---|
| `ComparisonBadge` | Now displays CMS's `compared_to_national` (DEC-022, all 5 values) instead of computed directional verdicts. Labels attribute to CMS. |
| `MeasureCard` | Central component. Handles score_text (DEC-024), count_suppressed (DEC-023), O/E ratios (DEC-016), direction_source (DEC-032), CMS comparison badge, CI bounds, sample size caveats, footnote pass-through. No computed comparison verdicts (DEC-030). |
| `BenchmarkBar` | Neutral position indicator — gray axis with national avg reference line, state avg dashed marker, CI translucent span. No directional color. Removed unused direction/reliabilityFlag props. |
| `ProviderContextPanel` | Rebuilt against actual HospitalContext type (5 fields). 10 stale field references removed. Deferred fields (DEC-004/005/006) explicitly acknowledged as "Not yet available." |
| `FootnoteDisclosure` | Always visible (was collapsed). Footnote 29 special-cased with prominent methodology change warning. Accepts nullable arrays. |
| `SuppressionIndicator` | Footnote pass-through added. Suppression footnotes (codes 1, 5, 11) now visible inline. |
| `TrendChart` | Full Recharts implementation. Blue-600 data line (non-directional). Methodology change line breaks via segment splitting. Suppressed/not-reported gap annotations. 3-period minimum enforced (Rule 12). National + state avg reference lines. Categorical measure guard. |
| `PatientSafetyRecord` | HACRP consecutive penalty integration (orange threshold). Sort: suppressed/not-reported first (absence is the signal), then by deviation from national avg. |
| `MeasureGroup` | Group-level SES disclosure. Group-level attribution (deduplicated by dataset). Display name mapping from constants. |
| `PaymentAdjustmentHistory` | All 3 penalty_flag states (true/false/null). Orange only for HACRP consecutive penalties. Tabular layout with score/percentile. Provider-type-aware program filtering. |

**Targeted fixes:**

| Component | Fix |
|---|---|
| `NonReporterIndicator` | Nullable trend prop, provider-agnostic "facility" language |
| `SESDisclosureBlock` | Blue→gray color palette |
| `MethodologyChangeFlag` | Amber→gray color palette, periodLabel prop, text from constants |
| `MultipleComparisonDisclosure` | "patient safety"→"tail risk" per Template 3d verbatim |
| `AttributionLine` | gray-400→gray-500 for contrast compliance |
| `DisclaimerBanner` | No changes needed (was already spec-compliant) |

**Post-rebuild audit findings fixed:** React hooks ordering in TrendChart, footnote
codes displayed even when text lookup fails (Rule 2), HACRP orange consistency between
PatientSafetyRecord and PaymentAdjustmentHistory, BenchmarkBar unused prop removal,
duplicate consecutivePenalties extracted to shared utility, ProviderContextPanel
contrast ratio, MeasureGroup display name mapping.

---

## Phase 1 Gate Criteria Status

### Pipeline — 11/13 complete

- [x] All hospital datasets ingest successfully from live CMS API (via CSV)
- [x] All nursing home datasets ingest successfully from live CMS API (via CSV)
- [x] CSV archive reader loads historical snapshots (2019–2026)
- [x] CSV column name adapter verified against all downloaded vintages
- [x] NH Provider Info vintage-aware column mapping (DEC-026)
- [x] Pipeline idempotency verified (upsert keys enforce identical row counts)
- [ ] 5% failure threshold abort in production mode (backfill mode uses savepoints)
- [x] All 213 measures seeded with direction, ses_sensitivity, direction_source
- [x] Longitudinal data: 22 distinct periods for quarterly measures from archives
- [ ] Credible intervals calculated (transform layer not yet built)
- [x] CMS-published intervals stored as-is for HGLM/SIR measures
- [x] Pipeline run audit trail in pipeline_runs table
- [x] Anomaly log captures unknown footnotes, missing providers, out-of-range values

### Export — 4/6 complete

- [x] JSON export produces valid files per provider (build_json.py)
- [x] JSON schema matches frontend/types/provider.ts (contract test enforced)
- [x] stratification empty string → null in export
- [x] Atomic staging → production rename
- [ ] Text templates render correctly (render layer not yet built)
- [ ] No template output contains prohibited language

### API — 0/3

- [ ] Provider endpoint returns complete data
- [ ] ses_sensitivity present alongside every measure value
- [ ] State-level provider listing

### Frontend — 10/13

- [x] DisclaimerBanner on every page (legal-compliance.md)
- [x] MeasureCard renders direction attribution from CMS source (DEC-032)
- [x] Direction rendering conditional on direction_source (DEC-032)
- [x] Data attribution visible per measure group (MeasureGroup + AttributionLine)
- [x] SES disclosure for HIGH/MODERATE measures (SESDisclosureBlock + MeasureGroup)
- [x] Tail risk measures in primary view (PatientSafetyRecord with HACRP integration)
- [x] Suppressed/not-reported/count-suppressed states displayed (3-state model)
- [x] BenchmarkBar with CI span (neutral position indicator, no directional color)
- [x] TrendChart with 3+ period validation, methodology breaks, gap annotations
- [x] All 16 components rebuilt against current spec, post-rebuild audit clean
- [ ] Hospital profile pages wired to static JSON (components ready, page assembly pending)
- [ ] Compare page
- [ ] Methodology page

### Testing — 3/5

- [x] pipeline/normalize/ at 92%+ coverage (18 normalizers)
- [ ] pipeline/validate/ at 100% (not yet built)
- [ ] pipeline/transform/ at 100% (not yet built)
- [x] All 30 non-optional test cases addressed (suppression, footnotes, decimals, etc.)
- [x] Contract test: provider.ts ↔ export schema synchronized

---

## What's Next — Implementation Steps

### Immediate (after backfill completes)

**1. Run export and verify JSON output.**
The export layer is built. Once the backfill finishes:
```python
from pipeline.export.build_json import export_all
export_all(db_url="postgresql+psycopg://postgres:postgres@localhost:5432/openchart")
```
This produces `build/data/{ccn}.json` for every provider. Spot-check a few files.
Verify trend arrays have multiple periods. Verify contested citations have
`originally_published_scope_severity` populated.

**2. Build `pipeline/transform/` — credible intervals and benchmarks.**
This is the last pipeline module. It computes:
- Bayesian credible intervals (Beta-Binomial, κ=10) for measures where
  `risk_adjustment_model="NONE"` and `numerator_denominator_published=True`
- `reliability_flag` from sample size thresholds
- `national_avg` and `state_avg` from the state/national average CSV files
  (already downloaded: `Complications_and_Deaths-National.csv`, etc.)

The transform layer reads from the database, computes, and writes back. It runs
after the store layer and before the export layer.

Design principle: the transform layer is the only place where we ADD information
that CMS didn't publish. Every other layer republishes CMS data. The credible
intervals are our calculation, clearly attributed as such (DEC-029). The
national/state averages are CMS data.

**3. Build `pipeline/render/` — deterministic text templates.**
Renders consumer-facing text from templates defined in `text-templates.md`. This
is pure string interpolation — no LLM, no inference. The `direction_source` field
governs whether the direction note renders. The `plain_language` field from
MEASURE_REGISTRY is the primary consumer description.

### Near-term (after transform + render)

**4. Build FastAPI endpoints.**
The API reads from exported JSON files (SSG architecture). Three endpoints:
- `GET /api/providers/{ccn}` — returns provider JSON
- `GET /api/providers?state={state}` — provider list for search
- `GET /api/measures/{measure_id}` — measure metadata

The API is thin — it serves pre-built JSON. No database queries on the hot path.

**5. Build hospital profile pages.**
SSG from `build/data/{ccn}.json`. The components exist (MeasureCard, etc.) but
need to be wired to real data. Key pages:
- Hospital profile with measure groups, tail risk primary view
- Compare page (client-side, two provider JSONs)
- Methodology page (CI methodology, data sources)

**6. Build nursing home profile pages.**
Same architecture as hospitals, plus:
- Inspection events with contested citation display (DEC-028)
- Penalty history with amount change transparency
- Ownership entity display with legal disclaimers (legal-compliance.md)
- Five-Star sub-rating display

### Performance optimization (when needed)

**7. Batch upserts for pipeline speed.**
The current row-by-row upsert is correct but slow for bulk loading (~3 hours per
full hospital backfill). For production quarterly refreshes this is fine (small
delta). For initial backfill of 113 archives, batch inserts with `executemany` or
PostgreSQL COPY would reduce load time from ~20 hours to ~2 hours.

Apply this optimization only after the pipeline is stable and producing correct
output. Premature optimization of the load path risks introducing data integrity
bugs in the most safety-critical code path.

---

## Antifragile Design Principles in Practice

These principles have guided every decision in the project. They should continue
to guide implementation choices going forward.

**Store what CMS gives you; don't invent what it doesn't.**
We removed `measure_spec_version` and `methodology_revision_date` because CMS
signals methodology changes via footnote code 29, not dedicated fields. We removed
6 deferred SES context fields because no CMS API source exists. We use `varchar`
for CMS-originated classification strings because CMS introduces new values without
notice. In every case: use what's there, don't approximate what isn't.

**Fail loud on the unexpected; absorb the expected gracefully.**
Unknown measure IDs from older archives are auto-registered as `is_active=False`
with a warning log — they're stored, not rejected. Unknown providers get stub rows.
Unknown footnote codes are stored as-is. The pipeline never crashes on data it
doesn't recognize; it logs the anomaly and preserves the value. A crashed pipeline
is a data blackout. A logged warning is recoverable.

**Single source of truth over denormalization.**
Measure metadata lives only in the `measures` table. Provider metadata lives only
in `providers`. Value rows carry only the value, its provenance, and its quality
signals. The export layer JOINs to reconstruct the full picture. Updating a
measure's direction or name is one row change, not a re-processing of millions of
value rows.

**Templates over generation; CMS language over ours.**
All consumer text is deterministic from templates. Direction assertions are
conditional on `direction_source` — we only say "CMS designates lower values as
better" when CMS actually said that in the API or Data Dictionary. When CMS
didn't make an explicit direction statement, the `plain_language` description
carries direction implicitly through CMS's own words.

**The seam should get more robust with scale.**
The `test_export_contract.py` validates every field in `provider.ts` against a
canonical schema on every test run. Adding a field requires updating three places
in the same commit (export builder, TypeScript types, contract test). The contract
test catches drift before it reaches production. The inspection lifecycle tracking
gets richer with every monthly snapshot loaded — more data means more transparency,
not more fragility.

**Non-disclosure is a signal, not a gap.**
Suppressed values, not-reported states, contested citations, and penalty revisions
are all first-class data. A hospital that didn't report infection data is as
important as one that reported a 2.3% rate. A citation that was revised from
immediate jeopardy to no actual harm surfaces both states — the original finding
and the revision. The consumer sees everything CMS published, in every state CMS
published it.

**Cost of the next dataset should be less than the last.**
Adding a new CMS dataset requires: a normalizer (inherits shared infrastructure),
a MEASURE_REGISTRY entry, and a line in the orchestrator. The 18th normalizer was
faster to write than the 3rd because the patterns (suppression detection, footnote
parsing, period extraction, compared_to_national mapping) are all reusable.

---

## Key Files Reference

| File | Purpose |
|---|---|
| `pipeline/config.py` | MEASURE_REGISTRY (213 entries), dataset IDs, canonical mappings |
| `pipeline/ingest/csv_reader.py` | CSV archive reader (113 archives, 3 naming eras) |
| `pipeline/normalize/common.py` | Shared normalizer infrastructure |
| `pipeline/normalize/*.py` | 18 per-dataset normalizers |
| `pipeline/store/upsert.py` | Idempotent upserts, DEC-028 lifecycle tracking |
| `pipeline/store/seed_measures.py` | Measures table seeding + auto-registration |
| `pipeline/export/build_json.py` | JSON export builder with trend arrays |
| `pipeline/orchestrate.py` | Pipeline orchestrator |
| `frontend/types/provider.ts` | TypeScript contract (architectural) |
| `tests/pipeline/test_export_contract.py` | Contract enforcement (canonical schema) |
| `.claude/rules/phase-1.md` | Phase 1 tasks and gate criteria |
| `docs/pipeline_decisions.md` | 28 DEC entries documenting all decisions |
| `docs/csv_findings.md` | CSV archive audit and longitudinal strategy |
| `docs/phase1_review_notes.md` | Code review findings and mutation display logic |
