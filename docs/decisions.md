# Decisions Log

This file documents any deviations from CLAUDE.md or the rules files discovered
during Phase 0 reconnaissance, along with the reasoning for each decision.

**Required format for each entry:**

- **Date:** YYYY-MM-DD
- **Rule or assumption affected:** Reference the specific rule file and section
- **Finding:** What reconnaissance revealed
- **Decision:** What was decided and why
- **Impact:** Any downstream effects on schema, pipeline, or display

Phase 0 gate criteria require at least one entry in this file before Phase 1 begins.

---

## Entries

### Payment and Value of Care removed from scope — CMS retired PAYM measures July 2025

- **Date:** 2026-03-14
- **Rule or assumption affected:** `CLAUDE.md` — CMS Datasets In Scope, Hospital Build section
- **Finding:** CLAUDE.md listed "Payment and Value of Care" as an in-scope hospital
  dataset. Phase 0 reconnaissance confirmed this dataset does not exist in the CMS
  Provider Data DKAN catalog. The CMS Hospital Data Dictionary (January 2026) confirms
  the PAYM measures (PAYM-30-AMI, PAYM-30-HF, PAYM-30-PN, PAYM-90-HIP-KNEE) and the
  composite Value of Care measure were retired by CMS effective the July 2025 release.
- **Decision:** Remove "Payment and Value of Care" from the in-scope dataset list.
  No pipeline code written. No MEASURE_REGISTRY entries created.
- **Impact:** CLAUDE.md and data_dictionary.md sections for this dataset marked as
  retired/removed. See DEC-002 in `docs/pipeline_decisions.md`.

---

### Health Equity Summary removed from scope — CMS retired HCHE measure October 2025

- **Date:** 2026-03-14
- **Rule or assumption affected:** `CLAUDE.md` — CMS Datasets In Scope, Hospital Build section
- **Finding:** CLAUDE.md listed "Health Equity Summary" as an in-scope hospital dataset.
  Phase 0 reconnaissance found no dedicated Health Equity dataset in the CMS Provider
  Data DKAN catalog. The CMS Hospital Data Dictionary (January 2026) confirms that HCHE
  (the sole Health Equity measure) was retired by CMS effective the October 2025 release.
  There is no replacement measure and no alternative dataset.
- **Decision:** Remove "Health Equity Summary" from the in-scope dataset list.
  No pipeline code written. No MEASURE_REGISTRY entries created.
- **Impact:** CLAUDE.md and data_dictionary.md sections for this dataset marked as
  retired/removed. See DEC-003 in `docs/pipeline_decisions.md`.

---

### VBP API dataset provides summary scores only, not individual measure data

- **Date:** 2026-03-14
- **Rule or assumption affected:** `CLAUDE.md` — pipeline architecture, `provider_payment_adjustments`
- **Finding:** The VBP Socrata dataset (`ypbt-wvdk`) provides summary domain scores
  (clinical outcomes, safety, person engagement, efficiency) and Total Performance Score
  (TPS), but not individual measure achievement/improvement points. The detailed
  measure-level data (e.g., MORT-30-AMI achievement threshold, benchmark, performance
  rate) exists only in downloadable CSV files not accessible via the DKAN API.
- **Decision:** Ingest VBP domain scores and TPS from `ypbt-wvdk` for the
  `provider_payment_adjustments` table. The payment adjustment determination is based
  on TPS, which is available in the API. Individual measure scores are out of scope
  for Phase 1.
- **Impact:** `provider_payment_adjustments` stores TPS and domain scores for VBP.
  No individual measure rows are stored from HVBP CSV files in Phase 1. See DEC-008
  in `docs/pipeline_decisions.md`.

---

### Timely and Effective Care API uses `_condition` (leading underscore) for condition field

- **Date:** 2026-03-14
- **Rule or assumption affected:** `coding-conventions.md` — no hardcoded strings
- **Finding:** The CMS data dictionary CSV shows column name `Condition`. The live
  DKAN API for `yv7e-xc69` returns this field as `_condition` (with a leading
  underscore). This is a known CMS API artifact for reserved-word column names.
- **Decision:** Use `_condition` as the API key in all pipeline ingest code for this
  dataset. Document in MEASURE_REGISTRY and normalizer. See DEC-008.
- **Impact:** Normalize `_condition` → `condition` in `pipeline/normalize/` before
  storing. Do not use `_condition` in any schema column name.

---

## Template

```
### [Short title]

- **Date:** YYYY-MM-DD
- **Rule or assumption affected:** `[rules file]` — [section or rule number]
- **Finding:** [What was discovered during reconnaissance]
- **Decision:** [What we decided and why]
- **Impact:** [Schema, pipeline, or display effects]
```
