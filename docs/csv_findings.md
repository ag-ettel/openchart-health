# CSV Download Findings

Full-population CSV scan results from the CMS "Download All Data" bundles.
Current snapshots downloaded 2026-02/03 to `data/hospitals/` and `data/nursing_homes/`.

These CSVs are the same data as the DKAN API but in bulk CSV format. Each download is
a point-in-time snapshot of the current release. **Archive snapshots of prior releases
are available from CMS going back 9 years** (confirmed by user 2026-03-20) — these are
the source for longitudinal/trend data.

---

## Key Finding: CSV Column Names Map Cleanly to API Fields

All CSV files use Title Case with spaces (`"Facility ID"`, `"Measure Name"`).
The API uses snake_case (`facility_id`, `measure_name`). The conversion is mechanical
and consistent across all datasets. One exception: T&E CSV uses `"Condition"` while
API uses `"_condition"` (leading underscore is an API artifact).

CSV-to-API normalizer adapter: lowercase, replace spaces with underscores, strip
special characters. This is a thin adapter on top of the existing API normalizers.

---

## Value Discoveries from Full-Population CSV Scan (2026-03-20)

These values were NOT observed in Phase 0 API samples (100-1000 rows) but appear in
the full-population CSVs (~5,000-100,000+ rows per dataset).

### compared_to_national — 6 New Phrasings

Phase 0 documented 8 phrasings from API samples. The full CSVs revealed 6 additional
phrasings used by EDAC and OP_36 measures:

| New Phrasing | Measure(s) | Canonical | Count |
|---|---|---|---|
| `"Average Days per 100 Discharges"` | EDAC_30_AMI/HF/PN | `NO_DIFFERENT` | 3,720 |
| `"More Days Than Average per 100 Discharges"` | EDAC_30_AMI/HF/PN | `WORSE` | 2,837 |
| `"Fewer Days Than Average per 100 Discharges"` | EDAC_30_AMI/HF/PN | `BETTER` | 1,791 |
| `"No Different than expected"` | OP_36 | `NO_DIFFERENT` | 2,590 |
| `"Better than expected"` | OP_36 | `BETTER` | 87 |
| `"Worse than expected"` | OP_36 | `WORSE` | 48 |

These have been added to `COMPARED_TO_NATIONAL_MAPPING` in `pipeline/config.py` and
documented in `docs/data_dictionary.md`.

### Footnote Codes — Full Distribution

Footnote codes observed across all hospital CSVs (full population):

| Code | CompDeaths | HAI | Readmissions | T&E | Imaging | MSPB |
|---|---|---|---|---|---|---|
| 1 | 12,820 | — | 15,922 | 11,642 | 5,178 | 75 |
| 2 | — | — | — | 11,591 | — | — |
| 3 | — | 3,952 | — | 3,970 | — | — |
| 4 | — | — | — | 627 | — | — |
| 5 | 9,323 | 24,784 | 12,712 | 63,996 | 308 | 1,501 |
| 7 | 1,863 | — | 850 | 537 | 2,672 | — |
| 8 | — | 2,118 | — | — | — | — |
| 11 | — | 12 | — | — | — | — |
| 12 | — | 12,408 | — | 3 | — | — |
| 13 | 16,380 | 30,852 | — | — | — | — |
| 19 | 3,260 | 5,868 | 2,282 | 3,717 | 652 | 163 |
| 23 | 92 | — | 1 | — | 4 | — |
| 28 | 100 | 288 | 86 | — | — | — |
| 29 | 1,046 | 2,304 | 663 | 863 | 152 | 51 |

**Codes confirmed present that were NOT in Phase 0 API samples:**
- Code `4` (T&E, 627 occurrences) — check Footnote_Crosswalk.csv for meaning
- Code `11` (HAI, 12 occurrences) — very rare, check meaning
- Code `23` (CompDeaths 92, Readmissions 1, Imaging 4) — rare

All codes should be verified against `docs/Footnote_Crosswalk.csv` to ensure the
lookup table covers the full set.

### HRRP Three-Way State — Full Population Counts

| State | Count | Description |
|---|---|---|
| Normal (all fields populated) | ~6,000+ | Standard |
| Count-only suppression (`"Too Few to Report"`) | 3,683 | DEC-023: count_suppressed=true |
| Full suppression (all `"N/A"`) | 6,610 | suppressed=true |
| Discharge-only suppression (`number_of_discharges="N/A"`) | 10,088 | Includes both states above |

