# Measure Group Misclassification — RESOLVED

**Status:** Fixed 2026-03-23.

## What Happened

The `ensure_measure_exists()` function in `pipeline/store/seed_measures.py`
auto-registers unknown/retired measure IDs encountered during historical CSV
backfill. It originally used `"SPENDING"` as a blind default `measure_group` for
all auto-registered measures. This caused 54 retired measures from older CMS
archives to be assigned the wrong group:

- 25 HCAHPS measures (`H_BATH_HELP_*`, `H_CALL_BUTTON_*`, `H_COMP_3_*`,
  `H_COMP_7_*`, `H_CT_*`) → should be `PATIENT_EXPERIENCE`
- 12 NH MDS measures → should be `NH_QUALITY_LONG_STAY`
- 1 NH Claims measure → should be `NH_QUALITY_CLAIMS`
- 13 SNF QRP measures → should be `NH_SNF_QRP`
- 3 PCH measures → should be `COMPLICATIONS`

## Fix Applied

1. **Database corrected** — all 54 measures updated to correct groups via SQL.
2. **`_infer_measure_group()` added** to `seed_measures.py` — infers the correct
   group from measure_id prefix patterns (H_ → PATIENT_EXPERIENCE, NH_MDS_ →
   NH_QUALITY_LONG_STAY, S_ → NH_SNF_QRP, etc.). Falls back to `SPENDING` only
   for truly unrecognizable IDs.
3. Future auto-registrations will be correctly classified without manual cleanup.
