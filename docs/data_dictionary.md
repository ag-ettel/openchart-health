# Data Dictionary

This document defines every entry in `MEASURE_REGISTRY` (located in `pipeline/config.py`).
Each entry records the confirmed basis for `direction`, `ses_sensitivity`, and
`tail_risk_flag` values, with a cross-reference to the Phase 0 finding that confirmed it.

**Rules:**
- Never add a MEASURE_REGISTRY entry without a corresponding entry here.
- Direction changes require a simultaneous update to this file in the same commit.
- `ses_sensitivity` must cite a published literature reference or CMS documentation.
- `tail_risk_flag` must cite a rationale (mortality, serious complication, HAI, adverse event, etc.).

---

## Interval Estimation Methodology

Every MEASURE_REGISTRY entry must document three fields that determine whether an
interval estimate is available, calculable, or neither. This classification drives
the display layer's ability to show uncertainty alongside point estimates.

See DEC-029 in `docs/pipeline_decisions.md` for full rationale on the Bayesian
credible interval methodology.

### Required Fields

| Field | Values | Purpose |
|---|---|---|
| `risk_adjustment_model` | `"HGLM"`, `"SIR"`, `"PATIENT_MIX_ADJUSTMENT"`, `"NONE"`, `"OTHER"`, or `None` | Statistical model CMS uses for the measure |
| `cms_ci_published` | `True`, `False`, or `None` | Whether CMS publishes interval bounds in the Provider Data download |
| `numerator_denominator_published` | `True`, `False`, or `None` | Whether raw counts are available in the Provider Data download |

`None` indicates REVIEW_NEEDED — the classification requires manual verification from
CMS technical specification documents before the measure can be finalized.

### Interval Availability Derivation

1. If `cms_ci_published` is True → **INTERVAL AVAILABLE** — use CMS-provided
   `lower_estimate` / `higher_estimate` values directly. Do not recalculate. (HGLM
   intervals are derived from posterior distributions and are approximately Bayesian
   credible intervals.)
2. If `risk_adjustment_model` is `"NONE"` and `numerator_denominator_published` is True
   → **INTERVAL CALCULABLE** — 95% Bayesian credible interval via Beta-Binomial model.
3. Otherwise → **INTERVAL NOT AVAILABLE** from published data.

### Bayesian Credible Interval Methodology (Internally Calculated)

For measures where we calculate intervals from published numerator/denominator:

**Model:** Beta-Binomial conjugate model.

**Prior selection hierarchy:**
1. State average rate → Beta(κ·p, κ·(1−p)) where p = state avg, κ = 10
2. National average rate → Beta(κ·p, κ·(1−p)) where p = national avg, κ = 10
3. Neither available → Beta(1, 1) (uninformative uniform prior)

**Concentration parameter κ = 10:** Represents ~10 pseudo-observations. Defensible
because it is weak enough that moderate samples (n ≥ 25) dominate the prior, while
providing meaningful shrinkage for very small samples — pulling extreme rates toward
the population average rather than displaying 0% or 100% from 3 observations.

**Posterior:** Beta(α + x, β + n − x) where x = numerator, n = denominator.

**95% credible interval:** 2.5th and 97.5th percentiles of the posterior Beta
distribution.

**CMS-published intervals** are used as-is. Database columns retain the names
`confidence_interval_lower` / `confidence_interval_upper` for schema stability.

### Risk Adjustment Model Types

| Model | Description | Used By | Interval Source |
|---|---|---|---|
| `HGLM` | Hierarchical Generalized Linear Model (hierarchical logistic regression). CMS standard for outcome measures. | Mortality, readmission, complication, EDAC, PSI, some outpatient outcome measures | CMS publishes `lower_estimate` / `higher_estimate` (approx. Bayesian credible intervals from posterior) |
| `SIR` | Standardized Infection Ratio (CDC NHSN methodology). Facility-level risk adjustment based on facility type and procedure mix. | HAI measures (CLABSI, CAUTI, SSI, MRSA, C.diff) | CMS publishes `CILOWER` / `CIUPPER` as companion measures |
| `PATIENT_MIX_ADJUSTMENT` | Linear regression patient-mix adjustment for survey responses. Adjusts for respondent age, education, language, self-reported health. | HCAHPS survey measures | No interval published; not calculable from adjusted percentages |
| `NONE` | Unadjusted raw rate or compliance percentage. No statistical model applied. | Process measures (sepsis bundles, stroke treatment, VTE prophylaxis, imaging efficiency, ED wait times) | 95% Bayesian credible interval calculable from rate + denominator for percentage measures; not calculable for median-based measures |
| `OTHER` | Other risk adjustment not fitting above categories. Specific model documented per measure. | MSPB-1 (payment standardization + HCC risk adjustment), OP_32/OP_35 | Varies — check `cms_ci_published` |

### Per-Dataset Interval Summary

| Dataset | Model | CMS Interval Published | Num/Denom Published | Interval Status | Method |
|---|---|---|---|---|---|
| Complications and Deaths (ynj2-r877) | HGLM | Yes | No | AVAILABLE | CMS-published (approx. credible interval) |
| Healthcare-Associated Infections (77hc-ibv8) | SIR | Yes | Yes | AVAILABLE | CMS-published |
| HCAHPS Patient Survey (dgck-syfz) | PATIENT_MIX_ADJUSTMENT | No | No | NOT AVAILABLE | — |
| Unplanned Hospital Visits (632h-zaca) — READM/EDAC/Hybrid/OP_36 | HGLM | Yes | No | AVAILABLE | CMS-published (approx. credible interval) |
| Unplanned Hospital Visits (632h-zaca) — OP_32/OP_35 | OTHER | Yes (confirmed 2026-03-18) | No | AVAILABLE | CMS-published |
| Timely & Effective Care (yv7e-xc69) — process measures | NONE | No | Yes | CALCULABLE | Bayesian Beta-Binomial (κ=10, state/national prior) |
| Timely & Effective Care (yv7e-xc69) — ED wait times (OP_18a-d) | NONE | No | No | NOT CALCULABLE | — (median-based) |
| Timely & Effective Care (yv7e-xc69) — eCQMs: HH_HYPER, HH_HYPO, HH_ORAE | NONE (confirmed 2026-03-18) | No | Yes (score=% event-days/eligible-days, sample=patient-days) | NOT APPLICABLE | Patient-day correlation violates independence assumption; display point estimate + sample size only |
| Timely & Effective Care (yv7e-xc69) — eCQM: SAFE_USE_OF_OPIOIDS | NONE | No | Yes (score=% encounters, sample=encounters) | CALCULABLE | Bayesian Beta-Binomial (κ=10); denominator is patient encounters (CMS506v6) |
| ~~Timely & Effective Care (yv7e-xc69) — eCQMs: GMCS (5 measures)~~ | REMOVED (2026-03-18) | — | — | — | Near-universal non-reporting; process measures only |
| Timely & Effective Care (yv7e-xc69) — EDV | NONE | No | No | NOT APPLICABLE | — (categorical) |
| Outpatient Imaging Efficiency (wkfw-kthe) | NONE | No | Yes | CALCULABLE | Bayesian Beta-Binomial (κ=10, state/national prior) |
| Medicare Spending Per Patient (rrqw-56er) | OTHER | Yes | No | AVAILABLE | CMS-published |

#### Nursing Home Datasets

| Dataset | Model | CMS Interval Published | Num/Denom Published | Interval Status | Method |
|---|---|---|---|---|---|
| MDS Quality Measures (djen-97ju) | NONE | No | No | NOT CALCULABLE | No num/denom in API; quarterly scores only |
| Claims Quality Measures (ijh5-nb2v) | OTHER (O/E adjustment) | No | No | NOT AVAILABLE | Adjusted/observed/expected triplet; no raw counts |
| Five-Star Sub-Ratings (4pq5-n9py) | Complex composite | No | N/A | NOT APPLICABLE | Ordinal 1-5 ratings; intervals not meaningful |
| SNF QRP — claims-based (S_004, S_005, S_039) | HGLM | Yes | Yes | AVAILABLE | CMS-published 95% credible intervals (`_RSRR_2_5`/`_RSRR_97_5`) |
| SNF QRP — risk-adjusted MDS (S_024, S_025, S_038, S_042) | OTHER (covariate adj) | No | Yes (unadj only) | NOT AVAILABLE | CMS-adjusted rate is primary; num/denom are for unadjusted rate only |
| SNF QRP — unadjusted process (S_007, S_013, S_040-S_045) | NONE | No | Yes | CALCULABLE | Num/denom published; Beta-Binomial applicable |
| SNF QRP — MSPB (S_006) | OTHER (payment std) | No | No | NOT AVAILABLE | Ratio score only; no counts |
| Staffing (4pq5-n9py) | PDPM case-mix adj | No | N/A | NOT APPLICABLE | Continuous HPRD values; not rates |
| Inspection (r5ix-sfxw, 4pq5-n9py) | NONE | No | N/A | NOT APPLICABLE | Raw deficiency counts; not rates |
| Penalties (4pq5-n9py, g6vv-u9sr) | NONE | No | N/A | NOT APPLICABLE | Counts and dollar amounts; not rates |

**Key nursing home findings (confirmed 2026-03-19 against live API):**
- **MDS measures have NO numerator/denominator fields** in the API — only quarterly
  percentage scores. Credible intervals cannot be calculated without raw counts.
- **Claims measures have observed/expected/adjusted triplet** but no raw numerator or
  denominator. The O/E ratio provides context but is not sufficient for CI calculation.
- **SNF QRP is the richest source** — 3 claims-based measures publish CMS credible
  intervals; 11 process/MDS measures publish numerator/denominator enabling Beta-
  Binomial calculation; only MSPB (S_006_01) has neither.
- **SNF QRP compound measure_code structure** confirmed: each base measure has multiple
  sub-measure codes as suffixes (e.g., `S_004_01_PPR_PD_RSRR`, `S_004_01_PPR_PD_RSRR_2_5`).
  The normalizer must parse these suffixes and store sub-values (CI bounds, numerator,
  denominator, volume, observed rate) as companion columns on the primary measure row.

### Maintenance

CMS periodically updates measure methodologies. When CMS changes a measure's risk
adjustment model (e.g., adopting HGLM for a previously unadjusted measure), the
`risk_adjustment_model`, `cms_ci_published`, and `numerator_denominator_published`
fields must be reviewed and updated. The CMS Measures Inventory Tool is the
authoritative starting point for locating per-measure technical specifications.

When state or national averages change between data refreshes, the Beta prior
parameters for internally calculated credible intervals update automatically (they
are computed from the current averages at pipeline run time, not hardcoded).

### Measures Requiring Manual Review

The following measures have `None` (REVIEW_NEEDED) for one or more CI fields. Before
Phase 1 pipeline code is written, each must be verified against CMS technical
specification documents:

**~~Outpatient unplanned visit measures (632h-zaca):~~ RESOLVED (2026-03-18)**
- `OP_32`, `OP_35_ADM`, `OP_35_ED` — Risk-adjusted with CMS-provided CIs confirmed.
  `lower_estimate`/`higher_estimate` populated in live API. CI status: **AVAILABLE**.