### HACRP Payment Reduction — Full Values

| Value | Count |
|---|---|
| `"No"` | 2,293 |
| `"Yes"` | 719 |
| `"N/A"` | 43 |

`"N/A"` is a third state (not participating / excluded), distinct from Yes/No.
Must be stored as a separate state, not as boolean.

### HCAHPS Sentinel Values

| Field | `"Not Applicable"` | `"Not Available"` |
|---|---|---|
| Patient Survey Star Rating | 282,551 | 14,454 |
| HCAHPS Answer Percent | 81,413 | 51,272 |

`"Not Applicable"` and `"Not Available"` are distinct states in HCAHPS. "Not Applicable"
means the question/answer category doesn't apply to this row type (e.g., star rating
on an individual answer row). "Not Available" means the data was expected but is missing.

### EDV Categorical Scores — Full Distribution

| Value | Count |
|---|---|
| `"low"` | 1,672 |
| `"medium"` | 917 |
| `"Not Available"` | 811 |
| `"very high"` | 704 |
| `"high"` | 553 |

Matches Phase 0 findings. No new values discovered. All lowercase as expected.

---

## CSV-Only Files (Not Available via API)

These files exist in the CSV download bundle but have no DKAN API equivalent:

| File | Purpose | Phase 1 Relevance |
|---|---|---|
| `Measure_Dates.csv` | Maps every measure ID to its reporting period | HIGH — essential for period tracking |
| `CMS_PSI_6_decimal_file.csv` | Individual PSI component rates at 6-decimal precision | MEDIUM — higher precision than API `Score` field |
| `HOSPITAL_QUARTERLY_MSPB_6_DECIMALS.csv` | High-precision MSPB values | LOW — only 1 measure |
| `hvbp_clinical_outcomes.csv` | VBP measure-level achievement/improvement/benchmark scores | HIGH — individual measure scoring not in API |
| `hvbp_safety.csv` | VBP safety domain detail | HIGH — same |
| `hvbp_efficiency_and_cost_reduction.csv` | VBP efficiency domain detail | HIGH — same |
| `hvbp_person_and_community_engagement.csv` | VBP patient experience domain detail | HIGH — same |
| `Data_Updates_January_2026.csv` | Documents which datasets were updated and when | LOW — pipeline metadata |
| `Maternal_Health-Hospital.csv` | PC_02, PC_07a maternal measures | OUT OF SCOPE currently |
| `Birthing_Friendly_Hospitals_Geocoded.csv` | Geocoded birthing-friendly list | OUT OF SCOPE |

---

## Historical/Archive Data Strategy

### Current State

The DKAN API and current CSV downloads both contain **only the latest reporting period**
per measure per provider. Each quarterly/annual CMS refresh replaces the previous data.

### Archive Availability

CMS provides archive snapshots going back **9 years** via the topic archive pages:
- https://data.cms.gov/provider-data/topics/hospitals (archive section)
- https://data.cms.gov/provider-data/topics/nursing-homes (archive section)

These are JS-rendered SPAs requiring manual browser download.

### Cross-Vintage Audit (completed 2026-03-20)

**Vintages audited:** Jul 2024, Feb 2025, Aug 2025 (archives) + current (Feb 2026).
Full audit output: `docs/csv_audit_output.txt`. Script: `scripts/csv_audit.py`.

**Longitudinal coverage confirmed — 4 distinct periods per measure family:**

