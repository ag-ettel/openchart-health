"""
MEASURE_REGISTRY Draft — Unplanned Hospital Visits / Readmissions (632h-zaca)

Drafted: 2026-03-15
Source: scripts/recon/raw_samples/632h-zaca.json (1000 rows, 10 pages)
Phase 0 reference: docs/phase_0_findings.md §7 (Unplanned Hospital Visits)

14 distinct measure_id values confirmed against live CMS API.

Direction reasoning:
    All 14 measures are LOWER_IS_BETTER. Every measure in this dataset
    captures unplanned returns to acute care — readmissions, ED visits,
    or excess hospital days. Fewer unplanned returns is unambiguously
    better. This is definitional.

SES sensitivity reasoning:
    30-day readmission measures (READM_30_*) and the hospital-wide
    readmission measure (Hybrid_HWR) are classified HIGH. This is the
    most well-documented SES-sensitive measure category. Post-discharge
    factors — medication adherence, access to follow-up care, food
    security, housing stability, health literacy — are strongly
    correlated with SES and substantially affect readmission rates.
    CMS risk adjustment for readmissions accounts for clinical factors
    but not patient SES characteristics. This is precisely why HRRP
    penalties have been criticized as disproportionately affecting
    safety-net hospitals.

    References:
    - Joynt & Jha (2013) "Characteristics of Hospitals Receiving
      Penalties Under the HRRP"
    - Bernheim et al. (2016) "Influence of Patient Socioeconomic Status"
    - MedPAC June 2023 chapter on social risk factors
    - ses-context.md explicitly lists "30-day readmissions" as HIGH

    EDAC measures (EDAC_30_*) inherit HIGH — they measure the same
    post-discharge outcomes as READM but in a different unit (days
    instead of events).

    Outpatient measures (OP_32, OP_35_ADM, OP_35_ED, OP_36) are
    classified MODERATE. These measure unplanned visits after outpatient
    procedures. SES effects are documented but smaller than inpatient
    readmissions — outpatient procedures involve shorter episodes and
    less post-discharge complexity.

tail_risk_flag reasoning:
    All 14 measures are tail_risk_flag = True. Unplanned hospital visits
    are adverse events — the patient required emergency or unplanned
    acute care they were not expecting. While readmission rates are
    higher-frequency than mortality events, each individual readmission
    can represent a serious deterioration (another cardiac event, post-
    surgical complication, medication error). The project's strategic
    philosophy states: "Any measure related to adverse events,
    complications, infections, or mortality belongs in the primary view."
    Unplanned hospital visits qualify as adverse events under this
    definition.

Reporting period: 36 months for condition-specific; 12 months for some
outpatient measures. Refreshed annually.

CI methodology classification:
    READM_30_* (6 measures), EDAC_30_* (3 measures), Hybrid_HWR (1 measure):
        risk_adjustment_model: HGLM. CMS uses hierarchical generalized linear
        models for all risk-standardized readmission and EDAC measures. EDAC
        specifically uses a two-part hierarchical model but is classified as
        HGLM here.
        cms_ci_published: True. The 632h-zaca dataset includes lower_estimate
        and higher_estimate fields for these measures.
        numerator_denominator_published: False. The score is a risk-standardized
        rate from the hierarchical model, not a simple numerator/denominator.

    OP_36 (1 measure):
        risk_adjustment_model: HGLM. O/E ratio using hierarchical model.
        cms_ci_published: True. Dataset includes lower/higher estimate fields.
        numerator_denominator_published: False.

    OP_32, OP_35_ADM, OP_35_ED (3 measures):
        risk_adjustment_model: OTHER. Confirmed risk-adjusted (2026-03-18).
        Specific model type not yet documented but confirmed not a raw rate.
        cms_ci_published: True. Confirmed (2026-03-18) against live API —
        lower_estimate and higher_estimate fields are populated for non-
        suppressed rows. Example OP_32: score="12.7", lower_estimate="9.5",
        higher_estimate="17", denominator="234". OP_35_ADM and OP_35_ED
        follow the same pattern.
        numerator_denominator_published: False. A denominator field is
        published but the score is a risk-adjusted rate, not a simple
        numerator/denominator ratio.

    CI calculability:
    - All 14 measures: AVAILABLE (CMS-provided).

compared_to_national normalization note:
    EDAC measures and OP_36 return "Not Available" for compared_to_national
    (they don't carry a national comparison). All READM_30_* and other
    measures use "Rate" phrasing. CMS capitalization is inconsistent
    within this dataset — "Number of Cases Too Small" and "Number of
    cases too small" both appear (see AMB-3 + phase_0_findings §7).
    Normalizer must use case-insensitive matching.
"""