**eCQM Hospital Harm measures (yv7e-xc69) — RESOLVED (2026-03-18):**
- `HH_HYPER`, `HH_HYPO`, `HH_ORAE` — Confirmed as ratio eCQMs (CMS871 spec).
  score = percentage of event-days / eligible patient-days. sample = patient-days
  (not patients). Credible interval **NOT APPLICABLE** — patient-days within the
  same hospitalization are correlated, violating the Beta-Binomial independence
  assumption. Display point estimate with patient-days context only.

**~~eCQM SAFE_USE_OF_OPIOIDS (yv7e-xc69):~~ RESOLVED (2026-03-19)**
- `SAFE_USE_OF_OPIOIDS` (CMS506v6) — Denominator is **inpatient hospitalizations**
  (patient encounters ≤120 days where patient ≥18 and prescribed opioid/benzo at
  discharge), NOT patient-days. Numerator is encounters with ≥2 opioids or opioid +
  benzo at discharge. Direction: LOWER_IS_BETTER. Beta-Binomial credible interval
  **IS applicable** — encounters are independent observations.
  Source: https://ecqi.healthit.gov/ecqm/hosp-inpt/2024/cms0506v6

**~~eCQM GMCS measures (yv7e-xc69):~~ REMOVED (2026-03-18)**
- `GMCS` and 4 sub-components removed from scope. Near-universal "Not Available" in
  live API. Process measures (tail_risk_flag = False) with no coverage impact.

---

## Hospital Measures

### Hospital General Information

_(Provider metadata only — no MEASURE_REGISTRY entries for this dataset.)_

Context fields derived from this dataset and stored in the `providers` table:

| Field | Type | Source | Status |
|-------|------|--------|--------|
| `is_critical_access` | bool | Derived: `hospital_type == "Critical Access Hospitals"` | Confirmed |
| `hospital_type` | varchar | `hospital_type` — xubh-q36u | Confirmed |
| `hospital_ownership` | varchar | `hospital_ownership` — xubh-q36u | Confirmed |
| `emergency_services` | bool | `emergency_services` — xubh-q36u (`"Yes"`/`"No"`) | Confirmed |
| `birthing_friendly_designation` | bool | `meets_criteria_for_birthing_friendly_designation` — xubh-q36u (`"Y"`/`"N"`) | Confirmed |
| `dsh_status` | bool | HCRIS Cost Reports — not in Provider Data API | Deferred (DEC-004) |
| `dsh_percentage` | decimal(5,2) | HCRIS Cost Reports — not in Provider Data API | Deferred (DEC-004) |
| `is_teaching_hospital` | bool | HCRIS Cost Reports — not in Provider Data API | Deferred (DEC-004) |
| `staffed_beds` | integer | HCRIS Cost Reports — not in Provider Data API | Deferred (DEC-004) |
| `dual_eligible_proportion` | decimal(5,2) | HRRP Impact Files — not in Provider Data API | Deferred (DEC-005) |
| `urban_rural_classification` | varchar | CMS Provider of Services file — not in Provider Data API | Deferred (DEC-006) |

#### `provider_subtype` (hospital_type) Enum Values

Confirmed 2026-03-15 against full dataset (5,426 rows) of xubh-q36u. API field: `hospital_type`.

| Enum Value | Count | Description |
|---|---|---|
| `Acute Care Hospitals` | 3,116 | General acute care |
| `Critical Access Hospitals` | 1,376 | Derives `is_critical_access = true` |
| `Psychiatric` | 633 | Inpatient psychiatric facilities |
| `Acute Care - Veterans Administration` | 132 | VHA medical centers |
| `Childrens` | 94 | Children's hospitals |
| `Rural Emergency Hospital` | 39 | New CMS designation (2023+); systematically receives footnote 19 |
| `Acute Care - Department of Defense` | 32 | DoD military hospitals |
| `Long-term` | 4 | Long-Term Acute Care Hospitals (LTACHs); extremely rare in dataset |

**Total: 8 distinct values.** See `docs/phase_0_findings.md §Provider Subtype Enum Values`
for full details including facility names for rare values.

#### `hospital_ownership` Enum Values

Confirmed 2026-03-15 against full dataset (5,426 rows) of xubh-q36u. API field: `hospital_ownership`.

| Enum Value | Count |
|---|---|
| `Voluntary non-profit - Private` | 2,304 |
| `Proprietary` | 1,069 |
| `Government - Hospital District or Authority` | 519 |
| `Government - Local` | 401 |
| `Voluntary non-profit - Other` | 355 |
| `Voluntary non-profit - Church` | 271 |
| `Government - State` | 209 |
| `Veterans Health Administration` | 132 |
| `Physician` | 76 |
| `Government - Federal` | 43 |
| `Department of Defense` | 32 |
| `Tribal` | 15 |

**Total: 12 distinct values.**

---

### Hospital Overall Star Rating

_(Not a separate dataset — `hospital_overall_rating` field lives in Hospital General Information, xubh-q36u.)_

---

### Complications and Deaths (ynj2-r877)

**Phase 0 reference:** `docs/phase_0_findings.md §5`

**20 measures total:** 7 mortality, 1 complication, 12 patient safety indicators.

#### Mortality Measures (7)

All 30-day risk-standardized mortality rates (RSMR). CMS calculates using hierarchical
logistic regression accounting for age, sex, and comorbidities. Models do NOT adjust
for patient SES characteristics. Reporting period: 36 months rolling, refreshed annually.

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `MORT_30_AMI` | Death rate for heart attack patients | LOWER_IS_BETTER | percent | HIGH | Yes | Lower 30-day death rate is unambiguously better |
| `MORT_30_CABG` | Death rate for CABG surgery patients | LOWER_IS_BETTER | percent | HIGH | Yes | Lower perioperative mortality is unambiguously better |
| `MORT_30_COPD` | Death rate for COPD patients | LOWER_IS_BETTER | percent | HIGH | Yes | Lower 30-day death rate is unambiguously better |
| `MORT_30_HF` | Death rate for heart failure patients | LOWER_IS_BETTER | percent | HIGH | Yes | Lower 30-day death rate is unambiguously better |
| `MORT_30_PN` | Death rate for pneumonia patients | LOWER_IS_BETTER | percent | HIGH | Yes | Lower 30-day death rate is unambiguously better |
| `MORT_30_STK` | Death rate for stroke patients | LOWER_IS_BETTER | percent | HIGH | Yes | Lower 30-day death rate is unambiguously better |
| `Hybrid_HWM` | Hybrid Hospital-Wide All-Cause Risk Standardized Mortality Rate | LOWER_IS_BETTER | percent | HIGH | Yes | Lower all-cause mortality is unambiguously better |

**SES sensitivity basis (HIGH):** 30-day mortality measures are well-documented as
substantially affected by patient socioeconomic mix. CMS risk adjustment accounts for
clinical factors but not patient SES. References: Bernheim et al. (2016); CMS IMPACT Act
reports; MedPAC June 2023 chapter on social risk factors. ses-context.md lists "30-day
mortality" as HIGH.

**Tail risk basis:** Mortality is the most severe adverse outcome. All measures in this
group directly capture patient death.

#### Complication Measure (1)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `COMP_HIP_KNEE` | Rate of complications for hip/knee replacement patients | LOWER_IS_BETTER | percent | MODERATE | Yes | Lower 90-day complication rate is unambiguously better |

**SES sensitivity basis (MODERATE):** Hip/knee replacement is elective surgery with
documented but smaller SES effects compared to emergency admission mortality. Patients
with lower SES may delay surgery and present with more advanced disease. Reference:
Singh & Lu (2004).

**Tail risk basis:** Serious surgical complications (prosthetic failure, infection,
bleeding requiring return to OR) can result in permanent disability or death.

#### Patient Safety Indicators (12)

AHRQ Patient Safety Indicators identify potentially preventable complications and
adverse events during hospitalization. CMS reports as risk-adjusted rates per eligible
discharges. Reporting period: 24 months. Numerator/denominator definitions confirmed
from CMS PSI-90 FactSheet (docs/psi90-FactSheet.txt).

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `PSI_03` | Pressure ulcer rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer adverse events is better |
| `PSI_04` | Death rate among surgical inpatients with serious treatable complications | LOWER_IS_BETTER | rate | MODERATE | Yes | Lower failure-to-rescue rate is better |
| `PSI_06` | Iatrogenic pneumothorax rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer procedural complications is better |
| `PSI_08` | In-hospital fall-associated fracture rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer falls with fracture is better |
| `PSI_09` | Postoperative hemorrhage or hematoma rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer bleeding events is better |
| `PSI_10` | Postoperative acute kidney injury requiring dialysis rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer renal failures is better |
| `PSI_11` | Postoperative respiratory failure rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer respiratory failures is better |
| `PSI_12` | Perioperative pulmonary embolism or deep vein thrombosis rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer blood clots is better |
| `PSI_13` | Postoperative sepsis rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer infections is better |
| `PSI_14` | Postoperative wound dehiscence rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer wound openings is better |
| `PSI_15` | Abdominopelvic accidental puncture or laceration rate | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer accidental injuries is better |
| `PSI_90` | CMS Medicare PSI 90: Patient safety and adverse events composite | LOWER_IS_BETTER | ratio | MODERATE | Yes | O/E ratio below 1.0 = fewer adverse events than expected |

**SES sensitivity basis (MODERATE):** PSI rates have documented moderate SES effects —
hospitals serving disadvantaged populations tend to have higher PSI rates partly due to
structural resource constraints. Reference: Encinosa & Hellinger (2008). PSI_90 inherits
as a composite. CMS uses PSI_90 in HACRP without SES adjustment; this has been criticized
(Rajaram et al., 2015).

**Tail risk basis:** Every PSI captures a serious adverse safety event: death from
treatable complications, organ injuries, life-threatening blood clots, respiratory
failure, sepsis, etc.

**Note:** `PSI_90` is an observed-to-expected ratio (unit=ratio), distinct from
individual PSIs (unit=rate). `PSI_90` uses "No Different Than the National Value"
phrasing for compared_to_national (not "Rate"). See AMB-3.

**Note:** `Hybrid_HWM` measure_id uses mixed case (capital H) — confirmed from CMS API.

---

### Healthcare-Associated Infections (77hc-ibv8)

**Phase 0 reference:** `docs/phase_0_findings.md §6`

**6 SIR measures** (primary quality measures). 30 companion sub-measures (CILOWER,
CIUPPER, DOPC, ELIGCASES, NUMERATOR) are handled by the normalizer via pattern matching
and do NOT get MEASURE_REGISTRY entries. Reporting period: 12 months, refreshed quarterly.

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `HAI_1_SIR` | Central Line Associated Bloodstream Infection (ICU + select Wards) | LOWER_IS_BETTER | ratio | LOW | Yes | SIR < 1.0 = fewer infections than expected |
| `HAI_2_SIR` | Catheter Associated Urinary Tract Infections (ICU + select Wards) | LOWER_IS_BETTER | ratio | LOW | Yes | SIR < 1.0 = fewer infections than expected |
| `HAI_3_SIR` | SSI - Colon Surgery | LOWER_IS_BETTER | ratio | LOW | Yes | SIR < 1.0 = fewer infections than expected |
| `HAI_4_SIR` | SSI - Abdominal Hysterectomy | LOWER_IS_BETTER | ratio | LOW | Yes | SIR < 1.0 = fewer infections than expected |
| `HAI_5_SIR` | MRSA Bacteremia | LOWER_IS_BETTER | ratio | LOW | Yes | SIR < 1.0 = fewer infections than expected |
| `HAI_6_SIR` | Clostridium Difficile (C.Diff) | LOWER_IS_BETTER | ratio | LOW | Yes | SIR < 1.0 = fewer infections than expected |

