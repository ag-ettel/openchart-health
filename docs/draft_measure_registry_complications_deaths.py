"""
MEASURE_REGISTRY Draft — Complications and Deaths (ynj2-r877)

Drafted: 2026-03-15
Source: scripts/recon/raw_samples/ynj2-r877.json (1000 rows, 10 pages)
Phase 0 reference: docs/phase_0_findings.md §5 (Complications and Deaths)

20 distinct measure_id values confirmed against live CMS API.

Direction reasoning documented per measure below.
All measures in this dataset are LOWER_IS_BETTER — these are death rates,
complication rates, and patient safety indicator rates. A lower value
always represents a better outcome.

All measures carry tail_risk_flag = True — every measure in this dataset
relates to mortality, serious surgical complications, or adverse safety
events. This is the definition of tail risk.

SES sensitivity reasoning:
  - MORT_30_* and Hybrid_HWM: HIGH. 30-day mortality measures are
    well-documented in the published literature as substantially affected
    by patient socioeconomic mix. CMS risk adjustment accounts for clinical
    factors (age, comorbidities) but not patient SES characteristics.
    References: Bernheim et al. (2016) "Influence of Patient Socioeconomic
    Status on Clinical Outcomes and Hospital Closures"; CMS IMPACT Act
    reports; MedPAC June 2023 chapter on social risk factors.
  - COMP_HIP_KNEE: MODERATE. Hip/knee replacement is elective surgery with
    some patient selection effects. Literature shows documented but smaller
    SES effects compared to emergency admission mortality. Patients with
    lower SES may have delayed access to elective surgery, presenting with
    more advanced disease. Reference: Singh & Lu (2004) "Socioeconomic
    disparities in TJA outcomes."
  - PSI individual measures (PSI_03–PSI_15): MODERATE. Patient safety
    indicators are risk-adjusted for clinical factors. Literature documents
    moderate SES effects — hospitals serving disadvantaged populations tend
    to have higher PSI rates partly due to structural resource constraints,
    not solely care quality. Reference: Encinosa & Hellinger (2008) "Impact
    of Medical Errors on Patient Safety Outcomes."
  - PSI_90 (composite): MODERATE. Aggregates individual PSIs; inherits
    their moderate SES sensitivity.

Unit assignments:
  - MORT_30_* and Hybrid_HWM: "percent" — CMS reports risk-standardized
    mortality rates as percentages (e.g., score "12.5" = 12.5% RSMR).
  - COMP_HIP_KNEE: "percent" — complication rate reported as percentage.
  - PSI individual (PSI_03–PSI_15): "rate" — AHRQ Patient Safety Indicators
    are rates: numerator = qualifying discharges with the adverse event,
    denominator = eligible discharges (surgical, medical, or elective
    surgical depending on the specific PSI). Confirmed from CMS PSI-90
    FactSheet (docs/psi90-FactSheet.pdf, September 2019). Each PSI has
    distinct inclusion/exclusion criteria for both numerator and denominator.
    Source reference: docs/psi90-FactSheet.txt (extracted text).
  - PSI_90: "ratio" — composite observed-to-expected ratio where 1.0 equals
    the national expected rate. Score of 0.95 = 5% below expected. PSI_90
    is a weighted average of the 10 component PSI indicators (PSI_03
    through PSI_15).

compared_to_national normalization note (AMB-3):
  PSI_90 uses "Value" phrasing ("No Different Than the National Value").
  All other measures use "Rate" phrasing. Both must normalize to a
  canonical enum before storage. See docs/pipeline_decisions.md.

CI methodology classification:
    risk_adjustment_model: HGLM for all 20 measures. CMS uses hierarchical
    generalized linear models (hierarchical logistic regression) for all
    outcome measures in this dataset. Mortality measures (MORT_30_*) and
    Hybrid_HWM use CMS's standard HGLM methodology. COMP_HIP_KNEE uses
    HGLM. PSI measures (PSI_03–PSI_15, PSI_90) use AHRQ Patient Safety
    Indicator methodology which also employs hierarchical models with
    signal-to-noise reliability adjustment — classified as HGLM here.

    cms_ci_published: True for all. The Complications and Deaths dataset
    (ynj2-r877) includes `lower_estimate` and `higher_estimate` fields
    for every measure, providing CMS-calculated 95% confidence intervals.

    numerator_denominator_published: False for all. CMS publishes a
    `denominator` field (number of eligible cases/discharges), but the
    score is a risk-standardized rate derived from the hierarchical model,
    not a simple numerator/denominator ratio. A raw numerator cannot be
    meaningfully derived from the published data.

    CI calculability: AVAILABLE (CMS-provided). Use the lower_estimate and
    higher_estimate values directly. Do not attempt to recalculate CIs.
"""

