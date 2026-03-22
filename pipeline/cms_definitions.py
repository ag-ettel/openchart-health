"""
CMS verbatim measure definitions sourced from official CMS data dictionaries.

DEC-037: These are the legally authoritative descriptions — they must not be
paraphrased, shortened, or modified. They establish the republication chain.

Source documents:
  - docs/HOSPITAL_Data_Dictionary.txt (CMS Hospital Downloadable Database
    Data Dictionary, January 2026)
  - docs/NH_Data_Dictionary.txt (CMS Nursing Home Data Dictionary)
  - docs/snf-qm-calculations-and-reporting-users-manual-v7.0.txt

CMS definitions are at the measure GROUP level for hospitals (e.g., one mortality
definition covers MORT_30_AMI through Hybrid_HWM). All measures in a group share
the same cms_measure_definition text. Where CMS provides a per-measure definition,
it is stored individually.

Measures with no entry here have cms_measure_definition = None (REVIEW_NEEDED).
"""

# ---------------------------------------------------------------------------
# Hospital CMS definitions (from HOSPITAL_Data_Dictionary.txt, Jan 2026)
# ---------------------------------------------------------------------------

_CMS_DEF_MORTALITY = (
    "The 30-day death measures are estimates of deaths within 30 days of the start "
    "of a hospital admission from any cause related to medical conditions, including "
    "heart attack (AMI), heart failure (HF), pneumonia (PN), chronic obstructive "
    "pulmonary disease (COPD), and stroke; as well as surgical procedures, including "
    "coronary artery bypass graft (CABG); additionally, hospital wide mortality (HWM) "
    "is also reported. Hospitals' rates are compared to the national rate to determine "
    "if hospitals' performance on these measures is better than the national rate "
    "(lower), no different than the national rate, or worse than the national rate "
    "(higher). CMS chose to measure death within 30 days instead of inpatient deaths "
    "to use a more consistent measurement time window because length of hospital stay "
    "varies across patients and hospitals. Lower rates for mortality are better."
)

_CMS_DEF_COMP_HIP_KNEE = (
    "CMS's publicly reported risk-standardized complication measure for elective "
    "primary total hip arthroplasty (THA) and/or total knee arthroplasty (TKA) "
    "assesses a broad set of healthcare activities that affect patients' well-being. "
    "The hip/knee complication rate is an estimate of complications within an "
    "applicable time period, for patients electively admitted for primary total hip "
    "and/or knee replacement. CMS measures the likelihood that at least 1 of 8 "
    "complications occurs within a specified time period: heart attack (AMI), "
    "pneumonia, or sepsis/septicemia/shock during the index admission or within 7 "
    "days of admission, surgical site bleeding, pulmonary embolism, or death during "
    "the index admission or within 30 days of admission, or mechanical complications "
    "or periprosthetic joint infection/wound infection during the index admission or "
    "within 90 days of admission. Lower rates for surgical complications are better."
)

_CMS_DEF_PSI = (
    "Measures of serious complications are drawn from the Agency for Healthcare "
    "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
    "score for serious complications is based on how often adult patients had "
    "certain serious, but potentially preventable, complications related to medical "
    "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
    "hospitalized adults and focus on potentially avoidable complications and "
    "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
    "discharged from a hospital paid through the IPPS. These indicators are risk "
    "adjusted to account for differences in hospital patients' characteristics. "
    "CMS publicly reports data on two PSIs — PSI-4 (death rate among surgical "
    "patients with serious treatable complications) and the composite measure "
    "PSI-90."
)

_CMS_DEF_HAI = (
    "The HAI measures show how often patients in a particular hospital contract "
    "certain infections during the course of their medical treatment, when compared "
    "to like hospitals. HAI measures provide information on infections that occur "
    "while the patient is in the hospital and include: central line-associated "
    "bloodstream infections (CLABSI), catheter-associated urinary tract infections "
    "(CAUTI), surgical site infection (SSI) from colon surgery or abdominal "
    "hysterectomy, methicillin-resistant Staphylococcus Aureus (MRSA) blood "
    "laboratory-identified events (bloodstream infections), and Clostridium "
    "difficile (C.diff.) laboratory-identified events (intestinal infections). The "
    "CDC calculates a Standardized Infection Ratio (SIR) which may take into account "
    "the type of patient care location, number of patients with an existing "
    "infection, laboratory methods, hospital affiliation with a medical school, bed "
    "size of the hospital, patient age, and classification of patient health. SIRs "
    "are calculated for the hospital, the state, and the nation. The HAI measures "
    "apply to all patients treated in acute care hospitals, including adult, "
    "pediatric, neonatal, Medicare, and non-Medicare patients."
)

