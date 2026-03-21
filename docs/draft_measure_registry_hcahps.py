"""
MEASURE_REGISTRY Draft — HCAHPS Patient Survey (dgck-syfz)

Drafted: 2026-03-15
Source: scripts/recon/raw_samples/dgck-syfz.json (2000 rows, 20 pages)
Phase 0 reference: docs/phase_0_findings.md §4 (HCAHPS Patient Survey)

68 distinct hcahps_measure_id values confirmed against live CMS API.

Note: API uses `hcahps_measure_id` (not `measure_id`) — normalizer must
handle this field name difference.

HCAHPS measures are patient experience survey results. They follow
predictable patterns by suffix and domain. This draft documents the
pattern rules and then lists all 68 entries.

Direction rules by suffix pattern:
    *_A_P     (Always %):        HIGHER_IS_BETTER — more "always" = better
    *_Y_P     (Yes %):           HIGHER_IS_BETTER — more "yes" = better
    *_DY      (Definitely Yes):  HIGHER_IS_BETTER — more "definitely yes" = better
    *_9_10    (Rating 9-10):     HIGHER_IS_BETTER — more high ratings = better
    *_SN_P    (Sometimes/Never): LOWER_IS_BETTER  — fewer "sometimes/never" = better
    *_N_P     (No %):            LOWER_IS_BETTER  — fewer "no" = better
    *_DN      (Definitely Not):  LOWER_IS_BETTER  — fewer "definitely not" = better
    *_0_6     (Rating 0-6):      LOWER_IS_BETTER  — fewer low ratings = better
    *_U_P     (Usually %):       None — NO DIRECTION (see note below)
    *_PY      (Probably Yes):    None — NO DIRECTION (see note below)
    *_7_8     (Rating 7-8):      None — NO DIRECTION (see note below)
    *_LINEAR_SCORE:              HIGHER_IS_BETTER — higher score = better
    *_STAR_RATING:               HIGHER_IS_BETTER — higher star = better

    DECISION (2026-03-15): Middlebox measures have NO direction.
    HCAHPS survey results should be self-explanatory to viewers without
    directional interpretation. The *_U_P (Usually), *_PY (Probably Yes),
    and *_7_8 (Rating 7-8) measures are middle-tier response categories
    that do not have a meaningful quality direction. They are presented
    as informational context alongside the topbox and bottombox measures.
    Direction is NULL in the measures reference table. These measures
    are excluded from all benchmarking, color coding, and trend analysis.

SES sensitivity: LOW for all HCAHPS measures.
    ses-context.md explicitly lists "HCAHPS scores" as LOW sensitivity.
    While patient demographics affect survey response patterns, HCAHPS
    adjusts for patient mix (age, education, language, self-reported
    health status) before reporting. Residual SES effects are minimal.

tail_risk_flag: False for all HCAHPS measures.
    Patient experience is important but does not capture mortality,
    serious complications, infections, or adverse events. HCAHPS
    measures belong in the patient experience section, not the
    primary safety view.

Unit: "percent" for all *_P, *_DY, *_DN, *_PY measures.
    "score" for LINEAR_SCORE measures (0-100 scale).
    "score" for STAR_RATING measures (1-5 scale).

Reporting period: 12 months, refreshed quarterly.

CI methodology classification:
    risk_adjustment_model: PATIENT_MIX_ADJUSTMENT for all HCAHPS measures.
    HCAHPS uses CMS's patient-mix adjustment model (linear regression-based)
    to adjust for respondent characteristics (age, education, language,
    self-reported health status). This is NOT hierarchical modeling.

    cms_ci_published: False for all. CMS does not publish confidence intervals
    for HCAHPS measures in the Provider Data download.

    numerator_denominator_published: False for all. While the number of
    completed surveys is published, the adjusted percentage is not a simple
    binomial proportion — CIs cannot be calculated from published data
    because the patient-mix adjustment model parameters are not published.

    CI calculability: NOT AVAILABLE. HCAHPS CIs are not published by CMS
    and cannot be calculated from the published adjusted percentages.
"""

