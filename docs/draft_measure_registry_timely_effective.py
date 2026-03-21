"""
MEASURE_REGISTRY Draft — Timely and Effective Care (yv7e-xc69)

Drafted: 2026-03-15
Source: scripts/recon/raw_samples/yv7e-xc69.json (1000 rows, 10 pages)
Phase 0 reference: docs/phase_0_findings.md §3 (Timely and Effective Care)

30 distinct measure_id values confirmed against live CMS API.

This is the most heterogeneous dataset — measures span ED wait times,
treatment compliance rates, harm events, vaccination, and nutrition
screening. Direction, unit, tail_risk, and SES sensitivity vary by
measure and each is reasoned individually below.

Key schema note (AMB-5):
    EDV (Emergency Department Volume) carries a TEXT score ("very high",
    "high", etc.) — not a numeric value. Cannot be stored in Decimal
    score column. Requires score_text column or equivalent. See
    docs/pipeline_decisions.md.

Reporting period: Varies by measure — see CMS refresh schedule in
phase_0_findings.md §3.

Field name note: API uses `_condition` (leading underscore) — must
strip in ingest layer.

CI methodology classification:
    This dataset contains the most heterogeneous mix of measure types.
    CI availability varies significantly by measure.

    UNADJUSTED PROCESS MEASURES (CI CALCULABLE from published data):
        OP_22, OP_23, SEP_1, SEP_SH_3HR, SEP_SH_6HR, SEV_SEP_3HR,
        SEV_SEP_6HR, STK_02, STK_03, STK_05, VTE_1, VTE_2, OP_40,
        IMM_3, OP_29, OP_31
        risk_adjustment_model: NONE. These are raw compliance/percentage
        rates with no risk adjustment.
        cms_ci_published: False. T&E dataset does not include CI fields.
        numerator_denominator_published: True. CMS publishes score (rate)
        and sample (denominator). Numerator derivable as score * sample / 100.
        CI calculability: CALCULABLE via standard binomial proportion CI.

    CATEGORICAL MEASURE (CI NOT APPLICABLE):
        EDV
        risk_adjustment_model: NONE. Categorical volume classification.
        cms_ci_published: False.
        numerator_denominator_published: False.
        CI calculability: NOT APPLICABLE (categorical text values).

    MEDIAN-BASED MEASURES (CI NOT CALCULABLE from published data):
        OP_18a, OP_18b, OP_18c, OP_18d
        risk_adjustment_model: NONE. Unadjusted medians.
        cms_ci_published: False.
        numerator_denominator_published: False. CMS publishes sample size
        but CI for a median requires the raw data distribution, not just
        the median and N.
        CI calculability: NOT CALCULABLE from published summary statistics.

    eCQM HOSPITAL HARM MEASURES (CONFIRMED RATIO eCQMs):
        HH_HYPER, HH_HYPO, HH_ORAE
        risk_adjustment_model: NONE. Confirmed (2026-03-18) as unadjusted
        ratio eCQMs — no risk adjustment applied.
        cms_ci_published: False.
        numerator_denominator_published: True. Confirmed (2026-03-18) against
        live API — `score` and `sample` fields populated for reporting
        facilities.

        RESOLVED (2026-03-18): Score interpretation confirmed from CMS eCQM
        technical specification (CMS871 for HH_HYPER):
          - score = percentage (ratio of event-days to eligible-days)
          - sample = denominator in PATIENT-DAYS (not patients)
          - numerator = event-days (derivable as score * sample / 100)

        IMPORTANT: These are patient-day-based ratio eCQMs, not patient-
        encounter proportions. The denominator counts eligible days of
        hospitalization (excluding first 24 hours). The numerator counts
        days with a qualifying event (e.g., glucose >= 200 mg/dL for
        HH_HYPER). Patient-days within the same hospitalization are
        correlated — the Beta-Binomial independence assumption does NOT
        hold. Do NOT calculate credible intervals for these measures.

        Credible interval: NOT APPLICABLE. Patient-day correlation violates
        the independence assumption required for Beta-Binomial. Display the
        point estimate with sample size (patient-days) context only.

        Many facilities report "Not Available" with footnote 5 (likely eCQM
        reporting threshold not met). These are suppressed, not zero.

    eCQM SAFE USE OF OPIOIDS:
        SAFE_USE_OF_OPIOIDS
        risk_adjustment_model: NONE. Confirmed (2026-03-18) as unadjusted.
        cms_ci_published: False.
        numerator_denominator_published: True. score and sample populated.
        REVIEW_NEEDED: Confirm whether SAFE_USE_OF_OPIOIDS is patient-day-
        based (like HH measures) or patient-encounter-based. If patient-
        encounter-based, Beta-Binomial credible interval is applicable.
        If patient-day-based, same restriction as HH measures applies.

    eCQM GMCS MEASURES — REMOVED (2026-03-18):
        GMCS and 4 sub-components removed from scope. Near-universal "Not
        Available" in live API data. Process measures (tail_risk_flag = False)
        with no bearing on safety or outcome coverage. See removal note in
        measure entries section below.
"""