_CMS_DEF_HCAHPS = (
    "The HCAHPS Patient Survey is a survey instrument and data collection "
    "methodology for measuring patients' perceptions of their hospital experience. "
    "The survey is administered to a random sample of adult inpatients after "
    "discharge. The HCAHPS survey contains patient perspectives on care and patient "
    "rating items that encompass key topics: communication with hospital staff, "
    "responsiveness of hospital staff, communication about medicines, discharge "
    "information, cleanliness of hospital environment, quietness of hospital "
    "environment, and transition of care."
)

_CMS_DEF_READM_BY_CONDITION = (
    "The 30-day unplanned readmission measures are estimates of unplanned "
    "readmission to any acute care hospital within 30 days of discharge from a "
    "hospitalization for any cause related to medical conditions, including heart "
    "attack (AMI), heart failure (HF), pneumonia (PN), and chronic obstructive "
    "pulmonary disease (COPD). The hospital return days measures (excess days in "
    "acute care or EDAC measures) add up the number of days patients spent back in "
    "the hospital within 30 days after they were first treated and released for AMI, "
    "HF, and pneumonia. Readmission rates are presented as percentages; lower rates "
    "are better. EDAC results are presented in days per 100 discharges and can be "
    "negative, zero, or positive."
)

_CMS_DEF_READM_BY_PROCEDURE = (
    "Measures of unplanned hospital visits show how often patients visit the "
    "hospital after a procedure like coronary artery bypass graft (CABG) surgery, "
    "hip/knee replacement, colonoscopy, chemotherapy, and surgical procedures. The "
    "CABG surgery and hip/knee replacement readmission measures are estimates of "
    "unplanned readmission within 30 days. The outpatient colonoscopy, chemotherapy "
    "and surgery measures are risk-standardized hospital visit rates after outpatient "
    "procedures. Lower percentages or ratios are better."
)

_CMS_DEF_READM_OVERALL = (
    "The 30-day unplanned hospital-wide readmission measure is an estimate of "
    "unplanned readmission to any acute care hospital within 30 days of discharge "
    "from a hospitalization for any cause. The hospital-wide readmission measure "
    "includes all eligible medical, surgical and gynecological, neurological, "
    "cardiovascular, and cardiorespiratory admissions. Lower rates are better."
)

_CMS_DEF_HRRP = (
    "In October 2012, CMS began reducing Medicare payments for subsection(d) "
    "hospitals with excess readmissions. Excess readmissions are measured by a "
    "ratio, calculated by dividing a hospital's predicted rate of readmission for "
    "heart attack (AMI), heart failure (HF), pneumonia, chronic obstructive "
    "pulmonary disease (COPD), hip/knee replacement (THA/TKA), and coronary artery "
    "bypass graft (CABG) surgery by the expected rate of readmission, based on an "
    "average hospital with similar patients."
)

_CMS_DEF_TIMELY_EFFECTIVE = (
    "The measures of timely and effective care show the percentage of hospital "
    "patients who got treatments known to get the best results for certain common, "
    "serious medical conditions or surgical procedures; how quickly hospitals treat "
    "patients who come to the hospital with certain medical emergencies; and how "
    "well hospitals provide preventive services. These measures only apply to "
    "patients for whom the recommended treatment would be appropriate."
)

_CMS_DEF_IMAGING = (
    "The measures on the use of medical imaging show how often a hospital provides "
    "specific imaging tests for Medicare beneficiaries under circumstances where "
    "they may not be medically appropriate. Lower percentages suggest more efficient "
    "use of medical imaging."
)

_CMS_DEF_MSPB = (
    "The Medicare Spending Per Beneficiary (MSPB-1) Measure assesses Medicare Part "
    "A and Part B payments for services provided to a Medicare beneficiary during a "
    "spending-per-beneficiary episode that spans from three days prior to an "
    "inpatient hospital admission through 30 days after discharge. The payments "
    "included in this measure are price-standardized and risk-adjusted."
)

# ---------------------------------------------------------------------------
# Nursing Home CMS definitions (from NH_Data_Dictionary.txt)
# These are file-level descriptions, not per-measure narratives.
# Per-measure definitions should be sourced from the SNF QM manual.
# ---------------------------------------------------------------------------

_CMS_DEF_NH_MDS_QUALITY = (
    "Quality measures that are based on the resident assessments that make up the "
    "nursing home Minimum Data Set (MDS). Each quality measure score represents the "
    "percentage of a facility's residents meeting the measure criteria during the "
    "assessment period."
)