# ─────────────────────────────────────────────────────────────────────
# All 68 HCAHPS Measures
#
# Organized by domain. Each entry follows the pattern rules above.
# Reasoning for direction, tail_risk, and ses_sensitivity is
# documented once at the domain level (above) and applies to all
# measures in that domain.
# ─────────────────────────────────────────────────────────────────────


# === Domain: Nurse Communication (H_COMP_1) ===

H_COMP_1_A_P = {
    "measure_id": "H_COMP_1_A_P",
    "name": "Patients who reported that their nurses \"Always\" communicated well",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses always "
        "communicated well at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_1_U_P = {
    "measure_id": "H_COMP_1_U_P",
    "name": "Patients who reported that their nurses \"Usually\" communicated well",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses usually "
        "communicated well at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_1_SN_P = {
    "measure_id": "H_COMP_1_SN_P",
    "name": "Patients who reported that their nurses \"Sometimes\" or \"Never\" communicated well",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses sometimes "
        "or never communicated well at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_1_LINEAR_SCORE = {
    "measure_id": "H_COMP_1_LINEAR_SCORE",
    "name": "Nurse communication - linear mean score",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "An overall score for how well nurses communicated with "
        "patients at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_1_STAR_RATING = {
    "measure_id": "H_COMP_1_STAR_RATING",
    "name": "Nurse communication - star rating",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "The star rating (1-5) for how well nurses communicated with "
        "patients at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Doctor Communication (H_COMP_2) ===

H_COMP_2_A_P = {
    "measure_id": "H_COMP_2_A_P",
    "name": "Patients who reported that their doctors \"Always\" communicated well",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors always "
        "communicated well at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_2_U_P = {
    "measure_id": "H_COMP_2_U_P",
    "name": "Patients who reported that their doctors \"Usually\" communicated well",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors usually "
        "communicated well at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_2_SN_P = {
    "measure_id": "H_COMP_2_SN_P",
    "name": "Patients who reported that their doctors \"Sometimes\" or \"Never\" communicated well",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors sometimes "
        "or never communicated well at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_2_LINEAR_SCORE = {
    "measure_id": "H_COMP_2_LINEAR_SCORE",
    "name": "Doctor communication - linear mean score",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "An overall score for how well doctors communicated with "
        "patients at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_2_STAR_RATING = {
    "measure_id": "H_COMP_2_STAR_RATING",
    "name": "Doctor communication - star rating",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "The star rating (1-5) for how well doctors communicated with "
        "patients at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Communication about Medicines (H_COMP_5) ===

H_COMP_5_A_P = {
    "measure_id": "H_COMP_5_A_P",
    "name": "Patients who reported that staff \"Always\" explained about medicines before giving them",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff always explained "
        "their medications before giving them at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_5_U_P = {
    "measure_id": "H_COMP_5_U_P",
    "name": "Patients who reported that staff \"Usually\" explained about medicines before giving them",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff usually explained "
        "their medications before giving them at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_5_SN_P = {
    "measure_id": "H_COMP_5_SN_P",
    "name": "Patients who reported that staff \"Sometimes\" or \"Never\" explained about medicines",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff sometimes or never "
        "explained their medications before giving them at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_5_LINEAR_SCORE = {
    "measure_id": "H_COMP_5_LINEAR_SCORE",
    "name": "Communication about medicines - linear mean score",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "An overall score for how well staff communicated about "
        "medications at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_5_STAR_RATING = {
    "measure_id": "H_COMP_5_STAR_RATING",
    "name": "Communication about medicines - star rating",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "The star rating (1-5) for how well staff communicated about "
        "medications at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Discharge Information (H_COMP_6) ===

H_COMP_6_Y_P = {
    "measure_id": "H_COMP_6_Y_P",
    "name": "Patients who reported YES, they were given information about what to do during recovery",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said they were given "
        "information about what to do during their recovery at home."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_6_N_P = {
    "measure_id": "H_COMP_6_N_P",
    "name": "Patients who reported NO, they were not given information about what to do during recovery",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said they were not given "
        "information about what to do during their recovery at home."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_6_LINEAR_SCORE = {
    "measure_id": "H_COMP_6_LINEAR_SCORE",
    "name": "Discharge information - linear mean score",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "An overall score for how well this hospital provided "
        "discharge information to patients."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_COMP_6_STAR_RATING = {
    "measure_id": "H_COMP_6_STAR_RATING",
    "name": "Discharge information - star rating",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "The star rating (1-5) for how well this hospital provided "
        "discharge information to patients."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Discharge Help (H_DISCH_HELP) ===

H_DISCH_HELP_Y_P = {
    "measure_id": "H_DISCH_HELP_Y_P",
    "name": "Patients who reported YES, they did discuss whether they would need help after discharge",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff discussed whether "
        "they would need help after leaving this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_DISCH_HELP_N_P = {
    "measure_id": "H_DISCH_HELP_N_P",
    "name": "Patients who reported NO, they did not discuss whether they would need help after discharge",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff did not discuss "
        "whether they would need help after leaving this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Symptoms Information (H_SYMPTOMS) ===

H_SYMPTOMS_Y_P = {
    "measure_id": "H_SYMPTOMS_Y_P",
    "name": "Patients who reported YES, they did receive written information about possible symptoms",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said they received written "
        "information about symptoms to watch for after leaving this "
        "hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_SYMPTOMS_N_P = {
    "measure_id": "H_SYMPTOMS_N_P",
    "name": "Patients who reported NO, they did not receive written information about possible symptoms",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said they did not receive "
        "written information about symptoms to watch for after leaving "
        "this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Cleanliness (H_CLEAN) ===

H_CLEAN_HSP_A_P = {
    "measure_id": "H_CLEAN_HSP_A_P",
    "name": "Patients who reported that their room and bathroom were \"Always\" clean",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their room and bathroom "
        "were always clean at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_CLEAN_HSP_U_P = {
    "measure_id": "H_CLEAN_HSP_U_P",
    "name": "Patients who reported that their room and bathroom were \"Usually\" clean",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their room and bathroom "
        "were usually clean at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_CLEAN_HSP_SN_P = {
    "measure_id": "H_CLEAN_HSP_SN_P",
    "name": "Patients who reported that their room and bathroom were \"Sometimes\" or \"Never\" clean",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their room and bathroom "
        "were sometimes or never clean at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_CLEAN_LINEAR_SCORE = {
    "measure_id": "H_CLEAN_LINEAR_SCORE",
    "name": "Cleanliness - linear mean score",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "An overall score for the cleanliness of rooms and bathrooms "
        "at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_CLEAN_STAR_RATING = {
    "measure_id": "H_CLEAN_STAR_RATING",
    "name": "Cleanliness - star rating",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "The star rating (1-5) for the cleanliness of rooms and "
        "bathrooms at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Quietness (H_QUIET) ===

H_QUIET_HSP_A_P = {
    "measure_id": "H_QUIET_HSP_A_P",
    "name": "Patients who reported that the area around their room was \"Always\" quiet at night",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said the area around their "
        "room was always quiet at night at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_QUIET_HSP_U_P = {
    "measure_id": "H_QUIET_HSP_U_P",
    "name": "Patients who reported that the area around their room was \"Usually\" quiet at night",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said the area around their "
        "room was usually quiet at night at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_QUIET_HSP_SN_P = {
    "measure_id": "H_QUIET_HSP_SN_P",
    "name": "Patients who reported that the area around their room was \"Sometimes\" or \"Never\" quiet at night",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said the area around their "
        "room was sometimes or never quiet at night at this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_QUIET_LINEAR_SCORE = {
    "measure_id": "H_QUIET_LINEAR_SCORE",
    "name": "Quietness - linear mean score",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "An overall score for how quiet the hospital was at night."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_QUIET_STAR_RATING = {
    "measure_id": "H_QUIET_STAR_RATING",
    "name": "Quietness - star rating",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "The star rating (1-5) for how quiet the hospital was at night."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Overall Hospital Rating (H_HSP_RATING) ===

H_HSP_RATING_9_10 = {
    "measure_id": "H_HSP_RATING_9_10",
    "name": "Patients who gave their hospital a rating of 9 or 10 (high)",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who gave this hospital a rating "
        "of 9 or 10 out of 10."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_HSP_RATING_7_8 = {
    "measure_id": "H_HSP_RATING_7_8",
    "name": "Patients who gave their hospital a rating of 7 or 8 (medium)",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision) — see note
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who gave this hospital a rating "
        "of 7 or 8 out of 10."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_HSP_RATING_0_6 = {
    "measure_id": "H_HSP_RATING_0_6",
    "name": "Patients who gave their hospital a rating of 6 or lower (low)",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who gave this hospital a rating "
        "of 6 or lower out of 10."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_HSP_RATING_LINEAR_SCORE = {
    "measure_id": "H_HSP_RATING_LINEAR_SCORE",
    "name": "Overall hospital rating - linear mean score",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "An overall score for how patients rated this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_HSP_RATING_STAR_RATING = {
    "measure_id": "H_HSP_RATING_STAR_RATING",
    "name": "Overall hospital rating - star rating",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "The star rating (1-5) for how patients rated this hospital "
        "overall."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Recommend Hospital (H_RECMND) ===

H_RECMND_DY = {
    "measure_id": "H_RECMND_DY",
    "name": "Patients who reported YES, they would definitely recommend the hospital",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said they would definitely "
        "recommend this hospital to friends and family."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_RECMND_PY = {
    "measure_id": "H_RECMND_PY",
    "name": "Patients who reported YES, they would probably recommend the hospital",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said they would probably "
        "recommend this hospital to friends and family."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_RECMND_DN = {
    "measure_id": "H_RECMND_DN",
    "name": "Patients who reported NO, they would probably not or definitely not recommend the hospital",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said they would probably not "
        "or definitely not recommend this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_RECMND_LINEAR_SCORE = {
    "measure_id": "H_RECMND_LINEAR_SCORE",
    "name": "Recommend hospital - linear mean score",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "An overall score for how likely patients would be to "
        "recommend this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_RECMND_STAR_RATING = {
    "measure_id": "H_RECMND_STAR_RATING",
    "name": "Recommend hospital - star rating",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "The star rating (1-5) for how likely patients would be to "
        "recommend this hospital."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Doctor Sub-Questions (H_DOCTOR_EXPLAIN, LISTEN, RESPECT) ===
# These are detailed breakdowns of H_COMP_2 (Doctor Communication).

H_DOCTOR_EXPLAIN_A_P = {
    "measure_id": "H_DOCTOR_EXPLAIN_A_P",
    "name": "Patients who reported that their doctors \"Always\" explained things in a way they could understand",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors always "
        "explained things in a way they could understand."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_DOCTOR_EXPLAIN_U_P = {
    "measure_id": "H_DOCTOR_EXPLAIN_U_P",
    "name": "Patients who reported that their doctors \"Usually\" explained things in a way they could understand",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors usually "
        "explained things in a way they could understand."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_DOCTOR_EXPLAIN_SN_P = {
    "measure_id": "H_DOCTOR_EXPLAIN_SN_P",
    "name": "Patients who reported that their doctors \"Sometimes\" or \"Never\" explained things in a way they could understand",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors sometimes "
        "or never explained things in a way they could understand."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_DOCTOR_LISTEN_A_P = {
    "measure_id": "H_DOCTOR_LISTEN_A_P",
    "name": "Patients who reported that their doctors \"Always\" listened carefully to them",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors always "
        "listened carefully to them."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_DOCTOR_LISTEN_U_P = {
    "measure_id": "H_DOCTOR_LISTEN_U_P",
    "name": "Patients who reported that their doctors \"Usually\" listened carefully to them",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors usually "
        "listened carefully to them."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_DOCTOR_LISTEN_SN_P = {
    "measure_id": "H_DOCTOR_LISTEN_SN_P",
    "name": "Patients who reported that their doctors \"Sometimes\" or \"Never\" listened carefully to them",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors sometimes "
        "or never listened carefully to them."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_DOCTOR_RESPECT_A_P = {
    "measure_id": "H_DOCTOR_RESPECT_A_P",
    "name": "Patients who reported that their doctors \"Always\" treated them with courtesy and respect",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors always "
        "treated them with courtesy and respect."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_DOCTOR_RESPECT_U_P = {
    "measure_id": "H_DOCTOR_RESPECT_U_P",
    "name": "Patients who reported that their doctors \"Usually\" treated them with courtesy and respect",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors usually "
        "treated them with courtesy and respect."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_DOCTOR_RESPECT_SN_P = {
    "measure_id": "H_DOCTOR_RESPECT_SN_P",
    "name": "Patients who reported that their doctors \"Sometimes\" or \"Never\" treated them with courtesy and respect",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their doctors sometimes "
        "or never treated them with courtesy and respect."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Nurse Sub-Questions (H_NURSE_EXPLAIN, LISTEN, RESPECT) ===
# Detailed breakdowns of H_COMP_1 (Nurse Communication).

H_NURSE_EXPLAIN_A_P = {
    "measure_id": "H_NURSE_EXPLAIN_A_P",
    "name": "Patients who reported that their nurses \"Always\" explained things in a way they could understand",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses always "
        "explained things in a way they could understand."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_NURSE_EXPLAIN_U_P = {
    "measure_id": "H_NURSE_EXPLAIN_U_P",
    "name": "Patients who reported that their nurses \"Usually\" explained things in a way they could understand",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses usually "
        "explained things in a way they could understand."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_NURSE_EXPLAIN_SN_P = {
    "measure_id": "H_NURSE_EXPLAIN_SN_P",
    "name": "Patients who reported that their nurses \"Sometimes\" or \"Never\" explained things in a way they could understand",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses sometimes "
        "or never explained things in a way they could understand."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_NURSE_LISTEN_A_P = {
    "measure_id": "H_NURSE_LISTEN_A_P",
    "name": "Patients who reported that their nurses \"Always\" listened carefully to them",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses always "
        "listened carefully to them."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_NURSE_LISTEN_U_P = {
    "measure_id": "H_NURSE_LISTEN_U_P",
    "name": "Patients who reported that their nurses \"Usually\" listened carefully to them",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses usually "
        "listened carefully to them."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_NURSE_LISTEN_SN_P = {
    "measure_id": "H_NURSE_LISTEN_SN_P",
    "name": "Patients who reported that their nurses \"Sometimes\" or \"Never\" listened carefully to them",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses sometimes "
        "or never listened carefully to them."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_NURSE_RESPECT_A_P = {
    "measure_id": "H_NURSE_RESPECT_A_P",
    "name": "Patients who reported that their nurses \"Always\" treated them with courtesy and respect",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses always "
        "treated them with courtesy and respect."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_NURSE_RESPECT_U_P = {
    "measure_id": "H_NURSE_RESPECT_U_P",
    "name": "Patients who reported that their nurses \"Usually\" treated them with courtesy and respect",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses usually "
        "treated them with courtesy and respect."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_NURSE_RESPECT_SN_P = {
    "measure_id": "H_NURSE_RESPECT_SN_P",
    "name": "Patients who reported that their nurses \"Sometimes\" or \"Never\" treated them with courtesy and respect",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said their nurses sometimes "
        "or never treated them with courtesy and respect."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Medication Communication Sub-Questions (H_MED_FOR, H_SIDE_EFFECTS) ===

H_MED_FOR_A_P = {
    "measure_id": "H_MED_FOR_A_P",
    "name": "Patients who reported that when receiving new medication the staff \"Always\" communicated what it was for",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff always told them "
        "what new medications were for."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_MED_FOR_U_P = {
    "measure_id": "H_MED_FOR_U_P",
    "name": "Patients who reported that when receiving new medication the staff \"Usually\" communicated what it was for",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff usually told them "
        "what new medications were for."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_MED_FOR_SN_P = {
    "measure_id": "H_MED_FOR_SN_P",
    "name": "Patients who reported that when receiving new medication the staff \"Sometimes\" or \"Never\" communicated what it was for",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff sometimes or never "
        "told them what new medications were for."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_SIDE_EFFECTS_A_P = {
    "measure_id": "H_SIDE_EFFECTS_A_P",
    "name": "Patients who reported that when receiving new medication the staff \"Always\" discussed possible side effects",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff always told them "
        "about possible side effects of new medications."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_SIDE_EFFECTS_U_P = {
    "measure_id": "H_SIDE_EFFECTS_U_P",
    "name": "Patients who reported that when receiving new medication the staff \"Usually\" discussed possible side effects",
    "group": "PATIENT_EXPERIENCE",
    "direction": None,  # middlebox — no direction (2026-03-15 decision)
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff usually told them "
        "about possible side effects of new medications."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

H_SIDE_EFFECTS_SN_P = {
    "measure_id": "H_SIDE_EFFECTS_SN_P",
    "name": "Patients who reported that when receiving new medication the staff \"Sometimes\" or \"Never\" discussed possible side effects",
    "group": "PATIENT_EXPERIENCE",
    "direction": "LOWER_IS_BETTER",
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who said staff sometimes or never "
        "told them about possible side effects of new medications."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}

# === Domain: Summary Star Rating (H_STAR_RATING) ===

H_STAR_RATING = {
    "measure_id": "H_STAR_RATING",
    "name": "Summary star rating",
    "group": "PATIENT_EXPERIENCE",
    "direction": "HIGHER_IS_BETTER",
    "unit": "score",
    "plain_language": (
        "The overall patient experience star rating (1-5) for this "
        "hospital based on all HCAHPS survey responses."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "PATIENT_MIX_ADJUSTMENT",
    "cms_ci_published": False,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Summary: HCAHPS Patient Survey (dgck-syfz)
# ─────────────────────────────────────────────────────────────────────
#
# MEASURE_REGISTRY entries: 68 measures
# All SES sensitivity: LOW
# All tail_risk_flag: False
# Direction: HIGHER_IS_BETTER (topbox, yes, scores, stars)
#            LOWER_IS_BETTER (bottombox, no, low ratings)
#            None / NO DIRECTION (middlebox: *_U_P, *_PY, *_7_8)
#
# Outstanding TODOs:
#   1. RESOLVED: Middlebox measures have no direction (NULL). Excluded
#      from benchmarking, color coding, and trend analysis.
#   2. Confirm MeasureGroup enum includes "PATIENT_EXPERIENCE".
#   3. Note API field name difference: `hcahps_measure_id` not `measure_id`.
#   4. LINEAR_SCORE and STAR_RATING measures have special suppression
#      encoding — "Not Applicable" is structural absence (not all rows
#      produce these values), NOT suppression. See phase_0_findings.md §4.
#   5. DEC-010: hcahps_linear_mean_value field is discarded per pipeline
#      decision (CMS internal artifact). Confirm this applies to all
#      LINEAR_SCORE measure rows or only to the raw API field.