**SES sensitivity basis (LOW):** HAI rates are primarily driven by infection prevention
and control practices (hand hygiene, central line insertion protocols, environmental
cleaning, antibiotic stewardship). SIR methodology already adjusts for facility type
and patient population characteristics. References: CDC NHSN Risk Adjustment methodology;
Krein et al. (2015). ses-context.md lists "HAI rates" as LOW.

**Tail risk basis:** All HAI measures capture serious adverse events with significant
attributable mortality: CLABSI (12-25%), MRSA bacteremia (20-30%), C. diff (5-10% in
elderly), SSI (2-11x increased mortality). These are preventable infections acquired
during medical care.

**Companion measures (not in MEASURE_REGISTRY):**
The normalizer recognizes HAI companion measures by suffix pattern:
`HAI_{1-6}_CILOWER` -> confidence_interval_lower,
`HAI_{1-6}_CIUPPER` -> confidence_interval_upper,
`HAI_{1-6}_NUMERATOR` -> sample_size (observed infection count),
`HAI_{1-6}_ELIGCASES` -> denominator (predicted/expected cases),
`HAI_{1-6}_DOPC` -> device days / patient days (exposure denominator).
See TODO-2 (HAI DOPC storage) for pending pipeline decision.

---

### Unplanned Hospital Visits / Readmissions (632h-zaca)

**Phase 0 reference:** `docs/phase_0_findings.md §7`

**14 measures total:** 6 condition-specific readmission rates, 3 excess days in acute
care, 1 hospital-wide readmission, 4 outpatient unplanned visit measures.

#### 30-Day Readmission Rates (6)

Risk-standardized readmission rates (RSRR). CMS hierarchical logistic regression.
Models account for age, sex, and comorbidities but NOT patient SES. Reporting period:
36 months rolling.

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `READM_30_AMI` | AMI 30-Day Readmission Rate | LOWER_IS_BETTER | percent | HIGH | Yes | Fewer readmissions is better |
| `READM_30_CABG` | Rate of readmission for CABG | LOWER_IS_BETTER | percent | HIGH | Yes | Fewer readmissions is better |
| `READM_30_COPD` | Rate of readmission for COPD patients | LOWER_IS_BETTER | percent | HIGH | Yes | Fewer readmissions is better |
| `READM_30_HF` | Heart failure 30-Day Readmission Rate | LOWER_IS_BETTER | percent | HIGH | Yes | Fewer readmissions is better |
| `READM_30_HIP_KNEE` | Rate of readmission after hip/knee replacement | LOWER_IS_BETTER | percent | HIGH | Yes | Fewer readmissions is better |
| `READM_30_PN` | Pneumonia 30-Day Readmission Rate | LOWER_IS_BETTER | percent | HIGH | Yes | Fewer readmissions is better |

#### Excess Days in Acute Care (3)

Days per 100 discharges: observed minus expected acute care days (including ED visits,
observation stays, unplanned readmissions within 30 days), scaled to 100 discharges.

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `EDAC_30_AMI` | Hospital return days for heart attack patients | LOWER_IS_BETTER | days_per_100 | HIGH | Yes | Fewer excess return days is better |
| `EDAC_30_HF` | Hospital return days for heart failure patients | LOWER_IS_BETTER | days_per_100 | HIGH | Yes | Fewer excess return days is better |
| `EDAC_30_PN` | Hospital return days for pneumonia patients | LOWER_IS_BETTER | days_per_100 | HIGH | Yes | Fewer excess return days is better |

#### Hospital-Wide Readmission (1)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `Hybrid_HWR` | Hybrid Hospital-Wide All-Cause Readmission Measure | LOWER_IS_BETTER | percent | HIGH | Yes | Lower all-cause readmission is better |

#### Outpatient Unplanned Visit Measures (4)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `OP_32` | Rate of unplanned hospital visits after colonoscopy | LOWER_IS_BETTER | rate | MODERATE | Yes | Fewer unplanned visits is better |
| `OP_35_ADM` | Rate of inpatient admissions for outpatient chemo patients | LOWER_IS_BETTER | percent | MODERATE | Yes | Fewer unplanned admissions is better |
| `OP_35_ED` | Rate of ED visits for outpatient chemo patients | LOWER_IS_BETTER | percent | MODERATE | Yes | Fewer ED visits is better |
| `OP_36` | Ratio of unplanned visits after outpatient surgery | LOWER_IS_BETTER | ratio | MODERATE | Yes | O/E ratio below 1.0 is better |

**SES sensitivity basis (HIGH — readmission/EDAC/hospital-wide):** 30-day readmission
rates are the most well-documented SES-sensitive measure category. Post-discharge factors
(medication adherence, follow-up care access, food security, housing stability, health
literacy) are strongly correlated with SES. CMS risk adjustment does not account for SES.
HRRP penalties have been criticized as disproportionately affecting safety-net hospitals.
References: Joynt & Jha (2013); Bernheim et al. (2016); MedPAC June 2023. ses-context.md
lists "30-day readmissions" as HIGH.

**SES sensitivity basis (MODERATE — outpatient measures):** Outpatient procedure
complication rates have documented but smaller SES effects than inpatient readmissions.
Post-procedure access to follow-up care has a moderate SES component, but the procedure
itself is the primary risk determinant.

**Tail risk basis:** Unplanned hospital visits are adverse events — each individual
readmission can represent serious deterioration (recurrent cardiac event, post-surgical
complication, treatment failure). Per project philosophy: "Any measure related to adverse
events belongs in the primary view."

**Note:** `Hybrid_HWR` measure_id uses mixed case (capital H) — confirmed from CMS API.

---

### Timely and Effective Care (yv7e-xc69)

**Phase 0 reference:** `docs/phase_0_findings.md §3`

**30 measures total.** Most heterogeneous dataset: ED wait times, treatment compliance
rates, harm events, vaccination, nutrition screening. Direction, unit, tail_risk, and
SES sensitivity vary by measure. API uses `_condition` field (leading underscore) — must
strip in ingest layer.

#### Emergency Department Volume (1)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `EDV` | Emergency department volume | None | category | LOW | No | Contextual volume classification, not quality. No direction. |

**Schema note (AMB-5):** EDV carries TEXT scores ("very high", "high", "medium", "low").
Cannot be stored in Decimal score column. Requires `score_text` column. EDV is excluded
from all benchmarking, color coding, and trend analysis. The `measure_direction` enum
column must be nullable.

#### ED Wait Time Measures (4)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `OP_18a` | Median time all patients spent in ED | LOWER_IS_BETTER | minutes | LOW | No | Shorter ED stays = more efficient care |
| `OP_18b` | Median time admitted patients spent in ED | LOWER_IS_BETTER | minutes | LOW | No | ED boarding is dangerous for admitted patients |
| `OP_18c` | Median time discharged patients spent in ED | LOWER_IS_BETTER | minutes | LOW | No | Shorter stays for discharged patients is better |
| `OP_18d` | Median time transfer patients spent in ED | LOWER_IS_BETTER | minutes | LOW | No | Transfer delays can be life-threatening |

#### ED Process Measures (2)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `OP_22` | Left before being seen | LOWER_IS_BETTER | percent | MODERATE | No | Fewer patients leaving untreated is better |
| `OP_23` | Head CT results | HIGHER_IS_BETTER | percent | LOW | Yes | Higher % of stroke patients imaged within 45 min is better |

**OP_22 SES basis (MODERATE):** LWBS rates are affected by patient factors — patients
without regular primary care (correlated with SES) are more likely to use the ED for
non-emergent conditions AND more likely to leave if waits are long.

**OP_23 tail risk basis:** Delayed stroke imaging directly affects eligibility for
clot-dissolving treatment. Delays can result in permanent brain damage or death.

#### Hospital Harm Measures (3)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `HH_HYPER` | Hospital Harm - Severe Hyperglycemia | LOWER_IS_BETTER | percent | MODERATE | Yes | Fewer hyperglycemia events is better |
| `HH_HYPO` | Hospital Harm - Severe Hypoglycemia | LOWER_IS_BETTER | percent | MODERATE | Yes | Fewer hypoglycemia events is better |
| `HH_ORAE` | Hospital Harm - Opioid Related Adverse Events | LOWER_IS_BETTER | percent | LOW | Yes | Fewer opioid adverse events is better |

**HH_HYPER/HH_HYPO SES basis (MODERATE):** Diabetes prevalence and baseline glucose
control (both correlated with SES) affect the at-risk population. However, in-hospital
glucose management is primarily a process-of-care measure.

**HH_ORAE SES basis (LOW):** In-hospital opioid adverse events are driven by prescribing
practices and monitoring protocols, not patient SES.

**Tail risk basis:** Severe hyperglycemia increases infection risk and mortality.
Severe hypoglycemia can cause seizures, cardiac arrhythmias, and death. Opioid-related
respiratory depression is a leading cause of preventable in-hospital death.

**TODO:** Confirm HH_* unit denomination (percent vs rate per 1,000 patient-days) from
CMS technical specifications before Phase 1 normalize code.

#### Safe Use of Opioids (1)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `SAFE_USE_OF_OPIOIDS` | Safe Use of Opioids - Concurrent Prescribing | LOWER_IS_BETTER | percent | LOW | Yes | Fewer concurrent prescriptions = lower overdose risk |

#### Sepsis Treatment Measures (5)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `SEP_1` | Appropriate care for severe sepsis and septic shock | HIGHER_IS_BETTER | percent | LOW | Yes | Higher bundle compliance = better |
| `SEP_SH_3HR` | Septic Shock 3-Hour Bundle | HIGHER_IS_BETTER | percent | LOW | Yes | Higher compliance = better |
| `SEP_SH_6HR` | Septic Shock 6-Hour Bundle | HIGHER_IS_BETTER | percent | LOW | Yes | Higher compliance = better |
| `SEV_SEP_3HR` | Severe Sepsis 3-Hour Bundle | HIGHER_IS_BETTER | percent | LOW | Yes | Higher compliance = better |
| `SEV_SEP_6HR` | Severe Sepsis 6-Hour Bundle | HIGHER_IS_BETTER | percent | LOW | Yes | Higher compliance = better |

**SES basis (LOW):** Sepsis bundle compliance is a process measure driven by hospital
protocols. **Tail risk basis:** Sepsis kills ~270,000 Americans per year; treatment
bundle compliance directly affects survival. Each hour of antibiotic delay increases
mortality by ~7%.

