# Fixture Gaps

This document records missing fixture categories per dataset, all distinct suppression
values observed, all distinct footnote codes observed, and encoding patterns confirmed
or updated in the expanded 1000-2000 row sample analysis (2026-03-14).

All fixture rows are verbatim from raw sample files in `scripts/recon/raw_samples/`.
Sample sizes reflect rows flattened across all pages in the raw sample file.

---

## xubh-q36u - Hospital General Information

**Sample size:** 1000 rows

**Suppression values observed (hospital_overall_rating):**
- `"Not Available"` — used for all suppressed/unavailable ratings

**Footnote codes observed (all footnote fields combined):**
- `5` — hospital_overall_rating_footnote, mort/safety/readm/pt_exp/te group footnotes
- `16` — hospital_overall_rating_footnote
- `19` — all group footnote fields (results cannot be calculated — Rural Emergency Hospital type)
- `22` — all group footnote fields

**not_reported:** FOUND. Rows where `hospital_overall_rating = "Not Available"` AND
`hospital_overall_rating_footnote = "19"` represent hospitals for which results cannot
be calculated for the current reporting period (Rural Emergency Hospitals primarily).
This is a distinct state from standard suppression (footnote 16 = insufficient volume).
The `not_reported` fixture uses a Rural Emergency Hospital row with footnote 19 across
all group footnote fields.

**null_denominator:** Not applicable. This dataset contains provider metadata, not
measure rate values with denominators.

**count_suppressed:** Not applicable.

---

## yv7e-xc69 - Timely and Effective Care

**Sample size:** 1000 rows

**Suppression values observed (score field):**
- `"Not Available"` — standard suppression (539 of 1000 rows)
- `"low"` — EDV categorical score
- `"medium"` — EDV categorical score
- `"high"` — EDV categorical score
- `"very high"` — EDV categorical score

**Footnote codes observed:**
- `1` — results based on fewer than the required number of cases/respondents
- `2` — data submitted was based on a sample
- `3` — results based on an incomplete calendar year
- `5` — results not available (hospital not reporting / participation)
- `7` — CMS and the hospital jointly reviewed the data
- `29` — measure methodology changed
- Comma-separated combinations observed: `"1, 3"`, `"2, 3"`, `"3, 29"`, `"1, 3, 29"`, `"2, 3, 29"`, etc.

**not_reported:** NULL. Footnote code 19 does not appear in this 1000-row sample for
the T&E dataset (all suppressed rows use footnote codes 1, 2, 3, 5, 7, 29). There is
no distinct not_reported encoding separate from suppressed in this sample. The EDV
measure has an empty `sample` field by design (categorical measure, not a rate). This
is captured in `null_denominator`, not `not_reported`.

**null_denominator:** FOUND. EDV rows have `sample = ""` (empty string) — EDV is a
categorical volume measure with no applicable denominator. This is structurally
distinct from suppression.

**count_suppressed:** Not applicable.

---

## dgck-syfz - HCAHPS Patient Survey

**Sample size:** 2000 rows

**Suppression values observed:**
- `hcahps_answer_percent`: `"Not Available"` (158 rows), `"Not Applicable"` (497 rows)
- `patient_survey_star_rating`: `"Not Applicable"` (1737 rows), `"Not Available"` (65 rows)
- `hcahps_linear_mean_value`: `"Not Applicable"` (1766 rows), `"Not Available"` (58 rows)

Note: `"Not Applicable"` indicates the question type does not have a percent answer
(e.g., star rating questions). This is a structural absence, not suppression.
`"Not Available"` indicates the hospital did not have enough responses to report.

**Footnote codes observed:**
- `hcahps_answer_percent_footnote`: `1`, `6`, `10`, `11`, `29`
- `patient_survey_star_rating_footnote`: `15`
- `number_of_completed_surveys_footnote`: `6`, `10`, `11`, `29`
- `survey_response_rate_percent_footnote`: `6`, `10`, `11`, `29`

**not_reported:** NULL. No encoding distinct from `"Not Available"` (suppressed) found
in this 2000-row sample. All suppressed `hcahps_answer_percent` rows use footnote code
`1` (too few responses). No separate not_reported state confirmed.

