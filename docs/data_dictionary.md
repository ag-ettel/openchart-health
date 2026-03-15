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

## Hospital Measures

### Hospital General Information

_(Provider metadata only — no MEASURE_REGISTRY entries for this dataset.)_

Context fields derived from this dataset and stored in the `providers` table:

| Field | Type | Description |
|-------|------|-------------|
| `dsh_status` | bool | Disproportionate Share Hospital designation |
| `dsh_percentage` | decimal(5,2) | DSH percentage from CMS |
| `is_teaching_hospital` | bool | CMS teaching hospital indicator |
| `staffed_beds` | integer | Number of staffed beds |
| `urban_rural_classification` | varchar | CMS Provider of Services file classification |
| `is_critical_access` | bool | Critical Access Hospital designation |

`provider_subtype` enum values confirmed in Phase 0. See `docs/phase_0_findings.md §Provider Subtype Enum Values`.

---

### Hospital Overall Star Rating

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Phase 0 Reference |
|-----------|-------------|-----------|------|----------------|-----------|-------------------|
| _(to be added after Phase 0)_ | | | | | | |

---

### Timely and Effective Care

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Phase 0 Reference |
|-----------|-------------|-----------|------|----------------|-----------|-------------------|
| _(to be added after Phase 0)_ | | | | | | |

---

### HCAHPS Patient Survey

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Phase 0 Reference |
|-----------|-------------|-----------|------|----------------|-----------|-------------------|
| _(to be added after Phase 0)_ | | | | | | |

---

### Complications and Deaths

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Phase 0 Reference |
|-----------|-------------|-----------|------|----------------|-----------|-------------------|
| _(to be added after Phase 0)_ | | | | | | |

**SES Sensitivity Note (Complications and Deaths):**
30-day mortality and complication rates are risk-adjusted by CMS for clinical factors
but not fully adjusted for socioeconomic characteristics. See ses-context.md for
full disclosure requirements. Classification basis: _(to be documented per measure)_.

---

### Healthcare-Associated Infections (HAI)

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Phase 0 Reference |
|-----------|-------------|-----------|------|----------------|-----------|-------------------|
| _(to be added after Phase 0)_ | | | | | | |

**SES Sensitivity Note (HAI):**
HAI rates have documented LOW SES sensitivity per published literature (process
compliance measures independent of patient socioeconomic mix). Basis: _(to be cited)_.

---

### Unplanned Hospital Visits (Readmissions)

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Phase 0 Reference |
|-----------|-------------|-----------|------|----------------|-----------|-------------------|
| _(to be added after Phase 0)_ | | | | | | |

**SES Sensitivity Note (Readmissions):**
30-day readmission rates are classified HIGH SES sensitivity. Published literature
documents substantial association between readmission rates and patient socioeconomic
factors independent of clinical risk adjustment. Basis: _(to be cited)_.

---

### Outpatient Imaging Efficiency

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Phase 0 Reference |
|-----------|-------------|-----------|------|----------------|-----------|-------------------|
| _(to be added after Phase 0)_ | | | | | | |

---

### Medicare Hospital Spending Per Patient

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Phase 0 Reference |
|-----------|-------------|-----------|------|----------------|-----------|-------------------|
| _(to be added after Phase 0)_ | | | | | | |

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

| Program | Table Column | Years Available | Notes |
|---------|-------------|----------------|-------|
| HRRP | `program = 'HRRP'` | _(to be confirmed)_ | |
| HACRP | `program = 'HACRP'` | _(to be confirmed)_ | |
| VBP | `program = 'VBP'` | _(to be confirmed)_ | |

---

## Nursing Home Measures

_(Pipeline deferred to Phase 2. MEASURE_REGISTRY entries to be drafted during hospital build phase.)_

### MDS Quality Measures — Long Stay

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Notes |
|-----------|-------------|-----------|------|----------------|-----------|-------|
| _(placeholder)_ | | | | | | |

### MDS Quality Measures — Short Stay

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Notes |
|-----------|-------------|-----------|------|----------------|-----------|-------|
| _(placeholder)_ | | | | | | |

### Nursing Home Staffing Data

_(Stored as provider context fields, not MEASURE_REGISTRY. To be specified at NH build time.)_

### Five-Star Sub-Ratings

| Measure ID | Measure Name | Direction | Unit | SES Sensitivity | Tail Risk | Notes |
|-----------|-------------|-----------|------|----------------|-----------|-------|
| _(placeholder)_ | | | | | | |

### SNF Value-Based Purchasing Program

_(Stored in `provider_payment_adjustments` as `program = 'SNF_VBP'`.)_

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