#### Stroke Treatment Measures (3)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `STK_02` | Discharged on Antithrombotic Therapy | HIGHER_IS_BETTER | percent | LOW | Yes | Higher prescribing compliance = better |
| `STK_03` | Anticoagulation Therapy for Atrial Fibrillation/Flutter | HIGHER_IS_BETTER | percent | LOW | Yes | Higher prescribing compliance = better |
| `STK_05` | Antithrombotic Therapy by End of Hospital Day 2 | HIGHER_IS_BETTER | percent | LOW | Yes | Earlier treatment = better |

**SES basis (LOW):** Prescribing at discharge is a provider decision. **Tail risk
basis:** Failure to prescribe antithrombotics after stroke directly increases recurrent
stroke risk. AF without anticoagulation carries 5-15% annual stroke recurrence;
anticoagulation reduces by ~65%.

#### VTE Prophylaxis Measures (2)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `VTE_1` | Venous Thromboembolism Prophylaxis | HIGHER_IS_BETTER | percent | LOW | Yes | Higher prophylaxis compliance = better |
| `VTE_2` | ICU Venous Thromboembolism Prophylaxis | HIGHER_IS_BETTER | percent | LOW | Yes | Higher prophylaxis compliance = better |

**Tail risk basis:** Hospital-acquired VTE (DVT/PE) is a leading cause of preventable
death. PE can be fatal within hours.

#### STEMI Treatment (1)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `OP_40` | ST-Segment Elevation Myocardial Infarction (STEMI) | HIGHER_IS_BETTER | percent | LOW | Yes | Higher compliance with reperfusion timing = better |

**TODO:** Confirm exact OP_40 measure definition from CMS technical specifications
(door-to-balloon time compliance vs. overall STEMI protocol adherence).

#### Vaccination (1)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `IMM_3` | Healthcare workers given influenza vaccination | HIGHER_IS_BETTER | percent | LOW | No | Higher vaccination rate = better patient protection |

#### Outpatient Procedure Measures (2)

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `OP_29` | Appropriate follow-up interval for normal colonoscopy | HIGHER_IS_BETTER | percent | LOW | No | Higher guideline adherence = better |
| `OP_31` | Improvement in visual function within 90 days after cataract surgery | HIGHER_IS_BETTER | percent | LOW | No | Higher improvement rate = better |

#### ~~Global Malnutrition Composite Score (5)~~ — REMOVED (2026-03-18)

Removed from scope. Near-universal "Not Available" in live API data. Process measures
(tail_risk_flag = False) with no bearing on safety or outcome coverage. The normalizer
must skip these measure_ids without error when they appear in API responses.

---

### HCAHPS Patient Survey (dgck-syfz)

**Phase 0 reference:** `docs/phase_0_findings.md §4`

**68 measures total.** Patient experience survey results. API uses `hcahps_measure_id`
(not `measure_id`) — normalizer must handle this field name difference.

**SES sensitivity (MODERATE for all):** HCAHPS adjusts for patient mix (age, education,
language, self-reported health status) before reporting, but published research documents
residual SES effects on patient experience scores even after adjustment. Hospitals
serving lower-income populations and those with lower health literacy tend to receive
lower HCAHPS scores independent of care quality. Classified as MODERATE rather than LOW
to ensure the SES disclosure fires for this measure group.

**Tail risk (False for all):** Patient experience is important but does not capture
mortality, serious complications, infections, or adverse events.

**Direction rules by suffix pattern:**
- `*_A_P` (Always %): HIGHER_IS_BETTER
- `*_Y_P` (Yes %): HIGHER_IS_BETTER
- `*_DY` (Definitely Yes): HIGHER_IS_BETTER
- `*_9_10` (Rating 9-10): HIGHER_IS_BETTER
- `*_SN_P` (Sometimes/Never): LOWER_IS_BETTER
- `*_N_P` (No %): LOWER_IS_BETTER
- `*_DN` (Definitely Not): LOWER_IS_BETTER
- `*_0_6` (Rating 0-6): LOWER_IS_BETTER
- `*_U_P` (Usually %): **None** — middlebox, no direction
- `*_PY` (Probably Yes): **None** — middlebox, no direction
- `*_7_8` (Rating 7-8): **None** — middlebox, no direction
- `*_LINEAR_SCORE`: HIGHER_IS_BETTER
- `*_STAR_RATING`: HIGHER_IS_BETTER

**Middlebox decision (2026-03-15):** Middlebox measures have NO direction (NULL in DB).
They are middle-tier response categories presented as informational context alongside
topbox and bottombox measures. Excluded from all benchmarking, color coding, and trend
analysis.

| Domain | Measures | Count |
|---|---|---|
| Nurse Communication (H_COMP_1) | H_COMP_1_A_P, H_COMP_1_U_P, H_COMP_1_SN_P, H_COMP_1_LINEAR_SCORE, H_COMP_1_STAR_RATING | 5 |
| Doctor Communication (H_COMP_2) | H_COMP_2_A_P, H_COMP_2_U_P, H_COMP_2_SN_P, H_COMP_2_LINEAR_SCORE, H_COMP_2_STAR_RATING | 5 |
| Communication about Medicines (H_COMP_5) | H_COMP_5_A_P, H_COMP_5_U_P, H_COMP_5_SN_P, H_COMP_5_LINEAR_SCORE, H_COMP_5_STAR_RATING | 5 |
| Discharge Information (H_COMP_6) | H_COMP_6_Y_P, H_COMP_6_N_P, H_COMP_6_LINEAR_SCORE, H_COMP_6_STAR_RATING | 4 |
| Discharge Help (H_DISCH_HELP) | H_DISCH_HELP_Y_P, H_DISCH_HELP_N_P | 2 |
| Symptoms Information (H_SYMPTOMS) | H_SYMPTOMS_Y_P, H_SYMPTOMS_N_P | 2 |
| Cleanliness (H_CLEAN) | H_CLEAN_HSP_A_P, H_CLEAN_HSP_U_P, H_CLEAN_HSP_SN_P, H_CLEAN_LINEAR_SCORE, H_CLEAN_STAR_RATING | 5 |
| Quietness (H_QUIET) | H_QUIET_HSP_A_P, H_QUIET_HSP_U_P, H_QUIET_HSP_SN_P, H_QUIET_LINEAR_SCORE, H_QUIET_STAR_RATING | 5 |
| Overall Hospital Rating (H_HSP_RATING) | H_HSP_RATING_9_10, H_HSP_RATING_7_8, H_HSP_RATING_0_6, H_HSP_RATING_LINEAR_SCORE, H_HSP_RATING_STAR_RATING | 5 |
| Recommend Hospital (H_RECMND) | H_RECMND_DY, H_RECMND_PY, H_RECMND_DN, H_RECMND_LINEAR_SCORE, H_RECMND_STAR_RATING | 5 |
| Doctor Sub-Questions | H_DOCTOR_EXPLAIN_A_P/U_P/SN_P, H_DOCTOR_LISTEN_A_P/U_P/SN_P, H_DOCTOR_RESPECT_A_P/U_P/SN_P | 9 |
| Nurse Sub-Questions | H_NURSE_EXPLAIN_A_P/U_P/SN_P, H_NURSE_LISTEN_A_P/U_P/SN_P, H_NURSE_RESPECT_A_P/U_P/SN_P | 9 |
| Medication Sub-Questions | H_MED_FOR_A_P/U_P/SN_P, H_SIDE_EFFECTS_A_P/U_P/SN_P | 6 |
| Summary Star Rating | H_STAR_RATING | 1 |
| **Total** | | **68** |

**Note:** LINEAR_SCORE and STAR_RATING measures have special suppression encoding —
"Not Applicable" is structural absence (not all rows produce these values), NOT
suppression. See phase_0_findings.md §4.

---

### Outpatient Imaging Efficiency (wkfw-kthe)

**Phase 0 reference:** `docs/phase_0_findings.md §8`

**4 measures.** All LOWER_IS_BETTER, all SES LOW, all tail_risk False.
Note: measure_id uses hyphen format (OP-8, OP-10, OP-13, OP-39).
No `compared_to_national` field in this dataset. Reporting period: 12 months, refreshed annually.

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `OP-8` | MRI Lumbar Spine for Low Back Pain | LOWER_IS_BETTER | percent | LOW | No | Lower rate of potentially inappropriate MRI is better |
| `OP-10` | Abdomen CT Use of Contrast Material | LOWER_IS_BETTER | percent | LOW | No | Lower rate of unnecessary dual-phase CT is better |
| `OP-13` | Cardiac imaging stress tests before low-risk surgery | LOWER_IS_BETTER | percent | LOW | No | Lower rate of unnecessary cardiac testing is better |
| `OP-39` | Breast Cancer Screening Recall Rates | LOWER_IS_BETTER | percent | LOW | No | Lower recall rate = better reading quality (ACR recommends <10%) |

**SES basis (LOW):** Imaging ordering patterns are driven by physician practice patterns,
defensive medicine, and institutional culture — not patient SES.

**OP-39 clinical context note:** While lower recall rates generally indicate better
reading quality, extremely low rates (<5%) could indicate under-reading (missed cancers).
The display layer should note that an optimal recall rate balances sensitivity with
specificity. This measure has clinically appropriate bounds, not just a simple "lower is
always better" interpretation.

---

### Medicare Hospital Spending Per Patient (rrqw-56er)

**Phase 0 reference:** `docs/phase_0_findings.md §9`

**1 measure.** Note: measure_id uses hyphen format (MSPB-1). CMS API title is "Medicare
Spending Per Beneficiary". Reporting period: 12 months, refreshed annually.

| Measure ID | Name | Direction | Unit | SES | Tail Risk | Direction Basis |
|---|---|---|---|---|---|---|
| `MSPB-1` | Medicare hospital spending per patient | LOWER_IS_BETTER | ratio | MODERATE | No | Lower spending ratio = more efficient resource use (CMS-aligned) |

**SES sensitivity basis (MODERATE):** MSPB is risk-adjusted for clinical factors (HCC
scores) but not fully for patient SES. Hospitals serving lower-SES populations may have
higher readmission-driven spending that inflates the 30-day post-discharge component.
MedPAC reports document moderate SES effects. The measure is used in VBP but has been
criticized for disproportionately penalizing safety-net hospitals.

---

### Payment and Value of Care

**Status: REMOVED FROM SCOPE.** CMS retired the PAYM measures (PAYM-30-AMI, PAYM-30-HF,
PAYM-30-PN, PAYM-90-HIP-KNEE) and the composite Value of Care measure effective the
July 2025 Care Compare release. No MEASURE_REGISTRY entries are created for this dataset.
See DEC-002 in `docs/pipeline_decisions.md`.

---

### Health Equity Summary

**Status: REMOVED FROM SCOPE.** The HCHE measure was retired by CMS effective the
October 2025 Care Compare release. No MEASURE_REGISTRY entries are created for this
dataset. See DEC-003 in `docs/pipeline_decisions.md`.

---

## Payment Adjustment Programs

These are stored in `provider_payment_adjustments`, not MEASURE_REGISTRY.

| Program | Table Column | Dataset ID | Notes |
|---------|-------------|-----------|-------|
| HRRP | `program = 'HRRP'` | 9n3s-kdb3 | Hospital Readmissions Reduction Program |
| HACRP | `program = 'HACRP'` | yq43-i98g | Hospital-Acquired Condition Reduction Program |
| VBP | `program = 'VBP'` | pudb-wetr | Hospital Value-Based Purchasing Program |