| Dataset | Jul 2024 | Feb 2025 | Aug 2025 | Current |
|---|---|---|---|---|
| CompDeaths mortality | 07/2020–06/2022 | 07/2020–06/2023 | 07/2021–06/2023 | 07/2022–06/2024 |
| CompDeaths PSI | 07/2020–06/2022 | 07/2021–06/2023 | 07/2021–06/2023 | 07/2022–06/2024 |
| HAI | 10/2022–09/2023 | 04/2023–03/2024 | 10/2023–09/2024 | 04/2024–03/2025 |
| HCAHPS | 10/2022–09/2023 | 04/2023–03/2024 | 10/2023–09/2024 | 04/2024–03/2025 |
| T&E (annual) | 01/2022–12/2022 | 01/2023–12/2023 | 01/2023–12/2023 | 01/2024–12/2024 |
| T&E (quarterly) | 10/2022–09/2023 | 04/2023–03/2024 | 10/2023–09/2024 | 04/2024–03/2025 |
| Imaging | 07/2022–06/2023 | 07/2022–06/2023 | 07/2023–06/2024 | 07/2023–06/2024 |
| MSPB | 01/2022–12/2022 | 01/2023–12/2023 | 01/2023–12/2023 | 01/2024–12/2024 |
| Readmissions | 07/2020–06/2023 | 07/2020–06/2023 | 07/2021–06/2024 | 07/2021–06/2024 |
| NH MDS | 2023Q2–2024Q1 | 2023Q4–2024Q3 | 2024Q2–2025Q1 | 2024Q4–2025Q3 |
| NH Claims | 2023/01–2023/12 | 2023/07–2024/06 | 2024/01–2024/12 | 2024/07–2025/06 |

**Note:** Some adjacent vintages share the same period (e.g., Imaging Jul 2024 = Feb
2025). This means loading both archives for that dataset produces duplicate rows — the
upsert key handles this correctly. For 3 distinct periods on annually-refreshed
measures, archives spanning 3+ years are needed.

**Download strategy (revised 2026-03-20):**
Download every available quarterly snapshot (Jan/Apr/Jul/Oct) for both hospitals and
nursing homes, going back to 2017. Rationale:
- Different measures refresh in different quarters within the same CSV bundle. A
  single annual download misses quarterly shifts for HAI/HCAHPS/T&E.
- Annual measures (mortality) use rolling 36-month windows that shift between
  quarters — even the Jul→Jan boundary produces a distinct period.
- ~24 ZIPs per provider type. Storage is negligible (~5-10 GB total uncompressed).
- More historical depth = richer trend display = stronger differentiator.

### Measure ID Changes Across Vintages

| Dataset | New (current only) | Retired (archives only) |
|---|---|---|
| CompDeaths | `Hybrid_HWM` | — |
| Readmissions | `Hybrid_HWR` | `READM_30_HOSP_WIDE` (renamed) |
| T&E | `GMCS` (5), `HH_HYPER/HYPO/ORAE`, `OP_18a/d` | `STK_06`, `HCP_COVID_19`, `ED_2_Strata_1/2`, `HH_01/02` |
| HCAHPS | — | 25 retired IDs (H_COMP_3_*, H_COMP_7_*, H_CT_*, H_BATH_*, H_CALL_*) |
| NH MDS | `481` | `405`, `419`, `453`, `471` |

The pipeline handles this naturally: retired measures exist in older vintages with
their own `period_label`, and the `measures` reference table marks them `is_active=false`.
New measures simply don't appear in older vintages — no special handling needed.

### NH Provider Info Schema Change (CRITICAL — see DEC-026)

The NH Provider Info CSV has **unstable headers across vintages:**

**Current (Feb 2026) has but older vintages lack:**
- `Urban`, `Chain Name`, `Chain ID`, `Chain Average *` (4 rating fields),
  `Number of Facilities in Chain`, `Rating Cycle 2/3 *` (combined columns)

**Older vintages have but current lacks:**
- `Rating Cycle 2 *` and `Rating Cycle 3 *` as SEPARATE columns (not combined)
- `Affiliated Entity Name`, `Affiliated Entity ID`
- `Number of Facility Reported Incidents`, `Number of Substantiated Complaints`

The CSV backfill normalizer must handle both column layouts. See DEC-026.

### Value Stability Across Vintages

All categorical values (compared_to_national, footnote codes, suppression sentinels,
hospital_type, ownership_type, scope_severity_codes, penalty types) are **stable across
all 4 vintages**. No new values in older archives. No values present in archives that
are absent from current. The normalizer mapping tables confirmed during Phase 0 are
sufficient for all archive vintages tested.

### Citation Lifecycle Analysis (CRITICAL — see DEC-028)

Cross-monthly diff of NH Health Citations (Jan/Feb/Mar 2024) revealed that citations
are **mutable between monthly snapshots**. This is not just cycle rotation — individual
citation rows change in place.

