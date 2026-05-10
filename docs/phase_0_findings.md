# Phase 0 Findings

This document records confirmed findings from Phase 0 reconnaissance against live CMS
Socrata API responses. Each section covers one dataset.

**Status key:**
- [ ] Not started
- [~] In progress
- [x] Complete

---

## Datasets

### 1. Hospital General Information

**Status:** [x] Confirmed 2026-03-14. All fields, suppression encoding, footnote structure, and refresh schedule confirmed. Sample expanded to 1000 rows (2026-03-14); footnote codes 19 and 22 confirmed; footnote 19 identified as a distinct not_reported state for Rural Emergency Hospitals. Provider subtype enum values confirmed against full dataset (5,426 rows) on 2026-03-15 — discovered `"Long-term"` value (4 rows) missed in 1000-row sample.

**Socrata Dataset ID:** `xubh-q36u` (confirmed via DKAN datastore query 2026-03-14)

**Total rows in dataset:** 5,426

**Sample file:** `scripts/recon/raw_samples/xubh-q36u.json` (1000 rows, 10 pages)

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| provider id (CCN) | `facility_id` | 6-char string, zero-padded e.g. `"010001"` |
| provider name | `facility_name` | |
| `hospital_type` | `hospital_type` | See confirmed enum values in Provider Subtype section |
| `hospital_ownership` | `hospital_ownership` | See confirmed enum values in Provider Subtype section |
| `emergency_services` | `emergency_services` | `"Yes"` / `"No"` — convert to bool |
| `hospital_overall_rating` | `hospital_overall_rating` | String `"1"`–`"5"` |
| star rating footnote | `hospital_overall_rating_footnote` | Empty string when absent |
| `birthing_friendly_designation` | `meets_criteria_for_birthing_friendly_designation` | `"Y"` / `"N"` — convert to bool |
| `is_critical_access` | _(derived)_ | No separate bool field; `hospital_type == "Critical Access Hospitals"` |
| `dsh_status` | _(absent)_ | NOT in this dataset — source is HCRIS |
| `dsh_percentage` | _(absent)_ | NOT in this dataset — source is HCRIS |
| `is_teaching_hospital` | _(absent)_ | NOT in this dataset — source is HCRIS |
| `staffed_beds` | _(absent)_ | NOT in this dataset — source is HCRIS |
| `dual_eligible_proportion` | _(absent)_ | NOT in this dataset — source is HRRP Impact Files |

**Suppression encoding:** `"Not Available"` string in `hospital_overall_rating` when the hospital is not rated. All "Not Available" rating rows carry footnote `"16"` (too few measures to calculate) or `"19"` (results cannot be calculated for this reporting period) in `hospital_overall_rating_footnote`. Zero empty-string values for `hospital_overall_rating` were observed — the prior note in this document was incorrect. Footnote fields use empty string when no footnote applies. The measure group count fields (`count_of_facility_*`, `count_of_*_measures_better/worse/no_different`) also use `"Not Available"` when the hospital does not report enough measures for that group. Confirmed from 1000-row sample analysis 2026-03-14.

**Not_reported distinct state:** Rows where `hospital_overall_rating = "Not Available"` AND all group footnote fields carry `"19"` (results cannot be calculated) represent a distinct not_reported state from standard suppression (footnote `"16"` = insufficient volume). Rural Emergency Hospitals systematically receive footnote 19 across all measure group fields. This is not visible in the 200-row sample (insufficient Rural Emergency Hospital coverage); confirmed in 1000-row sample.

**Footnote code structure:** Single string field per measure group: `hospital_overall_rating_footnote`, `mort_group_footnote`, `safety_group_footnote`, `readm_group_footnote`, `pt_exp_group_footnote`, `te_group_footnote`. Empty string when no footnote. Group footnote fields contain a single numeric code as a string (not pipe-delimited). Codes observed in 1000-row sample: `5` (data submitted based on a sample), `16` (too few measures to calculate overall rating), `19` (results cannot be calculated for this reporting period — Rural Emergency Hospitals), `22` (measure not applicable to this hospital type). See `docs/data_dictionary.md` §Footnote Code Lookup Table for code definitions.

**CMS refresh schedule:** Quarterly (January, April, July, October). Specific measures within the star rating calculation vary — the star rating itself updates with each quarterly publication. Source: CMS Hospital Data Dictionary January 2026, Measure Descriptions section.

**Fixture file:** `tests/pipeline/fixtures/hospital/general_information.json`

**Notes:** `hospital_overall_rating` (star rating) lives here, not in a separate dataset. Address fields (`address`, `citytown`, `state`, `zip_code`, `countyparish`, `telephone_number`) are present — will be needed for datasets like HRRP that omit address fields. API uses snake_case for all field names (e.g., `hospital_overall_rating_footnote` not `Hospital overall rating footnote`).

---

### 2. Hospital Overall Star Rating

**Status:** [x] Resolved — not a separate dataset (DEC-001, 2026-03-14)

**Socrata Dataset ID:** N/A — field lives in `xubh-q36u` (Hospital General Information)

**Fields:** `hospital_overall_rating` (string "1"–"5", empty when not rated), `hospital_overall_rating_footnote` (empty string or numeric code)

**Suppression encoding:** `"Not Available"` string in `hospital_overall_rating` when footnote 16 applies (too few measures to calculate) or other exclusion footnotes. The prior note in this entry was incorrect — zero empty-string values for `hospital_overall_rating` were found in the 400-row sample. All unrated hospitals use `"Not Available"`, not empty string. Confirmed 2026-03-14 via analyze_encodings.py and manual row inspection.

**Footnote code structure:** Single numeric code in `hospital_overall_rating_footnote`. Empty string when no footnote.

**CMS refresh schedule:** Updated with each quarterly Care Compare publication (Jan/Apr/Jul/Oct). Methodology may change between releases.

**Fixture file:** Covered by `tests/pipeline/fixtures/hospital/general_information.json` (no separate fixture needed)

**Notes:** See DEC-001 in `docs/pipeline_decisions.md`. This entry is closed — no separate pipeline dataset for star ratings.

---

### 3. Timely and Effective Care

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `yv7e-xc69` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 138,129

**Sample file:** `scripts/recon/raw_samples/yv7e-xc69.json`

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | 6-char string |
| facility name | `facility_name` | |
| condition | `_condition` | **Leading underscore** — CMS API artifact. Normalize to `condition` in pipeline. See `docs/decisions.md`. |
| measure id | `measure_id` | |
| measure name | `measure_name` | |
| score | `score` | `"Not Available"` when suppressed |
| sample | `sample` | Denominator / case count |
| footnote | `footnote` | One code or comma-separated codes (e.g., `"1, 3, 29"`) |
| start date | `start_date` | MM/DD/YYYY string |
| end date | `end_date` | MM/DD/YYYY string |
| address | `address` | |
| city | `citytown` | |
| state | `state` | |
| zip | `zip_code` | |
| county | `countyparish` | |
| phone | `telephone_number` | |

**Suppression encoding:** `"Not Available"` string in `score` field (539/1000 rows in sample). Footnote codes observed in 1000-row sample: `1` (too few cases), `2` (data submitted based on a sample), `3` (results based on incomplete calendar year), `5` (results not available — hospital not reporting), `7` (CMS and hospital jointly reviewed data), `29` (measure methodology changed). Multiple footnotes comma-separated (e.g., `"1, 3"`, `"2, 3"`, `"1, 3, 29"`, `"2, 3, 29"`, `"3, 29"`). Confirmed from 1000-row sample; prior 200-row finding omitted codes 5 and 7.

**Footnote code structure:** Single `footnote` field per row. Contains one numeric code or comma-separated codes. Empty string when no footnote. Full code definitions in `docs/data_dictionary.md`.

**CMS refresh schedule:**
- Most measures: 12 months, refreshed **annually** (EDV-1, GMCS, OP-22, OP-29, OP-31, IMM-3, HH-HYPO, HH-HYPER, HH-ORAE, OP-40, Safe Use of Opioids, STK-02, STK-03, STK-05, VTE-01, VTE-02)
- SEP-1, OP-18a, OP-18b, OP-18c, OP-18d, OP-23: 12 months, refreshed **quarterly**
- IMM-3: 6 months, refreshed annually
Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/timely_effective_care.json`

**Notes:** High row count (~138K) reflects one row per facility per measure. `_condition` leading underscore must be handled in ingest — strip underscore before normalization. Sample field contains denominator/case count, useful for uncertainty display.

**EDV measure uses categorical text score:** The `EDV` measure (`measure_id = "EDV"`) carries `score = "very high"` or `score = "high"` (string category, not a numeric value), and `sample = ""` (empty string — not "Not Available"; this field is not applicable for a categorical measure). This cannot be stored in a Decimal `score` column. A schema decision is required before the Alembic migration: either a separate `score_text` column, or a nullable text override alongside the numeric `score`. See pipeline_decisions.md for the decision record.

---

### 4. HCAHPS Patient Survey

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `dgck-syfz` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 325,652

**Sample file:** `scripts/recon/raw_samples/dgck-syfz.json`

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | 6-char string |
| facility name | `facility_name` | |
| measure id | `hcahps_measure_id` | Different from other datasets — not `measure_id` |
| question | `hcahps_question` | Full question text |
| answer description | `hcahps_answer_description` | |
| star rating | `patient_survey_star_rating` | `"Not Applicable"` when footnote applies |
| star rating footnote | `patient_survey_star_rating_footnote` | Separate field |
| answer percent | `hcahps_answer_percent` | `"Not Applicable"` or `""` when suppressed |
| answer percent footnote | `hcahps_answer_percent_footnote` | Separate field |
| linear mean value | `hcahps_linear_mean_value` | |
| completed surveys | `number_of_completed_surveys` | |
| completed surveys footnote | `number_of_completed_surveys_footnote` | Separate field |
| response rate | `survey_response_rate_percent` | |
| response rate footnote | `survey_response_rate_percent_footnote` | Separate field |
| start date | `start_date` | MM/DD/YYYY |
| end date | `end_date` | MM/DD/YYYY |
| address | `address` | |
| city | `citytown` | |
| state | `state` | |
| zip | `zip_code` | |
| county | `countyparish` | |
| phone | `telephone_number` | |

**Suppression encoding:** Two distinct non-numeric states in value fields, confirmed from 2000-row sample:

1. `"Not Available"` — hospital did not have enough responses to report a value. Appears in `hcahps_answer_percent` (158/2000 rows), `patient_survey_star_rating` (65/2000 rows), `hcahps_linear_mean_value` (58/2000 rows). This is genuine suppression — insufficient sample.
2. `"Not Applicable"` — question type does not produce a value of that form. Appears in `patient_survey_star_rating` (1737/2000 rows — most rows are individual question/answer pairs, not composite summary rows; star rating only appears on summary rows), `hcahps_answer_percent` (497/2000 rows), `hcahps_linear_mean_value` (1766/2000 rows). This is structural absence, not suppression. Do not store as `suppressed = True`.

Each value field has its own companion footnote column. Confirmed from 2000-row sample (2026-03-14); prior entry based on 200-row sample + targeted pull at offset ~50,000.

**Footnote code structure:** **Multiple footnote fields per row** — one per value field (`patient_survey_star_rating_footnote`, `hcahps_answer_percent_footnote`, `number_of_completed_surveys_footnote`, `survey_response_rate_percent_footnote`). This differs from other datasets that use a single `footnote` field. Each footnote field contains a **single numeric code** or empty string. **No multi-code (comma-separated) values observed** in 2000-row sample. Footnote codes confirmed from 2000-row sample:
- `hcahps_answer_percent_footnote`: `1` (too few responses), `6` (fewer than 100 completed surveys), `10` (hospital did not participate), `11` (fewer than 50 completed surveys), `29` (methodology changed)
- `patient_survey_star_rating_footnote`: `15` (not enough surveys to calculate star rating)
- `number_of_completed_surveys_footnote`: `6`, `10`, `11`, `29`
- `survey_response_rate_percent_footnote`: `6`, `10`, `11`, `29`

AMB-6 resolved via prior targeted pull at offset ~50,000 (2026-03-14); full code set confirmed in 2000-row sample. Prior targeted-pull entry listed only codes `5`, `19`, `29` — those codes were not present in the 2000-row sample and may reflect a different reporting period; the 2000-row sample is authoritative.

**CMS refresh schedule:** 12 months collection period, refreshed **quarterly** (January, April, July, October). Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/hcahps.json`

**Notes:** High row count (~325K) reflects one row per facility per HCAHPS question/answer combination. Measure field is `hcahps_measure_id` not `measure_id` — pipeline normalizer must handle this. Multiple footnote columns require bespoke footnote parsing logic for this dataset.

---

### 5. Complications and Deaths

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `ynj2-r877` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 95,780

**Sample file:** `scripts/recon/raw_samples/ynj2-r877.json`

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | 6-char string |
| facility name | `facility_name` | |
| measure id | `measure_id` | |
| measure name | `measure_name` | |
| compared to national | `compared_to_national` | `"Number of Cases Too Small"`, `"Better than National Rate"`, `"No Different than National Rate"`, `"Worse than National Rate"` |
| denominator | `denominator` | `"Not Available"` when suppressed |
| score | `score` | `"Not Available"` when suppressed |
| lower estimate | `lower_estimate` | `"Not Available"` when suppressed |
| higher estimate | `higher_estimate` | `"Not Available"` when suppressed |
| footnote | `footnote` | Single code or comma-separated |
| start date | `start_date` | MM/DD/YYYY |
| end date | `end_date` | MM/DD/YYYY |
| address fields | `address`, `citytown`, `state`, `zip_code`, `countyparish`, `telephone_number` | |

**Suppression encoding:** Three suppression strings confirmed from 200-row sample (manual row inspection 2026-03-14):

1. `"Not Available"` in `score`, `denominator`, `lower_estimate`, `higher_estimate` — primary suppression indicator. 48/200 rows (24%) suppressed — high suppression rate expected for tail-risk measures.
2. `"Number of Cases Too Small"` in `compared_to_national` — **confirmed suppression signal**, always co-occurs with `score = "Not Available"` and footnote `"1"`. Must be stored as `suppressed = True`, not stored as a display value. 24/200 rows.
3. `"Not Applicable"` in `denominator` — **NOT suppression**. Appears exclusively on `PSI_90` (composite measure) where the score IS populated (e.g., `"0.95"`). PSI_90 is an index with no single patient-count denominator. Store as `null` denominator with methodology note, not as `suppressed = True`. 10/200 rows.

**`compared_to_national` dual phrasing:** This field uses two parallel phrasings for the same concept depending on measure type:
- `"No Different Than the National Rate"` / `"Worse Than the National Rate"` — individual outcome measures
- `"No Different Than the National Value"` / `"Worse Than the National Value"` — composite/index measures (PSI_90)

These must normalize to a canonical enum in the pipeline before storage. Do not store the raw strings as-is — they will cause display inconsistency and complicate querying.

**Footnote code structure:** Single `footnote` field per row. Contains one numeric code or comma-space-separated codes. Empty string when no footnote. Footnote codes observed in 1000-row sample: `1` (too few cases), `5` (results not available — hospital not reporting), `7` (CMS and hospital jointly reviewed data), `28` (measure statistical methodology revised), `29` (measure methodology changed). Combinations observed: `"1, 28"`. Prior 200-row entry omitted codes 28.