---

## Nursing Home Measures

Nursing home measure IDs are confirmed against live CMS API responses (2026-03-17/18).
MEASURE_REGISTRY entries in `pipeline/config.py` are the authoritative source for
measure metadata. This section documents the basis for `direction`, `ses_sensitivity`,
and `tail_risk_flag` for each nursing home measure.

**Reference documents:**
- `docs/NH_Data_Dictionary.txt` — CMS Nursing Home Data Dictionary, February 2026
- `docs/nh-five-star-users-guide-january-2026.txt` — Five-Star Technical Users' Guide, January 2026
- `docs/snf-qm-calculations-and-reporting-users-manual-v7.0.txt` — SNF QRP QM Manual v7.0

### Nursing Home Provider Information

_(Provider metadata — no MEASURE_REGISTRY entries for this dataset.)_

Context fields derived from Provider Information dataset (4pq5-n9py) and stored in the
`providers` table. All confirmed against live API (2026-03-17).

| Field | Type | API Key | Status |
|-------|------|---------|--------|
| `provider_type` | varchar | `provider_type` | **Confirmed.** 3 values: `Medicare and Medicaid`, `Medicare`, `Medicaid` |
| `ownership_type` | varchar | `ownership_type` | **Confirmed.** 13 values. See phase_0_findings.md §12. |
| `number_of_certified_beds` | integer | `number_of_certified_beds` | **Confirmed.** |
| `average_daily_census` | decimal | `average_number_of_residents_per_day` | **Confirmed.** |
| `urban_rural` | bool | `urban` (`"Y"`/`"N"`) | **Confirmed.** |
| `provider_resides_in_hospital` | bool | `provider_resides_in_hospital` (`"Y"`/`"N"`) | **Confirmed.** |
| `chain_name` | varchar | `chain_name` (empty string when not in chain) | **Confirmed.** |
| `chain_id` | varchar | `chain_id` (empty string when not in chain) | **Confirmed.** |
| `continuing_care_retirement_community` | bool | `continuing_care_retirement_community` (`"Y"`/`"N"`) | **Confirmed.** |
| `special_focus_status` | varchar | `special_focus_status` (empty/`"SFF"`/`"SFF Candidate"`) | **Confirmed.** 88 SFF, 442 Candidates. |
| `abuse_icon` | bool | `abuse_icon` (`"Y"`/`"N"`) | **Confirmed.** |
| `ownership_changed_last_12_months` | bool | `provider_changed_ownership_in_last_12_months` (`"Y"`/`"N"`) | **Confirmed.** |

### MDS Quality Measures — Long Stay (Five-Star Rating)

Measures used in the Five-Star QM rating calculation (long-stay domain). 7 MDS measures
from `djen-97ju`, 2 claims measures from `ijh5-nb2v`. All confirmed against live API.

Phase 0 reference: `docs/phase_0_findings.md` §13, §14, §Confirmed NH Measure Code Catalog.

**Interval estimation (MDS measures):**
- `risk_adjustment_model`: `"NONE"` — unadjusted observed percentage rates
- `cms_ci_published`: `False` — no CMS-published intervals
- `numerator_denominator_published`: `False` — API provides only quarterly percentage
  scores (`q1_measure_score` through `q4_measure_score`, `four_quarter_average_score`);
  no raw resident counts. **Credible intervals NOT calculable.**
- Display: point estimate + sample size caveat when footnote 9 applies

**Interval estimation (Claims measures — NH_CLAIMS_551, NH_CLAIMS_552):**
- `risk_adjustment_model`: `"OTHER"` — CMS risk-adjustment producing observed/expected/
  adjusted triplet. The adjusted score is the primary display value.
- `cms_ci_published`: `False` — no CMS-published intervals
- `numerator_denominator_published`: `False` — API provides `adjusted_score`,
  `observed_score`, `expected_score` but no raw numerator or denominator counts.
  **Credible intervals NOT calculable.** Display O/E context alongside adjusted score.