# ─────────────────────────────────────────────────────────────────────
# Emergency Department Volume (1)
# ─────────────────────────────────────────────────────────────────────

EDV = {
    "measure_id": "EDV",
    "name": "Emergency department volume",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": None,
    # DECISION (2026-03-15): EDV has NO direction. It is a volume
    # classification ("very high", "high", "medium", "low"), not a
    # quality measure. Higher volume is not inherently better or worse.
    # CMS includes it in the T&E dataset as context for ED wait time
    # interpretation, not as a performance indicator.
    #
    # SCHEMA IMPLICATION: The measure_direction enum only supports
    # LOWER_IS_BETTER / HIGHER_IS_BETTER. EDV must be stored with a
    # NULL direction in the measures reference table. The direction
    # column must be nullable to accommodate this. EDV must be excluded
    # from all benchmarking, color coding, and trend analysis.
    # The display layer should present EDV as informational context
    # alongside the OP-18a/b/c/d wait time measures.
    "unit": "category",
    # Categorical text values: "very high", "high", "medium", "low".
    # Cannot be stored in numeric_value column. Requires score_text
    # column per AMB-5 decision.
    "plain_language": (
        "Whether this hospital's emergency department sees a very high, "
        "high, medium, or low number of patients."
    ),
    "tail_risk_flag": False,
    # Reasoning: Volume is a contextual measure, not a patient safety
    # indicator. It does not measure adverse events.
    "ses_sensitivity": "LOW",
    # Reasoning: ED volume is driven by geography, population density,
    # and hospital size — not directly by patient SES mix.
    "risk_adjustment_model": "NONE",  # Categorical classification, not a rate
    "cms_ci_published": False,
    "numerator_denominator_published": False,  # Categorical; CI not applicable
}


# ─────────────────────────────────────────────────────────────────────
# ED Wait Time Measures (4)
#
# Median time in minutes patients spend in the ED. Lower wait times
# are better — prolonged ED stays are associated with worse outcomes,
# especially for conditions requiring time-sensitive treatment (STEMI,
# stroke, sepsis).
# ─────────────────────────────────────────────────────────────────────

OP_18A = {
    "measure_id": "OP_18a",
    "name": (
        "Average (median) time all patients spent in the emergency "
        "department before leaving"
    ),
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Shorter ED stays mean patients are evaluated,
    # treated, and either admitted or discharged more efficiently.
    # Prolonged ED boarding is associated with increased mortality,
    # medication errors, and patient dissatisfaction.
    "unit": "minutes",
    "plain_language": (
        "The typical number of minutes all patients spent in this "
        "hospital's emergency department before leaving."
    ),
    "tail_risk_flag": False,
    # Reasoning: ED wait time is a timeliness/efficiency measure.
    # While prolonged waits can contribute to adverse outcomes, the
    # measure itself does not capture mortality, complications, or
    # infections. It is a process measure, not an outcome measure.
    "ses_sensitivity": "LOW",
    # Reasoning: ED wait times are primarily driven by hospital
    # capacity, staffing, and patient volume. Patient SES does not
    # substantially affect median wait times at a given facility.
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": False,  # Median-based; CI not calculable from summary stats
}