**CMS refresh schedule:**
- 30-day mortality measures: 36 months collection, refreshed **annually**
- Surgical complication (COMP-HIP-KNEE): 12 months, refreshed **annually**
- CMS Patient Safety Indicators (PSI): 24 months, refreshed **annually**
Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/complications_deaths.json`

**Notes:** Tail-risk dataset — includes mortality rates, surgical complications, PSI composite. High suppression rate in sample (24%). `lower_estimate` and `higher_estimate` provide confidence interval bounds — must be stored. Measure IDs include `MORT_30_AMI`, `MORT_30_HF`, `MORT_30_PN`, `MORT_30_COPD`, `MORT_30_CABG`, `COMP_HIP_KNEE`, PSI measures. All tail_risk_flag measures.

---

### 6. Healthcare-Associated Infections (HAI)

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `77hc-ibv8` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 172,404

**Sample file:** `scripts/recon/raw_samples/77hc-ibv8.json`

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | 6-char string |
| facility name | `facility_name` | |
| measure id | `measure_id` | |
| measure name | `measure_name` | |
| compared to national | `compared_to_national` | `"Not Available"` when suppressed |
| score | `score` | SIR value (Standardized Infection Ratio) or `"Not Available"` |
| footnote | `footnote` | Single code or comma-separated codes |
| start date | `start_date` | MM/DD/YYYY |
| end date | `end_date` | MM/DD/YYYY |
| address fields | `address`, `citytown`, `state`, `zip_code`, `countyparish`, `telephone_number` | |

**Note:** No `denominator` field in the API dataset (unlike the CSV which does not include denominator at measure level either). SIR is the scored value.

**Suppression encoding:** Two distinct suppression states confirmed via manual row inspection 2026-03-14:

1. `score = "Not Available"` + `compared_to_national = "Not Available"` + footnote `"13"` (or `"12"`, `"3"`) — **suppressed** (not enough cases; predicted infections < 1, or measure does not apply). 309/1000 rows (30.9%).
2. `score = "N/A"` + `compared_to_national` still populated + footnote `"8"` — **structurally inapplicable**, not suppressed. Appears exclusively on `CILOWER` sub-measures (`HAI_n_CILOWER`) when zero infections were observed, making the lower confidence-interval bound mathematically undefined. The hospital WAS evaluated; `compared_to_national` carries a valid value. Must be stored as `not_applicable`, never as `suppressed = True`. 22/1000 rows.

These two states are **not interchangeable** — using `"N/A"` to mean suppressed would be incorrect for CILOWER rows.

**Score field is heterogeneous by sub-measure type:** The `score` field carries different semantics depending on the `measure_id` suffix:
- `HAI_n_SIR` — decimal SIR ratio (e.g., `"0.268"`). Decimal rule applies.
- `HAI_n_CILOWER` / `HAI_n_CIUPPER` — decimal CI bound, or `"N/A"` (see above).
- `HAI_n_DOPC` / `HAI_n_ELIGCASES` / `HAI_n_NUMERATOR` — raw integer counts (e.g., `"111718"`). These are denominators and case counts, not rates. Decimal precision rule does not apply; store as integer.

The pipeline must branch on `measure_id` suffix when parsing `score` for this dataset.

**Footnote code structure:** Single `footnote` field per row. Contains one numeric code or comma-space-separated codes (e.g., `"3, 13"`, `"8, 29"`, `"3, 29"`, `"13, 29"`). **Delimiter is comma-space (", "), not pipe.** Empty string when no footnote. Footnote codes observed in 1000-row sample: `3` (fewer than required cases), `5` (results not available), `8` (no cases meeting inclusion criteria — CI bound not applicable), `12` (measure does not apply to this hospital type), `13` (results not available for this reporting period), `29` (measure methodology changed). Confirmed from 1000-row sample.

**CMS refresh schedule:** 12 months collection period, refreshed **quarterly** (January, April, July, October). Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/hai.json`

**Notes:** Tail-risk dataset. HAI measures include CLABSI, CAUTI, SSI (colon, hysterectomy), CDI, MRSA. Score field is SIR (ratio where 1.0 = national benchmark — lower-is-better). Measure IDs include `HAI_1` (CLABSI), `HAI_2` (CAUTI), `HAI_3` (SSI colon), `HAI_4` (SSI hysterectomy), `HAI_5` (MRSA), `HAI_6` (CDI), plus `_CILOWER`, `_CIUPPER` variants for confidence intervals. SES sensitivity is LOW per published literature (process compliance measures).

---

### 7. Unplanned Hospital Visits (Readmissions)

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `632h-zaca` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 67,046

**Sample file:** `scripts/recon/raw_samples/632h-zaca.json`

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | 6-char string |
| facility name | `facility_name` | |
| measure id | `measure_id` | |
| measure name | `measure_name` | |
| compared to national | `compared_to_national` | |
| denominator | `denominator` | `"Not Available"` when suppressed |
| score | `score` | `"Not Available"` when suppressed |
| lower estimate | `lower_estimate` | `"Not Available"` when suppressed |
| higher estimate | `higher_estimate` | `"Not Available"` when suppressed |
| number of patients | `number_of_patients` | Case count for readmission measures |
| number of patients returned | `number_of_patients_returned` | Additional count field (EDAC measures) |
| footnote | `footnote` | Single code or comma-separated |
| start date | `start_date` | MM/DD/YYYY |
| end date | `end_date` | MM/DD/YYYY |
| address fields | `address`, `citytown`, `state`, `zip_code`, `countyparish`, `telephone_number` | |

**Note:** `number_of_patients` and `number_of_patients_returned` are API-specific field names. The downloadable CSV calls the analogous field `Denominator`. Both should be stored as sample size fields.

**Suppression encoding:** `"Not Available"` string in `score`, `denominator`, `lower_estimate`, `higher_estimate` when suppressed. `"Not Applicable"` in `number_of_patients` and `number_of_patients_returned` for measures where a patient count is not applicable (e.g., EDAC measures use a different denominator concept).

**CMS inconsistent capitalization confirmed:** `compared_to_national` contains both `"Number of Cases Too Small"` (34 rows, 17%) and `"Number of cases too small"` (3 rows, 1.5%) — the same phrase with different capitalization in the same dataset snapshot. The normalize layer must use case-insensitive matching for this field; exact string comparison will miss rows. Confirmed from analyze_encodings.py run 2026-03-14.

Footnote codes observed in 1000-row sample: `1` (too few cases), `5` (results not available — hospital not reporting), `7` (CMS and hospital jointly reviewed data), `28` (measure statistical methodology revised), `29` (measure methodology changed). Combinations observed: `"1, 28"`. Score suppressed in 423/1000 rows. Prior 200-row entry omitted codes 7 and 28.

**Footnote code structure:** Single `footnote` field per row. Contains one numeric code or comma-separated codes. Empty string when no footnote. Confirmed from 1000-row sample.

**CMS refresh schedule:**
- By Condition (AMI, HF, PN, COPD readmissions; EDAC measures): 36 months, refreshed **annually**
- By Procedure (colonoscopy, CABG, hip/knee, surgery, chemo): 36 months for surgical measures, 12 months for chemo/surgery; refreshed **annually**
- Overall (HWR — Hospital-Wide Readmissions): 36 months, refreshed **annually**
Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/readmissions.json`

**Notes:** SES-sensitive dataset — HIGH SES sensitivity for 30-day readmission measures. Includes READM-30-AMI, READM-30-HF, READM-30-PN, READM-30-COPD, READM-30-HIP-KNEE, HWR, OP-32 (colonoscopy), OP-35 (chemo), OP-36 (CABG), OP-37 (surgery), EDAC-30-AMI, EDAC-30-HF, EDAC-30-PN. Confidence interval bounds (`lower_estimate`, `higher_estimate`) must be stored per Data Integrity Rule 8.

---

### 8. Outpatient Imaging Efficiency

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `wkfw-kthe` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 18,500

**Sample file:** `scripts/recon/raw_samples/wkfw-kthe.json`

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | 6-char string |
| facility name | `facility_name` | |
| measure id | `measure_id` | |
| measure name | `measure_name` | |
| score | `score` | `"Not Available"` when suppressed |
| footnote | `footnote` | Single code or comma-separated |
| start date | `start_date` | MM/DD/YYYY |
| end date | `end_date` | MM/DD/YYYY |
| address fields | `address`, `citytown`, `state`, `zip_code`, `countyparish`, `telephone_number` | |

**Note:** No `compared_to_national` field in this dataset. No `denominator` field. Score is a percentage rate.

**Suppression encoding:** `"Not Available"` string in `score` when suppressed (546/1000 rows). Footnote codes observed in 1000-row sample: `1` (too few cases), `5` (results not available — hospital not reporting), `7` (CMS and hospital jointly reviewed data), `19` (results cannot be calculated for this reporting period), `29` (measure methodology changed). Prior 200-row entry omitted codes 5 and 19.

**Not_reported distinct state:** Rows where `score = "Not Available"` AND `footnote = "19"` represent a distinct not_reported state (hospital's results cannot be calculated, e.g. insufficient operational period). 48/1000 rows carry footnote 19. This is separate from footnote 1 (too few cases) and footnote 5 (not reporting). The normalizer must store footnote 19 rows as `not_reported`, not `suppressed`.

**Footnote code structure:** Single `footnote` field per row. Contains one numeric code or comma-separated codes. Empty string when no footnote. Confirmed from sample.

**CMS refresh schedule:** 12 months collection period, refreshed **annually**. Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/imaging_efficiency.json`

**Notes:** CMS full name for this dataset is "Use of Medical Imaging: Outpatient Imaging Efficiency (OIE)". **Four** active measures as of January 2026: OP-8 (MRI Lumbar Spine for Low Back Pain), OP-10 (Abdomen CT — use of contrast), OP-13 (Cardiac Imaging for Preoperative Risk Assessment), OP-39 (Breast Cancer Screening Recall Rates). Lower-is-better for all measures (lower rate = more efficient/appropriate use). SES sensitivity LOW. **OP-39 was missed in the initial Phase 0 analysis (2026-03-14) and added during MEASURE_REGISTRY drafting (2026-03-15).** OP-39 measures the percentage of screening mammograms resulting in a recommendation for additional imaging; ACR recommends recall rates below 10%. Note: extremely low recall rates (<5%) may indicate under-reading — the display layer should note clinically appropriate bounds.

---

### 9. Medicare Hospital Spending Per Patient

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `rrqw-56er` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 4,625

**Sample file:** `scripts/recon/raw_samples/rrqw-56er.json`

**Note:** CMS API title is "Medicare Spending Per Beneficiary" (MSPB). The dataset is referenced as `Medicare_Hospital_Spending_Per_Patient-Hospital.csv` in downloadable form but the API uses the MSPB name.

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | 6-char string |
| facility name | `facility_name` | |
| measure id | `measure_id` | `"MSPB_1"` |
| measure name | `measure_name` | |
| score | `score` | Ratio (e.g., `"0.97"`); `"Not Available"` when suppressed |
| footnote | `footnote` | Single code or comma-separated |
| start date | `start_date` | MM/DD/YYYY |
| end date | `end_date` | MM/DD/YYYY |
| address fields | `address`, `citytown`, `state`, `zip_code`, `countyparish`, `telephone_number` | |

**Suppression encoding:** `"Not Available"` string in `score` (208/1000 rows). Footnote codes observed in 1000-row sample: `1` (too few cases), `5` (results not available — hospital not reporting), `19` (results cannot be calculated for this reporting period), `29` (measure methodology changed). **Correction:** Prior 200-row entry described footnote 19 as "IQR/OQR participation required" — this was incorrect. Footnote 19 means results cannot be calculated; no IQR/OQR framing applies to MSPB.

**Not_reported distinct state:** Rows where `score = "Not Available"` AND `footnote = "19"` represent hospitals where MSPB cannot be calculated for the current period (37/1000 rows). Distinct from footnote 1 (too few cases) and footnote 5 (not reporting). Store as `not_reported`.

**Footnote code structure:** Single `footnote` field per row. Contains one numeric code or comma-separated codes. Empty string when no footnote. Confirmed from sample.

**CMS refresh schedule:** 12 months collection period, refreshed **annually**. There is also a quarterly 6-decimal version (`HOSPITAL_QUARTERLY_MSPB_6_DECIMALS.csv`) accessible via the PDC — this is a separate downloadable CSV and not available via the primary Socrata API. Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/spending_per_patient.json`

**Notes:** MSPB-1 is the single measure in this dataset. Score is a ratio where 1.0 = national median (lower-is-better — spending below national median). SES sensitivity MODERATE — spending is risk-adjusted for clinical factors but not fully for patient socioeconomic mix. Only ~4,600 rows (one per facility with MSPB data), lower than most other datasets.

---

### 10. Payment and Value of Care

**Status:** [x] Resolved — RETIRED by CMS July 2025 (DEC-002, 2026-03-14)

**Socrata Dataset ID:** N/A — dataset does not exist

**Finding:** CMS retired the PAYM measures (PAYM-30-AMI, PAYM-30-HF, PAYM-30-PN,
PAYM-90-HIP-KNEE) and the composite Value of Care measure effective the July 2025
Care Compare release. No dataset exists in the current CMS Provider Data DKAN catalog.

**Decision:** Removed from scope. No pipeline code, no MEASURE_REGISTRY entries,
no fixture file. See DEC-002 in `docs/pipeline_decisions.md`.

**Fixture file:** Not applicable.

---

### 11. Health Equity Summary

**Status:** [x] Resolved — RETIRED by CMS October 2025 (DEC-003, 2026-03-14)

**Socrata Dataset ID:** N/A — dataset does not exist

**Finding:** The HCHE measure ("number of areas 0–5 that the hospital used to measure
their hospital commitment to health equity") was retired by CMS effective the October
2025 Care Compare release. There was never a dedicated Health Equity dataset — HCHE
was a single measure in the outpatient quality reporting program. No current CMS
public hospital reporting dataset covers health equity at the facility level.

**Decision:** Removed from scope. No pipeline code, no MEASURE_REGISTRY entries,
no fixture file. See DEC-003 in `docs/pipeline_decisions.md`.

**Fixture file:** Not applicable.

---

### 12. Hospital Readmissions Reduction Program (HRRP)

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `9n3s-kdb3` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 18,330

**Sample file:** `scripts/recon/raw_samples/9n3s-kdb3.json`

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | Numeric in API (NOT zero-padded 6-char) — must normalize to 6-char CCN |
| facility name | `facility_name` | |
| state | `state` | |
| measure name | `measure_name` | e.g., `"READM-30-HIP-KNEE-HRRP"` |
| number of discharges | `number_of_discharges` | `"N/A"` string when suppressed (not `"Not Available"`) |
| excess readmission ratio | `excess_readmission_ratio` | Numeric string, e.g., `"0.9875"` |
| predicted readmission rate | `predicted_readmission_rate` | |
| expected readmission rate | `expected_readmission_rate` | |
| number of readmissions | `number_of_readmissions` | `"Too Few to Report"` string when suppressed |
| footnote | `footnote` | Single code or empty string |
| start date | `start_date` | MM/DD/YYYY |
| end date | `end_date` | MM/DD/YYYY |

**Note:** No address fields in HRRP API dataset. CCN (`facility_id`) is numeric, not zero-padded — must zero-pad to 6 chars in normalizer. No separate `facility_name` / address — must join to General Information on CCN for display context.

**Suppression encoding:** Three distinct states confirmed via manual row inspection 2026-03-14:

1. **Normal**: all measure fields populated, `footnote = ""`
2. **Count-only suppression** (privacy disclosure): `number_of_discharges = "N/A"`, `number_of_readmissions = "Too Few to Report"`, but `excess_readmission_ratio` and rate fields **still populated**. The ratio was calculated; only the raw counts are suppressed to protect small-cell privacy. This is not measure suppression — it is a count-field-level disclosure rule. Must store `excess_readmission_ratio` normally; store count fields with `suppressed = True`.
3. **Full suppression**: all measure fields `"N/A"`, footnote `"1"` or `"5"`. The measure was not calculated at all.

States 2 and 3 are **not interchangeable**. "Too Few to Report" in `number_of_readmissions` always co-occurs with a populated ratio; `"N/A"` in all fields means no ratio exists.

Footnote codes confirmed in 1000-row sample: `"1"` (too few discharges to calculate), `"5"` (hospital not participating in program), `"7"` (CMS and hospital jointly reviewed data), `"29"` (measure methodology changed). Prior 200-row entry omitted code 7.

**Footnote code structure:** Single `footnote` field per row. One numeric code or empty string. No comma-separated multi-codes observed in 1000-row sample. The `suppressed` and `not_reported` fixture rows intentionally use different footnote codes: footnote `"5"` (non-participating) for suppressed, footnote `"1"` (too few discharges) for not_reported — these are distinguishably distinct states.

**CMS refresh schedule:** Fiscal year collection period (3 years of claims), refreshed **annually** (updated in January Care Compare release each year). Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/hrrp.json`

**Notes:** Stored in `provider_payment_adjustments`, not `provider_measure_values`. HRRP covers: READM-30-AMI-HRRP, READM-30-HF-HRRP, READM-30-PN-HRRP, READM-30-COPD-HRRP, READM-30-HIP-KNEE-HRRP, READM-30-CABG-HRRP. SES-sensitive — see `docs/ses-context.md`. The `excess_readmission_ratio` is the key payment adjustment input (ERR > 1.0 triggers penalty). `dual_eligible_proportion` is NOT in this dataset (see DEC-005).

---

### 13. Hospital-Acquired Condition Reduction Program (HACRP)

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `yq43-i98g` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 3,055