_CMS_DEF_NH_CLAIMS_QUALITY = (
    "Quality measures that are based on Medicare claims data. Each measure includes "
    "the risk-adjusted score, observed score, and expected score. The risk-adjusted "
    "score accounts for differences in the characteristics of residents across "
    "nursing homes."
)

_CMS_DEF_NH_FIVE_STAR = (
    "The Five-Star Quality Rating System was created by CMS to help consumers, "
    "their families, and caregivers compare nursing homes. The rating system gives "
    "each nursing home a rating of between 1 and 5 stars, where 5 stars is the "
    "highest rating and indicates much above average quality, and 1 star is the "
    "lowest rating and indicates quality much below average."
)

_CMS_DEF_NH_SNF_QRP = (
    "Skilled Nursing Facilities (SNFs) must report data on certain measures of "
    "quality to Medicare through the SNF Quality Reporting Program (QRP). This "
    "data contains SNF results on quality of resident care measures implemented "
    "under the IMPACT Act."
)

_CMS_DEF_NH_HEALTH_DEF = (
    "A list of nursing home health citations in the last three inspection cycles, "
    "including the associated inspection date, citation tag number and description, "
    "scope and severity, the current status of the citation and the correction date."
)

_CMS_DEF_NH_PENALTIES = (
    "A list of the fines and payment denials received by nursing homes in the last "
    "three years."
)

_CMS_DEF_NH_STAFFING = (
    "Staffing data are reported through the CMS Payroll Based Journal (PBJ) system, "
    "which collects actual payroll data rather than self-reported estimates. Staffing "
    "hours are reported as hours per resident per day (HPRD) and are adjusted for "
    "patient acuity using the PDPM case-mix classification system."
)

_CMS_DEF_NH_PROVIDER_INFO = (
    "General information on currently active nursing homes, including number of "
    "certified beds, monthly star ratings, staffing data and other information used "
    "in the Five-Star Rating System."
)


# ---------------------------------------------------------------------------
# Mapping: measure_id → CMS definition text
# ---------------------------------------------------------------------------
# Measures not in this dict have cms_measure_definition = None (REVIEW_NEEDED).