OP_18B = {
    "measure_id": "OP_18b",
    "name": (
        "Average (median) time patients spent in the emergency "
        "department before leaving from the visit — patients admitted"
    ),
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Same as OP_18a — shorter time for admitted patients
    # specifically. Admitted patients waiting in the ED (boarding)
    # is particularly dangerous.
    "unit": "minutes",
    "plain_language": (
        "The typical number of minutes patients who were admitted to "
        "this hospital spent waiting in the emergency department."
    ),
    "tail_risk_flag": False,
    # Reasoning: Process/timeliness measure.
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": False,  # Median-based; CI not calculable from summary stats
}

OP_18C = {
    "measure_id": "OP_18c",
    "name": (
        "Average (median) time patients spent in the emergency "
        "department before leaving from the visit — patients discharged"
    ),
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Same as OP_18a — shorter time for discharged patients.
    "unit": "minutes",
    "plain_language": (
        "The typical number of minutes patients who were sent home "
        "spent in this hospital's emergency department."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": False,  # Median-based; CI not calculable from summary stats
}

OP_18D = {
    "measure_id": "OP_18d",
    "name": (
        "Average (median) time transfer patients spent in the emergency "
        "department before leaving"
    ),
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Transfer patients are being sent to another facility
    # (often a higher-acuity center). Delays in transfer can be
    # life-threatening for stroke, STEMI, and trauma patients.
    "unit": "minutes",
    "plain_language": (
        "The typical number of minutes patients who were transferred "
        "to another hospital spent waiting in this hospital's "
        "emergency department."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": False,  # Median-based; CI not calculable from summary stats
}


# ─────────────────────────────────────────────────────────────────────
# ED Process Measures (2)
# ─────────────────────────────────────────────────────────────────────

OP_22 = {
    "measure_id": "OP_22",
    "name": "Left before being seen",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Patients who leave the ED without being seen (LWBS)
    # may have urgent conditions that go untreated. A lower LWBS rate
    # means the ED is managing throughput well enough that patients
    # are willing to wait. Higher LWBS rates are associated with
    # missed diagnoses and delayed treatment.
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who left this hospital's emergency "
        "department without being seen by a doctor or other provider."
    ),
    "tail_risk_flag": False,
    # Reasoning: Process/efficiency measure. While LWBS can lead to
    # adverse outcomes for individual patients, the measure itself
    # captures a process failure, not a direct adverse event.
    "ses_sensitivity": "MODERATE",
    # Reasoning: LWBS rates are affected by patient factors — patients
    # without regular primary care (correlated with SES) are more
    # likely to use the ED for non-emergent conditions AND more likely
    # to leave if waits are long. Published literature shows moderate
    # SES effects on LWBS rates.
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

OP_23 = {
    "measure_id": "OP_23",
    "name": "Head CT results",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: This measures the percentage of stroke patients who
    # received head CT/MRI results within 45 minutes of arrival.
    # For acute stroke, time-to-imaging is critical — CT/MRI determines
    # whether thrombolytic therapy (tPA) is appropriate. A higher
    # percentage meeting the 45-minute benchmark is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who came to the emergency department "
        "with stroke symptoms who received brain scan results within "
        "45 minutes of arrival."
    ),
    "tail_risk_flag": True,
    # Reasoning: Delayed stroke imaging directly affects eligibility
    # for clot-dissolving treatment. This is a time-critical safety
    # measure — delays can result in permanent brain damage or death.
    "ses_sensitivity": "LOW",
    # Reasoning: Imaging turnaround time is driven by hospital radiology
    # capacity and stroke protocols, not patient SES.
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}


# ─────────────────────────────────────────────────────────────────────
# Hospital Harm Measures (3)
#
# These measure preventable harm events during hospitalization.
# All are LOWER_IS_BETTER (fewer harm events = better).
# All are tail_risk_flag = True (serious adverse events).
# ─────────────────────────────────────────────────────────────────────

HH_HYPER = {
    "measure_id": "HH_HYPER",
    "name": "Hospital Harm - Severe Hyperglycemia",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Severe hyperglycemia (dangerously high blood sugar)
    # during hospitalization is a preventable harm event caused by
    # inadequate glucose monitoring and insulin management. A lower
    # rate is unambiguously better.
    "unit": "percent",
    # TODO: Confirm unit — rate per 1,000 patient-days or percentage.
    # Verify from CMS technical specifications.
    "plain_language": (
        "How often patients at this hospital experienced dangerously "
        "high blood sugar levels during their stay."
    ),
    "tail_risk_flag": True,
    # Reasoning: Severe hyperglycemia increases infection risk, impairs
    # wound healing, and is associated with increased mortality in
    # hospitalized patients. It is a recognized patient safety event.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Diabetes prevalence and baseline glucose control
    # (both correlated with SES) affect the at-risk population.
    # However, in-hospital glucose management is primarily a process-
    # of-care measure.
    # CONFIRMED (2026-03-18): Raw rate eCQM, no risk adjustment.
    # Ratio eCQM: score = % of event-days / eligible-days, sample = patient-days.
    # Credible interval NOT APPLICABLE — patient-days are correlated within
    # hospitalizations, violating Beta-Binomial independence assumption.
    "risk_adjustment_model": "NONE",  # Confirmed raw rate (2026-03-18)
    "cms_ci_published": False,
    "numerator_denominator_published": True,  # Confirmed 2026-03-18: score=% of event-days, sample=patient-days
}

HH_HYPO = {
    "measure_id": "HH_HYPO",
    "name": "Hospital Harm - Severe Hypoglycemia",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Severe hypoglycemia (dangerously low blood sugar)
    # during hospitalization is a preventable harm event caused by
    # medication errors (insulin overdose, inadequate monitoring).
    # A lower rate is unambiguously better.
    "unit": "percent",
    # TODO: Confirm unit — same as HH_HYPER.
    "plain_language": (
        "How often patients at this hospital experienced dangerously "
        "low blood sugar levels during their stay."
    ),
    "tail_risk_flag": True,
    # Reasoning: Severe hypoglycemia can cause seizures, loss of
    # consciousness, cardiac arrhythmias, and death. It is one of
    # the most common preventable medication errors.
    "ses_sensitivity": "MODERATE",
    # Reasoning: Same basis as HH_HYPER.
    # CONFIRMED (2026-03-18): Raw rate eCQM, no risk adjustment.
    # CI is CALCULABLE if numerator/denominator (sample) are published.
    # Ratio eCQM: score = % of event-days / eligible-days, sample = patient-days.
    # Credible interval NOT APPLICABLE — patient-days are correlated within
    # hospitalizations, violating Beta-Binomial independence assumption.
    "risk_adjustment_model": "NONE",  # Confirmed raw rate (2026-03-18)
    "cms_ci_published": False,
    "numerator_denominator_published": True,  # Confirmed 2026-03-18: score=% of event-days, sample=patient-days
}

HH_ORAE = {
    "measure_id": "HH_ORAE",
    "name": "Hospital Harm - Opioid Related Adverse Events",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Opioid-related adverse events (respiratory depression,
    # oversedation, naloxone administration) during hospitalization are
    # preventable harm events. A lower rate is unambiguously better.
    "unit": "percent",
    # TODO: Confirm unit — same as HH_HYPER.
    "plain_language": (
        "How often patients at this hospital experienced serious side "
        "effects from opioid pain medications during their stay, such "
        "as difficulty breathing."
    ),
    "tail_risk_flag": True,
    # Reasoning: Opioid-related respiratory depression is a leading
    # cause of preventable in-hospital death. Naloxone rescue events
    # indicate near-fatal oversedation.
    "ses_sensitivity": "LOW",
    # Reasoning: In-hospital opioid adverse events are driven by
    # prescribing practices and monitoring protocols, not patient SES.
    # Baseline opioid tolerance varies, but hospital dosing protocols
    # should account for this.
    # CONFIRMED (2026-03-18): Raw rate eCQM, no risk adjustment.
    # CI is CALCULABLE if numerator/denominator (sample) are published.
    # Ratio eCQM: score = % of event-days / eligible-days, sample = patient-days.
    # Credible interval NOT APPLICABLE — patient-days are correlated within
    # hospitalizations, violating Beta-Binomial independence assumption.
    "risk_adjustment_model": "NONE",  # Confirmed raw rate (2026-03-18)
    "cms_ci_published": False,
    "numerator_denominator_published": True,  # Confirmed 2026-03-18: score=% of event-days, sample=patient-days
}


# ─────────────────────────────────────────────────────────────────────
# Safe Use of Opioids (1)
# ─────────────────────────────────────────────────────────────────────

SAFE_USE_OF_OPIOIDS = {
    "measure_id": "SAFE_USE_OF_OPIOIDS",
    "name": "Safe Use of Opioids - Concurrent Prescribing",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: This measures the percentage of patients who received
    # concurrent opioid prescriptions (multiple opioids or opioid +
    # benzodiazepine). Concurrent prescribing increases overdose risk.
    # A lower rate is unambiguously better.
    "unit": "percent",
    "plain_language": (
        "The percentage of patients at this hospital who were given "
        "multiple opioid prescriptions at the same time, which "
        "increases the risk of overdose."
    ),
    "tail_risk_flag": True,
    # Reasoning: Concurrent opioid prescribing is a leading contributor
    # to opioid overdose deaths. This is a direct patient safety measure.
    "ses_sensitivity": "LOW",
    # Reasoning: Prescribing practices are driven by clinical protocols
    # and provider behavior, not patient SES.
    # CONFIRMED (2026-03-18): Raw rate eCQM, no risk adjustment.
    # score and sample populated in API.
    # REVIEW_NEEDED: Confirm whether this is patient-day-based (like HH
    # measures) or patient-encounter-based. If encounter-based, Beta-Binomial
    # credible interval is applicable. If day-based, same restriction as HH.
    "risk_adjustment_model": "NONE",  # Confirmed raw rate (2026-03-18)
    "cms_ci_published": False,
    "numerator_denominator_published": True,  # Confirmed 2026-03-18: score+sample populated; unit basis TBD
}


# ─────────────────────────────────────────────────────────────────────
# Sepsis Treatment Measures (5)
#
# Compliance rates with evidence-based sepsis treatment bundles.
# Higher compliance is better — sepsis is time-critical and each
# hour of delayed treatment increases mortality.
# ─────────────────────────────────────────────────────────────────────

SEP_1 = {
    "measure_id": "SEP_1",
    "name": "Appropriate care for severe sepsis and septic shock",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: This is the overall sepsis bundle compliance rate.
    # A higher percentage of patients receiving all required sepsis
    # treatment elements within the required timeframes is better.
    # Sepsis treatment delays directly increase mortality.
    "unit": "percent",
    "plain_language": (
        "The percentage of patients with severe sepsis or septic shock "
        "who received all recommended treatments within the required "
        "timeframes at this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Sepsis kills ~270,000 Americans per year. Treatment
    # bundle compliance directly affects survival. Non-compliance is
    # a serious patient safety failure.
    "ses_sensitivity": "LOW",
    # Reasoning: Sepsis bundle compliance is a process measure driven
    # by hospital protocols, not patient SES.
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

SEP_SH_3HR = {
    "measure_id": "SEP_SH_3HR",
    "name": "Septic Shock 3-Hour Bundle",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: Higher compliance with the 3-hour septic shock bundle
    # (blood cultures, lactate, broad-spectrum antibiotics within 3
    # hours) is better. These are the most time-critical interventions.
    "unit": "percent",
    "plain_language": (
        "The percentage of septic shock patients who received critical "
        "treatments — blood tests, antibiotics — within 3 hours at "
        "this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: 3-hour bundle compliance is the most time-critical
    # sepsis intervention. Each hour of antibiotic delay increases
    # mortality by approximately 7%.
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

SEP_SH_6HR = {
    "measure_id": "SEP_SH_6HR",
    "name": "Septic Shock 6-Hour Bundle",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: Higher compliance with the 6-hour septic shock bundle
    # (vasopressor administration, repeat lactate) is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of septic shock patients who received all "
        "recommended follow-up treatments within 6 hours at this "
        "hospital."
    ),
    "tail_risk_flag": True,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

SEV_SEP_3HR = {
    "measure_id": "SEV_SEP_3HR",
    "name": "Severe Sepsis 3-Hour Bundle",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: Higher compliance with the 3-hour severe sepsis bundle
    # is better. Severe sepsis precedes septic shock — early treatment
    # can prevent progression.
    "unit": "percent",
    "plain_language": (
        "The percentage of severe sepsis patients who received critical "
        "initial treatments within 3 hours at this hospital."
    ),
    "tail_risk_flag": True,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

SEV_SEP_6HR = {
    "measure_id": "SEV_SEP_6HR",
    "name": "Severe Sepsis 6-Hour Bundle",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: Higher compliance with the 6-hour severe sepsis bundle
    # is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of severe sepsis patients who received all "
        "recommended follow-up treatments within 6 hours at this "
        "hospital."
    ),
    "tail_risk_flag": True,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}


# ─────────────────────────────────────────────────────────────────────
# Stroke Treatment Measures (3)
#
# Compliance rates with evidence-based stroke treatments.
# Higher compliance is better.
# ─────────────────────────────────────────────────────────────────────

STK_02 = {
    "measure_id": "STK_02",
    "name": "Discharged on Antithrombotic Therapy",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: Stroke patients should be discharged on antithrombotic
    # medication (aspirin, clopidogrel, or anticoagulant) to prevent
    # recurrent stroke. A higher compliance rate is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of stroke patients who were prescribed blood "
        "clot prevention medication when they left this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Failure to prescribe antithrombotics after stroke
    # directly increases recurrent stroke risk. This is a critical
    # secondary prevention measure.
    "ses_sensitivity": "LOW",
    # Reasoning: Prescribing at discharge is a provider decision,
    # not influenced by patient SES. (Medication adherence post-
    # discharge is SES-dependent, but this measure captures the
    # prescribing act, not adherence.)
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

STK_03 = {
    "measure_id": "STK_03",
    "name": "Anticoagulation Therapy for Atrial Fibrillation/Flutter",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: Stroke patients with atrial fibrillation should be
    # discharged on anticoagulation therapy. AF is the most common
    # cause of cardioembolic stroke. Higher compliance is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of stroke patients with an irregular heartbeat "
        "(atrial fibrillation) who were prescribed blood-thinning "
        "medication when they left this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Untreated AF after stroke carries a 5–15% annual
    # recurrent stroke risk. Anticoagulation reduces this by ~65%.
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

STK_05 = {
    "measure_id": "STK_05",
    "name": "Antithrombotic Therapy by End of Hospital Day 2",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: Early antithrombotic therapy (within 48 hours of
    # admission) for ischemic stroke patients reduces recurrent
    # stroke risk. Higher compliance is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of stroke patients who received blood clot "
        "prevention medication within 2 days of being admitted to "
        "this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: Delayed antithrombotic therapy after ischemic stroke
    # increases recurrent stroke risk during the highest-risk period.
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}


# ─────────────────────────────────────────────────────────────────────
# VTE Prophylaxis Measures (2)
#
# Compliance rates with venous thromboembolism prevention.
# Higher compliance is better.
# ─────────────────────────────────────────────────────────────────────

VTE_1 = {
    "measure_id": "VTE_1",
    "name": "Venous Thromboembolism Prophylaxis",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: VTE prophylaxis (compression devices, anticoagulants)
    # prevents blood clots in hospitalized patients. A higher
    # compliance rate means more patients received appropriate
    # prevention. Higher is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of patients at this hospital who received "
        "appropriate blood clot prevention measures during their stay."
    ),
    "tail_risk_flag": True,
    # Reasoning: Hospital-acquired VTE (DVT/PE) is a leading cause
    # of preventable death. VTE prophylaxis is a core patient safety
    # measure. Non-compliance directly increases PE risk.
    "ses_sensitivity": "LOW",
    # Reasoning: Prophylaxis is a provider protocol decision, not
    # influenced by patient SES.
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

VTE_2 = {
    "measure_id": "VTE_2",
    "name": "Intensive Care Unit Venous Thromboembolism Prophylaxis",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: ICU patients are at highest VTE risk due to
    # immobility, central lines, and critical illness. Higher ICU
    # VTE prophylaxis compliance is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of ICU patients at this hospital who received "
        "appropriate blood clot prevention measures."
    ),
    "tail_risk_flag": True,
    # Reasoning: ICU patients have the highest VTE risk. Prophylaxis
    # failure in the ICU is a critical safety lapse.
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}


# ─────────────────────────────────────────────────────────────────────
# STEMI Treatment (1)
# ─────────────────────────────────────────────────────────────────────

OP_40 = {
    "measure_id": "OP_40",
    "name": "ST-Segment Elevation Myocardial Infarction (STEMI)",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: This measures timely reperfusion therapy for STEMI
    # patients. Higher compliance means more patients received
    # life-saving treatment (PCI or fibrinolysis) within guideline-
    # recommended timeframes. Higher is better.
    # TODO: Confirm exact measure definition — CMS name is ambiguous.
    # It may measure door-to-balloon time compliance or overall STEMI
    # protocol adherence. Verify from CMS technical specifications.
    "unit": "percent",
    "plain_language": (
        "The percentage of heart attack (STEMI) patients who received "
        "emergency artery-opening treatment within the recommended "
        "timeframe at this hospital."
    ),
    "tail_risk_flag": True,
    # Reasoning: STEMI is a time-critical emergency. Every minute of
    # delay in reperfusion increases myocardial damage and mortality.
    # "Time is muscle."
    "ses_sensitivity": "LOW",
    # Reasoning: Reperfusion timing is driven by hospital systems
    # (cath lab activation, transfer protocols), not patient SES.
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}


# ─────────────────────────────────────────────────────────────────────
# Vaccination (1)
# ─────────────────────────────────────────────────────────────────────

IMM_3 = {
    "measure_id": "IMM_3",
    "name": "Healthcare workers given influenza vaccination",
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: A higher percentage of healthcare workers vaccinated
    # against influenza means better protection for vulnerable
    # hospitalized patients. Higher is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of healthcare workers at this hospital who "
        "received an influenza (flu) vaccination."
    ),
    "tail_risk_flag": False,
    # Reasoning: While healthcare worker vaccination protects patients,
    # this is a workforce compliance measure, not a direct patient
    # outcome or adverse event measure.
    "ses_sensitivity": "LOW",
    # Reasoning: Employee vaccination rates are driven by hospital
    # policy (mandatory vs. voluntary), not patient SES.
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}


# ─────────────────────────────────────────────────────────────────────
# Outpatient Procedure Measures (2)
# ─────────────────────────────────────────────────────────────────────

OP_29 = {
    "measure_id": "OP_29",
    "name": (
        "Endoscopy/polyp surveillance: appropriate follow-up interval "
        "for normal colonoscopy"
    ),
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: A higher percentage of patients with a normal
    # colonoscopy receiving a recommended 10-year follow-up interval
    # (not an inappropriately short one) means better adherence to
    # guidelines. Inappropriate early repeat colonoscopy exposes
    # patients to unnecessary risk and cost.
    "unit": "percent",
    "plain_language": (
        "The percentage of patients with a normal colonoscopy result "
        "who were recommended an appropriate follow-up timeframe, "
        "rather than being brought back too soon."
    ),
    "tail_risk_flag": False,
    # Reasoning: Guideline adherence for surveillance intervals is an
    # appropriateness measure, not a direct adverse event.
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

OP_31 = {
    "measure_id": "OP_31",
    "name": (
        "Improvement in Patient's Visual Function within 90 Days "
        "Following Cataract Surgery"
    ),
    "group": "TIMELY_EFFECTIVE_CARE",
    "direction": "HIGHER_IS_BETTER",
    # Reasoning: A higher percentage of patients with improved visual
    # function after cataract surgery means better surgical outcomes.
    # Higher is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of patients whose vision improved within 90 "
        "days after cataract surgery at this hospital."
    ),
    "tail_risk_flag": False,
    # Reasoning: Cataract surgery outcomes are important but are not
    # mortality, serious complications, infections, or acute adverse
    # events. Vision improvement is a quality-of-life outcome measure.
    "ses_sensitivity": "LOW",
    # Reasoning: Surgical technique and patient eye anatomy are the
    # primary drivers. Minimal documented SES effect.
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}


# ─────────────────────────────────────────────────────────────────────
# Global Malnutrition Composite Score — REMOVED (2026-03-18)
#
# GMCS and its 4 sub-components (GMCS_Malnutrition_Screening,
# GMCS_Nutrition_Assessment, GMCS_Malnutrition_Diagnosis_Documented,
# GMCS_Nutritional_Care_Plan) have been removed from scope.
#
# Reason: Near-universal "Not Available" in live API data — almost no
# hospitals report these eCQM measures. Including them would add 5
# measures that are effectively empty for the vast majority of
# facilities. All 5 are process measures (tail_risk_flag = False)
# with no bearing on safety or outcome coverage.
#
# The normalizer must still recognize these measure_ids in the T&E
# dataset and skip them without error (they will appear in API
# responses). Do not create MEASURE_REGISTRY entries for them.
# ─────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────
# Summary: Timely and Effective Care (yv7e-xc69)
# ─────────────────────────────────────────────────────────────────────
#
# MEASURE_REGISTRY entries: 25 measures (30 in dataset, 5 GMCS removed)
#
# Direction summary:
#   NO DIRECTION (1): EDV (contextual volume classification, not quality)
#   LOWER_IS_BETTER (8): OP_18a-d, OP_22, HH_HYPER, HH_HYPO,
#     HH_ORAE, SAFE_USE_OF_OPIOIDS
#   HIGHER_IS_BETTER (13): OP_23, OP_29, OP_31, OP_40, SEP_1,
#     SEP_SH_3HR, SEP_SH_6HR, SEV_SEP_3HR, SEV_SEP_6HR, STK_02,
#     STK_03, STK_05, VTE_1, VTE_2, IMM_3
#
# tail_risk_flag = True (16): HH_HYPER, HH_HYPO, HH_ORAE,
#   SAFE_USE_OF_OPIOIDS, SEP_1, SEP_SH_3HR, SEP_SH_6HR, SEV_SEP_3HR,
#   SEV_SEP_6HR, STK_02, STK_03, STK_05, VTE_1, VTE_2, OP_23, OP_40
#
# Outstanding TODOs:
#   1. EDV direction: RESOLVED — EDV has no direction (NULL). The
#      measure_direction enum column must be nullable. EDV is excluded
#      from benchmarking and trend analysis.
#   2. EDV score_text schema decision (AMB-5) must be resolved before
#      Alembic migration.
#   3. Confirm HH_* score unit (count vs percentage) from CMS eCQM
#      technical specification before normalizer code is written.
#   4. Confirm OP_40 exact measure definition from CMS technical specs.
#   5. Confirm MeasureGroup enum includes "TIMELY_EFFECTIVE_CARE".
