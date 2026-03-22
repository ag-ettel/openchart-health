# Phase 1 Review Notes — 2026-03-21

Findings from comprehensive code review during hospital backfill.

## P0: Decisions Required

### 1. Orchestrator failure threshold semantics

**Finding:** The 5% dataset failure threshold (Rule 6) is not enforced. The
orchestrator uses per-dataset savepoints: a failed dataset rolls back only
its own rows, then the pipeline continues to the next dataset.

**Decision:** This is the correct behavior for **historical backfill**, where
partial loading is better than total abort. For **ongoing production runs**
(quarterly CMS refreshes), the all-or-nothing semantics from Rule 6 should
apply.

**Resolution:** Add a `backfill_mode` parameter to `run_pipeline()`. In backfill
mode (default during CSV archive loading), per-dataset savepoints with continue-
on-failure is correct. In production mode (ongoing API refreshes), enforce the
5% threshold across all datasets and abort the entire run on breach.

### 2. Nursing home footnote text lookup

**Finding:** `common.py` only has `HOSPITAL_FOOTNOTE_TEXT`. NH footnote codes
(1, 2, 6, 7, 9, 10, 13, 14, 18, 20-28) overlap with hospital codes in
numbering but may have different text. The NH data dictionary has a separate
footnote table.

**Resolution:** Add `NH_FOOTNOTE_TEXT` to common.py. Several codes (1, 2, 5, 7,
etc.) have identical text across hospital and NH. Codes unique to NH (6, 9, 10,
18, 20-28) need NH-specific text from the NH data dictionary. The `footnote_texts`
function should accept an optional provider_type parameter; default to hospital
lookup for backwards compatibility.

**Priority:** Before NH backfill goes to production. Not blocking current backfill
since footnote text is a display concern, not a data integrity concern — the
integer codes are stored correctly regardless of text lookup.

## P1: Important Watch Items

### 3. Auto-registered measures use wrong measure_group

When `ensure_measure_exists()` auto-registers a retired/unknown measure, it
uses `"SPENDING"` as a safe default group. This is better than rejecting the
row but creates technical debt. After backfill completes, query for all
`is_active=False` measures and assign correct groups.

### 4. Private `_` fields stripped by store layer

Normalizers attach context with `_` prefix (`_resident_type`, `_five_star_measure`,
`_number_of_patients_returned`, `_observed_count`, `_numerator`). The store layer
strips these. This is intentional — the `_` prefix convention means "normalizer
context, not stored in database." The export layer will either:
- Re-derive these from the database (JOIN to measures table), or
- Run normalizers again at export time (less efficient, more fresh)

Decision: The export layer JOINs to the `measures` table for metadata. The `_`
fields are transient normalizer context only.

### 5. SNF VBP fuzzy regex matching

The `_find_field()` function uses regex to match column names that embed fiscal
years. This is fragile but necessary — the VBP column names change every year
(`baseline_period:_fy_2022...` vs `baseline_period:_cy_2015...`). The alternative
(maintaining a mapping per fiscal year) is more work for no additional safety.
Accept the regex approach with good tests.

### 6. Inspection event_id generation

`nh_health_deficiencies.py` constructs event_id from
`f"{provider_id}_{survey_date}_{survey_type}"`. If survey_date is missing, this
produces `"015009__Health"`. The upsert key is
`(provider_id, event_id, deficiency_tag)` so uniqueness is still maintained.
The risk is low but the event_id should use the parsed date, not the raw string.

### 7. VBP domain score column naming

The VBP normalizer drops `"_normalized_"` from the efficiency domain score column
to match DEC-011, but the CSV column name doesn't have `"normalized"` in the
weighted version. This is actually correct — the naming asymmetry is in CMS's own
data. The normalizer faithfully reflects the CSV column names, which match the
schema per DEC-011.

## P2: Technical Debt (Address Later)

### 8. Module-level caches

`_known_providers` and `_registered_ids` are module-level sets. If the process
connects to multiple databases (unlikely in production), these would be stale.
Accept for now; scope to connection if/when multi-database use case arises.

### 9. Test coverage gaps