**Sample file:** `scripts/recon/raw_samples/yq43-i98g.json`

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | Numeric (not zero-padded) — must normalize to 6-char CCN |
| facility name | `facility_name` | |
| state | `state` | |
| fiscal year | `fiscal_year` | e.g., `"2026"` |
| psi 90 composite value | `psi_90_composite_value` | Numeric string |
| psi 90 composite footnote | `psi_90_composite_value_footnote` | Empty string or code |
| psi 90 w z score | `psi_90_w_z_score` | Winsorized Z-score |
| psi 90 w z footnote | `psi_90_w_z_footnote` | |
| psi 90 start date | `psi_90_start_date` | MM/DD/YYYY |
| psi 90 end date | `psi_90_end_date` | MM/DD/YYYY |
| clabsi sir | `clabsi_sir` | Numeric string |
| clabsi sir footnote | `clabsi_sir_footnote` | |
| clabsi w z score | `clabsi_w_z_score` | |
| clabsi w z footnote | `clabsi_w_z_footnote` | |
| cauti sir | `cauti_sir` | |
| cauti sir footnote | `cauti_sir_footnote` | |
| cauti w z score | `cauti_w_z_score` | |
| cauti w z footnote | `cauti_w_z_footnote` | |
| ssi sir | `ssi_sir` | |
| ssi sir footnote | `ssi_sir_footnote` | |
| ssi w z score | `ssi_w_z_score` | |
| ssi w z footnote | `ssi_w_z_footnote` | |
| cdi sir | `cdi_sir` | |
| cdi sir footnote | `cdi_sir_footnote` | |
| cdi w z score | `cdi_w_z_score` | |
| cdi w z footnote | `cdi_w_z_footnote` | |
| mrsa sir | `mrsa_sir` | |
| mrsa sir footnote | `mrsa_sir_footnote` | |
| mrsa w z score | `mrsa_w_z_score` | |
| mrsa w z footnote | `mrsa_w_z_footnote` | |
| hai start date | `hai_measures_start_date` | MM/DD/YYYY |
| hai end date | `hai_measures_end_date` | MM/DD/YYYY |
| total hac score | `total_hac_score` | Numeric (can be negative) |
| total hac score footnote | `total_hac_score_footnote` | |
| payment reduction | `payment_reduction` | `"Yes"` / `"No"` |
| payment reduction footnote | `payment_reduction_footnote` | |

**Suppression encoding:** **Correction from 200-row finding.** The 200-row sample noted "No 'Not Available' observed; scores are numeric or empty." This was a sampling artifact. The 1000-row sample confirms: HACRP uses **`"N/A"`** (not `"Not Available"`) as the suppression sentinel across all SIR fields and `total_hac_score`. This is a distinct encoding from all other hospital datasets. Suppressed field counts in 1000-row sample:
- `mrsa_sir`: 248/1000 rows `"N/A"`
- `ssi_sir`: 222/1000 rows `"N/A"`
- `clabsi_sir`: 216/1000 rows `"N/A"`
- `cauti_sir`: 164/1000 rows `"N/A"`
- `psi_90_composite_value`: 67/1000 rows `"N/A"`
- `cdi_sir`: 63/1000 rows `"N/A"`
- `total_hac_score`: 32/1000 rows `"N/A"`

The suppression sentinel for HACRP is `"N/A"`, not `"Not Available"`. The normalize layer must handle this as a separate branch. Footnote-per-field model: each SIR/score has its own companion footnote column. This dataset has **one row per facility per fiscal year** (wide format, not long format).

**Footnote code structure:** One footnote column per SIR/score field. Each contains a single numeric code or empty string. **This differs significantly from other datasets** — there is no single `footnote` field; instead each metric has a dedicated footnote column. Footnote codes observed in 1000-row sample: `5` (results not available — hospital not reporting/participating), `11` (fewer than required cases), `12` (measure does not apply to this hospital type), `13` (results not available for this reporting period), `18` (results suppressed due to confidentiality requirements), `23` (hospital excluded from this program), `29` (measure methodology changed). See `docs/data_dictionary.md` for full code definitions.