**Monthly change volume (single month transition, ~393K total citations):**

| Change Type | Jan->Feb | Feb->Mar | Notes |
|---|---|---|---|
| Added | 10,490 | 9,366 | New inspections + newly published citations |
| Removed | 10,101 | 8,933 | Cycle 3 dropping off (mostly) |
| Inspection Cycle changed | 18,981 | 16,536 | Cycle rotation: 1->2, 2->3 |
| Deficiency Corrected changed | 2,862 | 2,615 | Correction status updated |
| Correction Date changed | 1,074 | 1,068 | Date populated after correction |
| Complaint Deficiency flag changed | 546 | 647 | Reclassified standard<->complaint |
| Standard Deficiency flag changed | 263 | 259 | Reclassified |
| IDR flag changed | 178 | 165 | Informal Dispute Resolution filed/resolved |
| Infection Control flag changed | 66 | 37 | Reclassified |
| IIDR flag changed | 45 | 34 | Independent IDR filed/resolved |
| **Scope Severity Code changed** | **20** | **18** | **SEE BELOW** |

**Scope/severity changes that cross the immediate jeopardy threshold:**

In a single month (Feb->Mar 2024):
- **5 citations downgraded FROM immediate jeopardy** (J/K/L -> D/G/H): these
  facilities were previously flagged as posing imminent danger to residents, then the
  citation was reduced. Examples: K->H (two citations, same facility 185463),
  J->D (two facilities), J->G (one facility).
- **2 citations upgraded TO immediate jeopardy** (G->J): these facilities had a
  citation INCREASED in severity after initial publication.
- **186 IJ citations removed entirely** (Cycle 3 dropping off the 3-cycle window).

**232 immediate jeopardy citations were removed (Jan->Feb)** as Cycle 3 data dropped
off. These represent real historical events — residents were in imminent danger. They
should not vanish from our data just because CMS rotated their inspection cycles.

**Implications for pipeline design:**
1. The upsert key `(provider_id, survey_date, deficiency_tag)` is correct for the
   CURRENT snapshot. But for historical tracking, we need to preserve the state of
   each citation AS IT APPEARED in each monthly snapshot.
2. A citation that was scope J in January and scope D in March was genuinely J at
   the time of the original finding. Both states are true — the original finding and
   the post-IDR resolution.
3. Citations that drop off Cycle 3 are still real historical events. Our database
   should never delete them.

See DEC-028 for the design decision on handling citation mutability.

### Penalty Mutability (Jan->Mar 2024)

Penalty rows are also mutable between monthly snapshots:

| Change | Count | Notes |
|---|---|---|
| Added | 1,949 | New penalties published |
| Removed | 2,580 | Older penalties dropping off the 3-year window |
| Fine Amount changed | 1,262 | 622 increases + 640 decreases |
| Payment Denial Length changed | 6 | Rare |

Fine amounts change in both directions — not just appeal reductions. Total dollar
movement: $13.3M in decreases alone across 640 penalties in 2 months. Average change
is ~$20K per penalty.

**Pipeline implication:** Same lifecycle approach as citations. Store
`originally_published_fine_amount` on insert, track changes in the current value.
The `provider_penalties` table should add `originally_published_fine_amount`,
`originally_published_vintage`, and `last_seen_vintage` columns (same pattern as
DEC-028 for citations).

### Other Mutable Data — Edge Case Inventory

| Dataset | Mutable? | What Changes | Pipeline Handling |
|---|---|---|---|
| NH Health Citations | YES | Scope/severity, correction status, IDR flags, cycle rotation | DEC-028: full lifecycle tracking |
| NH Penalties | YES | Fine amounts, payment denial length | Same pattern as DEC-028 |
| NH Provider Info | YES | Ratings, staffing, ownership changes | Current snapshot only (latest = truth for context fields) |
| NH Quality Measures (MDS/Claims) | YES (period shifts) | Different reporting windows per vintage | Upsert on period_label naturally handles this |
| Hospital measures | YES (period shifts) | Different reporting windows per vintage | Upsert on period_label naturally handles this |
| NH Ownership | UNKNOWN | Entity changes between snapshots | Needs investigation when ownership pipeline is built |
| Hospital General Info | YES | Star ratings update quarterly | Current snapshot only (latest = truth) |