**null_denominator:** NULL. The `number_of_completed_surveys` field is always a numeric
value in this 2000-row sample (min: 27, max: 6361). No null/Not Available/zero values
observed for this field. Hospitals with very low survey counts (below CMS threshold)
appear to be excluded from the API response rather than included with a null denominator.

**count_suppressed:** Not applicable.

---

## ynj2-r877 - Complications and Deaths

**Sample size:** 1000 rows

**Suppression values observed (score field):**
- `"Not Available"` — 332 of 1000 rows

**Footnote codes observed:**
- `1` — results based on fewer than the required number of cases
- `5` — results not available (hospital not reporting)
- `7` — CMS and the hospital jointly reviewed the data
- `28` — measure statistical methodology revised
- `29` — measure methodology changed
- Combinations observed: `"1, 28"`

**not_reported:** NULL. All 332 suppressed rows use footnote codes 1, 5, 7, or 28.
There is no footnote code 19 in this dataset's 1000-row sample. Footnote code 5
(hospital not reporting) co-occurs with `score = "Not Available"` but is treated as
suppressed in the pipeline because the score field value is identical to the standard
suppression sentinel. No encoding that is structurally distinct from suppressed was
found. Note: `"Number of Cases Too Small"` value in `compared_to_national` co-occurs
with `score = "Not Available"` — this is a supplementary description of suppression,
not a separate not_reported state (see AMB-3 in pipeline_decisions.md).

**null_denominator:** FOUND. Rows with `measure_id = "PSI_90"` have
`denominator = "Not Applicable"` because PSI-90 is a composite index with no single
case count denominator.

**count_suppressed:** Not applicable.

---

## 77hc-ibv8 - Healthcare-Associated Infections (HAI)

**Sample size:** 1000 rows

**Suppression values observed (score field):**
- `"Not Available"` — 309 rows; standard suppression (typically footnote 13 or 12)
- `"N/A"` — 22 rows; distinct state: confidence interval bounds not applicable when
  observed infections = 0 or measure structurally inapplicable (footnote 8)

**Footnote codes observed:**
- `3` — fewer than the required number of cases
- `5` — results not available
- `8` — no cases meeting the inclusion criteria; confidence interval not applicable
- `12` — this measure does not apply to this hospital
- `13` — results are not available for this reporting period
- `29` — measure methodology changed
- Combinations observed: `"3, 29"`, `"3, 13"`, `"13, 29"`, `"8, 29"`

**not_reported:** FOUND with semantic caveat. Rows where `score = "N/A"` with `footnote = "8"` represent a structurally distinct state: the HAI confidence interval sub-measure is mathematically undefined because zero infections were observed (footnote 8 = "no cases meeting inclusion criteria; confidence interval not applicable"). The hospital WAS evaluated — `compared_to_national` carries a valid value. This differs from `"Not Available"` (suppressed) which indicates insufficient data to report. The `not_reported` fixture uses a CILOWER sub-measure row with `score = "N/A"` and `footnote = "8"`.

**Normalizer decision needed:** Whether to store this as `not_reported` or `not_applicable` is a schema question. Arguments for `not_applicable`: the hospital had zero infections, so the CI bound is structurally undefined, not withheld. Arguments for `not_reported`: from a display perspective, the CI bound cannot be shown. The normalizer should handle this as a third distinct state (beyond `suppressed` and `not_reported`) if the schema allows — see pipeline_decisions.md for the resolution.

**null_denominator:** Not applicable. HAI dataset does not include a denominator field
in the API response (denominator is embedded in the SIR calculation, not exposed).

**count_suppressed:** Not applicable.

---

## 632h-zaca - Unplanned Hospital Visits (Readmissions)

**Sample size:** 1000 rows

**Suppression values observed (score field):**
- `"Not Available"` — 423 of 1000 rows

**Footnote codes observed:**
- `1` — results based on fewer than the required number of cases
- `5` — results not available (hospital not reporting)
- `7` — CMS and the hospital jointly reviewed the data
- `28` — measure statistical methodology revised
- `29` — measure methodology changed
- Combinations observed: `"1, 28"`

**not_reported:** NULL. All suppressed rows use footnote codes 1, 5, 7, or 28. No
footnote code 19 observed in this 1000-row sample. No encoding structurally distinct
from the standard suppressed state (`score = "Not Available"`) was found.