**Direction confirmation:**
- All LOWER_IS_BETTER MDS measures represent adverse conditions or worsening function —
  direction is inherent in the measure name ("residents with pressure ulcers", "falls
  with major injury", "whose need for help has increased"). CMS does not publish an
  explicit directional field for MDS measures, but Five-Star QM scoring awards more
  points for lower values on these measures (confirmed from Five-Star Technical Users'
  Guide quintile/decile tables). Direction status: **CONFIRMED via Five-Star scoring.**
- Claims measures (551, 552): hospitalizations and ED visits are unambiguously adverse
  events. Direction status: **CONFIRMED via Five-Star scoring + measure definition.**

| Measure ID | CMS Code | Measure Name | Direction | Unit | SES | Tail Risk | Five-Star |
|-----------|----------|-------------|-----------|------|-----|-----------|-----------|
| `NH_MDS_401` | 401 | % long-stay residents whose need for help with daily activities has increased | LOWER_IS_BETTER | percent | MODERATE | No | **Y** |
| `NH_MDS_451` | 451 | % long-stay residents whose ability to walk independently worsened | LOWER_IS_BETTER | percent | MODERATE | No | **Y** |
| `NH_MDS_479` | 479 | % long-stay residents with pressure ulcers | LOWER_IS_BETTER | percent | MODERATE | Yes | **Y** |
| `NH_MDS_406` | 406 | % long-stay residents with a catheter inserted and left in their bladder | LOWER_IS_BETTER | percent | LOW | No | **Y** |
| `NH_MDS_407` | 407 | % long-stay residents with a urinary tract infection | LOWER_IS_BETTER | percent | MODERATE | Yes | **Y** |
| `NH_MDS_410` | 410 | % long-stay residents experiencing one or more falls with major injury | LOWER_IS_BETTER | percent | MODERATE | Yes | **Y** |
| `NH_MDS_481` | 481 | % long-stay residents who got an antipsychotic medication | LOWER_IS_BETTER | percent | MODERATE | Yes | **Y** |
| `NH_CLAIMS_551` | 551 | Hospitalizations per 1,000 long-stay resident days | LOWER_IS_BETTER | rate | HIGH | Yes | **Y** |
| `NH_CLAIMS_552` | 552 | Outpatient ED visits per 1,000 long-stay resident days | LOWER_IS_BETTER | rate | MODERATE | No | **Y** |

**SES sensitivity basis:**
- Rehospitalization rate — NH_CLAIMS_551, NH_CLAIMS_521 (HIGH): Same published basis as
  hospital 30-day readmissions. Post-discharge factors are strongly SES-correlated.
  Reference: Joynt & Jha (2013); MedPAC June 2023.
- Other long-stay adverse event measures (MODERATE): Documented moderate SES effects —
  facilities serving disadvantaged populations may have higher rates partly due to
  structural resource constraints. Reference: GAO-19-80 (2018).
- Catheter use — NH_MDS_406 (LOW): Primarily a process-of-care decision, minimal SES
  confounding.

**Tail risk basis:** Falls with major injury (NH_MDS_410), pressure ulcers (NH_MDS_479),
UTI (NH_MDS_407), antipsychotic overuse (NH_MDS_481), and rehospitalization
(NH_CLAIMS_551, NH_CLAIMS_521) all represent serious adverse events or conditions that
can result in significant patient harm or death.

### MDS Quality Measures — Short Stay (Five-Star Rating)

6 measures used in Five-Star QM rating (short-stay domain): 1 MDS from `djen-97ju`,
2 claims from `ijh5-nb2v`, 3 from SNF QRP `fykj-qjee`. All confirmed against live API.

Phase 0 reference: `docs/phase_0_findings.md` §13, §14, §21, §Confirmed NH Measure
Code Catalog, §Critical Finding: Discharge Function and Successful Return Measures.

**Interval estimation:** MDS (434) and Claims (521, 522) follow same rules as long-stay
(see above — NOT calculable). SNF QRP measures (S_042_02, S_038_02, S_005_02) have
numerator/denominator available; S_005_02 also has CMS-published credible intervals.
See SNF QRP section for details.

| Measure ID | CMS Code | Measure Name | Direction | Unit | SES | Tail Risk | Source |
|-----------|----------|-------------|-----------|------|-----|-----------|--------|
| `NH_MDS_434` | 434 | % short-stay residents who newly received antipsychotic medication | LOWER_IS_BETTER | percent | LOW | Yes | MDS (djen-97ju) |
| `NH_CLAIMS_521` | 521 | % short-stay residents rehospitalized after NH admission | LOWER_IS_BETTER | percent | HIGH | Yes | Claims (ijh5-nb2v) |
| `NH_CLAIMS_522` | 522 | % short-stay residents who had outpatient ED visit | LOWER_IS_BETTER | percent | MODERATE | No | Claims (ijh5-nb2v) |
| `S_042_02` | S_042_02 | Discharge function score (composite self-care + mobility) | HIGHER_IS_BETTER | percent | MODERATE | No | SNF QRP (fykj-qjee) |
| `S_038_02` | S_038_02 | New/worsened pressure ulcers/injuries | LOWER_IS_BETTER | percent | MODERATE | Yes | SNF QRP (fykj-qjee) |
| `S_005_02` | S_005_02 | Successful return to home and community | HIGHER_IS_BETTER | percent | MODERATE | No | SNF QRP (fykj-qjee) |

**Critical cross-dataset dependency:** The Five-Star QM rating draws from THREE
datasets (djen-97ju, ijh5-nb2v, fykj-qjee). See phase_0_findings.md §Critical Finding.

### MDS Quality Measures — Additional (Not in Five-Star Rating)

These measures are reported in the MDS Quality Measures dataset (djen-97ju) but are NOT
used in the Five-Star QM rating calculation. All confirmed against live API (2026-03-17).

| Measure ID | CMS Code | Measure Name | Direction | Unit | SES | Tail Risk | Notes |
|-----------|----------|-------------|-----------|------|-----|-----------|-------|
| `NH_MDS_404` | 404 | % long-stay residents who lose too much weight | LOWER_IS_BETTER | percent | MODERATE | No | |
| `NH_MDS_408` | 408 | % long-stay residents who have depressive symptoms | LOWER_IS_BETTER | percent | MODERATE | No | |
| `NH_MDS_409` | 409 | % long-stay residents who were physically restrained | LOWER_IS_BETTER | percent | LOW | Yes | Restraint use |
| `NH_MDS_415` | 415 | % long-stay residents given pneumococcal vaccine | HIGHER_IS_BETTER | percent | LOW | No | |
| `NH_MDS_454` | 454 | % long-stay residents given seasonal influenza vaccine | HIGHER_IS_BETTER | percent | LOW | No | |
| `NH_MDS_452` | 452 | % long-stay residents who received antianxiety/hypnotic medication | LOWER_IS_BETTER | percent | LOW | No | |
| `NH_MDS_480` | 480 | % long-stay residents with new/worsened bowel or bladder incontinence | LOWER_IS_BETTER | percent | MODERATE | No | |
| `NH_MDS_430` | 430 | % short-stay residents given pneumococcal vaccine | HIGHER_IS_BETTER | percent | LOW | No | |
| `NH_MDS_472` | 472 | % short-stay residents given seasonal influenza vaccine | HIGHER_IS_BETTER | percent | LOW | No | |

### Nursing Home Staffing Measures

9 staffing measures are stored in MEASURE_REGISTRY / `provider_measure_values`.
See DEC-033 in `docs/pipeline_decisions.md` for full rationale.

**Five-Star staffing sub-measures (6):** These are scored on decile scales and summed
to produce the staffing star rating (380 max points). Source: PBJ system via Provider
Information dataset (4pq5-n9py). All confirmed against live API (2026-03-17).

| Measure ID | API Key | Direction | Unit | Max Pts | Scoring |
|-----------|---------|-----------|------|---------|---------|
| `NH_STAFF_ADJ_TOTAL_HPRD` | `casemix_total_nurse_staffing_hours_per_resident_per_day` | HIGHER_IS_BETTER | hours/day | 100 | Decile (10-100) |
| `NH_STAFF_ADJ_RN_HPRD` | `casemix_rn_staffing_hours_per_resident_per_day` | HIGHER_IS_BETTER | hours/day | 100 | Decile (10-100) |
| `NH_STAFF_ADJ_WEEKEND_HPRD` | `casemix_weekend_total_nurse_staffing_hours_per_resident_per_day` | HIGHER_IS_BETTER | hours/day | 50 | Decile (5-50) |
| `NH_STAFF_TOTAL_TURNOVER` | `total_nursing_staff_turnover` | LOWER_IS_BETTER | percent | 50 | Decile, inverted (5-50) |
| `NH_STAFF_RN_TURNOVER` | `registered_nurse_turnover` | LOWER_IS_BETTER | percent | 50 | Decile, inverted (5-50) |
| `NH_STAFF_ADMIN_DEPARTURES` | `number_of_administrators_who_have_left_the_nursing_home` | LOWER_IS_BETTER | count | 30 | Fixed: 0→30, 1→25, 2+→10 |

**Reported (unadjusted) PBJ staffing (3):** Raw hours before case-mix adjustment,
included for consumer transparency — the adjustment can obscure real staffing
differences.

| Measure ID | API Key | Direction | Unit |
|-----------|---------|-----------|------|
| `NH_STAFF_REPORTED_TOTAL_HPRD` | `reported_total_nurse_staffing_hours_per_resident_per_day` | HIGHER_IS_BETTER | hours/day |
| `NH_STAFF_REPORTED_RN_HPRD` | `reported_rn_staffing_hours_per_resident_per_day` | HIGHER_IS_BETTER | hours/day |
| `NH_STAFF_REPORTED_AIDE_HPRD` | `reported_nurse_aide_staffing_hours_per_resident_per_day` | HIGHER_IS_BETTER | hours/day |

**SES sensitivity basis (all LOW):** Staffing levels are facility operational decisions
driven by budget, management, and labor market conditions. While facilities serving
disadvantaged populations may face tighter budgets, the measure itself reflects facility
choices, not patient population characteristics.

**Tail risk basis (all false):** Staffing levels are a structural risk factor but not
themselves adverse events. Low staffing is a predictor of harm, not harm itself. The
harm measures (falls, pressure ulcers, infections) carry the tail risk flags.

**Context-only staffing fields (stored in `providers` table, not MEASURE_REGISTRY):**
LPN HPRD (reported/case-mix/adjusted), Licensed HPRD, Physical Therapist HPRD,
weekend RN HPRD, case-mix index, case-mix ratio. These are intermediate calculation
values or supplementary context.

_(HPRD = Hours Per Resident Per Day. PBJ = Payroll-Based Journal, CMS's mandatory
electronic staffing reporting system.)_

**Interval estimation:**
- `risk_adjustment_model`: `"OTHER"` (PDPM case-mix adjustment) for adjusted measures;
  `"NONE"` for reported measures
- `cms_ci_published`: `False` — no CMS-published intervals for staffing
- `numerator_denominator_published`: N/A — staffing is continuous (hours/day), not a
  rate with counts. **Credible intervals NOT applicable.**
- Turnover rates (percent): no numerator/denominator published; cannot calculate CI.

**Direction confirmation:** CMS Five-Star staffing domain awards more points for higher
HPRD and lower turnover (published cut point tables in Five-Star Technical Users'
Guide). The scoring direction is explicit and published. Direction status: **CONFIRMED
via Five-Star staffing scoring tables.**

### Nursing Home Inspection Measures

8 inspection-derived measures are stored in MEASURE_REGISTRY / `provider_measure_values`.
See DEC-034 in `docs/pipeline_decisions.md` for full rationale.

**Tail risk measures (4):** Aggregated from individual deficiency citations in Health
Deficiencies dataset (r5ix-sfxw). Computed by pipeline normalizer, not pre-computed
by CMS. All confirmed against live API (2026-03-17, 419,452 rows).

| Measure ID | Direction | Unit | Tail Risk | SES | Source Filter |
|-----------|-----------|------|-----------|-----|---------------|
| `NH_INSP_IJ_CITATIONS` | LOWER_IS_BETTER | count | **Yes** | MODERATE | `scope_severity_code` in J, K, L |
| `NH_INSP_HARM_CITATIONS` | LOWER_IS_BETTER | count | **Yes** | MODERATE | `scope_severity_code` in G, H, I |
| `NH_INSP_ABUSE_CITATIONS` | LOWER_IS_BETTER | count | **Yes** | MODERATE | `deficiency_category` = Freedom from Abuse |
| `NH_INSP_INFECTION_CTRL` | LOWER_IS_BETTER | count | **Yes** | LOW | `infection_control_inspection_deficiency` = Y |

**SES sensitivity basis:**
- IJ/Harm/Abuse citations (MODERATE): Facilities serving disadvantaged populations may
  face higher inspection scrutiny and have fewer resources for compliance. However,
  immediate jeopardy and actual harm findings reflect objective safety failures, not
  purely SES-driven differences. The MODERATE classification reflects documented but
  modest correlation between facility SES mix and citation rates.
- Infection control (LOW): Infection prevention is a facility process measure; citation
  rates reflect infection control practices, not patient population characteristics.

**Tail risk basis:**
- IJ citations: CMS scope/severity J/K/L = "immediate jeopardy to resident health or
  safety." Residents face imminent danger of death or serious harm.
- Harm citations: CMS scope/severity G/H/I = "actual harm that is not immediate
  jeopardy." Residents suffered real injury or impairment.
- Abuse citations: CMS caps health inspection rating at 2 stars when abuse citations
  (F600/F602/F603) reach harm level. Abuse is the most serious quality failure.
- Infection control: Directly relevant to resident safety; infection outbreaks in
  nursing homes can cause rapid, widespread harm.

**Context measures (4):** Pre-computed fields from Provider Information (4pq5-n9py).

| Measure ID | API Key | Direction | Unit | Tail Risk | SES |
|-----------|---------|-----------|------|-----------|-----|
| `NH_INSP_TOTAL_HEALTH_DEF` | `rating_cycle_1_total_number_of_health_deficiencies` | LOWER_IS_BETTER | count | No | MODERATE |
| `NH_INSP_TOTAL_FIRE_DEF` | `total_number_of_fire_safety_deficiencies` (cycle 1) | LOWER_IS_BETTER | count | No | LOW |
| `NH_INSP_WEIGHTED_SCORE` | `total_weighted_health_survey_score` | LOWER_IS_BETTER | score | No | MODERATE |
| `NH_INSP_REVISIT_SCORE` | `rating_cycle_1_health_revisit_score` | LOWER_IS_BETTER | score | No | LOW |

**Scope/severity point values (Five-Star Technical Users' Guide Table 1):**

| Code | Severity | Points | SQoC Points |
|------|----------|--------|-------------|
| A-C | No harm, potential for minimal | 0 | 0 |
| D | No harm, potential > minimal (isolated) | 4 | 4 |
| E | No harm, potential > minimal (pattern) | 8 | 8 |
| F | No harm, potential > minimal (widespread) | 16 | 20 |
| G | Actual harm (isolated) | 20 | 20 |
| H | Actual harm (pattern) | 35 | 40 |
| I | Actual harm (widespread) | 45 | 50 |
| J | Immediate jeopardy (isolated) | 50 | 75 |
| K | Immediate jeopardy (pattern) | 100 | 125 |
| L | Immediate jeopardy (widespread) | 150 | 175 |

_(SQoC = Substandard Quality of Care — higher points when deficiency meets SQoC
criteria. Past non-compliance at J/K/L severity reduces to G-level 20 points.)_

#### Complaint Investigation Measure

| Measure ID | Direction | Unit | Tail Risk | SES | Source Filter |
|-----------|-----------|------|-----------|-----|---------------|
| `NH_INSP_COMPLAINT_DEF` | LOWER_IS_BETTER | count | **Yes** | MODERATE | `complaint_deficiency` = Y in r5ix-sfxw |

31.6% of all health deficiency citations (132,743 of 419,452 rows) come from complaint
investigations, not routine standard inspections. Complaint-triggered deficiencies are a
critical consumer signal because they indicate problems serious enough that someone
(resident, family member, staff, or ombudsman) filed a formal complaint.

**SES sensitivity (MODERATE):** Facilities serving disadvantaged populations may receive
fewer complaints due to lower family engagement or health literacy, while also receiving
more complaints due to higher care burden with fewer resources. The relationship is
complex and documented as moderate. Reference: GAO-19-433 (2019).

**Tail risk (true):** Complaint investigations are triggered by specific allegations of
harm, neglect, or rights violations — they are a direct signal of potential serious harm.

#### Penalty Measures

| Measure ID | API Key | Direction | Unit | Tail Risk | SES |
|-----------|---------|-----------|------|-----------|-----|
| `NH_PENALTY_FINE_TOTAL` | `total_amount_of_fines_in_dollars` | LOWER_IS_BETTER | dollars | **Yes** | LOW |
| `NH_PENALTY_COUNT` | `total_number_of_penalties` | LOWER_IS_BETTER | count | **Yes** | LOW |
| `NH_PENALTY_PAYMENT_DENIALS` | `number_of_payment_denials` | LOWER_IS_BETTER | count | **Yes** | LOW |
| `NH_PENALTY_FINE_COUNT` | `number_of_fines` | LOWER_IS_BETTER | count | No | LOW |

Source: Provider Information (4pq5-n9py) for aggregate counts. Individual penalty
records with dates and amounts are in the Penalties dataset (g6vv-u9sr, 17,463 rows)
and stored in `provider_penalties`.

**SES sensitivity (all LOW):** Penalties are an enforcement response to verified
quality failures, not a population characteristic. The decision to impose a fine or
payment denial reflects CMS's assessment of the facility's compliance, not its patient
population.

**Tail risk basis:**
- `NH_PENALTY_FINE_TOTAL` (true): Dollar amounts signal severity — CMS calibrates fine
  amounts to the seriousness of the violation. A $183K fine indicates a more serious
  failure than a $5K fine.
- `NH_PENALTY_COUNT` (true): Multiple penalties indicate persistent or repeated quality
  failures that the facility has not corrected.
- `NH_PENALTY_PAYMENT_DENIALS` (true): Payment denials are the most severe enforcement
  action short of decertification — CMS stops paying the facility for new admissions.
  This is reserved for situations where residents face serious ongoing risk.
- `NH_PENALTY_FINE_COUNT` (false): The count of fines alone is less informative than
  the dollar total or the presence of payment denials.

### Nursing Home Provider Context Fields (Non-Measures)

These fields are stored in the `providers` table and prominently displayed on profiles
but are NOT MEASURE_REGISTRY entries. All confirmed against live API (2026-03-17).

| Field | API Key | Type | Display Priority | Notes |
|-------|---------|------|-----------------|-------|
| `abuse_icon` | `abuse_icon` | bool (Y/N) | **Critical** | Cited for abuse at harm level (F600/F602/F603 at scope G+). CMS caps health inspection rating at 2 stars. Must be visually prominent. |
| `special_focus_status` | `special_focus_status` | varchar | **Critical** | `"SFF"` (88 facilities), `"SFF Candidate"` (442). History of serious quality issues. Per project principles, must be surfaced with same prominence as tail risk measures. |
| `most_recent_inspection_over_2yr` | `most_recent_health_inspection_more_than_2_years_ago` | bool (Y/N) | **High** | Data staleness signal — if true, all inspection-derived measures may be outdated. |
| `ownership_changed_12mo` | `provider_changed_ownership_in_last_12_months` | bool (Y/N) | **High** | Context for quality trend interpretation. New ownership may mean prior performance data is less predictive. |
| `resident_family_council` | `with_a_resident_and_family_council` | varchar | Moderate | `"Resident"`, `"Both"`, `"None"`. Quality-of-life indicator. |
| `sprinkler_status` | `automatic_sprinkler_systems_in_all_required_areas` | varchar | Moderate | `"Yes"`, `"Partial"`, `"Data Not Available"`. Fire safety context. |

**Abuse icon filter logic confirmed (2026-03-19):** The `deficiency_category` value
`"Freedom from Abuse, Neglect, and Exploitation Deficiencies"` captures F-tags 0226,
0600, 0602, 0604, 0605, 0607, 0609, 0610, 0943 — broader than the three F-tags
(F600/F602/F603) that trigger the abuse icon. The abuse icon is triggered specifically
by F600/F602/F603 at scope/severity G or higher on cycle 1, OR at D or higher on both
cycles 1 and 2. The `NH_INSP_ABUSE_CITATIONS` measure uses the broader category filter,
which is more protective for consumers.

### Five-Star Sub-Ratings

Stored in `provider_measure_values` with the nursing home CCN as provider_id.
Source: Provider Information dataset (4pq5-n9py). All confirmed against live API
(2026-03-17). Phase 0 reference: `docs/phase_0_findings.md` §12, §Five-Star Quality
Rating System.

| Measure ID | API Field | Direction | Unit | SES | Tail Risk | Notes |
|-----------|-----------|-----------|------|-----|-----------|-------|
| `NH_STAR_OVERALL` | `overall_rating` | HIGHER_IS_BETTER | score | MODERATE | No | 1-5 scale; not a simple average — see Five-Star methodology |
| `NH_STAR_HEALTH_INSP` | `health_inspection_rating` | HIGHER_IS_BETTER | score | MODERATE | No | 1-5 scale; state-level relative (not national) |
| `NH_STAR_QM` | `qm_rating` | HIGHER_IS_BETTER | score | MODERATE | No | 1-5 scale; composite of 15 measures |
| `NH_STAR_LS_QM` | `longstay_qm_rating` | HIGHER_IS_BETTER | score | MODERATE | No | 1-5 scale; 9 measures |
| `NH_STAR_SS_QM` | `shortstay_qm_rating` | HIGHER_IS_BETTER | score | MODERATE | No | 1-5 scale; 6 measures |
| `NH_STAR_STAFFING` | `staffing_rating` | HIGHER_IS_BETTER | score | LOW | No | 1-5 scale; 6 sub-measures |

**SES sensitivity basis for Five-Star ratings:**
- Overall, Health Inspection, QM ratings (MODERATE): Composite ratings aggregate
  individual measures with varying SES sensitivity. The overall rating inherits the
  MODERATE SES effects present in its constituent QM and health inspection domains.
  Reference: GAO-19-80, MedPAC June 2023.
- Staffing rating (LOW): Based on facility-level staffing decisions and PBJ-reported
  data, not resident population characteristics.

**Interval estimation:**
- `risk_adjustment_model`: Complex composite algorithm (not a single model)
- `cms_ci_published`: `False` — ratings are ordinal 1-5, not continuous values
- `numerator_denominator_published`: N/A
- **Credible intervals NOT applicable** — ordinal categorical ratings.

**Direction confirmation:** CMS explicitly defines 5 stars = best, 1 star = worst. The
Five-Star system is the most explicitly directional construct in CMS nursing home data.
Direction status: **CONFIRMED — self-evident from CMS Five-Star design.** No direction
assertion needed in consumer-facing text.

### SNF QRP Measures

SNF Quality Reporting Program measures. 15 measures total. Separate from Five-Star
rating measures, though 3 measures (S_038_02, S_042_02, S_005_02) are also used in the
Five-Star QM domain.

**Reference document:** `docs/snf-qm-calculations-and-reporting-users-manual-v7.0.txt`
(CMS SNF QRP QM Calculations and Reporting Users Manual v7.0, effective 10/01/2025)

**API dataset:** `fykj-qjee` (confirmed 2026-03-16). Data uses compound measure_code
format with suffixes (e.g., `S_004_01_PPR_PD_RSRR`). See `docs/phase_0_findings.md`
§21 for suffix documentation.

**Interval estimation — per-measure sub-field availability (confirmed 2026-03-19):**

| Base Code | Sub-fields in API | CMS CI | Num/Denom | Interval Status |
|-----------|-------------------|--------|-----------|-----------------|
| S_004_01 | `RSRR`, `RSRR_2_5`, `RSRR_97_5`, `OBS`, `OBS_READM`, `VOLUME`, `COMP_PERF` | **Yes** | Volume only | AVAILABLE (CMS credible interval) |
| S_005_02 | `RS_RATE`, `RS_RATE_2_5`, `RS_RATE_97_5`, `OBS_RATE`, `NUMBER`, `VOLUME`, `COMP_PERF` | **Yes** | Volume + number | AVAILABLE (CMS credible interval) |
| S_006_01 | `MSPB_SCORE`, `MSPB_NUMB` | No | Number only | NOT AVAILABLE |
| S_007_02 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | **Yes** | CALCULABLE (Beta-Binomial) |
| S_013_02 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | **Yes** | CALCULABLE (Beta-Binomial) |
| S_024_06 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | Yes (unadj) | NOT AVAILABLE — CMS-adjusted rate is primary display value |
| S_025_06 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | Yes (unadj) | NOT AVAILABLE — CMS-adjusted rate is primary display value |
| S_038_02 | `ADJ_RATE`, `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | Yes (unadj) | NOT AVAILABLE — CMS-adjusted rate is primary display value |
| S_039_01 | `RS_RATE`, `RS_RATE_2_5`, `RS_RATE_97_5`, `OBS_RATE`, `NUMBER`, `VOLUME`, `COMP_PERF` | **Yes** | Volume + number | AVAILABLE (CMS credible interval) |
| S_040_02 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | **Yes** | CALCULABLE (Beta-Binomial) |
| S_041_01 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | **Yes** | CALCULABLE (Beta-Binomial) |
| S_042_02 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | Yes (unadj) | NOT AVAILABLE — CMS-adjusted rate is primary display value |
| S_043_02 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | **Yes** | CALCULABLE (Beta-Binomial) |
| S_044_02 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | **Yes** | CALCULABLE (Beta-Binomial) |
| S_045_01 | `NUMERATOR`, `DENOMINATOR`, `OBS_RATE` | No | **Yes** | CALCULABLE (Beta-Binomial) |

**Note on risk-adjusted measures with num/denom (S_024, S_025, S_038, S_042):** These
measures are risk-adjusted by CMS (using covariate models with 4-23 covariates). The
CMS-adjusted value is the primary display measure — it is the value CMS intends for
public reporting and comparison. The `OBS_RATE` (unadjusted) and `NUMERATOR`/
`DENOMINATOR` are stored for transparency and audit but are NOT used as the primary
display value. Do not override CMS's risk adjustment with our own calculations.

Credible intervals are **NOT calculable** for these measures because the adjusted rate
is model-derived, not a simple proportion. The numerator/denominator correspond to the
unadjusted rate, not the adjusted one, so applying Beta-Binomial to them would produce
intervals for the wrong quantity. Interval status: **NOT AVAILABLE** for the adjusted
value. Display the CMS-adjusted point estimate with sample size context (denominator).

**Direction confirmation:** CMS SNF QM manual v7.0 explicitly documents direction for
all 15 measures. Lower readmission/hospitalization/infection rates are better; higher
discharge function/community return/vaccination/compliance rates are better. Direction
status: **CONFIRMED via CMS SNF QM manual.**

| Measure Code | Measure Name | Direction | Unit | SES | Tail Risk | Type | Risk-Adj | Period | Notes |
|---|---|---|---|---|---|---|---|---|---|
| S_004_01 | Potentially Preventable 30-Day Post-Discharge Readmission (PPR) | LOWER_IS_BETTER | percent | HIGH | Yes | Claims, Outcome | Yes | 12 mo | |
| S_005_02 | Discharge to Community (DTC) | HIGHER_IS_BETTER | percent | MODERATE | No | Claims, Outcome | Yes | 12 mo | **Also in Five-Star QM** |
| S_006_01 | Medicare Spending Per Beneficiary (MSPB) | LOWER_IS_BETTER | ratio | MODERATE | No | Claims, Cost | Yes | 12 mo | Ratio to national median |
| S_007_02 | Drug Regimen Review with Follow-Up (DRR) | HIGHER_IS_BETTER | percent | LOW | No | MDS, Process | No | 12 mo | |
| S_013_02 | Falls with Major Injury (SNF stay) | LOWER_IS_BETTER | percent | MODERATE | Yes | MDS, Outcome | No | 12 mo | |
| S_024_07 | Discharge Self-Care Score | HIGHER_IS_BETTER | percent | MODERATE | No | MDS, Outcome | Yes (18 cov) | 12 mo | API shows `S_024_06` |
| S_025_07 | Discharge Mobility Score | HIGHER_IS_BETTER | percent | MODERATE | No | MDS, Outcome | Yes (18 cov) | 12 mo | API shows `S_025_06` |
| S_038_02 | New/Worsened Pressure Ulcers/Injuries | LOWER_IS_BETTER | percent | MODERATE | Yes | MDS, Outcome | Yes (4 cov) | 12 mo | **Also in Five-Star QM** |
| S_039_01 | SNF HAI Requiring Hospitalization | LOWER_IS_BETTER | percent | LOW | Yes | Claims, Outcome | Yes | 12 mo | |
| S_040_02 | HCP COVID-19 Vaccination Coverage | HIGHER_IS_BETTER | percent | LOW | No | NHSN, Process | No | Annual | |
| S_041_01 | HCP Influenza Vaccination Coverage | HIGHER_IS_BETTER | percent | LOW | No | NHSN, Process | No | Annual | |
| S_042_03 | Discharge Function Score (composite) | HIGHER_IS_BETTER | percent | MODERATE | No | MDS, Outcome | Yes (23 cov) | 12 mo | **Also in Five-Star QM**; API shows `S_042_02` |
| S_043_02 | Transfer of Health Info to Provider | HIGHER_IS_BETTER | percent | LOW | No | MDS, Process | No | 12 mo | Effective 10/01/2024 |
| S_044_02 | Transfer of Health Info to Patient/Family | HIGHER_IS_BETTER | percent | LOW | No | MDS, Process | No | 12 mo | Effective 10/01/2024 |
| S_045_01 | Resident COVID-19 Vaccination | HIGHER_IS_BETTER | percent | LOW | No | MDS, Process | No | **3 mo** | **Single quarter only** |

**SES sensitivity basis:**
- PPR/S_004_01 (HIGH): Same readmission dynamics as hospital HRRP — post-discharge
  factors (medication adherence, follow-up access) are strongly SES-correlated.
  Reference: Joynt & Jha (2013); MedPAC June 2023.
- DTC/S_005_02 (MODERATE): Discharge to community is affected by availability of
  community supports, housing stability, and caregiver resources.
  Reference: GAO-19-80 (2018).
- Falls, pressure ulcers, discharge function/mobility (MODERATE): Facility-level staffing
  and care quality are primary drivers, but resident population SES mix has documented
  moderate effects on baseline risk. Reference: GAO-19-80 (2018).
- Staffing-driven process measures, vaccination (LOW): Facility decisions, not resident
  SES.
- SNF HAI/S_039_01 (LOW): Infection control is primarily a facility process measure.

**Tail risk basis:** PPR (readmission = potential deterioration), Falls (major injury
including fractures, head injuries), Pressure Ulcers (serious wound complications,
sepsis risk), SNF HAI (infection requiring hospitalization = life-threatening).

**MEASURE_REGISTRY IDs:** All 15 SNF QRP measures are registered in `pipeline/config.py`
using their CMS base codes as measure_id: `S_004_01`, `S_005_02`, `S_006_01`,
`S_007_02`, `S_013_02`, `S_024_06`, `S_025_06`, `S_038_02`, `S_039_01`, `S_040_02`,
`S_041_01`, `S_042_02`, `S_043_02`, `S_044_02`, `S_045_01`.

**Version discrepancy note:** Live API codes encode the measure version at time of data
collection (e.g., `S_042_02`), while the current manual documents version `.03`. The
pipeline must map API codes to current measure specifications. See phase_0_findings.md
§21 for details.

### SNF Value-Based Purchasing Program

Stored in `provider_payment_adjustments` as `program = 'SNF_VBP'`.

**FY 2026 measures (4):**

| Measure | Direction | Notes |
|---------|-----------|-------|
| SNF 30-Day All-Cause Readmission (SNFRM) | LOWER_IS_BETTER | Risk-standardized readmission rate |
| SNF Healthcare-Associated Infections (SNF HAI) | LOWER_IS_BETTER | Risk-standardized HAI rate |
| Total Nursing Staff Turnover Rate | LOWER_IS_BETTER | PBJ-derived |
| SNF Quality Measure Suite (SNFQMS) | _(TBD)_ | Composite — direction depends on composition |

**Fields per measure:** Baseline period result, performance period result, achievement
score (0-10), improvement score (0-9), measure score, performance score, ranking,
incentive payment multiplier.

_(All fields to be confirmed against live API during Phase 0.)_

---

## Nursing Home Footnote Code Lookup Table

Nursing home footnote codes are **distinct from hospital footnote codes.** The hospital
footnote crosswalk (`docs/Footnote_Crosswalk.csv`) does NOT apply to nursing home data.
See `docs/phase_0_findings.md` §Nursing Home Footnote Code Lookup Table for the draft
table pending confirmation against live API data.

---

## Footnote Code Lookup Table

Raw CMS footnote codes and human-readable explanations. Source: CMS Hospital
Downloadable Database Data Dictionary, January 2026, Appendix E — Footnote Crosswalk.
Updated 2026-03-14.

| Code | Explanation | Suppression? | Notes |
|------|-------------|--------------|-------|
| 1 | The number of cases/patients is too few to report | Yes | Applied when case count doesn't meet minimum for public reporting, count is too small to reliably assess performance, or to protect PHI |
| 2 | Data submitted were based on a sample of cases/patients | No | Hospital submitted data for a random sample following specific selection rules |
| 3 | Results are based on a shorter time period than required | No | Results based on less than the maximum possible collection period |
| 4 | Data suppressed by CMS for one or more quarters | Yes | Results excluded for various reasons including data inaccuracies |
| 5 | Results are not available for this reporting period | Yes | Applied when facility elected not to submit entire period, had no claims data, or elected to suppress from public reporting |
| 6 | Fewer than 100 patients completed the CAHPS survey | Partial | Use with caution; count too low to reliably assess performance. Applied when completed surveys < 100 |
| 7 | No cases met the criteria for this measure | Yes | Hospital had no cases meeting inclusion criteria |
| 8 | The lower limit of the confidence interval cannot be calculated if the number of observed infections equals zero | No | HAI-specific |
| 9 | No data are available from the state/territory for this reporting period | Yes | Applied when too few state/territory facilities had data |
| 10 | Very few patients were eligible for CAHPS survey (fewer than 50 completed surveys) | Partial | Use with caution; count too low to reliably assess performance. Applied when completed surveys < 50 |
| 11 | There were discrepancies in the data collection process | No | Applied when deviations from data collection protocols occurred |
| 12 | This measure does not apply to this hospital for this reporting period | Yes | Applied when: zero device days/procedures for entire period, hospital lacks ICU locations, new NHSN member, hospital doesn't report voluntary measure, or VA hospital results combined with parent |
| 13 | Results cannot be calculated for this reporting period | Yes | Applied when predicted infections < 1 or when MRSA/C. difficile community-onset prevalence above predetermined cutpoint |
| 14 | The results for this state are combined with nearby states to protect confidentiality | No | Applied when state has fewer than 10 hospitals. Combined states: DC+DE, AK+WA, ND+SD, NH+VT |
| 15 | The number of cases/patients is too few to report a star rating | Yes | Applied when HCAHPS completed surveys < 100 |
| 16 | There are too few measures or measure groups reported to calculate a star rating or measure group score | Yes | Applied when hospital reported < 3 measures in any group, < 3 measure groups, or did not report at least 1 outcomes measure group |
| 17 | This hospital's star rating only includes data reported on inpatient services | No | Applied when hospital only reports inpatient hospital services data |
| 18 | This result is not based on performance data; hospital did not submit data and did not submit HAI exemption form | Yes | Hospital receives maximum Winsorized z-score for HACRP Domain 2 |
| 19 | Data are shown only for hospitals that participate in IQR and OQR programs | Yes | Applied for hospitals not participating in IQR/OQR programs |
| 20 | State and national averages do not include VHA hospital data | No | **No longer used** |
| 21 | Patient survey results for VHA hospitals do not represent official HCAHPS results | No | **No longer used** |
| 22 | Overall star ratings are not calculated for DoD hospitals | Yes | DoD hospitals excluded from star rating calculations |
| 23 | The data are based on claims hospital submitted to CMS; hospital reported discrepancies | No | Hospital alerted CMS to possible claims data issues |
| 24 | Results for this VA hospital are combined with those from the VA administrative parent hospital | No | VA hospitals only |
| 25 | State and national averages include VHA hospital data | No | VHA hospitals calculated with other inpatient acute-care hospitals |
| 26 | State and national averages include DoD hospital data | No | DoD hospitals calculated with other inpatient acute-care hospitals |
| 27 | Patient survey results for DoD hospitals do not represent official HCAHPS results | No | **No longer used** |
| 28 | The results are based on hospital/facility data submissions; CMS approved Extraordinary Circumstances Exception request | No | Calculated values should be used with caution |
| 29 | This measure was calculated using partial performance period data due to CMS-approved exception | No | Results based on less than maximum time period with CMS-approved Extraordinary Circumstances Exception |
| * | Maryland: no data available to calculate PSI 90; Total HAC score dependent on Domain 2 score only | No | HACRP-specific |
| ** | Value calculated using data reported by hospital in compliance with program requirements; does not account for information available at later date | No | HACRP-specific |
| a | Maryland hospitals are waived from receiving payment adjustments under HACRP | No | HACRP-specific |

**Datasets where each footnote code has been observed in samples (2026-03-14):**

| Code | Observed in |
|------|------------|
| 1 | CompDeaths, HAI, HRRP, MSPB, OIE, TE, Readmissions |
| 2 | TE |
| 3 | HAI, TE |
| 5 | CompDeaths, HAI, HRRP, MSPB, OIE, Readmissions |
| 7 | CompDeaths, HRRP, OIE |
| 8 | HAI |
| 12 | HAI |
| 13 | HAI |
| 19 | MSPB |
| 29 | CompDeaths, HAI, HRRP, MSPB, OIE, TE, Readmissions |

**Rule:** When CMS returns a footnote code not listed here, log it with full context
and add it before the next production deploy. See data-integrity.md Rule 2.

---

## compared_to_national Canonical Values (AMB-3, DEC-022)

CMS uses inconsistent phrasings across datasets. The normalizer must map all observed
phrasings to these canonical values using case-insensitive matching before storage.
Column type: `varchar null` (not PostgreSQL enum — same convex-over-concave reasoning
as DEC-013).

| Canonical Value | CMS Raw Strings (case-insensitive) |
|---|---|
| `BETTER` | `"Better Than the National Rate"`, `"Better Than the National Value"`, `"Better than the National Benchmark"`, `"Better than expected"`, `"Fewer Days Than Average per 100 Discharges"` |
| `NO_DIFFERENT` | `"No Different Than the National Rate"`, `"No Different Than the National Value"`, `"No Different than National Benchmark"`, `"No Different than expected"`, `"Average Days per 100 Discharges"` |
| `WORSE` | `"Worse Than the National Rate"`, `"Worse Than the National Value"`, `"Worse than the National Benchmark"`, `"Worse than expected"`, `"More Days Than Average per 100 Discharges"` |
| `TOO_FEW_CASES` | `"Number of Cases Too Small"`, `"Number of cases too small"` |
| `NOT_AVAILABLE` | `"Not Available"`, `"Not Applicable"` |

**Phrasing variants by measure family (confirmed from full-population CSV scan 2026-03-20):**
- CompDeaths mortality/PSI: "Rate" (individual measures) / "Value" (PSI_90 composite)
- HAI: "Benchmark" phrasing, lowercase "than"
- Readmissions READM_30/Hybrid_HWR: "Rate" phrasing
- EDAC measures (EDAC_30_AMI, EDAC_30_HF, EDAC_30_PN): "Days" phrasing —
  `"Average Days per 100 Discharges"` / `"More Days Than Average..."` /
  `"Fewer Days Than Average..."` (excess days metric, not a rate)
- OP_36: "expected" phrasing — `"No Different than expected"` / `"Better than expected"`
  / `"Worse than expected"` (O/E ratio comparison)

CMS 632h-zaca confirmed to contain both capitalizations of "Number of Cases Too Small"
in the same dataset snapshot. The normalizer must use case-insensitive matching for all
`compared_to_national` values.