**Summary:** Citations and penalties require lifecycle tracking because individual rows
are contested/revised. Quality measures and provider metadata don't need lifecycle
tracking because different vintages contain different reporting periods (natural
longitudinal data) or represent the current institutional state.

---

## CSV Exploration Checklist

### Downloads

- [x] Download 3+ hospital archive snapshots — Jul 2024, Feb 2025, Aug 2025 (2026-03-20)
- [x] Download 3+ nursing home archive snapshots — Jul 2024, Feb 2025, Jul 2025 (2026-03-20)
- [ ] Download full quarterly hospital archives (Jan/Apr/Jul/Oct per year, 2017–2025)
- [ ] Download quarterly nursing home archives (Jan/Apr/Jul/Oct per year, 2017–2025)

**Download plan (in progress 2026-03-20):**

Hospitals — every available quarterly release (Jan/Apr/Jul/Oct):
- 2017: Jan, Apr, Jul, Oct
- 2018: Jan, Apr, Jul, Oct
- 2019: Jan, Apr, Jul, Oct
- 2020: Jan, Apr, Jul, Oct
- 2021: Jan, Apr, Jul, Oct
- 2022: Jan, Apr, Jul, Oct
- 2023: Jan, Apr, Jul, Oct
- 2024: Jan, ~~Jul~~ (already have Jul 2024)
- 2025: ~~Feb~~ (already have), Apr, ~~Aug~~ (already have), Oct

Nursing homes — quarterly (Jan/Apr/Jul/Oct):
- Same year range, same quarterly cadence
- NH has monthly releases; skip the in-between months (quality measures refresh
  quarterly, monthly releases mostly update inspection/penalty data)

**Folder structure:**
```
data/hospitals/hospitals_MM_YYYY/
data/nursing_homes/nursing_homes_including_rehab_services_MM_YYYY/
```

`scripts/csv_audit.py` auto-discovers all subdirectories. Re-run after downloads to
verify column stability and build the full period grid.

### Column Stability Verification

- [x] Compare column headers across archive vintages — STABLE for all hospital datasets
      and most NH datasets (2026-03-20)
- [x] Check for added/removed columns — NH Provider Info has schema changes (DEC-026)
- [x] Check for renamed columns — `Rating Cycle 2/3` split confirmed
- [x] Check for changed sentinel values — STABLE across all vintages
- [x] Check for retired measure IDs — documented above
- [x] Check for new measure IDs — documented above

### Period Overlap Analysis

- [x] Confirm different archive snapshots contain different reporting periods — confirmed
- [x] Document period progression per measure — table above
- [x] Identify rolling vs fixed windows — mortality uses rolling 36mo, HAI/HCAHPS
      quarterly, T&E mixed annual/quarterly
- [x] Determine minimum archives for 3+ periods — 4 vintages sufficient for quarterly
      measures; annual measures need archives spanning 3+ years

### Footnote Code Stability

- [ ] Compare footnote codes across archive vintages — confirm same codes mean the
      same thing (CMS could theoretically reassign codes)
- [ ] Cross-reference all observed codes against `docs/Footnote_Crosswalk.csv`

### CSV Backfill Pipeline Design

- [ ] Write `pipeline/ingest/csv_reader.py` — thin adapter that reads CSV files and
      produces the same `list[dict]` output as `client.py` API responses, with column
      names converted to snake_case
- [ ] Add `archive_date` or `release_date` metadata to track which CMS release a
      row came from (separate from the measure's own `period_label`)
- [ ] Confirm that the existing normalizers work on CSV-sourced rows after the
      column name adapter (the values should be identical to API responses)
- [ ] Idempotency: loading the same archive twice must not create duplicate rows
      (upsert key `(provider_id, measure_id, period_label, stratification)` should
      handle this naturally since period_label differs across releases)

### VBP Detail Files (CSV-Only)

- [ ] Document field structure of `hvbp_clinical_outcomes.csv`,
      `hvbp_safety.csv`, `hvbp_efficiency_and_cost_reduction.csv`,
      `hvbp_person_and_community_engagement.csv`
- [ ] Determine whether VBP individual measure scores should be stored in
      `provider_measure_values` or `provider_payment_adjustments`
- [ ] Document in `docs/pipeline_decisions.md` as a DEC entry