Lowest coverage:
- `snf_qrp.py` — 0% (compound parsing untested)
- `imaging.py` — 72%
- `hospital_info.py` — 73%
- `nh_ownership.py` — 78%

These all work against real data (verified in CSV backfill runs). The coverage
gap is in unit tests, not in real-world validation. Add tests before Phase 1
gate review, not before backfill.

### 10. 2019 archive column name aliases

The csv_reader.py column override system works for all tested archives (2019-2026).
New archives could introduce new column names. The override dict is the single
place to update — this is the convex choice (DEC-013/014 principle applied to
the ingest layer).

## Citation/Penalty Mutation Display Logic

Three types of data mutation between CMS monthly snapshots:

### Type 1: Routine updates (cycle rotation, correction dates)
- Inspection cycle 1→2→3 as new inspections happen
- Correction status and date populated after deficiency is corrected
- **Display:** Current value only. No original-value transparency needed.
  This is bookkeeping, not a disputed finding.

### Type 2: Contested citations (scope/severity changes)
- Facility disputes finding via IDR (Informal Dispute Resolution)
- CMS revises scope/severity code (e.g., J→D = immediate jeopardy→no actual harm)
- Both original and revised are CMS-published facts from different snapshots
- **Display rules:**
  - Current CMS classification shows as **primary** (solid, full visual weight)
  - Original finding shows as **secondary context** (lighter treatment, clearly
    labeled as "Originally cited as [X]")
  - A "Contested" or "Revised" indicator appears alongside
  - The timeline from `scope_severity_history` is available on drill-down
  - If the revision CROSSED the immediate jeopardy threshold (J/K/L → lower),
    this is especially important to surface — the facility was once assessed as
    posing imminent danger to residents
- **Never suppress the original finding.** A J→D revision means CMS originally
  found immediate jeopardy. That's a fact the consumer needs, even if it was
  later revised. Suppressing it would violate Principle 3 (non-disclosure is a
  signal).

### Type 3: Penalty amount changes
- Fine amounts adjusted through appeals or settlements
- Payment denial lengths may change
- **Display rules:**
  - Current amount shows as **primary**
  - If `originally_published_fine_amount` differs from current `fine_amount`,
    show: "Originally [original]. Current: [current]."
  - No judgment about whether the change was justified — both are CMS-published
    values from different snapshots

### What NOT to do
- Do not hide the original finding/amount when it was revised
- Do not use language like "overturned" or "reversed" — CMS revised the finding,
  we don't know the institutional reason
- Do not color-code original vs. revised (no red/green)
- Do not editorialize about the dispute process

## TODO: NH Deficiency Upsert Optimization

**Problem:** The DEC-028 lifecycle tracking does a per-row SELECT existence check
before every INSERT/UPDATE on provider_inspection_events. For 400K+ rows per monthly
archive × 82 archives, this is ~33M individual SELECT queries. The full NH backfill
takes ~50+ hours.

**Fix for next backfill run:** Add a `backfill_mode` parameter to
`upsert_inspection_events()`. In backfill mode (chronological first load):
1. First archive for each provider: use INSERT ON CONFLICT DO NOTHING (all rows are
   new, no lifecycle tracking needed)
2. Subsequent archives: use the current SELECT-then-UPDATE logic for lifecycle tracking

This is safe because archives are processed chronologically (DEC-028 requirement).
The first archive's citations are guaranteed to be new inserts. Only subsequent
archives can contain updates to existing citations.

**Expected speedup:** ~10x for the initial backfill (eliminates 80% of SELECTs).
Ongoing monthly refreshes (1 archive at a time) are already fast enough.

**Gate item:** Optimize before the next full re-load. Not blocking current work
since hospital data is already loaded and usable.

## Current Backfill Status

- Hospital backfill: running, ~2021-2026 loading successfully
- 2019-2020 archives failed on first run (FK violations on retired measures/providers)
- Fixes applied: `ensure_measure_exists`, `_ensure_provider_exists`
- Need clean re-run of 2019-2020 after current run completes
- NH backfill: normalizers ready, measure IDs aligned, ready to launch