# ─────────────────────────────────────────────────────────────────────
# 30-Day Readmission Measures (6)
#
# Risk-standardized readmission rates (RSRR). CMS calculates these
# using hierarchical logistic regression. Models account for age, sex,
# and comorbidities but NOT patient SES characteristics.
#
# Direction: LOWER_IS_BETTER for all. A lower readmission rate is
# unambiguously better.
# ─────────────────────────────────────────────────────────────────────

READM_30_AMI = {
    "measure_id": "READM_30_AMI",
    "name": "Acute Myocardial Infarction (AMI) 30-Day Readmission Rate",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower 30-day readmission rate after heart attack means
    # fewer patients needed to return to the hospital within 30 days.
    # This reflects better discharge planning, medication management,
    # and follow-up care coordination.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare heart attack patients who had to "
        "return to a hospital within 30 days of leaving this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Readmission after AMI often involves recurrent cardiac
    # events, heart failure exacerbation, or medication complications.
    "ses_sensitivity": "HIGH",
    # Reasoning: 30-day AMI readmission is one of the HRRP penalty
    # conditions. Extensively documented SES sensitivity — post-discharge
    # medication access, follow-up cardiology appointments, and cardiac
    # rehabilitation access are all SES-dependent.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

READM_30_CABG = {
    "measure_id": "READM_30_CABG",
    "name": "Rate of readmission for CABG",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower readmission rate after CABG surgery means fewer
    # patients needed emergency or unplanned care after open-heart
    # surgery.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare patients who had to return to a "
        "hospital within 30 days of coronary artery bypass graft "
        "(open-heart) surgery at this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Post-CABG readmission often involves serious
    # complications — wound infections, cardiac events, or respiratory
    # failure.
    "ses_sensitivity": "HIGH",
    # Reasoning: Same basis as READM_30_AMI. CABG is an HRRP condition.
    # Post-surgical recovery resources (home health, medication access,
    # wound care) are SES-dependent.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

READM_30_COPD = {
    "measure_id": "READM_30_COPD",
    "name": "Rate of readmission for chronic obstructive pulmonary disease (COPD) patients",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower readmission rate for COPD means fewer patients
    # had a COPD exacerbation or respiratory deterioration requiring
    # return to hospital within 30 days.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare COPD patients who had to return to "
        "a hospital within 30 days of leaving this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: COPD readmissions frequently involve respiratory failure
    # requiring mechanical ventilation.
    "ses_sensitivity": "HIGH",
    # Reasoning: COPD readmission is an HRRP condition. Medication
    # adherence (inhalers are expensive), smoking cessation support,
    # and home oxygen access are all SES-dependent. COPD
    # disproportionately affects low-income populations.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

READM_30_HF = {
    "measure_id": "READM_30_HF",
    "name": "Heart failure (HF) 30-Day Readmission Rate",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower readmission rate for heart failure means fewer
    # patients had fluid overload, cardiac decompensation, or other
    # exacerbations requiring return to hospital.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare heart failure patients who had to "
        "return to a hospital within 30 days of leaving this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: HF readmission often involves acute decompensated heart
    # failure, which carries significant mortality risk.
    "ses_sensitivity": "HIGH",
    # Reasoning: Heart failure is the HRRP condition with the highest
    # documented SES sensitivity. Dietary sodium restriction, daily
    # weight monitoring, medication management (diuretics, ACE-I),
    # and access to HF clinics are all heavily SES-dependent.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

READM_30_HIP_KNEE = {
    "measure_id": "READM_30_HIP_KNEE",
    "name": "Rate of readmission after hip/knee replacement",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower readmission rate after elective joint
    # replacement means fewer patients needed to return for surgical
    # complications, infection, or other adverse events.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare patients who had to return to a "
        "hospital within 30 days of an elective hip or knee replacement "
        "at this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Post-arthroplasty readmission can involve prosthetic
    # joint infection, DVT/PE, wound complications, or dislocation.
    "ses_sensitivity": "HIGH",
    # Reasoning: Hip/knee readmission is an HRRP condition. Post-
    # surgical rehabilitation access, home health services, and
    # physical therapy availability are SES-dependent.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

READM_30_PN = {
    "measure_id": "READM_30_PN",
    "name": "Pneumonia (PN) 30-Day Readmission Rate",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower readmission rate for pneumonia means fewer
    # patients had respiratory deterioration or treatment failure
    # requiring return to hospital.
    "unit": "percent",
    "plain_language": (
        "The percentage of Medicare pneumonia patients who had to return "
        "to a hospital within 30 days of leaving this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Pneumonia readmission often involves treatment failure,
    # secondary infection, or respiratory failure.
    "ses_sensitivity": "HIGH",
    # Reasoning: Pneumonia readmission is an HRRP condition. Post-
    # discharge antibiotic adherence, follow-up chest imaging, and
    # home recovery conditions are SES-dependent.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Excess Days in Acute Care (EDAC) Measures (3)
#
# EDAC measures the number of days patients spent in acute care
# (inpatient, ED, observation) within 30 days of discharge BEYOND
# what would be expected. Lower = fewer excess return days = better.
#
# These complement the READM_30_* measures by capturing intensity
# of return care, not just whether a return occurred.
# ─────────────────────────────────────────────────────────────────────

EDAC_30_AMI = {
    "measure_id": "EDAC_30_AMI",
    "name": "Hospital return days for heart attack patients",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Fewer excess days spent in acute care after discharge
    # for heart attack is unambiguously better. A lower number means
    # patients spent fewer days back in hospitals/EDs than expected.
    "unit": "days_per_100",
    # EDAC is reported in days per 100 discharges. Specifically, it
    # expresses the difference between the observed average number of
    # days patients spend in acute care (including ED visits, observation
    # stays, and unplanned readmissions within 30 days) and the expected
    # number of days given the hospital's patient case mix, scaled to
    # 100 discharges. A negative value means fewer excess days than
    # expected; a positive value means more. Confirmed 2026-03-15.
    "plain_language": (
        "The number of extra days per 100 patients that Medicare heart "
        "attack patients spent back in acute care within 30 days of "
        "leaving this hospital, compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Excess days in acute care represent ongoing adverse
    # events — patients are spending more time in hospitals than expected
    # after their initial stay.
    "ses_sensitivity": "HIGH",
    # Reasoning: Inherits HIGH from READM_30_AMI — same post-discharge
    # SES factors drive both readmission events and excess acute care days.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

EDAC_30_HF = {
    "measure_id": "EDAC_30_HF",
    "name": "Hospital return days for heart failure patients",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Same as EDAC_30_AMI — fewer return days is better.
    "unit": "days_per_100",
    # Days per 100 discharges (observed - expected). See EDAC_30_AMI.
    "plain_language": (
        "The number of extra days per 100 patients that Medicare heart "
        "failure patients spent back in acute care within 30 days of "
        "leaving this hospital, compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Same as EDAC_30_AMI.
    "ses_sensitivity": "HIGH",
    # Reasoning: Inherits HIGH from READM_30_HF.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}

EDAC_30_PN = {
    "measure_id": "EDAC_30_PN",
    "name": "Hospital return days for pneumonia patients",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Same as EDAC_30_AMI — fewer return days is better.
    "unit": "days_per_100",
    # Days per 100 discharges (observed - expected). See EDAC_30_AMI.
    "plain_language": (
        "The number of extra days per 100 patients that Medicare "
        "pneumonia patients spent back in acute care within 30 days "
        "of leaving this hospital, compared to what would be expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Same as EDAC_30_AMI.
    "ses_sensitivity": "HIGH",
    # Reasoning: Inherits HIGH from READM_30_PN.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Hospital-Wide Readmission (1)
#
# Hybrid measure using clinical and claims data. Captures readmissions
# across ALL conditions, not limited to specific diagnoses.
# ─────────────────────────────────────────────────────────────────────

HYBRID_HWR = {
    "measure_id": "Hybrid_HWR",
    "name": "Hybrid Hospital-Wide All-Cause Readmission Measure (HWR)",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower hospital-wide readmission rate means fewer
    # patients across all conditions needed to return to hospital within
    # 30 days. This is the broadest readmission measure.
    "unit": "percent",
    "plain_language": (
        "The overall percentage of Medicare patients who had to return "
        "to a hospital within 30 days of leaving this hospital, across "
        "all conditions, adjusted for how sick the patients were."
    ),
    "tail_risk_flag": True,
    # Reasoning: Hospital-wide readmission captures all unplanned
    # returns — the broadest adverse event signal.
    "ses_sensitivity": "HIGH",
    # Reasoning: Hospital-wide readmission inherits the HIGH SES
    # sensitivity of the condition-specific readmission measures it
    # encompasses.
    "risk_adjustment_model": "HGLM",
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Outpatient Unplanned Visit Measures (4)
#
# These measure unplanned returns after outpatient procedures or
# treatment. Direction is LOWER_IS_BETTER for all — fewer unplanned
# returns is better.
# ─────────────────────────────────────────────────────────────────────

OP_32 = {
    "measure_id": "OP_32",
    "name": "Rate of unplanned hospital visits after colonoscopy (per 1,000 colonoscopies)",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower rate of unplanned visits after colonoscopy
    # means fewer patients experienced complications (perforation,
    # bleeding, post-polypectomy syndrome) requiring emergency care.
    "unit": "rate",
    # Per 1,000 colonoscopies — explicit in measure name.
    "plain_language": (
        "How often patients had to make an unplanned visit to a hospital "
        "or emergency room after having a colonoscopy at this hospital, "
        "per 1,000 colonoscopies."
    ),
    "tail_risk_flag": True,
    # Reasoning: Unplanned hospital visits after colonoscopy can involve
    # bowel perforation (a life-threatening surgical emergency),
    # significant bleeding, or post-procedural infection.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Outpatient procedure complications have a smaller
    # documented SES effect than inpatient readmissions. The procedure
    # itself is the primary risk determinant. Post-procedure access to
    # follow-up care has a moderate SES component.
    # CONFIRMED (2026-03-18): Risk-adjusted measure. CMS publishes CI
    # bounds (lower_estimate, higher_estimate) in the API. Verified against
    # live data: score="12.7", lower_estimate="9.5", higher_estimate="17",
    # denominator="234".
    "risk_adjustment_model": "OTHER",  # Risk-adjusted; confirmed 2026-03-18
    "cms_ci_published": True,  # Confirmed populated in live API 2026-03-18
    "numerator_denominator_published": False,
}

OP_35_ADM = {
    "measure_id": "OP_35_ADM",
    "name": "Rate of inpatient admissions for patients receiving outpatient chemotherapy",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower rate of unplanned inpatient admissions during
    # outpatient chemotherapy means fewer patients experienced severe
    # treatment toxicity, infection (neutropenic fever), or other
    # complications requiring hospitalization.
    "unit": "percent",
    "plain_language": (
        "How often patients receiving outpatient chemotherapy at this "
        "hospital had to be admitted to the hospital for an unplanned "
        "stay."
    ),
    "tail_risk_flag": True,
    # Reasoning: Unplanned hospitalization during chemotherapy often
    # involves neutropenic sepsis, severe dehydration, or organ toxicity
    # — all high-severity events.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Chemotherapy toxicity management depends partly on
    # patient access to supportive care (anti-emetics, hydration,
    # growth factors) and timely access to urgent evaluation — both
    # SES-dependent. But treatment protocol adherence by the oncology
    # team is the primary driver.
    # CONFIRMED (2026-03-18): Risk-adjusted measure. CMS publishes CI
    # bounds (lower_estimate, higher_estimate) in the API. Same pattern
    # as OP_32 — verified against live data.
    "risk_adjustment_model": "OTHER",  # Risk-adjusted; confirmed 2026-03-18
    "cms_ci_published": True,  # Confirmed populated in live API 2026-03-18
    "numerator_denominator_published": False,
}

OP_35_ED = {
    "measure_id": "OP_35_ED",
    "name": "Rate of emergency department (ED) visits for patients receiving outpatient chemotherapy",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower rate of ED visits during outpatient
    # chemotherapy means fewer patients needed emergency care for
    # treatment side effects or complications.
    "unit": "percent",
    "plain_language": (
        "How often patients receiving outpatient chemotherapy at this "
        "hospital had to visit an emergency room."
    ),
    "tail_risk_flag": True,
    # Reasoning: ED visits during chemotherapy indicate treatment
    # complications — fever, pain, dehydration, or other acute events
    # requiring emergency evaluation.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Same basis as OP_35_ADM. ED use during chemotherapy
    # can also reflect lack of access to urgent oncology clinic
    # appointments (patients go to ED when they can't reach their
    # oncologist), which is partly SES-dependent.
    # CONFIRMED (2026-03-18): Risk-adjusted measure. CMS publishes CI
    # bounds (lower_estimate, higher_estimate) in the API. Same pattern
    # as OP_32 — verified against live data.
    "risk_adjustment_model": "OTHER",  # Risk-adjusted; confirmed 2026-03-18
    "cms_ci_published": True,  # Confirmed populated in live API 2026-03-18
    "numerator_denominator_published": False,
}

OP_36 = {
    "measure_id": "OP_36",
    "name": "Ratio of unplanned hospital visits after hospital outpatient surgery",
    "group": "READMISSIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: A lower ratio of unplanned visits after outpatient
    # surgery means fewer patients experienced post-surgical
    # complications requiring emergency care. Note: CMS reports this
    # as a ratio (O/E), not a raw rate.
    "unit": "ratio",
    # O/E ratio where 1.0 = national expected rate.
    "plain_language": (
        "How this hospital's rate of unplanned hospital visits after "
        "outpatient surgery compares to what would be expected, where "
        "a number below 1.0 means fewer unplanned visits than expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: Unplanned returns after outpatient surgery can involve
    # surgical site complications, bleeding, or infection requiring
    # emergency treatment.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Outpatient surgery complication rates have moderate
    # SES effects. Post-operative care access and recovery conditions
    # are partly SES-dependent, but surgical technique is the primary
    # quality driver.
    "risk_adjustment_model": "HGLM",  # O/E ratio using hierarchical model
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Summary: Unplanned Hospital Visits / Readmissions (632h-zaca)
# ─────────────────────────────────────────────────────────────────────
#
# MEASURE_REGISTRY entries: 14 measures
#   - 6 READM_30_* (condition-specific 30-day readmission rates)
#   - 3 EDAC_30_* (excess days in acute care)
#   - 1 Hybrid_HWR (hospital-wide readmission)
#   - 4 OP_* (outpatient unplanned visit measures)
#
# Outstanding TODOs:
#   1. RESOLVED: EDAC unit is days per 100 discharges (observed minus
#      expected acute care days, scaled to 100 discharges). Confirmed
#      2026-03-15.
#   2. Confirm MeasureGroup enum includes "READMISSIONS".
#   3. Note that Hybrid_HWR uses mixed-case measure_id (capital H) —
#      same pattern as Hybrid_HWM in Complications dataset.
#   4. The `number_of_patients` and `number_of_patients_returned` fields
#      are specific to this dataset (EDAC measures). Decide where to
#      store them — `sample_size` and `denominator`, or separate columns.
#      Document in pipeline_decisions.md.
