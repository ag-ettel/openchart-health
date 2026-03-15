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

**Status:** [x] Confirmed 2026-03-14. All fields, suppression encoding, footnote structure, and refresh schedule confirmed. Sample expanded to 1000 rows (2026-03-14); footnote codes 19 and 22 confirmed; footnote 19 identified as a distinct not_reported state for Rural Emergency Hospitals.

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

**Notes:** CMS full name for this dataset is "Use of Medical Imaging: Outpatient Imaging Efficiency (OIE)". Three active measures as of January 2026: OP-8 (MRI Lumbar Spine for Low Back Pain), OP-10 (Abdomen CT — use of contrast), OP-13 (Cardiac Imaging for Preoperative Risk Assessment). Lower-is-better for all measures (lower rate = more efficient/appropriate use). SES sensitivity LOW.

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

**Status:** [x] Confirmed 2026-03-14 from 400-row sample of xubh-q36u.

Confirmed `hospital_type` enum values from Hospital General Information (xubh-q36u):

| CMS API String | Notes |
|---|---|
| `Acute Care Hospitals` | Most common (~67% of 400-row sample) |
| `Critical Access Hospitals` | Maps to `is_critical_access = true` — no separate boolean field |
| `Psychiatric` | |
| `Rural Emergency Hospital` | Relatively new designation |
| `Acute Care - Veterans Administration` | VHA facilities |
| `Childrens` | |
| `Acute Care - Department of Defense` | DoD facilities |

Confirmed `hospital_ownership` enum values from Hospital General Information (xubh-q36u):

| CMS API String |
|---|
| `Voluntary non-profit - Private` |
| `Proprietary` |
| `Government - Hospital District or Authority` |
| `Voluntary non-profit - Other` |
| `Government - Local` |
| `Voluntary non-profit - Church` |
| `Tribal` |
| `Government - State` |
| `Government - Federal` |
| `Veterans Health Administration` |
| `Physician` |
| `Department of Defense` |

**Note:** These values come from a 1000-row sample (expanded from initial 400-row sample; no new enum values found in the additional 600 rows). The full dataset has 5,426 rows. Additional rare values may exist. The migration enum must accommodate future values via a fallback or use varchar rather than a rigid PostgreSQL enum if CMS adds new ownership/type strings without notice.

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

## Open Items

- [x] All active Socrata dataset IDs confirmed against live API (DEC-008, 2026-03-14)
- [x] At least one suppressed row fixture per dataset — complete for 10/11 datasets; ypbt-wvdk has no suppression in the full dataset (confirmed 1000-row sample). See `tests/pipeline/fixtures/hospital/fixture_gaps.md`.
- [x] At least one not-reported row fixture per dataset — complete where a distinct not_reported state exists; 4 datasets have no structurally distinct not_reported encoding (yv7e-xc69, dgck-syfz, ynj2-r877, 632h-zaca). See `fixture_gaps.md`.
- [x] At least one footnote-code row fixture per dataset — complete for 10/11 datasets; ypbt-wvdk has no footnote fields. See `fixture_gaps.md`.
- [x] All field name discrepancies resolved (see DEC-008, decisions.md — `_condition` key in TE, HCAHPS footnote structure, HACRP wide-format, VBP summary-only)
- [x] All suppression encodings documented per dataset (see each dataset section above — confirmed 2026-03-14 via analyze_encodings.py and manual row inspection)
- [x] All footnote code structures confirmed per dataset (confirmed 2026-03-14 — comma-space delimiter; HCAHPS targeted pull resolved AMB-6)
- [x] provider_subtype hospital enum values confirmed (2026-03-14, see Provider Subtype section)
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
- [ ] Write initial Alembic migration — requires schema decisions for AMB-3, AMB-5 (T&E EDV `score_text`), AMB-4 (HRRP count_suppressed) to be recorded in pipeline_decisions.md first (B-1 through B-4 now resolved via DEC-009 through DEC-012)
- [ ] Draft MEASURE_REGISTRY entries for all hospital datasets with direction, ses_sensitivity, tail_risk_flag, and phase_0_findings.md references
- [ ] Populate `docs/data_dictionary.md` measure tables (per-measure direction and SES classifications)
- [ ] Document AMB-3 canonical enum values for `compared_to_national` in data_dictionary.md
- [ ] Document AMB-5 T&E EDV schema decision in pipeline_decisions.md
- [ ] Document AMB-4 HRRP count-suppression schema decision in pipeline_decisions.md
- [x] Document B-1: xubh-q36u group summary field scope decision — DEC-009 (2026-03-14)
- [x] Document B-2: `hcahps_linear_mean_value` storage decision — DEC-010 (2026-03-14)
- [x] Document B-3: VBP domain score column naming decision — DEC-011 (2026-03-14)
- [x] Document B-4: HACRP Winsorized Z-score storage decision — DEC-012 (2026-03-14)