**CMS refresh schedule:**
- PSI-90 collection: 15 months; HACRP Domain 2 (CAUTI, CDI, CLABSI, MRSA, SSI): 24 months; Total HAC Score: 30 months. Refreshed **annually**.
Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/hacrp.json`

**Notes:** Stored in `provider_payment_adjustments`. Wide-format dataset (one row per facility). `payment_reduction` = `"Yes"` when hospital receives 1% payment reduction penalty. `total_hac_score` can be negative. CCN (`facility_id`) is numeric — must zero-pad to 6 chars. No address fields; join to General Information for display context.

---

### 14. Hospital Value-Based Purchasing Program (VBP)

**Status:** [x] Confirmed 2026-03-14. API fields, suppression, footnote structure, refresh schedule confirmed.

**Socrata Dataset ID:** `ypbt-wvdk` (confirmed via live DKAN API call 2026-03-14)

**Total rows in dataset:** 2,455

**Sample file:** `scripts/recon/raw_samples/ypbt-wvdk.json`

**Expected fields confirmed:** [x]

| Schema field | Actual API Key | Notes |
|---|---|---|
| facility id | `facility_id` | Numeric (not zero-padded) — must normalize to 6-char CCN |
| facility name | `facility_name` | |
| state | `state` | |
| fiscal year | `fiscal_year` | e.g., `"2026"` |
| total performance score | `total_performance_score` | Numeric string |
| clinical outcomes domain | `unweighted_normalized_clinical_outcomes_domain_score` | |
| efficiency domain | `unweighted_normalized_efficiency_and_cost_reduction_domain_score` | |
| safety domain | `unweighted_normalized_safety_domain_score` | |
| person engagement domain | `unweighted_person_and_community_engagement_domain_score` | |
| weighted clinical outcomes | `weighted_normalized_clinical_outcomes_domain_score` | |
| weighted efficiency | `weighted_efficiency_and_cost_reduction_domain_score` | |
| weighted safety | `weighted_safety_domain_score` | |
| weighted person engagement | `weighted_person_and_community_engagement_domain_score` | |
| address fields | `address`, `citytown`, `zip_code`, `countyparish` | |

**Note:** The API dataset (`ypbt-wvdk`) provides domain scores and TPS only. Individual measure achievement/improvement points (e.g., MORT-30-AMI achievement threshold, benchmark, performance rate, achievement points) are available only in downloadable CSV files (`hvbp_clinical_outcomes.csv`, `hvbp_safety.csv`, etc.) — not in the Socrata API. The actual **incentive payment adjustment percentage** (the final VBP payment modifier) is in `hvbp_tps.csv` (downloadable only, not in the Socrata API). See `docs/decisions.md` for the scope decision.

**Suppression encoding:** No suppression observed across 1000-row sample (full confirmation). TPS and domain scores have numeric values in all 1000 rows. No `"Not Available"`, `"N/A"`, or empty values in any score field. Hospitals that do not receive a VBP score appear to be omitted from the dataset rather than included with a suppression sentinel. No footnote fields present in this API dataset.

**Footnote code structure:** No footnote fields in this API dataset. Confirmed across 1000 rows.

**CMS refresh schedule:** 12 months, refreshed **annually** (updated in each January Care Compare release for the new fiscal year). Source: CMS Hospital Data Dictionary January 2026.

**Fixture file:** `tests/pipeline/fixtures/hospital/vbp.json`

**Notes:** Stored in `provider_payment_adjustments`. One row per facility per fiscal year. VBP program adjusts Medicare inpatient payments based on TPS: hospitals below 50th percentile receive a payment reduction, those above may receive a bonus. CCN (`facility_id`) is numeric — must zero-pad to 6 chars. The VBP TPS and domain scores are the primary values needed for the payment adjustment record. Individual measure scores deferred to Phase 2 (requires downloadable CSV ingestion).

---

## Provider Subtype Enum Values

**Status:** [x] Confirmed 2026-03-15 against full dataset (5,426 rows) of xubh-q36u via
live API query. Previous 1000-row sample missed `"Long-term"` (only 4 rows in full dataset).

Confirmed `hospital_type` enum values from Hospital General Information (xubh-q36u):

| CMS API String | Count (full dataset) | % of total | Notes |
|---|---|---|---|
| `Acute Care Hospitals` | 3,116 | 57.4% | Most common |
| `Critical Access Hospitals` | 1,376 | 25.4% | Maps to `is_critical_access = true` — no separate boolean field |
| `Psychiatric` | 633 | 11.7% | Inpatient psychiatric facilities |
| `Acute Care - Veterans Administration` | 132 | 2.4% | VHA facilities |
| `Childrens` | 94 | 1.7% | Children's hospitals |
| `Rural Emergency Hospital` | 39 | 0.7% | Relatively new designation (2023+) |
| `Acute Care - Department of Defense` | 32 | 0.6% | DoD facilities |
| `Long-term` | 4 | 0.07% | Long-Term Acute Care Hospitals (LTACHs). **Missed in 1000-row sample.** Only 4 facilities: Sage Specialty Hospital (LA), Intensive Specialty Hospital (LA), Allegiance Specialty Hospital of Greenville (MS), Silver Lake Hospital LTACH (NJ). |

**Total: 8 distinct values confirmed across all 5,426 rows.**

Confirmed `hospital_ownership` enum values from Hospital General Information (xubh-q36u):

| CMS API String | Count (full dataset) | % of total |
|---|---|---|
| `Voluntary non-profit - Private` | 2,304 | 42.5% |
| `Proprietary` | 1,069 | 19.7% |
| `Government - Hospital District or Authority` | 519 | 9.6% |
| `Government - Local` | 401 | 7.4% |
| `Voluntary non-profit - Other` | 355 | 6.5% |
| `Voluntary non-profit - Church` | 271 | 5.0% |
| `Government - State` | 209 | 3.9% |
| `Veterans Health Administration` | 132 | 2.4% |
| `Physician` | 76 | 1.4% |
| `Government - Federal` | 43 | 0.8% |
| `Department of Defense` | 32 | 0.6% |
| `Tribal` | 15 | 0.3% |

**Total: 12 distinct values confirmed across all 5,426 rows.**

**Note:** Values confirmed against the **full** 5,426-row dataset on 2026-03-15 (not a
sample). The 1000-row sample used in prior sessions missed `"Long-term"` due to its
extreme rarity (4 of 5,426 rows = 0.07%). Per DEC-013, both `hospital_type` and
`hospital_ownership` are stored as `varchar` (not PostgreSQL enum) with Pydantic
allowlist validation + unknown-value logging. See `docs/pipeline_decisions.md` §DEC-013.

---

## Hospital Context Fields: Source Confirmation

**Status:** [~] Partially confirmed 2026-03-14.

The following provider context fields listed in `ses-context.md` were investigated
against live API responses during Phase 0 reconnaissance.

### Confirmed in xubh-q36u (Hospital General Information)

| Field (schema) | API key | Notes |
|---|---|---|
| `hospital_type` | `hospital_type` | String value; "Critical Access Hospitals" maps to `is_critical_access` |
| `hospital_ownership` | `hospital_ownership` | String value |
| `emergency_services` | `emergency_services` | `"Yes"` / `"No"` — convert to bool |
| `birthing_friendly_designation` | `meets_criteria_for_birthing_friendly_designation` | `"Y"` / `"N"` — convert to bool. Relevant for maternity care decisions. |
| `hospital_overall_rating` | `hospital_overall_rating` | String `"1"`–`"5"`; footnote in `hospital_overall_rating_footnote` |

### NOT in xubh-q36u — Deferred

| Field (schema) | Previously assumed source | Actual source | Status |
|---|---|---|---|
| `dsh_status` | CMS Hospital General Information | HCRIS Cost Reports (Worksheet E) | Deferred; needs pipeline_decisions.md entry |
| `dsh_percentage` | CMS Hospital General Information | HCRIS Cost Reports (Worksheet E) | Deferred; needs pipeline_decisions.md entry |
| `is_teaching_hospital` | CMS Hospital General Information | HCRIS Cost Reports (resident-to-bed ratio) | Deferred; needs pipeline_decisions.md entry |
| `staffed_beds` | CMS Hospital General Information | HCRIS Cost Reports (Worksheet S-3, Part I) | Deferred; needs pipeline_decisions.md entry |
| `dual_eligible_proportion` | CMS supplemental data | HRRP Impact Files / IPPS Supplementary | Deferred; needs pipeline_decisions.md entry |
| `urban_rural_classification` | CMS Provider of Services file | Provider of Services file (healthdata.gov candidate ID m5p7-uvg2) | Pending confirmation of dataset ID and API access |

---

## Cross-Dataset Notes

### SES Context Fields: Exhaustive Search Summary (2026-03-14)

The following methods were used to search for `dsh_status`, `dsh_percentage`,
`is_teaching_hospital`, `staffed_beds`, `dual_eligible_proportion`, and
`urban_rural_classification` across all accessible CMS data:

| Method | Result |
|---|---|
| DKAN catalog keyword search (10+ queries) | Zero matches for any of these fields |
| All 11 raw sample JSON files scanned (grep) | Zero matches across all datasets |
| CMS Hospital Data Dictionary PDF (1.29MB, Oct 2025) | Downloaded; fully binary-compressed, unreadable without PDF library. Documented as 29 columns — none are the missing fields |
| Socrata-to-DKAN mapping PDF (319KB) | Downloaded; fully binary-compressed, zero readable strings |
| Legacy Socrata API (data.cms.gov/resource/) | HTTP 410 Gone — deprecated |
| healthdata.gov Socrata (m5p7-uvg2) | HTTP 404 — dataset removed |
| catalog.data.gov CKAN API | Timeout |
| Direct CSV download URL patterns (downloads.cms.gov) | All HTTP 404 |
| data.cms.gov/provider-characteristics page | JS-rendered SPA, no API endpoint accessible |

**Conclusion:** These fields are not available via any programmatic CMS API as of
2026-03-14. Their sources (HCRIS, POS CSV, IPPS supplemental files) all require
non-API ingestion. See DEC-004, DEC-005, DEC-006 in `docs/pipeline_decisions.md`.

---

## Field Name Cross-Reference Analysis

Produced: 2026-03-14. Systematic comparison of field names referenced in `CLAUDE.md`
and rules files against actual CMS Socrata API field names observed in
`scripts/recon/raw_samples/*.json` (10–11 datasets, 1000 rows each). Uses
`docs/HOSPITAL_Data_Dictionary.pdf` (January 2026) as a reference for CMS-canonical
field names.

---

### Group A: Fields Referenced in CLAUDE.md / Rules That Are Absent from API Responses

Fields that `CLAUDE.md`, `ses-context.md`, or other rules files reference by name as
schema targets, but which do not appear in any CMS Provider Data Catalog API response.

| Referenced Field | Expected Dataset | API Status | Best-Guess Mapping | Disposition |
|---|---|---|---|---|
| `dsh_status` | `xubh-q36u` | **Absent** | None via API — HCRIS Worksheet E only | Deferred (DEC-004) — schema column nullable |
| `dsh_percentage` | `xubh-q36u` | **Absent** | None via API — HCRIS Worksheet E only | Deferred (DEC-004) — schema column nullable |
| `is_teaching_hospital` | `xubh-q36u` | **Absent** | None via API — HCRIS resident-to-bed ratio | Deferred (DEC-004) — schema column nullable |
| `staffed_beds` | `xubh-q36u` | **Absent** | None via API — HCRIS Worksheet S-3, Part I | Deferred (DEC-004) — schema column nullable |
| `dual_eligible_proportion` | `9n3s-kdb3` or supplemental | **Absent from all 11 datasets** | None via Provider Data Catalog API | Deferred (DEC-005) — schema column nullable |
| `urban_rural_classification` | Provider of Services file | **Absent** | POS file (healthdata.gov) — no confirmed DKAN ID | Deferred (DEC-006) — schema column nullable |
| `measure_id` (HRRP rows) | `9n3s-kdb3` | **Absent** — only `measure_name` present | `measure_name` contains parseable IDs (e.g. `"READM-30-HIP-KNEE-HRRP"`) | See note A-1 below |
| `hospital_overall_rating` as integer | `xubh-q36u` | Present but as **string** `"1"`–`"5"`, not integer | `hospital_overall_rating` — cast to int in normalizer | Confirmed — cast on ingest |
| `birthing_friendly_designation` (schema alias) | `xubh-q36u` | Present as full CMS name | `meets_criteria_for_birthing_friendly_designation` | Confirmed — schema uses abbreviated alias; API uses full name |

**Note A-1 (HRRP `measure_id`):** The `provider_payment_adjustments` table is keyed
by `(provider_id, program, program_year)` per Data Integrity Rule 5 — no `measure_id`
column is required for payment adjustment rows. The `measure_name` field
(`"READM-30-HIP-KNEE-HRRP"`) is the display label; the pipeline must not attempt to
join HRRP rows to `MEASURE_REGISTRY` using it. HRRP rows go to
`provider_payment_adjustments`, not `provider_measure_values`. Resolution confidence: **HIGH**.

---

### Group B: Fields Present in API Responses Not Referenced in CLAUDE.md / Rules

Fields observed in raw API samples that are not mentioned in `CLAUDE.md` or rules
files but appear potentially relevant to the pipeline.

#### B.1 Hospital General Information (xubh-q36u) — 18 Unreferenced Summary Fields

The General Information dataset has 38 API fields. The following 18 are present in
every row but not mentioned in `CLAUDE.md` or any rules file:

**Domain-level measure count fields (`count_of_facility_*`):**

| API Field | Description | Pipeline Relevance |
|---|---|---|
| `count_of_facility_mort_measures` | Number of mortality measures the hospital submits | Reporting completeness — thin reporting base = higher uncertainty |
| `count_of_facility_readm_measures` | Number of readmission measures submitted | As above |
| `count_of_facility_safety_measures` | Number of safety measures submitted | As above |
| `count_of_facility_pt_exp_measures` | Number of patient experience measures submitted | As above |
| `count_of_facility_te_measures` | Number of T&E measures submitted | As above |

**Domain-level performance breakdown fields (`count_of_*_measures_better/no_different/worse`):**

| API Field | Description | Pipeline Relevance |
|---|---|---|
| `count_of_mort_measures_better` / `_no_different` / `_worse` | Mortality measure performance breakdown | Aggregate signal without drilling into individual measures |
| `count_of_readm_measures_better` / `_no_different` / `_worse` | Readmission breakdown (HIGH SES sensitivity) | Interpretive context for readmission domain |
| `count_of_safety_measures_better` / `_no_different` / `_worse` | Safety measure breakdown | Tail-risk signal |

**Star rating group measure count and footnote fields:**

| API Field | Description | Pipeline Relevance |
|---|---|---|
| `mort_group_measure_count` | Measures in mortality group used for star rating | Star rating calculation input — governs whether group score exists |
| `mort_group_footnote` | Footnote code for mortality group aggregate | Already partially documented under suppression encoding |
| `readm_group_measure_count` / `readm_group_footnote` | Readmission group count and footnote | As above |
| `safety_group_measure_count` / `safety_group_footnote` | Safety group count and footnote | As above |
| `pt_exp_group_measure_count` / `pt_exp_group_footnote` | Patient experience group | As above |
| `te_group_measure_count` / `te_group_footnote` | T&E group | As above |

**Assessment:** These fields are directly relevant to Principle 1 (surface uncertainty,
never suppress it). `count_of_facility_*_measures` and `*_group_measure_count` expose
when a hospital has a thin reporting base. The `*_group_footnote` fields govern whether
a domain-level score is valid in the star rating calculation (footnotes `16` and `19`
already confirmed as suppression states).

**Decision (DEC-009, 2026-03-14):** Store 10 fields in the `providers` table: the 5
`count_of_facility_*_measures` fields (CMS-authoritative counts, integrity check signal)
and the 5 `*_group_footnote` fields (non-derivable star rating validity flags). Discard
the 9 `count_of_*_measures_better/no_different/worse` fields (derivable from
`provider_measure_values.compared_to_national`) and the 5 `*_group_measure_count`
fields (redundant with `count_of_facility_*`). See DEC-009 in `docs/pipeline_decisions.md`.

#### B.2 HCAHPS (dgck-syfz) — `hcahps_linear_mean_value` Not Referenced

`hcahps_linear_mean_value` appears in the HCAHPS dataset but is not mentioned in
`CLAUDE.md` or any rules file. This is the linear transformation of the HCAHPS percent
score used for cross-hospital comparison; it removes ceiling/floor effects that affect
raw percentage scores. CMS uses linear mean values — not percent-positive scores — in
the HCAHPS star rating calculation.

Present on: summary-level composite HCAHPS rows only. `"Not Applicable"` on
individual answer-level rows (1766/2000 rows in sample). `"Not Available"` on
suppressed rows (58/2000).

**Assessment:** More useful for comparison purposes than `hcahps_answer_percent` for
the subset of composite HCAHPS measures. Should be stored alongside `score` (which
captures `hcahps_answer_percent`).

**Decision (DEC-010, 2026-03-14):** Discard. This is a CMS scoring smoothing artifact
that applies to ~11% of rows and adds schema complexity without proportionate benefit.
`hcahps_answer_percent` is the consumer-verifiable primary score. See DEC-010 in
`docs/pipeline_decisions.md`.

#### B.3 VBP (ypbt-wvdk) — Domain Score Column Naming Not Mapped to Schema

Eight domain-score columns are present in the VBP dataset. `CLAUDE.md` identifies
VBP as a payment adjustment program but does not define schema column names for the
domain score fields. The CMS API column names are very long:

| API Column (CMS name) | Domain | Weight status |
|---|---|---|
| `unweighted_normalized_clinical_outcomes_domain_score` | Clinical Outcomes | Unweighted |
| `unweighted_normalized_efficiency_and_cost_reduction_domain_score` | Efficiency | Unweighted |
| `unweighted_normalized_safety_domain_score` | Safety | Unweighted |
| `unweighted_person_and_community_engagement_domain_score` | Patient Engagement | Unweighted |
| `weighted_normalized_clinical_outcomes_domain_score` | Clinical Outcomes | Weighted |
| `weighted_efficiency_and_cost_reduction_domain_score` | Efficiency | Weighted |
| `weighted_safety_domain_score` | Safety | Weighted |
| `weighted_person_and_community_engagement_domain_score` | Patient Engagement | Weighted |

**Note:** The naming convention is inconsistent — `unweighted_normalized_*` for some
domains vs. `unweighted_*` for patient engagement; `weighted_normalized_*` for clinical
outcomes vs. `weighted_*` for efficiency, safety, and patient engagement. This is a
CMS naming artifact, not a data anomaly.

**Decision (DEC-011, 2026-03-14):** Use CMS API names directly as schema column names,
with one adjustment: `unweighted_normalized_efficiency_and_cost_reduction_domain_score`
→ `unweighted_efficiency_and_cost_reduction_domain_score` (drop `_normalized_` to avoid
the 63-char PostgreSQL identifier boundary). All other columns use CMS names verbatim.
See DEC-011 in `docs/pipeline_decisions.md`.

#### B.4 HACRP (yq43-i98g) — Winsorized Z-Score Fields Not Referenced

Each HAI component in the HACRP dataset has a companion `*_w_z_score` field:
`clabsi_w_z_score`, `cauti_w_z_score`, `ssi_w_z_score`, `cdi_w_z_score`,
`mrsa_w_z_score`, `psi_90_w_z_score`. These Winsorized Z-scores are the inputs to the
`total_hac_score` calculation and are not mentioned in `CLAUDE.md` or rules files.

**Assessment:** These are intermediate calculation values, not patient-facing quality
signals. The `total_hac_score` and `payment_reduction` fields are sufficient for the
payment adjustment record. The Z-scores provide auditability but are not needed for
display.

**Decision (DEC-012, 2026-03-14):** Discard. Intermediate calculation values with no
patient-facing signal. `total_hac_score` and `payment_reduction` are sufficient for
the payment adjustment record. See DEC-012 in `docs/pipeline_decisions.md`.

#### B.5 HACRP / HAI SIR Field Overlap

HACRP contains SIR values for the same HAI types in the HAI dataset:
`clabsi_sir`, `cauti_sir`, `ssi_sir`, `cdi_sir`, `mrsa_sir`. These overlap with
`HAI_1_SIR` – `HAI_6_SIR` in `77hc-ibv8`.

**Key distinction:** HACRP SIR values are tied to the HACRP fiscal year period
(24-month collection); HAI dataset SIR values use calendar-period ranges. They
are NOT the same values.

**Resolution:** Store HACRP SIR values only in `provider_payment_adjustments` (as
context for the penalty calculation). Never store them in `provider_measure_values`
alongside HAI dataset SIR values. Confidence: **HIGH**.

---

### Group C: Mapping Discrepancies — High-Confidence Resolutions

Field-name discrepancies between `CLAUDE.md` / rules references and API field names
that are resolved with high confidence and require no further human review. Consolidated
here as a pipeline implementer reference.

| CLAUDE.md / Rules Reference | Actual API Field | Dataset | Resolution | Confidence |
|---|---|---|---|---|
| CCN / `facility_id` as 6-char zero-padded string | `facility_id` numeric string (not zero-padded) | `9n3s-kdb3`, `yq43-i98g`, `ypbt-wvdk` | Zero-pad to 6 chars in normalizer for all three payment-program datasets | HIGH |
| Standard `measure_id` field | `hcahps_measure_id` | `dgck-syfz` (HCAHPS) | Map `hcahps_measure_id` → `measure_id` in normalize layer | HIGH |
| `condition` (normalize target) | `_condition` (leading underscore) | `yv7e-xc69` (T&E) | Strip leading underscore in ingest; Socrata API artifact | HIGH |
| `birthing_friendly_designation` (schema alias) | `meets_criteria_for_birthing_friendly_designation` | `xubh-q36u` | Long CMS API name maps to short schema alias; `"Y"`/`"N"` → bool | HIGH |
| `hospital_overall_rating` as integer 1–5 | String `"1"`–`"5"` or `"Not Available"` | `xubh-q36u` | Parse string to int; `"Not Available"` → `suppressed=True` | HIGH |
| `score` as `Decimal` | String requiring parse; EDV carries `"very high"` / `"high"` | All measure datasets | Parse to `Decimal` for numeric values; branch on EDV for `score_text` (AMB-5) | HIGH |
| `compared_to_national` canonical enum | Two phrasings: `"No Different Than the National Rate"` vs `"No Different Than the National Value"` | `ynj2-r877` | Normalize to canonical enum before storage (AMB-3) | HIGH |
| `compared_to_national` case consistency | `"Number of Cases Too Small"` vs `"Number of cases too small"` in same snapshot | `632h-zaca` | Case-insensitive matching required in normalizer | HIGH |
| `footnote` as single field | Multiple companion footnote fields per value column | `dgck-syfz` (HCAHPS), `yq43-i98g` (HACRP) | Dataset-specific footnote parsing in normalize layer; no generic single-field assumption | HIGH |
| `suppressed` sentinel is `"Not Available"` | HACRP uses `"N/A"` (not `"Not Available"`) | `yq43-i98g` | `"N/A"` is the HACRP suppression sentinel; normalizer must branch on dataset | HIGH |
| `number_of_discharges` suppressed as `"Not Available"` | HRRP uses `"N/A"` for `number_of_discharges` | `9n3s-kdb3` | `"N/A"` is the HRRP count-suppression sentinel (not `"Not Available"`) | HIGH |

---

### Group D: Items Requiring Human Review — Resolved

All four items resolved 2026-03-14. Decisions documented in `docs/pipeline_decisions.md`.

| Item ID | Dataset | Decision | DEC Reference |
|---|---|---|---|
| B-1 | `xubh-q36u` | Store 5 `count_of_facility_*` + 5 `*_group_footnote` fields in `providers` table. Discard 8 others. | DEC-009 |
| B-2 | `dgck-syfz` | Discard `hcahps_linear_mean_value` — CMS scoring artifact, not consumer-facing signal | DEC-010 |
| B-3 | `ypbt-wvdk` | Use CMS API names as schema columns; drop `_normalized_` from one 63-char column | DEC-011 |
| B-4 | `yq43-i98g` | Discard Winsorized Z-score fields — intermediate calculation values, not patient-facing | DEC-012 |

---

## CMS Data Refresh Schedule Summary

All refresh schedules confirmed from CMS Hospital Downloadable Database Data Dictionary,
January 2026 edition (pages 8–15). CMS Care Compare hospital data publications occur
quarterly in January, April, July, and October; however, not all datasets refresh each
quarter — most refresh annually within the January publication only.

| Dataset | Dataset ID | Refresh Schedule | Collection Period | Source |
|---|---|---|---|---|
| Hospital General Information | `xubh-q36u` | Quarterly (Jan/Apr/Jul/Oct) | Varies by measure | CMS Hospital Data Dictionary Jan 2026, p. 8 |
| Hospital Overall Star Rating | _(field in `xubh-q36u`)_ | Quarterly (Jan/Apr/Jul/Oct) | Varies by measure | CMS Hospital Data Dictionary Jan 2026, p. 8 |
| Timely and Effective Care | `yv7e-xc69` | Mixed — see note ¹ | 12 months (most); 6 months (IMM-3) | CMS Hospital Data Dictionary Jan 2026, p. 14 |
| HCAHPS Patient Survey | `dgck-syfz` | Quarterly (Jan/Apr/Jul/Oct) | 12 months | CMS Hospital Data Dictionary Jan 2026, p. 11 |
| Complications and Deaths | `ynj2-r877` | Annually | 24–36 months (varies by measure) | CMS Hospital Data Dictionary Jan 2026, pp. 9–10 |
| Healthcare-Associated Infections | `77hc-ibv8` | Quarterly (Jan/Apr/Jul/Oct) | 12 months | CMS Hospital Data Dictionary Jan 2026, p. 9 |
| Unplanned Hospital Visits | `632h-zaca` | Annually | 12–36 months (varies by measure) | CMS Hospital Data Dictionary Jan 2026, pp. 14–15 |
| Outpatient Imaging Efficiency | `wkfw-kthe` | Annually | 12 months | CMS Hospital Data Dictionary Jan 2026, p. 15 |
| Medicare Hospital Spending Per Patient | `rrqw-56er` | Annually | 12 months | CMS Hospital Data Dictionary Jan 2026, p. 12 |
| Hospital Readmissions Reduction Program | `9n3s-kdb3` | Annually | 36 months | CMS Hospital Data Dictionary Jan 2026, p. 11 |
| Hospital-Acquired Condition Reduction Program | `yq43-i98g` | Annually | 15–30 months (varies by domain) | CMS Hospital Data Dictionary Jan 2026, p. 10 |
| Hospital Value-Based Purchasing Program | `ypbt-wvdk` | Annually | 12–33 months (varies by domain) | CMS Hospital Data Dictionary Jan 2026, pp. 11–12 |

**¹ Timely and Effective Care refresh detail:**
- **Annually:** EDV-1, GMCS, OP-22, OP-29, OP-31, IMM-3, HH-HYPO, HH-HYPER, HH-ORAE, OP-40, Safe Use of Opioids, STK-02, STK-03, STK-05, VTE-01, VTE-02
- **Quarterly:** SEP-1, OP-18a, OP-18b, OP-18c, OP-18d, OP-23

**Pipeline implications:**
- 4 datasets refresh quarterly and should be checked at every Care Compare publication: Hospital General Information, HCAHPS, HAI, and the quarterly subset of Timely and Effective Care.
- 8 datasets refresh annually (typically in the January publication). The pipeline should still check for updates at every quarterly run but can expect no change outside January for these datasets.
- The DKAN metadata API does not expose a machine-readable `accrualPeriodicity` or `nextUpdateDate` field for any hospital dataset. Schedule detection must rely on comparing `modified`/`released` timestamps across runs, not on metadata polling.

---

## Open Items

- [x] All active Socrata dataset IDs confirmed against live API (DEC-008, 2026-03-14)
- [x] At least one suppressed row fixture per dataset — complete for 10/11 datasets; ypbt-wvdk has no suppression in the full dataset (confirmed 1000-row sample). See `tests/pipeline/fixtures/hospital/fixture_gaps.md`.
- [x] At least one not-reported row fixture per dataset — complete where a distinct not_reported state exists; 4 datasets have no structurally distinct not_reported encoding (yv7e-xc69, dgck-syfz, ynj2-r877, 632h-zaca). See `fixture_gaps.md`.
- [x] At least one footnote-code row fixture per dataset — complete for 10/11 datasets; ypbt-wvdk has no footnote fields. See `fixture_gaps.md`.
- [x] All field name discrepancies resolved (see DEC-008, decisions.md — `_condition` key in TE, HCAHPS footnote structure, HACRP wide-format, VBP summary-only)
- [x] All suppression encodings documented per dataset (see each dataset section above — confirmed 2026-03-14 via analyze_encodings.py and manual row inspection)
- [x] All footnote code structures confirmed per dataset (confirmed 2026-03-14 — comma-space delimiter; HCAHPS targeted pull resolved AMB-6)
- [x] provider_subtype hospital enum values confirmed (2026-03-15, full-dataset verification — see Provider Subtype section; `"Long-term"` added)
- [x] CMS refresh schedule confirmed per dataset (see each dataset section above; source: CMS Hospital Data Dictionary January 2026)
- [x] DEC-001: Hospital Overall Star Rating confirmed as field in xubh-q36u, not separate dataset
- [x] DEC-002: Payment and Value of Care — PAYM measures retired July 2025, removed from scope
- [x] DEC-003: Health Equity Summary — HCHE measure retired October 2025, removed from scope
- [x] DEC-004: HCRIS fields (DSH, teaching, staffed beds) deferred, schema nullable
- [x] DEC-005: dual_eligible_proportion deferred, schema nullable
- [x] DEC-006: urban_rural_classification deferred, schema nullable
- [x] DEC-007: birthing_friendly_designation added to scope
- [x] DEC-008: All active dataset Socrata IDs confirmed (2026-03-14)
- [x] AMB-1 (HAI): `score = "N/A"` vs `"Not Available"` — confirmed distinct states (2026-03-14)
- [x] AMB-2 (Complications): `denominator = "Not Applicable"` on PSI_90 — confirmed not suppression (2026-03-14)
- [x] AMB-3 (Complications): `compared_to_national` dual phrasing — documented, canonical enum required before pipeline code
- [x] AMB-4 (HRRP): `"Too Few to Report"` three-way state — confirmed and documented (2026-03-14)
- [x] AMB-5 (T&E): EDV categorical score — identified, schema decision required before migration
- [x] AMB-6 (HCAHPS): Footnote format confirmed via targeted pull at offset ~50,000 — single integer per companion field, no multi-code (2026-03-14)
- [x] AMB-7: Footnote delimiter is comma-space `", "`, not pipe — confirmed in HAI and T&E (2026-03-14)

**Remaining before Phase 1 gate:**
- [x] Copy fixture rows from `scripts/recon/raw_samples/` to `tests/pipeline/fixtures/hospital/` — complete (2026-03-14, 1000–2000 row expanded samples)
- [x] Write initial Alembic migration — complete (2026-03-19). AMB-3 (DEC-022), AMB-4 (DEC-023), AMB-5 (DEC-024), DEC-025 (provider_penalties) all documented in pipeline_decisions.md before migration written. Migration covers all 8 tables, 8 enum types, hospital + NH columns.
- [ ] Draft MEASURE_REGISTRY entries for all hospital datasets with direction, ses_sensitivity, tail_risk_flag, and phase_0_findings.md references
- [ ] Populate `docs/data_dictionary.md` measure tables (per-measure direction and SES classifications)
- [x] Document AMB-3 canonical enum values for `compared_to_national` — DEC-022 (2026-03-19)
- [x] Document AMB-5 T&E EDV schema decision in pipeline_decisions.md — DEC-024 (2026-03-19)
- [x] Document AMB-4 HRRP count-suppression schema decision in pipeline_decisions.md — DEC-023 (2026-03-19)
- [x] Document B-1: xubh-q36u group summary field scope decision — DEC-009 (2026-03-14)
- [x] Document B-2: `hcahps_linear_mean_value` storage decision — DEC-010 (2026-03-14)
- [x] Document B-3: VBP domain score column naming decision — DEC-011 (2026-03-14)
- [x] Document B-4: HACRP Winsorized Z-score storage decision — DEC-012 (2026-03-14)
- [ ] Crosscheck footnote definitions against docs/Footnote_Crosswalk.csv

---

## Nursing Home Recon Watchouts

These items were identified during initial review of CMS nursing home documentation
(NH Data Dictionary Feb 2026, Five-Star Technical Users' Guide Jan 2026) and require
special attention during live API reconnaissance. Each item represents a known
divergence from hospital data patterns that could cause pipeline failures if not
handled explicitly.

### W-NH-1: Nursing home footnote codes are completely separate from hospital footnotes

Hospital and nursing home footnote systems share some numeric code values (e.g., both
use code 1 and code 7) but with **different meanings.** Hospital code 1 = "too few
cases to report." NH code 1 = "newly certified, <12-15 months data." The pipeline must
use separate footnote lookup tables keyed by provider_type. A single unified footnote
table will produce incorrect explanations.

NH-specific codes with no hospital equivalent: 6 (staffing criteria not met), 18 (SFF
program), 20-21 (accuracy validation), 23-27 (staffing data issues), 28 (annual
measure, no quarterly data).

### W-NH-2: MDS quality measures use per-quarter scoring with per-quarter footnotes

Hospital measures store a single score per reporting period. NH MDS measures store Q1,
Q2, Q3, Q4 individual scores plus a 4-quarter average, each with its own footnote
column. This means up to 5 score values and 5 footnote values per measure per provider.

Schema implications: Either store as 5 rows in `provider_measure_values` (one per
quarter + one for the average, differentiated by `period_label`), or add quarterly
columns. The former is more consistent with the existing schema pattern. This requires
a `docs/pipeline_decisions.md` entry before migration.

### W-NH-3: Claims-based measures have observed/expected/adjusted triplets

Hospital claims measures typically report a single score plus a compared_to_national
benchmark. NH claims-based quality measures (Table 12) report three separate numeric
values per measure: `Adjusted Score`, `Observed Score`, and `Expected Score`. All three
must be stored — the observed/expected relationship is critical for interpreting whether
risk adjustment helps or hurts a facility's apparent performance.

Schema implications: `numeric_value` stores the adjusted score; `observed_score` and
`expected_score` need additional columns or a structured approach. Evaluate whether the
existing `confidence_interval_lower`/`upper` columns can be repurposed or whether new
columns are needed. Document decision in `docs/pipeline_decisions.md`.

### W-NH-4: Five-Star rating methodology is significantly more complex than hospital stars

Hospital overall star rating is a single field from CMS with limited transparency into
the calculation. NH Five-Star has three fully documented domains with published scoring
formulas:

- **Health Inspection:** State-level relative scoring (not national), weighted across 2
  inspection cycles, includes complaint/infection control deficiencies and revisit
  penalties. Cut points vary by state.
- **Staffing:** 6 sub-measures (3 staffing level + 3 turnover), case-mix adjusted using
  PDPM, with specific cut points per measure. Facilities that don't submit data or
  submit erroneous data receive minimum scores.
- **Quality Measures:** 15 measures scored individually into points (quintile or decile
  based), summed into long-stay and short-stay sub-scores, combined into overall QM
  score. Cut points published in the Technical Users' Guide.

The overall rating is NOT a simple average — it starts from health inspection rating
and adjusts up/down based on staffing and QM performance with specific rules about
maximum adjustments per domain.

This complexity is an asset for consumer transparency. We should surface the domain
breakdown and explain the methodology clearly.

### W-NH-5: API endpoint — CONFIRMED same as hospital data (+ FAQ details)

**Resolved 2026-03-16.** Nursing home datasets use the **same DKAN API base URL** as
hospital datasets: `data.cms.gov/provider-data/api/1/datastore/query/{dataset_id}`.

All 18 nursing home dataset IDs were discovered via the DKAN metastore API
(`/api/1/metastore/schemas/dataset/items` filtered by theme = "Nursing homes including
rehab services") and confirmed live against the datastore query endpoint. Pagination
and query parameters work identically to hospital datasets.

Dataset IDs are recorded in `pipeline/config.py` as `NH_DATASET_IDS`.

**Additional API details confirmed from `docs/nh-faq.txt` (CMS PDC FAQ):**
- No API key required
- No rate limits or restrictions
- Max batch size: 1,500 results per request (we use 100 per page, which is fine)
- Dataset IDs are stable across data refreshes (Distribution IDs change, Dataset IDs don't)
- Index in URL path is always `0` for all PDC datasets (single distribution per dataset)
- Endpoint: `datastore/query/{datasetID}/{index}` — confirmed this is the recommended pattern
- To list all datasets: `metastore/schemas/dataset/items`
- To filter by topic: `/api/1/search?theme=Nursing%20homes%20including%20rehab%20services`
- Five-Star rating field for nursing homes: `overall_rating` (in Provider Info dataset)
- Archived data snapshots available for past 7 years via topic archive pages

### W-NH-6: Special Focus Facility (SFF) status requires prominent display

The SFF program identifies nursing homes with a history of serious quality issues. CMS
provides SFF status and SFF Candidate status in the Provider Information dataset. Per
project principles (tail risk is primary, non-disclosure is a signal), SFF and SFF
Candidate status must be surfaced with the same visual prominence as tail_risk_flag
measures. A consumer viewing a nursing home profile should see SFF status immediately,
not buried in metadata.

### W-NH-7: Nursing home ownership chain data is uniquely important

NH Data Dictionary Table 13 (Ownership) provides ownership information including chain
affiliation. Private equity ownership of nursing homes is a documented consumer concern
with published research linking PE ownership to quality changes. The chain-level average
ratings in Provider Information (chain average overall, health inspection, staffing, QM)
provide unique cross-facility comparison context not available for hospitals.

---

### 12. Nursing Home Provider Information

**Status:** [~] In progress — dataset ID confirmed, field names confirmed, full recon pending

**Socrata Dataset ID:** `4pq5-n9py` (confirmed via DKAN datastore query 2026-03-16)

**Total rows in dataset:** 14,710 (99 columns)

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Table 2 (Provider Information file variables)
- `docs/nh-five-star-users-guide-january-2026.txt` — Five-Star rating methodology

**Confirmed API field names (from live API response 2026-03-16):**

All 99 columns confirmed. API uses `snake_case` field names. Key field name mappings:

| Schema field | Actual API Key | Notes |
|---|---|---|
| provider id (CCN) | `cms_certification_number_ccn` | 6-char string, zero-padded e.g. `"015009"` |
| provider name | `provider_name` | |
| ownership type | `ownership_type` | e.g. `"For profit - Corporation"` |
| provider type | `provider_type` | e.g. `"Medicare and Medicaid"` |
| number of certified beds | `number_of_certified_beds` | String in API, convert to int |
| average daily census | `average_number_of_residents_per_day` | String e.g. `"48.4"` |
| average daily census footnote | `average_number_of_residents_per_day_footnote` | Empty string when absent |
| provider resides in hospital | `provider_resides_in_hospital` | `"Y"` / `"N"` |
| urban/rural | `urban` | `"Y"` / `"N"` |
| chain name | `chain_name` | Empty string when not in chain |
| chain id | `chain_id` | Empty string when not in chain |
| number of facilities in chain | `number_of_facilities_in_chain` | Empty string when not in chain |
| chain avg overall rating | `chain_average_overall_5star_rating` | Empty string when not in chain |
| chain avg health inspection | `chain_average_health_inspection_rating` | |
| chain avg staffing | `chain_average_staffing_rating` | |
| chain avg QM | `chain_average_qm_rating` | |
| CCRC | `continuing_care_retirement_community` | `"Y"` / `"N"` |
| special focus status | `special_focus_status` | Empty string, `"SFF"`, or `"SFF Candidate"` |
| abuse icon | `abuse_icon` | `"Y"` / `"N"` |
| most recent inspection >2yr | `most_recent_health_inspection_more_than_2_years_ago` | `"Y"` / `"N"` |
| ownership changed | `provider_changed_ownership_in_last_12_months` | `"Y"` / `"N"` |
| resident/family council | `with_a_resident_and_family_council` | `"Resident"`, `"Family"`, `"Both"`, `"None"` |
| sprinkler systems | `automatic_sprinkler_systems_in_all_required_areas` | `"Yes"`, `"Partial"`, `"No"`, `"Data Not Available"` |
| overall rating | `overall_rating` | String `"1"`-`"5"` |
| overall rating footnote | `overall_rating_footnote` | Empty string when absent |
| health inspection rating | `health_inspection_rating` | String `"1"`-`"5"` |
| QM rating | `qm_rating` | String `"1"`-`"5"` |
| long-stay QM rating | `longstay_qm_rating` | String `"1"`-`"5"` |
| short-stay QM rating | `shortstay_qm_rating` | String `"1"`-`"5"` |
| staffing rating | `staffing_rating` | String `"1"`-`"5"` |
| (each rating has `*_footnote`) | | Empty string when absent |
| reported nurse aide HPRD | `reported_nurse_aide_staffing_hours_per_resident_per_day` | String decimal |
| reported LPN HPRD | `reported_lpn_staffing_hours_per_resident_per_day` | String decimal |
| reported RN HPRD | `reported_rn_staffing_hours_per_resident_per_day` | String decimal |
| reported licensed HPRD | `reported_licensed_staffing_hours_per_resident_per_day` | RN + LPN |
| reported total nurse HPRD | `reported_total_nurse_staffing_hours_per_resident_per_day` | Aide+LPN+RN |
| weekend total nurse HPRD | `total_number_of_nurse_staff_hours_per_resident_per_day_on_t_4a14` | **Truncated key** |
| weekend RN HPRD | `registered_nurse_hours_per_resident_per_day_on_the_weekend` | |
| PT HPRD | `reported_physical_therapist_staffing_hours_per_resident_per_day` | |
| total nursing turnover | `total_nursing_staff_turnover` | Percent string e.g. `"33.3"` |
| RN turnover | `registered_nurse_turnover` | Percent string |
| admin turnover count | `number_of_administrators_who_have_left_the_nursing_home` | Integer as string |
| nursing case-mix index | `nursing_casemix_index` | |
| nursing case-mix ratio | `nursing_casemix_index_ratio` | |
| (case-mix adjusted staffing) | `casemix_*` prefix | 5 fields |
| (adjusted staffing) | `adjusted_*` prefix | 5 fields |
| cycle 1 survey date | `rating_cycle_1_standard_survey_health_date` | Date string |
| cycle 1 total deficiencies | `rating_cycle_1_total_number_of_health_deficiencies` | |
| cycle 1 standard deficiencies | `rating_cycle_1_number_of_standard_health_deficiencies` | |
| cycle 1 complaint deficiencies | `rating_cycle_1_number_of_complaint_health_deficiencies` | |
| cycle 1 deficiency score | `rating_cycle_1_health_deficiency_score` | |
| cycle 1 revisits | `rating_cycle_1_number_of_health_revisits` | |
| cycle 1 revisit score | `rating_cycle_1_health_revisit_score` | |
| cycle 1 total score | `rating_cycle_1_total_health_score` | |
| cycle 2 survey date | `rating_cycle_2_standard_health_survey_date` | |
| cycle 2/3 fields | `rating_cycle_23_*` | Note: "23" not "2_3" |
| total weighted health score | `total_weighted_health_survey_score` | Decimal string e.g. `"44.000"` |
| infection control citations | `number_of_citations_from_infection_control_inspections` | Empty string when 0 |
| number of fines | `number_of_fines` | |
| total fine amount | `total_amount_of_fines_in_dollars` | e.g. `"23989.00"` |
| payment denials | `number_of_payment_denials` | |
| total penalties | `total_number_of_penalties` | |
| location | `location` | Composite address string |
| latitude | `latitude` | |
| longitude | `longitude` | |
| geocoding footnote | `geocoding_footnote` | |
| processing date | `processing_date` | e.g. `"2026-02-01"` |

**Notable API observations:**
- **Truncated field name:** `total_number_of_nurse_staff_hours_per_resident_per_day_on_t_4a14`
  — the DKAN API appears to truncate long column names and append a hash. Must handle
  this in field mapping.
- **All numeric values are strings** — same pattern as hospital data.
- **Empty string used for absent values** — footnotes, chain fields, special focus status.
- **Footnote structure:** Per-field footnote columns (e.g., `overall_rating_footnote`,
  `staffing_rating_footnote`) — same pattern as hospital data. Empty string when absent.

**Suppression encoding (confirmed 2026-03-17 from 1000-row sample):**

Footnote codes observed in Provider Info (1000 rows):

| Field | Codes Observed | Count |
|---|---|---|
| `overall_rating_footnote` | 1, 18 | 8 rows |
| `health_inspection_rating_footnote` | 1, 18 | 8 rows |
| `qm_rating_footnote` | 1, 2, 18, 20 | 14 rows |
| `staffing_rating_footnote` | 1, 2, 18, 23, 24, 25 | 43 rows |
| `reported_staffing_footnote` | 6, 23, 25 | 21 rows |
| `longstay_qm_rating_footnote` | 1, 2, 18, 20 | 35 rows |
| `shortstay_qm_rating_footnote` | 1, 2, 18, 20 | 145 rows |

SFF status: 27 "SFF Candidate" + 6 "SFF" in 1000 rows.
Abuse icon: 102 rows with `abuse_icon = "Y"` in 1000 rows (~10% of sample).

**Confirmed `ownership_type` values (full dataset, 14,710 rows, 2026-03-17):**

| Enum Value | Count | % |
|---|---|---|
| `For profit - Corporation` | 4,939 | 33.6% |
| `For profit - Limited Liability company` | 4,832 | 32.8% |
| `Non profit - Corporation` | 2,305 | 15.7% |
| `For profit - Individual` | 669 | 4.5% |
| `For profit - Partnership` | 408 | 2.8% |
| `Government - County` | 358 | 2.4% |
| `Non profit - Other` | 332 | 2.3% |
| `Government - Hospital district` | 294 | 2.0% |
| `Non profit - Church related` | 285 | 1.9% |
| `Government - State` | 159 | 1.1% |
| `Government - City/county` | 64 | 0.4% |
| `Government - City` | 54 | 0.4% |
| `Government - Federal` | 11 | 0.1% |

**13 distinct values. No additional values beyond the 1000-row sample.**
Note: Nursing home ownership categories differ from hospital ownership categories.
66.4% are for-profit (Corporation + LLC). Must use varchar, not enum (same DEC-013
rationale as hospitals).

**Confirmed `provider_type` values (full dataset, 14,710 rows):**

| Enum Value | Count | % |
|---|---|---|
| `Medicare and Medicaid` | 13,904 | 94.5% |
| `Medicare` | 551 | 3.7% |
| `Medicaid` | 255 | 1.7% |

**3 distinct values.**

**Confirmed `special_focus_status` values (full dataset):**

| Value | Count | Notes |
|---|---|---|
| _(empty string)_ | 14,180 | Not SFF or candidate |
| `SFF Candidate` | 442 | CMS has identified quality concerns |
| `SFF` | 88 | Active Special Focus Facility |

**Confirmed `with_a_resident_and_family_council` values (full dataset):**
`Resident` (12,082), `Both` (1,809), `None` (819). **3 distinct values.**
Note: `"Family"` listed in data dictionary but not observed in current data.

**Confirmed `automatic_sprinkler_systems_in_all_required_areas` values (full dataset):**
`Yes` (14,654), `Partial` (33), `Data Not Available` (23). **3 distinct values.**
Note: `"No"` listed in data dictionary but not observed in current data.

**Refresh schedule:** Monthly (per NH Data Dictionary, confirmed by `processing_date`)

---

### 13. MDS Quality Measures

**Status:** [~] In progress — dataset ID confirmed, field names confirmed, full measure catalog pending

**Socrata Dataset ID:** `djen-97ju` (confirmed via DKAN datastore query 2026-03-16)

**Total rows in dataset:** 250,070 (23 columns)

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Table 11 (MDS Quality Measures file variables)
- `docs/nh-five-star-users-guide-january-2026.txt` — Quality Measure Domain section

**Confirmed API field names (from live API response 2026-03-16):**

| API Key | Type | Notes |
|---|---|---|
| `cms_certification_number_ccn` | String(6) | Zero-padded |
| `provider_name` | String | |
| `provider_address` | String | |
| `citytown` | String | |
| `state` | String(2) | |
| `zip_code` | String | |
| `measure_code` | String | Numeric code e.g. `"401"` |
| `measure_description` | String | Full measure name |
| `resident_type` | String | `"Long Stay"` or `"Short Stay"` |
| `q1_measure_score` | String | Decimal e.g. `"11.428571"` |
| `footnote_for_q1_measure_score` | String | Empty string when absent |
| `q2_measure_score` | String | |
| `footnote_for_q2_measure_score` | String | |
| `q3_measure_score` | String | |
| `footnote_for_q3_measure_score` | String | |
| `q4_measure_score` | String | |
| `footnote_for_q4_measure_score` | String | |
| `four_quarter_average_score` | String | e.g. `"11.278195"` |
| `footnote_for_four_quarter_average_score` | String | |
| `used_in_quality_measure_five_star_rating` | String | `"Y"` / `"N"` |
| `measure_period` | String | e.g. `"2024Q4-2025Q3"` |
| `location` | String | Composite address |
| `processing_date` | String | e.g. `"2026-02-01"` |

**Confirmed W-NH-2:** Per-quarter scoring with per-quarter footnotes confirmed in live
data. Each measure has 5 score columns (Q1-Q4 + average) and 5 footnote columns.

**Suppression encoding (confirmed 2026-03-17 from 1000-row sample):**
- Footnote codes observed: `9` (too few residents, 161 rows), `28` (annual measure, 10 rows)
- Suppressed rows have empty `four_quarter_average_score` with footnote `9`
- Footnote `28` appears on vaccination measures (annual — no quarterly breakdown)
- Empty string = no footnote (not suppressed)

**Quality measures used in Five-Star rating (15 total):**

Long-stay MDS measures (7):
- Percentage of long-stay residents whose ability to walk independently worsened
- Percentage of long-stay residents whose need for help with daily activities has increased
- Percentage of long-stay residents with pressure ulcers
- Percentage of long-stay residents with a catheter inserted and left in their bladder
- Percentage of long-stay residents with a urinary tract infection
- Percentage of long-stay residents experiencing one or more falls with major injury
- Percentage of long-stay residents who got an antipsychotic medication

Short-stay MDS measures (3):
- Percentage of SNF residents who are at or above an expected ability to care for
  themselves and move around at discharge
- Percentage of short-stay residents with pressure ulcers/pressure injuries that are
  new or worsened
- Percentage of short-stay residents who got antipsychotic medication for the first time

**Additional MDS measures reported but NOT in Five-Star rating (to be confirmed):**
- Percentage of long-stay residents who lose too much weight
- Percentage of long-stay residents who have depressive symptoms
- Percentage of long-stay residents who were physically restrained
- Percentage of long-stay residents assessed and appropriately given the pneumococcal vaccine
- Percentage of long-stay residents assessed and appropriately given the seasonal influenza vaccine
- Percentage of long-stay residents who received an antianxiety or hypnotic medication
- Percentage of long-stay residents with new or worsened bowel or bladder incontinence
- Percentage of short-stay residents assessed and appropriately given the pneumococcal vaccine
- Percentage of short-stay residents assessed and appropriately given the seasonal influenza vaccine

**Suppression encoding:** _(to be confirmed)_

**Footnote structure:** Per-quarter footnotes plus aggregate footnote _(confirm against live data)_

**Refresh schedule:** Quarterly (per NH Data Dictionary)

---

### 14. Medicare Claims Quality Measures

**Status:** [~] In progress — dataset ID confirmed, field names confirmed, full measure catalog pending

**Socrata Dataset ID:** `ijh5-nb2v` (confirmed via DKAN datastore query 2026-03-16)

**Total rows in dataset:** 58,840 (17 columns)

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Table 12 (Medicare Claims Quality Measures file variables)
- `docs/nh-five-star-users-guide-january-2026.txt` — Quality Measure Domain section

**Confirmed API field names (from live API response 2026-03-16):**

| API Key | Type | Notes |
|---|---|---|
| `cms_certification_number_ccn` | String(6) | |
| `provider_name` | String | |
| `provider_address` | String | |
| `citytown` | String | |
| `state` | String(2) | |
| `zip_code` | String | |
| `measure_code` | String | e.g. `"521"` |
| `measure_description` | String | Truncated in API response — confirm full text |
| `resident_type` | String | `"Short Stay"` or `"Long Stay"` |
| `adjusted_score` | String | Risk-adjusted value e.g. `"18.638785"` |
| `observed_score` | String | e.g. `"17.543860"` |
| `expected_score` | String | e.g. `"22.436904"` |
| `footnote_for_score` | String | Empty string when absent |
| `used_in_quality_measure_five_star_rating` | String | `"Y"` / `"N"` |
| `measure_period` | String | e.g. `"20240701-20250630"` — date range format |
| `location` | String | Composite address |
| `processing_date` | String | |

**Confirmed W-NH-3:** Observed/expected/adjusted triplet confirmed in live data.
`adjusted_score` is the primary display value; `observed_score` and `expected_score`
provide interpretive context (O/E ratio).

**Suppression encoding (confirmed 2026-03-17 from 1000-row sample):**
- Footnote codes observed: `9` (too few residents, 100 rows), `10` (data missing, 116 rows)
- Suppressed rows have empty `adjusted_score`, `observed_score`, `expected_score`
- Footnote `10` = "data missing or not submitted" — distinct from `9` = "too few"
- 216 of 1000 rows had footnotes (21.6% suppression rate in sample)

**Claims-based measures used in Five-Star rating (5):**

Long-stay claims-based (2):
- Number of hospitalizations per 1,000 long-stay resident days
- Number of outpatient ED visits per 1,000 long-stay resident days

Short-stay claims-based (3):
- Percentage of short-stay residents who were rehospitalized after a nursing home admission
- Percentage of short-stay residents who had an outpatient emergency department visit
- Rate of successful return to home and community from a SNF

**Suppression encoding:** _(to be confirmed)_

**Refresh schedule:** Quarterly (per NH Data Dictionary)

---

### 15. Nursing Home Health Deficiencies

**Status:** [~] In progress — dataset ID confirmed, field names confirmed

**Socrata Dataset ID:** `r5ix-sfxw` (confirmed via DKAN datastore query 2026-03-16)

**Total rows in dataset:** 419,452 (23 columns)

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Table 7 (Health Deficiencies file variables)

**Confirmed API field names (from live API response 2026-03-16):**

`cms_certification_number_ccn`, `provider_name`, `provider_address`, `citytown`,
`state`, `zip_code`, `survey_date` (e.g. `"2023-03-02"`), `survey_type` (e.g.
`"Health"`), `deficiency_prefix` (e.g. `"F"`), `deficiency_category` (e.g.
`"Infection Control Deficiencies"`), `deficiency_tag_number` (e.g. `"0880"`),
`deficiency_description`, `scope_severity_code` (e.g. `"F"` — single char),
`deficiency_corrected` (e.g. `"Deficient, Provider has date of correction"`),
`correction_date`, `inspection_cycle` (e.g. `"1"`), `standard_deficiency` (`"Y"`/`"N"`),
`complaint_deficiency` (`"Y"`/`"N"`), `infection_control_inspection_deficiency`
(`"Y"`/`"N"`), `citation_under_idr` (`"Y"`/`"N"`), `citation_under_iidr` (`"Y"`/`"N"`),
`location`, `processing_date`.

**Scope/Severity codes (confirmed against full dataset, 419,452 rows, 2026-03-17):**

| Code | Severity | Scope | Count | % |
|---|---|---|---|---|
| D | No actual harm, potential for more than minimal | Isolated | 262,091 | 62.5% |
| E | No actual harm, potential for more than minimal | Pattern | 95,113 | 22.7% |
| F | No actual harm, potential for more than minimal | Widespread | 28,588 | 6.8% |
| G | Actual harm, not immediate jeopardy | Isolated | 13,273 | 3.2% |
| J | Immediate jeopardy | Isolated | 6,976 | 1.7% |
| B | No actual harm, potential for minimal | Pattern | 5,195 | 1.2% |
| C | No actual harm, potential for minimal | Widespread | 4,634 | 1.1% |
| K | Immediate jeopardy | Pattern | 2,370 | 0.6% |
| L | Immediate jeopardy | Widespread | 695 | 0.2% |
| H | Actual harm, not immediate jeopardy | Pattern | 499 | 0.1% |
| I | Actual harm, not immediate jeopardy | Widespread | 18 | <0.01% |

**11 of 12 possible codes observed.** Code `A` (no actual harm, potential for minimal,
isolated) not observed — this carries 0 points in the Five-Star scoring and may not be
cited in practice. The database schema should still accept all 12 codes (A-L).

**Immediate jeopardy citations (J/K/L): 10,041 rows (2.4%)** — these are the most
serious findings and drive `is_immediate_jeopardy = true` in the schema.

**Confirmed `deficiency_prefix` values:** Only `F` (F-tags) in health deficiencies.
K-tags and E-tags appear in the Fire Safety Deficiencies dataset only.

**Confirmed `survey_type` values:** Only `Health` in this dataset.

**Confirmed `deficiency_corrected` values (6 distinct):**

| Value | Count |
|---|---|
| `Deficient, Provider has date of correction` | 409,002 |
| `Past Non-Compliance` | 5,579 |
| `Deficient, Provider has plan of correction` | 2,648 |
| `Deficient, Provider has no plan of correction` | 1,617 |
| `Waiver has been granted` | 435 |
| `No revisit needed` | 171 |

**Confirmed Inspection Dates `type_of_survey` values (4 distinct):**
`Fire Safety Standard`, `Health Standard`, `Health Complaint`, `Infection Control`.
Note: No `Fire Safety Complaint` in sample — may exist but rare.

**Confirmed `penalty_type` values (2 distinct):**
`Fine` (1,258), `Payment Denial` (242).

**Refresh schedule:** Monthly (per NH Data Dictionary)

---

### 16. Fire Safety Deficiencies

**Status:** [x] Confirmed 2026-03-17. Field names, deficiency structure, scope/severity codes confirmed.

**Socrata Dataset ID:** `ifjz-ge4w` (confirmed 2026-03-16, 199,578 rows, 24 columns)

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Table 6 (Fire Safety Deficiencies file variables)

**Fixture file:** `tests/pipeline/fixtures/nursing_home/ifjz-ge4w.json` (100 rows)

**Confirmed API field names (from live API response 2026-03-17):**

Structurally identical to Health Deficiencies (r5ix-sfxw) — same 24 fields:
`cms_certification_number_ccn`, `provider_name`, `provider_address`, `citytown`,
`state`, `zip_code`, `survey_date`, `survey_type`, `deficiency_prefix`,
`deficiency_category`, `deficiency_tag_number`, `tag_version`, `deficiency_description`,
`scope_severity_code`, `deficiency_corrected`, `correction_date`, `inspection_cycle`,
`standard_deficiency`, `complaint_deficiency`, `infection_control_inspection_deficiency`,
`citation_under_idr`, `citation_under_iidr`, `location`, `processing_date`.

**Notable:** Has `tag_version` field (value `"New"`) — also present in Health Deficiencies
but not previously documented.

**Key differences from Health Deficiencies:**
- `deficiency_prefix`: `K` (fire safety) and `E` (life safety) — not `F` (health)
- `survey_type`: `"Fire Safety"` only (not `"Health"`)
- `scope_severity_code`: Codes `C`, `D`, `E`, `F` observed in 100-row sample — lower
  severity range than Health Deficiencies (which includes A-L). Higher severity codes
  (G-L = actual harm / immediate jeopardy) may exist but rare for fire safety.
- `citation_under_idr` and `citation_under_iidr`: All `"N"` in 100-row sample —
  immediate jeopardy citations are primarily a health inspection concept.

**Confirmed `deficiency_category` values (6 distinct in 100-row sample):**
`Gas, Vacuum, and Electrical Systems Deficiencies`, `Services Deficiencies`,
`Emergency Preparedness Deficiencies`, `Smoke Deficiencies`, `Egress Deficiencies`,
`Miscellaneous Deficiencies`.

**Refresh schedule:** Monthly (per NH Data Dictionary)

---

### 17. Survey Summary

**Status:** [x] Confirmed 2026-03-17. Field names, structure, deficiency categories confirmed.

**Socrata Dataset ID:** `tbry-pc2d` (confirmed 2026-03-16, 43,983 rows, 41 columns)

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Table 10 (Survey Summary file variables)

**Fixture file:** `tests/pipeline/fixtures/nursing_home/tbry-pc2d.json` (100 rows)

**Structure:** 3 rows per facility (one per inspection cycle: 1, 2, 3). 34 unique CCNs
in 100-row sample confirms this pattern (100 / 3 ≈ 33).

**Confirmed API field names (41 columns, from live API response 2026-03-17):**

| API Key | Type | Notes |
|---|---|---|
| `cms_certification_number_ccn` | String(6) | |
| `provider_name` | String | |
| `provider_address` | String | |
| `citytown` | String | |
| `state` | String(2) | |
| `zip_code` | String | |
| `inspection_cycle` | String | `"1"`, `"2"`, `"3"` |
| `health_survey_date` | String | Date e.g. `"2023-03-02"` |
| `fire_safety_survey_date` | String | Date e.g. `"2023-03-02"` |
| `total_number_of_health_deficiencies` | String | Integer as string |
| `total_number_of_fire_safety_deficiencies` | String | Integer as string |

**Health deficiency category counts (11 categories):**
`count_of_freedom_from_abuse_and_neglect_and_exploitation_de_4353` (truncated),
`count_of_quality_of_life_and_care_deficiencies`,
`count_of_resident_assessment_and_care_planning_deficiencies`,
`count_of_nursing_and_physician_services_deficiencies`,
`count_of_resident_rights_deficiencies`,
`count_of_nutrition_and_dietary_deficiencies`,
`count_of_pharmacy_service_deficiencies`,
`count_of_environmental_deficiencies`,
`count_of_administration_deficiencies`,
`count_of_infection_control_deficiencies`,
`count_of_emergency_preparedness_deficiencies`.

**Fire safety deficiency category counts (18 categories):**
`count_of_automatic_sprinkler_systems_deficiencies`,
`count_of_construction_deficiencies`,
`count_of_services_deficiencies`,
`count_of_corridor_walls_and_doors_deficiencies`,
`count_of_egress_deficiencies`,
`count_of_electrical_deficiencies`,
`count_of_emergency_plans_and_fire_drills_deficiencies`,
`count_of_fire_alarm_systems_deficiencies`,
`count_of_smoke_deficiencies`,
`count_of_interior_deficiencies`,
`count_of_gas_and_vacuum_and_electrical_systems_deficiencies`,
`count_of_hazardous_area_deficiencies`,
`count_of_illumination_and_emergency_power_deficiencies`,
`count_of_laboratories_deficiencies`,
`count_of_medical_gases_and_anaesthetizing_areas_deficiencies`,
`count_of_smoking_regulations_deficiencies`,
`count_of_miscellaneous_deficiencies`.

Plus `location`, `processing_date`.

**Notable:** One health category field name is truncated with hash suffix
(`count_of_freedom_from_abuse_and_neglect_and_exploitation_de_4353`). Same DKAN
truncation behavior as Provider Info and SNF VBP datasets.

**Assessment:** This is the aggregated view of the Health Deficiencies and Fire Safety
Deficiencies datasets. The per-cycle structure enables cross-cycle comparison of total
deficiency counts by category without querying the detailed deficiency datasets. Useful
for the "deficiency pattern" display feature — combine Summary (counts by category per
cycle) with Deficiencies (individual citations with severity) for both overview and
drill-down views.

**Refresh schedule:** Monthly (per NH Data Dictionary)

---

### 18. Inspection Dates

**Status:** [x] Confirmed 2026-03-17. All field names and survey types confirmed.

**Socrata Dataset ID:** `svdt-c123` (confirmed 2026-03-16, 151,849 rows, 5 columns)

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Table 5 (Inspection Dates file variables)

**Fixture file:** `tests/pipeline/fixtures/nursing_home/svdt-c123.json` (100 rows)

**Confirmed API field names (5 columns, from live API response 2026-03-17):**
`cms_certification_number_ccn`, `survey_date` (e.g. `"2023-03-02"`),
`type_of_survey`, `survey_cycle` (e.g. `"1"`), `processing_date`.

**Structure:** Multiple rows per facility — one row per survey type per date per cycle.
A single inspection visit generates multiple rows (e.g., Health Standard + Fire Safety
Standard + Health Complaint all on the same date). Typical pattern: 6-10 rows per
facility (3 cycles × 2-3 survey types per cycle).

**Confirmed `type_of_survey` values (4 distinct in 100-row sample):**
`Fire Safety Standard`, `Health Standard`, `Health Complaint`, `Infection Control`.

**Notable:** No `Fire Safety Complaint` type observed in sample. Expected per NH Data
Dictionary but may be rare. Survey dates span 2017-2025 in sample, confirming multi-year
inspection history is available.

**Survey cycle numbering is per survey type, not global.** A "Health Complaint" at
cycle 3 on the same date as a "Health Standard" at cycle 1 are independent cycle counts.
Complaint surveys and standard surveys can occur on the same date with different cycle
numbers. Pipeline must not assume a single cycle number applies across all survey types
for a facility.

**Assessment:** This is the simplest nursing home dataset — a lookup table of when each
facility was inspected and what type of inspection occurred. Critical for the "inspection
recency" display feature and for cross-referencing deficiency citations to specific
inspection events. Joined to Survey Summary on `(ccn, inspection_cycle)` — relationship
is one-to-many (one Summary row per cycle, multiple Dates rows per cycle due to multiple
survey types on the same date).

**Refresh schedule:** Monthly (per NH Data Dictionary)

---

### 19. Nursing Home Penalties

**Status:** [~] In progress — dataset ID confirmed, field names confirmed

**Socrata Dataset ID:** `g6vv-u9sr` (confirmed 2026-03-16, 17,463 rows, 13 columns)

**Confirmed API field names:** `cms_certification_number_ccn`, `provider_name`,
`provider_address`, `citytown`, `state`, `zip_code`, `penalty_date` (e.g.
`"2023-03-02"`), `penalty_type` (e.g. `"Fine"`), `fine_amount` (e.g. `"5000"`),
`payment_denial_start_date`, `payment_denial_length_in_days`, `location`,
`processing_date`.

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Table 14 (Penalties file variables)

**Expected fields:** _(to be confirmed — Table 14 details needed from data dictionary)_

**Refresh schedule:** Monthly (per NH Data Dictionary)

---

### 20. Nursing Home Ownership

**Status:** [x] Confirmed 2026-03-17. All field names, role types, owner structure,
ownership percentage encoding, and association date format confirmed from 100-row sample.

**Socrata Dataset ID:** `y2hd-n93e` (confirmed 2026-03-16, 159,220 rows, 13 columns)

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Table 13 (Ownership file variables)

**Fixture file:** `tests/pipeline/fixtures/nursing_home/y2hd-n93e.json` (100 rows)

**Confirmed API field names (13 columns, from live API response 2026-03-17):**

| API Key | Type | Notes |
|---|---|---|
| `cms_certification_number_ccn` | String(6) | |
| `provider_name` | String | |
| `provider_address` | String | |
| `citytown` | String | |
| `state` | String(2) | |
| `zip_code` | String | |
| `role_played_by_owner_or_manager_in_facility` | String | See role values below |
| `owner_type` | String | `"Individual"` or `"Organization"` |
| `owner_name` | String | Named person or entity name |
| `ownership_percentage` | String | `"5%"`, `"81%"`, `"100%"`, `"NOT APPLICABLE"`, `"NO PERCENTAGE PROVIDED"` |
| `association_date` | String | Format: `"since MM/DD/YYYY"` — requires prefix strip + date parse |
| `location` | String | Composite address |
| `processing_date` | String | e.g. `"2026-02-01"` |

**Structure:** Multiple rows per facility — one row per owner/manager/interested party.
159,220 rows for ~14,710 facilities = ~10.8 rows per facility average. In 100-row
sample: 7-19 rows per facility (11 unique CCNs).

**Confirmed `role_played_by_owner_or_manager_in_facility` values (11 distinct,
confirmed from 200-row sample across 2 pages):**

| Role | Notes |
|---|---|
| `5% OR GREATER DIRECT OWNERSHIP INTEREST` | Primary owners |
| `5% OR GREATER INDIRECT OWNERSHIP INTEREST` | Parent entities, holding companies, trusts |
| `5% OR GREATER SECURITY INTEREST` | Lenders, banks |
| `5% OR GREATER MORTGAGE INTEREST` | Mortgage holders |
| `GENERAL PARTNERSHIP INTEREST` | General partners |
| `LIMITED PARTNERSHIP INTEREST` | Limited partners |
| `OPERATIONAL/MANAGERIAL CONTROL` | Management companies and administrators |
| `W-2 MANAGING EMPLOYEE` | On-payroll managers |
| `CONTRACTED MANAGING EMPLOYEE` | Third-party management |
| `CORPORATE OFFICER` | Named individuals |
| `CORPORATE DIRECTOR` | Board members |

**Confirmed `owner_type` values (2 distinct):** `Individual`, `Organization`.

**Ownership percentage encoding:**
- Numeric with `%` suffix: `"5%"`, `"18%"`, `"81%"`, `"100%"` — parse to integer
- `"NOT APPLICABLE"` — used for management roles, security interests, mortgage interests
- `"NO PERCENTAGE PROVIDED"` — used for some indirect ownership interests. GAO has
  documented >55% of owners in top chains have missing ownership percentages.

**Association date format:** `"since MM/DD/YYYY"` — strip `"since "` prefix, parse
MM/DD/YYYY. Dates range from 1969 to 2024 in sample, confirming long association
histories.

**Critical findings for product feature feasibility:**

1. **Corporate ownership chains are visible.** Example: GENESIS HOLDINGS LLC (100%
   direct) → FC-GEN OPERATIONS INVESTMENT LLC (indirect) → GEN OPERATIONS I LLC →
   GEN OPERATIONS II LLC → GENESIS HEALTHCARE INC → GENESIS HEALTHCARE LLC →
   SUN HEALTHCARE GROUP INC → WELLTOWER OP LLC (REIT). Multi-layer LLC structures
   including REITs are exposed through the indirect ownership role.

2. **Management companies identifiable.** `OPERATIONAL/MANAGERIAL CONTROL` role with
   `owner_type = "Organization"` identifies management companies (e.g.,
   `PRIME MANAGEMENT, LLC`, `BALL HEALTHCARE SERVICE, INC`).

3. **Same person can hold multiple roles.** Confirmed: one individual appeared as direct
   owner (81%), corporate director, corporate officer, AND W-2 managing employee — four
   rows for one person at one facility. Pipeline must handle this for display grouping.

4. **Ownership change detection via association dates.** When all owners for a facility
   share a recent date, it signals a recent ownership change. Mixed dates (some "since
   1969", some "since 2024") indicate partial restructuring. Richer than the binary
   `provider_changed_ownership_in_last_12_months` flag in Provider Info.

5. **Security and mortgage interests reveal financial relationships.** Banks and lenders
   with 5%+ interests are listed (e.g., `REGIONS BANK`, `BERKADIA COMMERCIAL MORTGAGE
   LLC`).

6. **No suppression mechanism.** No null/empty values, no footnote fields in this
   dataset. Every row has all 13 fields populated. This is a disclosure dataset with
   no suppression — if an owner is listed, all fields are present.

**Limitations confirmed:**
- **No PE identification.** `owner_type` is only `Individual` / `Organization`. CMS
  cannot distinguish PE-backed LLCs from other for-profit corporate structures. GAO
  has confirmed PE identification from CMS data alone is unreliable.
- **Current snapshot only.** When an owner leaves, their row is removed. No historical
  ownership data retained. Previous owners are not available.
- **Ownership percentages incomplete.** `"NO PERCENTAGE PROVIDED"` is common for
  indirect interests, making controlling interest determination impossible through the
  ownership chain in many cases.

**Display approach:** Surface what CMS publishes — named entities, roles, ownership
percentages where available, association dates. Flag ownership change clustering. Show
management company identity when distinct from owning entity. Do not claim PE
identification. See `docs/product_philosophy.md` for full product treatment.

**Refresh schedule:** Monthly (per NH Data Dictionary)

---

### 21. SNF QRP Provider Data

**Status:** [~] In progress — dataset ID confirmed, field names confirmed

**Socrata Dataset ID:** `fykj-qjee` (confirmed 2026-03-16, 838,470 rows, 16 columns)

**Confirmed API field names:** `cms_certification_number_ccn`, `provider_name`,
`address_line_1` (**note: different from NH datasets which use `provider_address`**),
`citytown`, `state`, `zip_code`, `countyparish`, `telephone_number`, `cms_region`,
`measure_code` (e.g. `"S_004_01_PPR_PD_COMP_PERF"`), `score` (e.g. `"No Different
than the National Rate"`), `footnote` (e.g. `"-"`), `start_date` (e.g.
`"10/01/2022"` — MM/DD/YYYY format, **different from other datasets**), `end_date`,
`measure_date_range`, `location1` (**note: `location1` not `location`**).

**Notable API observations:**
- `measure_code` includes a suffix (e.g. `_PPR_PD_COMP_PERF`) beyond the base code
  documented in the NH Data Dictionary (e.g. `S_004_01`). Must catalog all distinct
  measure_code values to understand the naming pattern.
- `score` field contains both numeric values AND categorical text (e.g. `"No Different
  than the National Rate"`) — similar to hospital `compared_to_national` issue.
- `footnote` uses `"-"` dash for no footnote (not empty string like other NH datasets).
- Date format is `MM/DD/YYYY` not `YYYY-MM-DD` — normalizer must handle this.

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Tables 19-22 (SNF QRP variables and measure codes)

**Expected measure codes:**
S_004_01, S_005_02, S_006_01, S_007_02, S_013_02, S_024_06, S_025_06, S_038_02,
S_039_01, S_040_02, S_041_01, S_042_02, S_043_02, S_044_02, S_045_01

**Suppression encoding:** Footnotes 1, 7, 9, 10, 13, 14 _(confirm against live data)_

**Refresh schedule:** Quarterly — January, April, July, October

---

### 22. SNF VBP Facility-Level Dataset

**Status:** [~] In progress — dataset ID confirmed, field names confirmed

**Socrata Dataset ID:** `284v-j9fz` (confirmed 2026-03-16, 13,900 rows, 49 columns)

**Reference docs:**
- `docs/NH_Data_Dictionary.txt` — Tables 24-25 (SNF VBP variables)

**FY 2026 measures (4):**
- SNF 30-Day All-Cause Readmission (SNFRM)
- SNF Healthcare-Associated Infections Requiring Hospitalization (SNF HAI)
- Total Nursing Staff Turnover Rate
- SNF Quality Measure Suite (SNFQMS)

**Confirmed API field names (selected — 49 total):**

The SNF VBP dataset has 4 measures, each with: baseline rate, performance rate,
achievement score, improvement score, and measure score (5 fields × 4 measures = 20),
plus footnotes for each (another 20), plus ranking, performance score, and incentive
payment multiplier.

Key confirmed fields:
- `snf_vbp_program_ranking` — program ranking (string integer)
- `cms_certification_number_ccn`, `provider_name`, address fields
- `baseline_period_fy_2022_riskstandardized_readmission_rate` — SNFRM baseline
- `performance_period_fy_2024_riskstandardized_readmission_rate` — SNFRM performance
- `snfrm_achievement_score`, `snfrm_improvement_score`, `snfrm_measure_score`
- Similar pattern for `snf_hai_*` fields
- `total_nursing_staff_turnover_*` fields — note: many facilities show `"---"` with
  footnote about not meeting case minimum
- `total_nurse_staffing_*` fields — the 4th measure (SNFQMS = adjusted total nurse
  staffing hours per resident per day)
- `performance_score` — aggregate
- `incentive_payment_multiplier` — e.g. `"1.0272499277"`

**Notable:** Some field names are truncated with hash suffixes (e.g.
`footnote__baseline_period_fy_2022_riskstandardized_readmiss_01ae`). Same truncation
issue as NH Provider Info (W-NH-5 resolved, but field name truncation is a general
DKAN behavior).

**Notable:** `"---"` used as sentinel for excluded/not-applicable values (not empty
string). Footnote text provides the reason (e.g. "This facility did not meet this
measure's case minimum policy requirement").

**Refresh schedule:** Annual (per fiscal year)

---

### Confirmed Nursing Home Measure Code Catalog

**Status:** [x] Complete — all measure codes confirmed against live API 2026-03-17

#### MDS Quality Measures (djen-97ju) — 17 measures

| Code | Resident Type | Five-Star | Measure Name |
|------|---------------|-----------|--------------|
| 401 | Long Stay | **Y** | Percentage of long-stay residents whose need for help with daily activities has increased |
| 404 | Long Stay | N | Percentage of long-stay residents who lose too much weight |
| 406 | Long Stay | **Y** | Percentage of long-stay residents with a catheter inserted and left in their bladder |
| 407 | Long Stay | **Y** | Percentage of long-stay residents with a urinary tract infection |
| 408 | Long Stay | N | Percentage of long-stay residents who have depressive symptoms |
| 409 | Long Stay | N | Percentage of long-stay residents who were physically restrained |
| 410 | Long Stay | **Y** | Percentage of long-stay residents experiencing one or more falls with major injury |
| 415 | Long Stay | N | Percentage of long-stay residents assessed and appropriately given the pneumococcal vaccine |
| 430 | Short Stay | N | Percentage of short-stay residents assessed and appropriately given the pneumococcal vaccine |
| 434 | Short Stay | **Y** | Percentage of short-stay residents who newly received an antipsychotic medication |
| 451 | Long Stay | **Y** | Percentage of long-stay residents whose ability to walk independently worsened |
| 452 | Long Stay | N | Percentage of long-stay residents who received an antianxiety or hypnotic medication |
| 454 | Long Stay | N | Percentage of long-stay residents assessed and appropriately given the seasonal influenza vaccine |
| 472 | Short Stay | N | Percentage of short-stay residents who were assessed and appropriately given the seasonal influenza vaccine |
| 479 | Long Stay | **Y** | Percentage of long-stay residents with pressure ulcers |
| 480 | Long Stay | N | Percentage of long-stay residents with new or worsened bowel or bladder incontinence |
| 481 | Long Stay | **Y** | Percentage of long-stay residents who received an antipsychotic medication |

**7 long-stay Five-Star measures:** 401, 406, 407, 410, 451, 479, 481
**1 short-stay Five-Star measure:** 434
**9 non-Five-Star measures:** 404, 408, 409, 415, 430, 452, 454, 472, 480

#### Medicare Claims Quality Measures (ijh5-nb2v) — 4 measures

| Code | Resident Type | Five-Star | Measure Name |
|------|---------------|-----------|--------------|
| 521 | Short Stay | **Y** | Percentage of short-stay residents who were rehospitalized after a nursing home admission |
| 522 | Short Stay | **Y** | Percentage of short-stay residents who had an outpatient emergency department visit |
| 551 | Long Stay | **Y** | Number of hospitalizations per 1000 long-stay resident days |
| 552 | Long Stay | **Y** | Number of outpatient emergency department visits per 1000 long-stay resident days |

**2 long-stay Five-Star measures:** 551, 552
**2 short-stay Five-Star measures:** 521, 522

#### Critical Finding: Discharge Function and Successful Return Measures

The Five-Star Technical Users' Guide lists 15 measures in the QM domain: 9 long-stay +
6 short-stay. The MDS and Claims datasets contain only 12 of these 15. The remaining 3
measures come from **different datasets**:

| Five-Star Measure | NOT in MDS/Claims | Actual Source |
|---|---|---|
| Discharge function score (short-stay) | Not in djen-97ju or ijh5-nb2v | SNF QRP: `S_042_02` (fykj-qjee) |
| Short-stay pressure ulcer (new/worsened) | Not in ijh5-nb2v | SNF QRP: `S_038_02` (fykj-qjee) |
| Successful return to home/community (short-stay) | Not in ijh5-nb2v | SNF QRP: `S_005_02` (fykj-qjee) |

Wait — looking more carefully: short-stay pressure ulcer IS measure 434? No, 434 is
antipsychotic. Let me check: The Five-Star guide lists "Percentage of SNF residents
with pressure ulcers/pressure injuries that are new or worsened" as a short-stay MDS
measure, but it's not in the 17 MDS codes above.

**Reconciliation of Five-Star 15 measures vs. dataset sources:**

Long-stay (9 in Five-Star):
- 7 MDS: 401, 451, 479, 406, 407, 410, 481
- 2 Claims: 551, 552

Short-stay (6 in Five-Star):
- 1 MDS: 434 (antipsychotic)
- 2 Claims: 521, 522
- 3 from SNF QRP dataset: S_042_02 (discharge function), S_038_02 (new/worsened
  pressure ulcers), S_005_02 (successful return to community)

**This means the Five-Star QM rating calculation draws from THREE datasets, not two.**
The pipeline must join data from djen-97ju, ijh5-nb2v, AND fykj-qjee to reproduce the
full 15-measure QM domain. This is a schema/pipeline design decision that must be
documented in `docs/pipeline_decisions.md`.

#### SNF QRP Measure Codes (fykj-qjee) — 57 distinct measure_code values

The SNF QRP dataset uses a compound measure_code format:
`{base_code}_{suffix}` where:
- Base codes: S_004_01, S_005_02, S_006_01, S_007_02, S_013_02, S_024_06, S_025_06,
  S_038_02, S_039_01, S_040_02, S_041_01, S_042_02, S_043_02, S_044_02, S_045_01
- Suffixes indicate sub-measures: `_OBS_RATE` (observed rate), `_DENOMINATOR`,
  `_NUMERATOR`, `_ADJ_RATE` (adjusted rate), `_COMP_PERF` (compared to national),
  `_RSRR` (risk-standardized rate), `_RSRR_2_5` / `_RSRR_97_5` (confidence interval),
  `_VOLUME`, `_NUMBER`, `_SCORE`

**Suppression encoding:** `"Not Available"` in `score` field. `"-"` (dash) in
`footnote` field when no footnote applies.

**Date format anomaly:** `start_date` and `end_date` use `MM/DD/YYYY` format (e.g.
`"10/01/2022"`), unlike all other NH datasets which use `YYYY-MM-DD`.

**Compound measure_code suffixes (confirmed from SNF QM manual v7.0 + live API):**

The manual uses base IDs like `S004.01` but the API uses compound codes with suffixes.
The suffix pattern is `{base}_{abbreviation}_{data_type}`:

| Suffix | Meaning | Example |
|---|---|---|
| `_OBS_RATE` | Observed (unadjusted) rate | `S_004_01_PPR_PD_OBS` (observed count) |
| `_RSRR` | Risk-standardized readmission/return rate | `S_004_01_PPR_PD_RSRR` |
| `_RSRR_2_5` | Risk-standardized rate — 2.5th percentile CI | `S_004_01_PPR_PD_RSRR_2_5` |
| `_RSRR_97_5` | Risk-standardized rate — 97.5th percentile CI | `S_004_01_PPR_PD_RSRR_97_5` |
| `_COMP_PERF` | Compared to national rate (categorical) | `S_004_01_PPR_PD_COMP_PERF` |
| `_VOLUME` | Eligible stay/episode count | `S_004_01_PPR_PD_VOLUME` |
| `_OBS_READM` | Observed readmission count | `S_004_01_PPR_PD_OBS_READM` |
| `_DENOMINATOR` | Denominator count | `S_013_02_DENOMINATOR` |
| `_NUMERATOR` | Numerator count | `S_013_02_NUMERATOR` |
| `_ADJ_RATE` | Risk-adjusted rate | `S_038_02_ADJ_RATE` |
| `_NUMBER` | Count (e.g., eligible episodes) | `S_005_02_DTC_NUMBER` |
| `_RS_RATE` | Risk-standardized rate (DTC variant) | `S_005_02_DTC_RS_RATE` |
| `_RS_RATE_2_5` | RS rate — 2.5th percentile CI | `S_005_02_DTC_RS_RATE_2_5` |
| `_RS_RATE_97_5` | RS rate — 97.5th percentile CI | `S_005_02_DTC_RS_RATE_97_5` |
| `_SCORE` | MSPB ratio score | `S_006_01_MSPB_SCORE` |
| `_NUMB` | MSPB episode count | `S_006_01_MSPB_NUMB` |

Middle abbreviations: `PPR` = Potentially Preventable Readmission, `PD` = unknown
(possibly "Provider Data" or "Public Display"), `DTC` = Discharge to Community,
`MSPB` = Medicare Spending Per Beneficiary, `HAI` = Healthcare-Associated Infections.

**The manual does NOT document these compound codes.** They are CMS internal API
conventions. The base measure IDs from the manual are: S004.01, S005.02, S006.01,
S007.02, S013.02, S024.06/.07, S025.06/.07, S038.02, S039.01, S040.02, S041.01,
S042.02/.03, S043.02, S044.02, S045.01.

**Version discrepancy:** The live API currently shows `S_042_02` but the SNF QM
manual v7.0 (effective 10/01/2025) documents version `.03`. The live data may be on
the previous version's reporting period. Must verify which version is active in the
current data refresh. Similarly, `S_024_06` in live data but manual documents `.07`,
and `S_025_06` in live data but manual documents `.07`. This suggests the API code
encodes the version at time of data collection, not the current measure version.

**SNF QRP measure classification (from SNF QM manual v7.0):**

| Measure | Type | Risk-Adjusted | Reporting Period | CBE |
|---|---|---|---|---|
| S004.01 (PPR) | Claims, Outcome | Yes | 12 mo | No |
| S005.02 (DTC) | Claims, Outcome | Yes | 12 mo | Yes |
| S006.01 (MSPB) | Claims, Cost | Yes | 12 mo | No |
| S007.02 (DRR) | MDS, Process | No | 12 mo | No |
| S013.02 (Falls) | MDS, Outcome | No | 12 mo | No |
| S024.07 (Self-Care) | MDS, Outcome | Yes (18 covariates) | 12 mo | No |
| S025.07 (Mobility) | MDS, Outcome | Yes (18 covariates) | 12 mo | No |
| S038.02 (Pressure Ulcer) | MDS, Outcome | Yes (4 covariates) | 12 mo | No |
| S039.01 (SNF HAI) | Claims, Outcome | Yes | 12 mo | Yes |
| S040.02 (HCP COVID Vax) | NHSN, Process | No | Annual | Yes |
| S041.01 (HCP Flu Vax) | NHSN, Process | No | Annual | Yes |
| S042.03 (Function Score) | MDS, Outcome | Yes (23 covariates) | 12 mo | Yes |
| S043.02 (TOH-Provider) | MDS, Process | No | 12 mo | No |
| S044.02 (TOH-Patient) | MDS, Process | No | 12 mo | No |
| S045.01 (Resident COVID) | MDS, Process | No | **3 mo (1 quarter)** | No |

**Critical finding: S045.01 uses ONE QUARTER only** — not cumulative across quarters
like other measures. Each quarter stands alone.

**MDS version transition (10/01/2025):** MDS 3.0 v1.19.1 → v1.20.1 affects risk
adjustment for S024.07, S025.07, and S042.03. Items O0400B/O0400C replaced by
O0425B/O0425C for therapy covariate. Risk-Adjustment Appendix File will contain
separate coefficient tables per MDS version. The pipeline must handle both item sets
based on assessment target date.

---

### Five-Star Quality Rating System — Confirmed Methodology

**Status:** [x] Complete — methodology extracted from CMS Five-Star Technical Users'
Guide (January 2026). Source: `docs/nh-five-star-users-guide-january-2026.txt`.

#### Overall Rating Composition (3 steps)

The overall Five-Star rating is **NOT a weighted average.** It is built in three steps:

1. **Start with the Health Inspection rating** (1-5 stars)
2. **Adjust for Staffing:** +1 star if staffing = 5 stars; -1 star if staffing = 1 star
3. **Adjust for Quality Measures:** +1 star if QM = 5 stars; -1 star if QM = 1 star

**Cap rule:** If health inspection rating = 1 star, the overall rating cannot be
upgraded by more than 1 star total from staffing + QM combined. Minimum = 1, maximum = 5.

**Rationale:** Health inspection is weighted most heavily because it reflects findings
from actual onsite visits by trained surveyors. CMS does not want high staffing or QM
scores to override serious inspection findings.

**Missing data:** If no health inspection rating → no overall rating. If nursing home
is too new for two standard surveys → no ratings displayed for any domain. If in SFF
program → no ratings displayed (yellow warning sign instead).

#### Health Inspection Domain

**Rating basis:** State-level relative performance (not national).
- Top 10% in state → 5 stars
- Middle 70% → 2, 3, or 4 stars (equal thirds: ~23.3% each)
- Bottom 20% → 1 star

**Score calculation:**
- Based on 2 most recent standard inspection surveys (changed from 3 in July 2025)
- Plus complaint/infection control deficiencies from most recent 36 months
- Each deficiency scored by scope/severity (Table 1 in guide):
  - Immediate jeopardy (J/K/L): 50-175 points
  - Actual harm (G/H/I): 20-50 points
  - Potential harm (D/E/F): 4-20 points
  - Potential minimal harm (A/B/C): 0 points
- Substandard quality of care adds bonus points (parenthetical values in Table 1)
- Past non-compliance at immediate jeopardy level → reduced to G-level (20 points)
- Repeat revisit penalties: 2nd revisit = 50%, 3rd = 70%, 4th = 85% of inspection score
- Weighting: Cycle 1 (most recent) = 3/4, Cycle 2 = 1/4
- Complaint/infection control: 0-12 months = 3/4 weight, 13-36 months = 1/4 weight

**Abuse icon:** Facilities cited for abuse (F600/F602/F603) at harm level or above get
health inspection rating capped at 2 stars and icon displayed.

**Cut points:** State-specific, recalibrated monthly. Available in the State-Level
Health Inspection Cut Points dataset (`hicp-9999`).

#### Staffing Domain

**6 measures, max 380 points total:**

| Measure | Max Points | Scoring | Source |
|---------|-----------|---------|--------|
| Adjusted Total Nurse HPRD | 100 | Deciles (10-100) | PBJ + MDS case-mix |
| Adjusted RN HPRD | 100 | Deciles (10-100) | PBJ + MDS case-mix |
| Adjusted Weekend Total Nurse HPRD | 50 | Deciles (5-50) | PBJ + MDS case-mix |
| Total Nurse Turnover (%) | 50 | Deciles (5-50, inverted) | PBJ 6-quarter |
| RN Turnover (%) | 50 | Deciles (5-50, inverted) | PBJ 6-quarter |
| Administrator Departures | 30 | 0→30pts, 1→25pts, 2+→10pts | PBJ 4-quarter |

**Rating thresholds (380 max):**

| Stars | Point Range |
|-------|-------------|
| 1 | < 155 |
| 2 | 155-204 |
| 3 | 205-254 |
| 4 | 255-319 |
| 5 | 320-380 |

**Scoring exceptions (force 1-star):**
- No staffing data submitted
- 4+ days with no RN hours when residents present
- Failed PBJ audit with significant discrepancies

**Missing turnover data:** If staffing levels valid but turnover measures missing, score
is rescaled: `actual_points × (380 / max_possible_points)`.

**Cut points for individual measures:** See Appendix Table A2 in the guide. Recorded
in `docs/nh-five-star-users-guide-january-2026.txt` pages 28-31.

#### Quality Measure Domain

**15 measures, 3 scoring tiers:**

**150-point measures (decile scoring, 15-point intervals):**
- Long-stay: ADL worsening (401), antipsychotic (481), mobility decline (451),
  hospitalizations (551), ED visits (552)
- Short-stay: discharge function (S_042_02), successful return (S_005_02),
  rehospitalization (521), ED visits (522)

**100-point measures (quintile scoring, 20-point intervals):**
- Long-stay: falls (410), pressure ulcers (479), UTI (407), catheter (406)
- Short-stay: antipsychotic (434), new/worsened pressure ulcers (S_038_02)

**Score ranges:**
- Long-stay QM score: 155-1,150 points (9 measures)
- Short-stay QM score (unadjusted): 100-800 points (6 measures)
- Short-stay QM score (adjusted): 144-1,150 points (multiplied by 1,150/800 = 1.4375)
- Overall QM score: 299-2,300 points (long-stay + adjusted short-stay)

**Rating thresholds (as of January 2025):**

| Stars | Long-Stay | Short-Stay (adj) | Overall |
|-------|-----------|-------------------|---------|
| 1 | 155-465 | 144-438 | 299-904 |
| 2 | 466-565 | 439-525 | 905-1,091 |
| 3 | 566-640 | 526-625 | 1,092-1,266 |
| 4 | 641-735 | 626-719 | 1,267-1,455 |
| 5 | 736-1,150 | 720-1,150 | 1,456-2,300 |

**Missing data imputation:**
- If ≥5 of 9 long-stay measures available → impute missing from state average
- If ≥4 of 6 short-stay measures available → impute missing from state average
- If fewer than thresholds above → rate based on available domain only
- Imputed values NOT publicly reported; only used for rating calculation

**Schizophrenia coding audit penalty:** Facilities found coding inaccurately have QM
and long-stay QM ratings forced to 1 star for 6 months.

**QM cut points for individual measures:** See Appendix Table A3 in the guide. Recorded
in `docs/nh-five-star-users-guide-january-2026.txt` pages 30-35.

---

### Nursing Home Footnote Code Lookup Table

**Status:** [~] In progress — reference table documented, must be confirmed against live data samples

**Source:** NH Data Dictionary, Table 15

Nursing home footnote codes are **distinct from hospital footnote codes** and must not
be conflated. The hospital footnote crosswalk (`docs/Footnote_Crosswalk.csv`) does NOT
apply to nursing home data.

| Code | Expected Explanation | Suppression? | Notes |
|------|---------------------|--------------|-------|
| 1 | Newly certified NH, <12-15 months data or <6 months open | Yes | |
| 2 | Not enough data for star rating | Yes | |
| 6 | Data did not meet criteria for staffing measure | Partial | |
| 7 | CMS determined percentage not accurate or data suppressed | Yes | |
| 9 | Number of residents/stays too small to report | Yes | |
| 10 | Data missing or not submitted | Yes | |
| 13 | Results based on shorter time period than required | No | |
| 14 | Not required to submit SNF QRP data | Yes | |
| 18 | Not rated due to SFF program | Yes | |
| 20 | Accuracy of data for this rating could not be validated | No | |
| 21 | Accuracy of data for this measure could not be validated | No | |
| 22 | Street address could not be matched; lat/long based on zip | No | |
| 23 | Facility did not submit staffing data | Yes | |
| 24 | Facility reported high number of days without RN onsite | No | |
| 25 | Accuracy of staffing data could not be validated | No | |
| 26 | No staffing data or invalid data for turnover; receives minimum points | Yes | |
| 27 | Staffing data did not meet criteria for turnover; excluded from rating | Partial | |
| 28 | Annual measure; quarterly data not available | No | |

_(All codes to be confirmed against live API responses during recon)_