CMS_MEASURE_DEFINITIONS: dict[str, str] = {
    # -- Mortality (7) --
    "MORT_30_AMI": _CMS_DEF_MORTALITY,
    "MORT_30_CABG": _CMS_DEF_MORTALITY,
    "MORT_30_COPD": _CMS_DEF_MORTALITY,
    "MORT_30_HF": _CMS_DEF_MORTALITY,
    "MORT_30_PN": _CMS_DEF_MORTALITY,
    "MORT_30_STK": _CMS_DEF_MORTALITY,
    "Hybrid_HWM": _CMS_DEF_MORTALITY,

    # -- Complications: Hip/Knee (1) --
    "COMP_HIP_KNEE": _CMS_DEF_COMP_HIP_KNEE,

    # -- Complications: PSI (12) --
    "PSI_90": _CMS_DEF_PSI,
    "PSI_03": _CMS_DEF_PSI,
    "PSI_04": _CMS_DEF_PSI,
    "PSI_4_SURG_COMP": _CMS_DEF_PSI,
    "PSI_06": _CMS_DEF_PSI,
    "PSI_08": _CMS_DEF_PSI,
    "PSI_09": _CMS_DEF_PSI,
    "PSI_10": _CMS_DEF_PSI,
    "PSI_11": _CMS_DEF_PSI,
    "PSI_12": _CMS_DEF_PSI,
    "PSI_13": _CMS_DEF_PSI,
    "PSI_14": _CMS_DEF_PSI,
    "PSI_15": _CMS_DEF_PSI,

    # -- HAI (6) --
    "HAI_1_SIR": _CMS_DEF_HAI,
    "HAI_2_SIR": _CMS_DEF_HAI,
    "HAI_3_SIR": _CMS_DEF_HAI,
    "HAI_4_SIR": _CMS_DEF_HAI,
    "HAI_5_SIR": _CMS_DEF_HAI,
    "HAI_6_SIR": _CMS_DEF_HAI,

    # -- HCAHPS (68) -- all share the same group-level definition
    **{mid: _CMS_DEF_HCAHPS for mid in [
        "H_COMP_1_A_P", "H_COMP_1_U_P", "H_COMP_1_SN_P",
        "H_COMP_1_LINEAR_SCORE", "H_COMP_1_STAR_RATING",
        "H_COMP_2_A_P", "H_COMP_2_U_P", "H_COMP_2_SN_P",
        "H_COMP_2_LINEAR_SCORE", "H_COMP_2_STAR_RATING",
        "H_COMP_5_A_P", "H_COMP_5_U_P", "H_COMP_5_SN_P",
        "H_COMP_5_LINEAR_SCORE", "H_COMP_5_STAR_RATING",
        "H_COMP_6_Y_P", "H_COMP_6_N_P",
        "H_COMP_6_LINEAR_SCORE", "H_COMP_6_STAR_RATING",
        "H_DISCH_HELP_Y_P", "H_DISCH_HELP_N_P",
        "H_SYMPTOMS_Y_P", "H_SYMPTOMS_N_P",
        "H_CLEAN_HSP_A_P", "H_CLEAN_HSP_U_P", "H_CLEAN_HSP_SN_P",
        "H_CLEAN_LINEAR_SCORE", "H_CLEAN_STAR_RATING",
        "H_QUIET_HSP_A_P", "H_QUIET_HSP_U_P", "H_QUIET_HSP_SN_P",
        "H_QUIET_LINEAR_SCORE", "H_QUIET_STAR_RATING",
        "H_HSP_RATING_9_10", "H_HSP_RATING_7_8", "H_HSP_RATING_0_6",
        "H_HSP_RATING_LINEAR_SCORE", "H_HSP_RATING_STAR_RATING",
        "H_RECMND_DY", "H_RECMND_PY", "H_RECMND_DN",
        "H_RECMND_LINEAR_SCORE", "H_RECMND_STAR_RATING",
        "H_DOCTOR_EXPLAIN_A_P", "H_DOCTOR_EXPLAIN_U_P", "H_DOCTOR_EXPLAIN_SN_P",
        "H_DOCTOR_LISTEN_A_P", "H_DOCTOR_LISTEN_U_P", "H_DOCTOR_LISTEN_SN_P",
        "H_DOCTOR_RESPECT_A_P", "H_DOCTOR_RESPECT_U_P", "H_DOCTOR_RESPECT_SN_P",
        "H_NURSE_EXPLAIN_A_P", "H_NURSE_EXPLAIN_U_P", "H_NURSE_EXPLAIN_SN_P",
        "H_NURSE_LISTEN_A_P", "H_NURSE_LISTEN_U_P", "H_NURSE_LISTEN_SN_P",
        "H_NURSE_RESPECT_A_P", "H_NURSE_RESPECT_U_P", "H_NURSE_RESPECT_SN_P",
        "H_MED_FOR_A_P", "H_MED_FOR_U_P", "H_MED_FOR_SN_P",
        "H_SIDE_EFFECTS_A_P", "H_SIDE_EFFECTS_U_P", "H_SIDE_EFFECTS_SN_P",
        "H_STAR_RATING",
    ]},

    # -- Readmissions by condition (7) --
    "READM_30_AMI": _CMS_DEF_READM_BY_CONDITION,
    "READM_30_COPD": _CMS_DEF_READM_BY_CONDITION,
    "READM_30_HF": _CMS_DEF_READM_BY_CONDITION,
    "READM_30_PN": _CMS_DEF_READM_BY_CONDITION,
    "EDAC_30_AMI": _CMS_DEF_READM_BY_CONDITION,
    "EDAC_30_HF": _CMS_DEF_READM_BY_CONDITION,
    "EDAC_30_PN": _CMS_DEF_READM_BY_CONDITION,

    # -- Readmissions by procedure (6) --
    "READM_30_CABG": _CMS_DEF_READM_BY_PROCEDURE,
    "READM_30_HIP_KNEE": _CMS_DEF_READM_BY_PROCEDURE,
    "OP_32": _CMS_DEF_READM_BY_PROCEDURE,
    "OP_35_ADM": _CMS_DEF_READM_BY_PROCEDURE,
    "OP_35_ED": _CMS_DEF_READM_BY_PROCEDURE,
    "OP_36": _CMS_DEF_READM_BY_PROCEDURE,

    # -- Readmissions overall (1) --
    "Hybrid_HWR": _CMS_DEF_READM_OVERALL,

    # -- HRRP excess ratios (6) --
    "HRRP_AMI": _CMS_DEF_HRRP,
    "HRRP_CABG": _CMS_DEF_HRRP,
    "HRRP_COPD": _CMS_DEF_HRRP,
    "HRRP_HF": _CMS_DEF_HRRP,
    "HRRP_HIP_KNEE": _CMS_DEF_HRRP,
    "HRRP_PN": _CMS_DEF_HRRP,

    # -- Timely and Effective Care (30) --
    **{mid: _CMS_DEF_TIMELY_EFFECTIVE for mid in [
        "EDV", "OP_18a", "OP_18b", "OP_18c", "OP_18d",
        "OP_22", "OP_23", "OP_29", "OP_31", "OP_40",
        "SEP_1", "SEP_SH_3HR", "SEP_SH_6HR", "SEV_SEP_3HR", "SEV_SEP_6HR",
        "STK_02", "STK_03", "STK_05",
        "VTE_1", "VTE_2",
        "IMM_3",
        "HH_HYPER", "HH_HYPO", "HH_ORAE",
        "SAFE_USE_OF_OPIOIDS",
        "GMCS", "GMCS_Malnutrition_Screening", "GMCS_Nutrition_Assessment",
        "GMCS_Malnutrition_Diagnosis_Documented", "GMCS_Nutritional_Care_Plan",
    ]},

    # -- Imaging Efficiency (4) --
    "OP-8": _CMS_DEF_IMAGING,
    "OP-10": _CMS_DEF_IMAGING,
    "OP-13": _CMS_DEF_IMAGING,
    "OP-39": _CMS_DEF_IMAGING,

    # -- MSPB (1) --
    "MSPB-1": _CMS_DEF_MSPB,

    # ===================================================================
    # Nursing Home definitions
    # ===================================================================

    # -- NH MDS Quality (long-stay + short-stay, 17+ measures) --
    # NH measure_ids use NH_MDS_ prefix from MEASURE_REGISTRY
    **{mid: _CMS_DEF_NH_MDS_QUALITY for mid in [
        "NH_MDS_401", "NH_MDS_404", "NH_MDS_406", "NH_MDS_407",
        "NH_MDS_408", "NH_MDS_409", "NH_MDS_410", "NH_MDS_415",
        "NH_MDS_451", "NH_MDS_452", "NH_MDS_454", "NH_MDS_479",
        "NH_MDS_480", "NH_MDS_481",
        # Short-stay
        "NH_MDS_430", "NH_MDS_434", "NH_MDS_472",
    ]},

    # -- NH Claims Quality (4 measures) --
    **{mid: _CMS_DEF_NH_CLAIMS_QUALITY for mid in [
        "NH_CLAIMS_521", "NH_CLAIMS_522", "NH_CLAIMS_551", "NH_CLAIMS_552",
    ]},

    # -- NH Five-Star Sub-Ratings (6) --
    **{mid: _CMS_DEF_NH_FIVE_STAR for mid in [
        "NH_STAR_OVERALL", "NH_STAR_HEALTH_INSP", "NH_STAR_QM",
        "NH_STAR_LS_QM", "NH_STAR_SS_QM", "NH_STAR_STAFFING",
    ]},

    # -- NH Staffing (9) --
    **{mid: _CMS_DEF_NH_STAFFING for mid in [
        "NH_STAFF_ADJ_TOTAL_HPRD", "NH_STAFF_ADJ_RN_HPRD",
        "NH_STAFF_ADJ_WEEKEND_HPRD",
        "NH_STAFF_REPORTED_TOTAL_HPRD", "NH_STAFF_REPORTED_RN_HPRD",
        "NH_STAFF_REPORTED_AIDE_HPRD",
        "NH_STAFF_TOTAL_TURNOVER", "NH_STAFF_RN_TURNOVER",
        "NH_STAFF_ADMIN_DEPARTURES",
    ]},

    # -- NH Inspection + Penalties (13) --
    **{mid: _CMS_DEF_NH_HEALTH_DEF for mid in [
        "NH_INSP_IJ_CITATIONS", "NH_INSP_HARM_CITATIONS",
        "NH_INSP_ABUSE_CITATIONS", "NH_INSP_INFECTION_CTRL",
        "NH_INSP_COMPLAINT_DEF",
        "NH_INSP_TOTAL_HEALTH_DEF", "NH_INSP_TOTAL_FIRE_DEF",
        "NH_INSP_WEIGHTED_SCORE", "NH_INSP_REVISIT_SCORE",
    ]},
    **{mid: _CMS_DEF_NH_PENALTIES for mid in [
        "NH_PENALTY_FINE_TOTAL", "NH_PENALTY_COUNT",
        "NH_PENALTY_PAYMENT_DENIALS", "NH_PENALTY_FINE_COUNT",
    ]},

    # -- NH SNF QRP (15) --
    **{mid: _CMS_DEF_NH_SNF_QRP for mid in [
        "S_004_01", "S_005_02", "S_006_01", "S_007_02", "S_013_02",
        "S_024_06", "S_025_06", "S_038_02", "S_039_01",
        "S_040_02", "S_041_01", "S_042_02", "S_043_02", "S_044_02",
        "S_045_01",
    ]},
}