# ─────────────────────────────────────────────────────────────────────
# Mortality Measures (6)
#
# All 30-day risk-standardized mortality rates (RSMR). CMS calculates
# these using hierarchical logistic regression models that account for
# age, sex, comorbidities, and prior diagnoses. The models do NOT adjust
# for patient SES characteristics.
#
# Direction: LOWER_IS_BETTER for all. A lower death rate is
# unambiguously better. This is definitional — not inferred.
#
# Reporting period: 36 months rolling, refreshed annually.
# ─────────────────────────────────────────────────────────────────────

MORT_30_AMI = {
    "measure_id": "MORT_30_AMI",
    "name": "Death rate for heart attack patients",
    "group": "MORTALITY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower 30-day death rate for acute myocardial infarction
    # patients is unambiguously better. This measures the percentage of
    # Medicare patients who die within 30 days of hospital admission for
    # heart attack.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare heart attack patients who died within "
        "30 days of being admitted to this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Mortality is the most severe adverse outcome. Heart attack
    # mortality is the canonical tail-risk measure.
    "ses_sensitivity": "HIGH",
    # Reasoning: 30-day mortality for AMI is well-documented as substantially
    # affected by patient socioeconomic mix. Hospitals serving higher
    # proportions of dual-eligible and low-income patients show higher
    # observed mortality rates even after clinical risk adjustment.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

MORT_30_CABG = {
    "measure_id": "MORT_30_CABG",
    "name": "Death rate for CABG surgery patients",
    "group": "MORTALITY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower 30-day death rate after coronary artery bypass
    # graft surgery is unambiguously better. CABG is a high-risk cardiac
    # procedure and perioperative mortality is a direct quality signal.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare patients who died within 30 days of "
        "coronary artery bypass graft (open-heart) surgery at this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Perioperative death during cardiac surgery is a
    # high-severity adverse event.
    "ses_sensitivity": "HIGH",
    # Reasoning: Same basis as MORT_30_AMI — 30-day surgical mortality
    # is affected by patient SES mix. CABG patients from disadvantaged
    # populations may present with more advanced disease and comorbidities
    # not fully captured by clinical risk adjustment.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

MORT_30_COPD = {
    "measure_id": "MORT_30_COPD",
    "name": "Death rate for COPD patients",
    "group": "MORTALITY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower 30-day death rate for chronic obstructive
    # pulmonary disease patients is unambiguously better.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare patients admitted for a COPD flare-up "
        "who died within 30 days of being admitted to this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Death from a COPD exacerbation is a high-severity
    # adverse event.
    "ses_sensitivity": "HIGH",
    # Reasoning: COPD disproportionately affects low-income and
    # smoking-prevalent populations. 30-day mortality for COPD is
    # documented as SES-sensitive — post-discharge support, medication
    # adherence, and housing stability all influence 30-day survival.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

MORT_30_HF = {
    "measure_id": "MORT_30_HF",
    "name": "Death rate for heart failure patients",
    "group": "MORTALITY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower 30-day death rate for heart failure patients
    # is unambiguously better.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare heart failure patients who died within "
        "30 days of being admitted to this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Heart failure mortality is a high-severity adverse event.
    "ses_sensitivity": "HIGH",
    # Reasoning: Heart failure 30-day mortality is one of the most
    # studied SES-sensitive measures. Post-discharge factors (medication
    # access, follow-up care, diet, housing) strongly influenced by SES
    # affect 30-day survival.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

MORT_30_PN = {
    "measure_id": "MORT_30_PN",
    "name": "Death rate for pneumonia patients",
    "group": "MORTALITY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower 30-day death rate for pneumonia patients is
    # unambiguously better.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare pneumonia patients who died within "
        "30 days of being admitted to this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Pneumonia mortality is a high-severity adverse event.
    "ses_sensitivity": "HIGH",
    # Reasoning: Pneumonia mortality follows the same SES sensitivity
    # pattern as other 30-day mortality measures. CMS includes it in the
    # same risk adjustment framework.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

MORT_30_STK = {
    "measure_id": "MORT_30_STK",
    "name": "Death rate for stroke patients",
    "group": "MORTALITY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower 30-day death rate for stroke patients is
    # unambiguously better. Stroke mortality is time-sensitive —
    # rapid access to stroke centers and thrombolytic therapy directly
    # affects survival.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare stroke patients who died within "
        "30 days of being admitted to this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Stroke mortality is a high-severity adverse event.
    "ses_sensitivity": "HIGH",
    # Reasoning: 30-day stroke mortality is SES-sensitive. Access to
    # stroke centers, time-to-treatment, and post-acute rehabilitation
    # are all influenced by patient socioeconomic factors.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Hybrid Hospital-Wide Mortality (1)
#
# This is a newer CMS measure using hybrid clinical and claims data.
# It captures all-cause inpatient mortality across all conditions,
# not limited to specific diagnoses like the MORT_30_* measures.
#
# Direction: LOWER_IS_BETTER. A lower hospital-wide mortality rate
# is unambiguously better.
#
# Reporting period: Varies (hybrid data collection); refreshed annually.
# ─────────────────────────────────────────────────────────────────────

HYBRID_HWM = {
    "measure_id": "Hybrid_HWM",
    "name": "Hybrid Hospital-Wide All-Cause Risk Standardized Mortality Rate",
    "group": "MORTALITY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: This is a risk-standardized mortality rate across all
    # inpatient stays. A lower rate means fewer patients died relative
    # to what would be expected given patient mix. Lower is unambiguously
    # better.
    "unit": "percent",
    "plain_language": (
        "The overall percentage of Medicare patients who died during or "
        "shortly after a stay at this hospital, adjusted for how sick "
        "the patients were."
    ),
    "tail_risk_flag": True,
    # Reasoning: Hospital-wide mortality is the broadest mortality
    # measure — it captures all deaths, not just specific conditions.
    "ses_sensitivity": "HIGH",
    # Reasoning: Hospital-wide mortality inherits the SES sensitivity
    # of the condition-specific mortality measures it encompasses.
    # All-cause mortality is documented as substantially affected by
    # patient socioeconomic mix.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Complication Measure (1)
#
# Direction: LOWER_IS_BETTER. A lower complication rate after elective
# joint replacement is unambiguously better.
#
# Reporting period: 12 months, refreshed annually.
# ─────────────────────────────────────────────────────────────────────

COMP_HIP_KNEE = {
    "measure_id": "COMP_HIP_KNEE",
    "name": "Rate of complications for hip/knee replacement patients",
    "group": "COMPLICATIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: This measures the rate of serious complications
    # (mechanical failure, periprosthetic infection, wound complications,
    # surgical site bleeding) within 90 days of elective hip or knee
    # replacement. A lower rate is unambiguously better.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare patients who had a serious complication "
        "within 90 days of an elective hip or knee replacement at this "
        "hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Serious surgical complications (prosthetic failure,
    # infection, bleeding requiring return to OR) are high-severity
    # adverse events that can result in permanent disability or death.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Hip/knee replacement is elective surgery. Patients with
    # lower SES may delay surgery and present with more advanced disease,
    # but the primary determinant of 90-day complications is surgical
    # technique and post-operative care. Literature shows documented but
    # smaller SES effects compared to emergency admission mortality.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Patient Safety Indicators — Individual Measures (12)
#
# AHRQ Patient Safety Indicators (PSIs) identify potentially
# preventable complications and adverse events during hospitalization.
# CMS reports these as risk-adjusted rates.
#
# Direction: LOWER_IS_BETTER for all. A lower rate of adverse safety
# events is unambiguously better. This is definitional.
#
# Reporting period: 24 months for PSIs, refreshed annually.
#
# Note on units: CMS reports these as risk-adjusted rates. The exact
# denomination (per discharge, per 1,000 discharges, or as O/E ratios)
# must be confirmed from CMS technical specifications before Phase 1.
# The raw score values in the API (e.g., PSI_12 = 3.24 with CI 1.13–5.36)
# are consistent with rates per 1,000 eligible discharges.
# ─────────────────────────────────────────────────────────────────────

PSI_03 = {
    "measure_id": "PSI_03",
    "name": "Pressure ulcer rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower rate of hospital-acquired pressure ulcers
    # (bedsores) is unambiguously better. Pressure ulcers are a
    # preventable harm — they result from inadequate repositioning,
    # nutrition, and skin assessment during hospitalization.
    "unit": "rate",
    # Confirmed: rate per eligible discharges. Numerator and denominator
    # definitions per CMS PSI-90 FactSheet (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often patients developed serious bed sores during their "
        "stay at this hospital, compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Stage 3/4 pressure ulcers are serious adverse events
    # that cause significant patient suffering, can lead to sepsis, and
    # are a recognized marker of nursing care quality.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Pressure ulcer rates have documented moderate SES
    # effects — patients with poorer baseline nutrition, mobility, and
    # skin integrity (correlated with SES) are at higher risk. Hospital
    # staffing levels (which correlate with payer mix) also contribute.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_04 = {
    "measure_id": "PSI_04",
    "name": "Death rate among surgical inpatients with serious treatable complications",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: This measures "failure to rescue" — the rate at which
    # surgical patients who develop a serious complication (pneumonia,
    # DVT, sepsis, etc.) die from that complication. A lower rate means
    # the hospital is better at rescuing patients from complications.
    # Lower is unambiguously better.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often surgical patients who developed a serious but treatable "
        "complication died at this hospital, compared to what would be "
        "expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Death from a treatable complication is one of the most
    # severe adverse events. "Failure to rescue" is a sentinel indicator
    # of hospital safety culture and rapid response capability.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Failure-to-rescue rates have documented moderate SES
    # effects. Hospitals serving disadvantaged populations may have
    # fewer resources for rapid response and ICU capacity.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_06 = {
    "measure_id": "PSI_06",
    "name": "Iatrogenic pneumothorax rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Iatrogenic pneumothorax (lung collapse caused by a
    # medical procedure such as central line insertion or thoracentesis)
    # is a preventable procedural complication. A lower rate is
    # unambiguously better.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often a medical procedure accidentally caused a patient's "
        "lung to collapse at this hospital, compared to what would be "
        "expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Iatrogenic pneumothorax can be life-threatening and
    # requires emergency treatment (chest tube insertion). It is a
    # recognized marker of procedural safety.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Procedural complication rates have a smaller documented
    # SES effect than mortality measures. The primary driver is
    # procedural technique and supervision quality.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_08 = {
    "measure_id": "PSI_08",
    "name": "In-hospital fall-associated fracture rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Falls with resulting fracture during hospitalization
    # are preventable adverse events. A lower rate is unambiguously
    # better. Falls are strongly linked to staffing adequacy and
    # fall prevention protocols.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often patients fell and broke a bone during their stay at "
        "this hospital, compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Hip fractures from in-hospital falls are high-severity
    # events, especially in elderly patients — they significantly
    # increase mortality risk, length of stay, and loss of independence.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Fall rates have moderate SES effects — related to
    # staffing levels and patient population characteristics (frailty,
    # cognitive impairment) that correlate with SES.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_09 = {
    "measure_id": "PSI_09",
    "name": "Postoperative hemorrhage or hematoma rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Postoperative bleeding requiring drainage or
    # reoperation is a preventable surgical complication. A lower rate
    # is unambiguously better.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often surgical patients had serious bleeding after their "
        "operation at this hospital, compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Postoperative hemorrhage requiring return to OR is a
    # serious adverse event that can result in hemodynamic instability,
    # transfusion reactions, and death.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Surgical complication rates have documented moderate
    # SES effects. Primary driver is surgical technique and
    # anticoagulation management.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_10 = {
    "measure_id": "PSI_10",
    "name": "Postoperative acute kidney injury requiring dialysis rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Acute kidney injury severe enough to require dialysis
    # after surgery is a serious preventable complication. A lower rate
    # is unambiguously better.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often surgical patients developed kidney failure requiring "
        "dialysis after their operation at this hospital, compared to "
        "what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Postoperative renal failure requiring dialysis is a
    # life-threatening complication with high associated mortality and
    # risk of permanent renal impairment.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Preoperative renal function (which correlates with SES
    # via diabetes, hypertension prevalence) is a risk factor, but CMS
    # risk adjustment partially accounts for this. Moderate residual
    # SES effect documented.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_11 = {
    "measure_id": "PSI_11",
    "name": "Postoperative respiratory failure rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Postoperative respiratory failure (requiring prolonged
    # mechanical ventilation or reintubation) is a serious complication.
    # A lower rate is unambiguously better.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often surgical patients had serious breathing problems "
        "requiring a ventilator after their operation at this hospital, "
        "compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Postoperative respiratory failure is a life-threatening
    # event. Prolonged mechanical ventilation carries high mortality,
    # risk of ventilator-associated pneumonia, and long ICU stays.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Baseline pulmonary function (correlated with smoking
    # rates and occupational exposures, which correlate with SES) is a
    # risk factor. Moderate residual SES effect after clinical risk
    # adjustment.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_12 = {
    "measure_id": "PSI_12",
    "name": "Perioperative pulmonary embolism or deep vein thrombosis rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Perioperative blood clots (PE/DVT) are preventable
    # with appropriate prophylaxis. A lower rate is unambiguously better.
    # This is a direct marker of whether a hospital follows VTE
    # prevention protocols.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often surgical patients developed a blood clot in the lungs "
        "or legs around the time of their operation at this hospital, "
        "compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Pulmonary embolism is a leading cause of preventable
    # in-hospital death. PE can be fatal within hours if unrecognized.
    "ses_sensitivity": "MODERATE",
    # Reasoning: VTE prophylaxis is a process-of-care measure at its
    # core — adherence to protocols is the primary driver. Moderate SES
    # effect documented via patient mobility (early ambulation) and
    # length-of-stay patterns.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_13 = {
    "measure_id": "PSI_13",
    "name": "Postoperative sepsis rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Postoperative sepsis (bloodstream infection after
    # surgery) is a serious and often preventable complication. A lower
    # rate is unambiguously better. Sepsis carries high mortality and is
    # a key marker of infection control and surgical site management.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often surgical patients developed a serious bloodstream "
        "infection after their operation at this hospital, compared to "
        "what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Sepsis is a life-threatening condition with mortality
    # rates of 15–30% even with treatment. Postoperative sepsis is a
    # recognized Never Event indicator.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Infection risk has documented moderate SES effects —
    # baseline immune function, diabetes prevalence, and nutritional
    # status (which correlate with SES) affect susceptibility. Hospital
    # infection control practices are the primary modifiable factor.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_14 = {
    "measure_id": "PSI_14",
    "name": "Postoperative wound dehiscence rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Wound dehiscence (surgical wound reopening) is a
    # preventable complication related to surgical technique, wound
    # closure method, and patient management. A lower rate is
    # unambiguously better.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often a surgical wound reopened after an abdominal or pelvic "
        "operation at this hospital, compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Wound dehiscence requires reoperation, carries
    # significant infection risk, and substantially extends
    # hospitalization and recovery.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Wound healing is affected by nutritional status,
    # diabetes control, and smoking — all correlated with SES. However,
    # surgical technique is the primary modifiable factor.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

PSI_15 = {
    "measure_id": "PSI_15",
    "name": "Abdominopelvic accidental puncture or laceration rate",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Accidental puncture or laceration of an organ during
    # abdominal or pelvic surgery is a preventable procedural
    # complication. A lower rate is unambiguously better.
    "unit": "rate",
    # Confirmed: rate per eligible discharges (docs/psi90-FactSheet.txt).
    "plain_language": (
        "How often a surgeon accidentally cut or punctured an organ "
        "during an abdominal or pelvic operation at this hospital, "
        "compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Accidental organ injury during surgery can cause
    # hemorrhage, peritonitis, or damage requiring additional surgery.
    # It is a direct marker of surgical safety.
    "ses_sensitivity": "MODERATE",
    # Reasoning: This is primarily a procedural technique measure.
    # Patient SES has minimal direct effect on whether an accidental
    # laceration occurs. Classified MODERATE (not LOW) because hospital
    # resource constraints (surgical volume, supervision, technology)
    # that correlate with payer mix may contribute.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Patient Safety Indicator — Composite (1)
#
# PSI_90 is a weighted composite of the individual PSI measures above.
# It uses an observed-to-expected ratio where 1.0 = national expected
# rate.
#
# Note: PSI_90 uses "No Different Than the National Value" phrasing
# in compared_to_national (not "Rate"). The denominator field is
# "Not Applicable" because composites have no single patient count.
# ─────────────────────────────────────────────────────────────────────

PSI_90 = {
    "measure_id": "PSI_90",
    "name": "CMS Medicare PSI 90: Patient safety and adverse events composite",
    "group": "SAFETY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: PSI_90 is an observed-to-expected ratio. A value below
    # 1.0 means fewer adverse events than expected; a value above 1.0
    # means more. Lower is unambiguously better. This is the primary
    # composite patient safety measure used by CMS for hospital
    # comparison and payment programs (HACRP).
    "unit": "ratio",
    # PSI_90 is an O/E composite ratio. 1.0 = national expected rate.
    # This is distinct from the individual PSI measures which are rates.
    "plain_language": (
        "An overall score combining multiple patient safety measures to "
        "show whether this hospital had more or fewer serious "
        "complications than expected, where a score below 1.0 is better."
    ),
    "tail_risk_flag": True,
    # Reasoning: PSI_90 aggregates the most serious preventable adverse
    # events. It is the composite used in the Hospital-Acquired Condition
    # Reduction Program (HACRP) to determine payment penalties.
    "ses_sensitivity": "MODERATE",
    # Reasoning: As a composite of the individual PSIs above, PSI_90
    # inherits their moderate SES sensitivity. CMS uses PSI_90 in HACRP
    # without SES adjustment, which has been criticized in published
    # literature (Rajaram et al., 2015). The effect is documented but
    # smaller than for mortality/readmission measures.
    # AHRQ PSI methodology uses hierarchical models with signal-to-noise
    # reliability adjustment — classified as HGLM.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Summary: All 20 measures, Complications and Deaths (ynj2-r877)
# ─────────────────────────────────────────────────────────────────────
#
# MEASURE_REGISTRY_COMPLICATIONS_DEATHS = [
#     MORT_30_AMI, MORT_30_CABG, MORT_30_COPD, MORT_30_HF, MORT_30_PN,
#     MORT_30_STK, HYBRID_HWM, COMP_HIP_KNEE,
#     PSI_03, PSI_04, PSI_06, PSI_08, PSI_09, PSI_10, PSI_11, PSI_12,
#     PSI_13, PSI_14, PSI_15, PSI_90,
# ]
#
# Outstanding TODOs before these entries are finalized:
#   1. RESOLVED: PSI unit confirmed as rate per eligible discharges.
#      Source: CMS PSI-90 FactSheet (docs/psi90-FactSheet.txt).
#   2. Confirm MeasureGroup enum values ("MORTALITY", "COMPLICATIONS",
#      "SAFETY") match the database schema enum definition.
#   3. Verify that Hybrid_HWM measure_id casing matches API exactly
#      (confirmed: API uses "Hybrid_HWM" with capital H — this is the
#      only measure_id in this dataset that uses mixed case).
#   4. Cross-reference plain_language text against legal-compliance.md
#      prohibited language list before finalizing.