**null_denominator:** FOUND. Rows where `number_of_patients = "Not Applicable"` (e.g.,
Hybrid_HWR measure) have a denominator field present but not applicable. These rows
still have a populated `denominator` (case count for the rate), but `number_of_patients`
and `number_of_patients_returned` are `"Not Applicable"` because the Hybrid measure
uses a different methodology that doesn't count patients the same way.

**count_suppressed:** Not applicable.

---

## wkfw-kthe - Outpatient Imaging Efficiency

**Sample size:** 1000 rows

**Suppression values observed (score field):**
- `"Not Available"` — 546 of 1000 rows

**Footnote codes observed:**
- `1` — results based on fewer than the required number of cases
- `5` — results not available (hospital not reporting)
- `7` — CMS and the hospital jointly reviewed the data
- `19` — results cannot be calculated for this reporting period
- `29` — measure methodology changed

**not_reported:** FOUND. Rows where `score = "Not Available"` AND `footnote = "19"`
represent hospitals where results cannot be calculated for the current reporting period
(distinct from footnote 1 = too few cases, or footnote 5 = hospital not reporting).
48 rows with footnote 19 found in 1000-row sample.

**null_denominator:** Not applicable. This dataset does not include a denominator field.

**count_suppressed:** Not applicable.

---

## rrqw-56er - Medicare Hospital Spending Per Patient

**Sample size:** 1000 rows

**Suppression values observed (score field):**
- `"Not Available"` — 208 of 1000 rows

**Footnote codes observed:**
- `1` — results based on fewer than the required number of cases
- `5` — results not available (hospital not reporting)
- `19` — results cannot be calculated for this reporting period
- `29` — measure methodology changed

**not_reported:** FOUND. Rows where `score = "Not Available"` AND `footnote = "19"`
represent hospitals where MSPB results cannot be calculated for the current period.
37 rows with footnote 19 found in 1000-row sample.

**null_denominator:** Not applicable. Single MSPB-1 measure; no denominator field.

**count_suppressed:** Not applicable.

---

## 9n3s-kdb3 - Hospital Readmissions Reduction Program (HRRP)

**Sample size:** 1000 rows

**Suppression values observed:**
- `excess_readmission_ratio`: `"N/A"` — 413 rows (measure not applicable)
- `number_of_readmissions`: `"N/A"` — 413 rows, `"Too Few to Report"` — 209 rows
- `number_of_discharges`: `"N/A"` — 607 rows

**Footnote codes observed:**
- `1` — too few discharges to calculate (small volume)
- `5` — hospital not participating in the program
- `7` — CMS and the hospital jointly reviewed the data
- `29` — measure methodology changed

**not_reported:** FOUND. Rows where `excess_readmission_ratio = "N/A"` AND
`footnote = "1"` (too few discharges) are distinct from rows with `footnote = "5"`
(hospital not participating). The `not_reported` fixture uses a row with `footnote = "1"`
to represent the small-volume non-reporting state, distinct from the `suppressed`
fixture which uses `footnote = "5"` (non-participation).

**null_denominator:** Not applicable. No denominator field in this dataset.

**count_suppressed (AMB-4):** CONFIRMED. 209 rows found where
`number_of_readmissions = "Too Few to Report"` co-occur with a populated numeric
`excess_readmission_ratio` value. This is count-field disclosure suppression: the
count is withheld to prevent patient re-identification, but the ratio (calculated from
a sufficiently large denominator) is reportable. The schema must distinguish this state
from full measure suppression. See AMB-4 in `docs/pipeline_decisions.md`.

---

## yq43-i98g - Hospital-Acquired Condition Reduction Program (HACRP)

**Sample size:** 1000 rows

**Suppression values observed (all score-like fields):**
- `"N/A"` — used across all SIR fields and `total_hac_score` (no `"Not Available"` sentinel found)
  - `psi_90_composite_value`: 67 N/A rows
  - `clabsi_sir`: 216 N/A rows
  - `cauti_sir`: 164 N/A rows
  - `ssi_sir`: 222 N/A rows
  - `cdi_sir`: 63 N/A rows
  - `mrsa_sir`: 248 N/A rows
  - `total_hac_score`: 32 N/A rows

**Footnote codes observed (per-measure footnote fields):**
- `5` — results not available (hospital not reporting/participating)
- `11` — fewer than the required number of cases to report
- `12` — measure does not apply to this hospital type
- `13` — results not available for this reporting period
- `18` — results suppressed due to confidentiality requirements
- `23` — hospital excluded from this program
- `29` — measure methodology changed

**suppressed:** FOUND. Rows where a SIR field is `"N/A"` AND the corresponding
`*_footnote` field contains a code (e.g., `clabsi_sir = "N/A"` with
`clabsi_sir_footnote = "13"`) represent suppressed individual measures. Note: this
dataset uses `"N/A"` (not `"Not Available"`) as the suppression sentinel.

**not_reported:** FOUND using `total_hac_score = "N/A"` without a `total_hac_score_footnote`.
Rows where `total_hac_score = "N/A"` with an empty footnote field but individual SIR
fields also `"N/A"` represent hospitals not scored overall — structurally distinct from
a hospital with a populated score where individual component SIRs are suppressed.

**null_denominator:** Not applicable. Wide-format dataset; no denominator fields exposed.

**count_suppressed:** Not applicable.

---

## ypbt-wvdk - Hospital Value-Based Purchasing Program (VBP)

**Sample size:** 1000 rows

**Suppression values observed:**
- None. All 1000 rows have numeric values in all score fields.

**Footnote codes observed:**
- None. No footnote fields are present in this dataset's API response.

**suppressed:** NULL. No suppression observed in the 1000-row expanded sample. This
confirms prior 200-row Phase 0 finding. CMS does not publish suppressed VBP rows via
this API endpoint — hospitals that do not receive a VBP score appear to be omitted
entirely from the dataset rather than included with a suppression sentinel.

**not_reported:** NULL. No not-reported encoding in this dataset. Confirmed across
1000 rows.

**footnote:** NULL. No footnote fields exist in the VBP API response. Confirmed.

**null_denominator:** Not applicable. No denominator fields in this dataset.

**count_suppressed:** Not applicable.

---

## Summary: New Findings vs. Prior 200-Row Analysis

The following findings were confirmed or updated in the expanded 1000-2000 row analysis
that were not fully visible in the prior 200-row sample:

1. **xubh-q36u `not_reported` confirmed:** Footnote code 19 (Rural Emergency Hospitals
   cannot be scored) provides a genuinely distinct not_reported state. Rural Emergency
   Hospital type systematically receives footnote 19 across all measure groups.
   Previously listed as null.

2. **dgck-syfz footnote codes confirmed:** Codes 1, 6, 10, 11, 15, 29 are all present
   in the 2000-row sample. The prior 200-row finding noted footnote codes might not be
   present. The expanded sample resolves this — footnote rows are now present.

3. **yq43-i98g suppressed confirmed:** The prior 200-row sample missed suppressed HACRP
   rows. The 1000-row sample confirms `"N/A"` with a per-measure footnote code (e.g.,
   `clabsi_sir_footnote = "13"`) is the suppression pattern. `"Not Available"` is NOT
   used in HACRP; the sentinel is `"N/A"`.

4. **9n3s-kdb3 AMB-4 confirmed:** 209 rows with `number_of_readmissions =
   "Too Few to Report"` co-occurring with a populated `excess_readmission_ratio`.
   Pattern is structurally confirmed and the `count_suppressed` fixture row is present.

5. **9n3s-kdb3 suppressed/not_reported distinction:** All N/A rows have a footnote code.
   Footnote 5 (non-participating) vs. footnote 1 (too few discharges) provides a
   distinguishable not_reported vs. suppressed pair. Fixtures updated to use different
   footnote codes for these two categories.

6. **77hc-ibv8 dual suppression sentinel confirmed:** Both `"Not Available"` (standard
   suppression, footnote 13) and `"N/A"` (CI bound not applicable, footnote 8) coexist
   in the HAI dataset. These are semantically distinct and must be normalized separately.

7. **ypbt-wvdk suppression absence confirmed across 1000 rows:** No suppression,
   no footnotes, no null denominators in full 1000-row sample. This dataset has no
   fixture rows for suppressed/not_reported/footnote/null_denominator categories.
