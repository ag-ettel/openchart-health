"""
Pipeline configuration: constants, dataset IDs, and MEASURE_REGISTRY.

All CMS dataset IDs, measure IDs, and registry entries live here.
No other module may hardcode these values.

MEASURE_REGISTRY is the authoritative list of every CMS quality measure
this pipeline ingests. Each entry declares the measure's direction,
SES sensitivity, tail-risk classification, and display metadata.

Rules (enforced by coding-conventions.md and data-integrity.md):
  - direction must be explicitly declared; never inferred from data.
  - ses_sensitivity must have a documented basis in docs/data_dictionary.md.
  - No entry may be added here without a corresponding entry in
    docs/data_dictionary.md (same commit).
  - Never use Python float for measure values reported as percentages
    or rates (Data Integrity Rule 10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# CMS Socrata Dataset IDs (confirmed Phase 0, 2026-03-14/15/16)
# ---------------------------------------------------------------------------

# Hospital datasets (confirmed 2026-03-14/15)
HOSPITAL_DATASET_IDS: dict[str, str] = {
    "hospital_general_information": "xubh-q36u",
    "timely_effective_care": "yv7e-xc69",
    "hcahps": "dgck-syfz",
    "complications_deaths": "ynj2-r877",
    "hai": "77hc-ibv8",
    "readmissions": "632h-zaca",
    "outpatient_imaging": "wkfw-kthe",
    "mspb": "rrqw-56er",
    "hrrp": "9n3s-kdb3",
    "hacrp": "yq43-i98g",
    "vbp": "pudb-wetr",
}

# Nursing home datasets (confirmed 2026-03-16 via DKAN metastore + datastore query)
# All use the same DKAN API base URL as hospital datasets.
NH_DATASET_IDS: dict[str, str] = {
    # Primary nursing home data
    "nh_provider_info": "4pq5-n9py",        # 14,710 rows, 99 cols
    "nh_mds_quality": "djen-97ju",           # 250,070 rows, 23 cols
    "nh_claims_quality": "ijh5-nb2v",        # 58,840 rows, 17 cols
    "nh_health_deficiencies": "r5ix-sfxw",   # 419,452 rows, 23 cols
    "nh_fire_safety": "ifjz-ge4w",           # 199,578 rows, 24 cols
    "nh_survey_summary": "tbry-pc2d",        # 43,983 rows, 41 cols
    "nh_inspection_dates": "svdt-c123",      # 151,849 rows, 5 cols
    "nh_penalties": "g6vv-u9sr",             # 17,463 rows, 13 cols
    "nh_ownership": "y2hd-n93e",             # 159,220 rows, 13 cols
    "nh_state_averages": "xcdc-v8bm",        # 54 rows, 51 cols
    # Reference / lookup tables
    "nh_data_collection": "qmdc-9999",       # 47 rows — measure date ranges
    "nh_citation_lookup": "tagd-9999",       # 643 rows — deficiency tag descriptions
    "nh_inspection_cutpoints": "hicp-9999",  # 53 rows — state-level Five-Star cut points
    # SNF Quality Reporting Program
    "snf_qrp_provider": "fykj-qjee",        # 838,470 rows, 16 cols
    "snf_qrp_national": "5sqm-2qku",        # 27 rows — national averages
    "snf_qrp_swing_bed": "6uyb-waub",       # 43,890 rows — swing bed facilities
    # SNF Value-Based Purchasing
    "snf_vbp_facility": "284v-j9fz",         # 13,900 rows, 49 cols — FY 2026
    "snf_vbp_aggregate": "ujcx-uaut",        # 1 row — national aggregate
}

# Combined for backwards compatibility and pipeline orchestration
DATASET_IDS: dict[str, str] = {**HOSPITAL_DATASET_IDS, **NH_DATASET_IDS}

# Dataset ID → default direction_source (DEC-011/DEC-032)
# Per-measure overrides can be added to MeasureEntry if needed.
# See docs/direction_verification_checklist.md for full verification.
DATASET_DIRECTION_SOURCE: dict[str, str] = {
    "ynj2-r877": "CMS_API",              # Complications: compared_to_national has direction
    "77hc-ibv8": "CMS_API",              # HAI: compared_to_national has direction
    "632h-zaca": "CMS_API",              # Readmissions: compared_to_national has direction
    "wkfw-kthe": "CMS_DATA_DICTIONARY",  # Imaging: Data Dictionary "lower = more efficient"
    "yv7e-xc69": "CMS_MEASURE_DEFINITION",  # T&E: mixed — eCQMs have spec, others have definition
    "dgck-syfz": "CMS_MEASURE_DEFINITION",  # HCAHPS: no explicit CMS direction statement
    "rrqw-56er": "CMS_MEASURE_DEFINITION",  # MSPB: no explicit CMS direction statement
    "9n3s-kdb3": "CMS_API",              # HRRP: excess ratio — lower is better per program
    "djen-97ju": "CMS_MEASURE_DEFINITION",  # MDS Quality: measure descriptions carry direction
    "ijh5-nb2v": "CMS_MEASURE_DEFINITION",  # Claims Quality: measure descriptions carry direction
    "fykj-qjee": "CMS_API",              # SNF QRP: compared_to_national in API
    "4pq5-n9py": "CMS_MEASURE_DEFINITION",  # Provider Info (Five-Star): higher = better
    "r5ix-sfxw": "CMS_MEASURE_DEFINITION",  # Health Deficiencies: lower = better
    "g6vv-u9sr": "CMS_MEASURE_DEFINITION",  # Penalties: lower = better
}

# Dataset ID → CMS dataset name mapping for per-measure attribution
# (legal-compliance.md: required on every measure display)
DATASET_NAMES: dict[str, str] = {
    "xubh-q36u": "Hospital General Information",
    "yv7e-xc69": "Timely and Effective Care — Hospital",
    "dgck-syfz": "Patient Survey (HCAHPS) — Hospital",
    "ynj2-r877": "Complications and Deaths — Hospital",
    "77hc-ibv8": "Healthcare Associated Infections — Hospital",
    "632h-zaca": "Unplanned Hospital Visits — Hospital",
    "wkfw-kthe": "Outpatient Imaging Efficiency — Hospital",
    "rrqw-56er": "Medicare Hospital Spending Per Patient — Hospital",
    "9n3s-kdb3": "Hospital Readmissions Reduction Program",
    "yq43-i98g": "Hospital-Acquired Condition Reduction Program",
    "pudb-wetr": "Hospital Value-Based Purchasing Program",
    "4pq5-n9py": "Nursing Home Provider Information",
    "djen-97ju": "MDS Quality Measures",
    "ijh5-nb2v": "Medicare Claims Quality Measures",
    "r5ix-sfxw": "Health Deficiencies",
    "g6vv-u9sr": "Penalties",
    "y2hd-n93e": "Ownership",
    "fykj-qjee": "SNF Quality Reporting Program — Provider Data",
    "284v-j9fz": "SNF Value-Based Purchasing — Facility Performance",
}

# CMS DKAN API base URL
CMS_API_BASE_URL = "https://data.cms.gov/provider-data/api/1/datastore/query"


# ---------------------------------------------------------------------------
# MeasureGroup enum values
# ---------------------------------------------------------------------------
# These must match the PostgreSQL measure_group enum exactly.
# See docs/draft_measure_group_enum.py for design rationale.

MEASURE_GROUPS = [
    # Hospital
    "MORTALITY",
    "SAFETY",
    "COMPLICATIONS",
    "INFECTIONS",
    "READMISSIONS",
    "TIMELY_EFFECTIVE_CARE",
    "PATIENT_EXPERIENCE",
    "IMAGING_EFFICIENCY",
    "SPENDING",
    # Nursing Home
    "NH_QUALITY_LONG_STAY",
    "NH_QUALITY_SHORT_STAY",
    "NH_STAFFING",
    "NH_STAR_RATING",
    "NH_QUALITY_CLAIMS",
    "NH_INSPECTION",
    "NH_PENALTIES",
    "NH_SNF_QRP",
]


# ---------------------------------------------------------------------------
# compared_to_national canonical enum values (AMB-3)
# ---------------------------------------------------------------------------
# CMS uses inconsistent phrasings across datasets. The normalizer must
# map all observed phrasings to these canonical values before storage.

COMPARED_TO_NATIONAL_CANONICAL = [
    "BETTER",       # Rate/Value/Benchmark variants + "Better than expected" + "Fewer Days Than Average..."
    "WORSE",        # Rate/Value/Benchmark variants + "Worse than expected" + "More Days Than Average..."
    "NO_DIFFERENT", # Rate/Value/Benchmark variants + "No Different than expected" + "Average Days per 100..."
    "NOT_AVAILABLE", # "Not Available", "Not Applicable"
    "TOO_FEW_CASES", # "Number of Cases Too Small" / "Number of cases too small"
]

# Full mapping from CMS raw strings to canonical values (case-insensitive).
# Confirmed from full-population CSV scan 2026-03-20.
COMPARED_TO_NATIONAL_MAPPING: dict[str, str] = {
    # CompDeaths — Rate phrasing (mortality, complications)
    "better than the national rate": "BETTER",
    "no different than the national rate": "NO_DIFFERENT",
    "worse than the national rate": "WORSE",
    # CompDeaths — Value phrasing (PSI_90 composite)
    "better than the national value": "BETTER",
    "no different than the national value": "NO_DIFFERENT",
    "worse than the national value": "WORSE",
    # HAI — Benchmark phrasing
    "better than the national benchmark": "BETTER",
    "no different than national benchmark": "NO_DIFFERENT",
    "worse than the national benchmark": "WORSE",
    # EDAC — Days phrasing (excess days measures)
    "fewer days than average per 100 discharges": "BETTER",
    "average days per 100 discharges": "NO_DIFFERENT",
    "more days than average per 100 discharges": "WORSE",
    # OP_36 — Expected phrasing (O/E ratio)
    "better than expected": "BETTER",
    "no different than expected": "NO_DIFFERENT",
    "worse than expected": "WORSE",
    # Suppression sentinels
    "number of cases too small": "TOO_FEW_CASES",
    "not available": "NOT_AVAILABLE",
    "not applicable": "NOT_AVAILABLE",
}


# ---------------------------------------------------------------------------
# Credible interval configuration (DEC-029)
# ---------------------------------------------------------------------------

# Concentration parameter κ for Beta-Binomial prior.
# Represents ~10 pseudo-observations. Weak enough that n ≥ 25 dominates the prior,
# provides meaningful shrinkage for very small samples (n < 10).
CREDIBLE_INTERVAL_CONCENTRATION: int = 10

# Credible interval level (two-tailed).
CREDIBLE_INTERVAL_LEVEL: float = 0.95


# ---------------------------------------------------------------------------
# MeasureEntry dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MeasureEntry:
    """One entry in the MEASURE_REGISTRY."""

    measure_id: str
    name: str
    group: str
    direction: Optional[str]  # "LOWER_IS_BETTER", "HIGHER_IS_BETTER", or None
    unit: str  # "percent", "ratio", "rate", "minutes", "days_per_100", "score", "category"
    plain_language: str
    tail_risk_flag: bool
    ses_sensitivity: str  # "HIGH", "MODERATE", "LOW", "UNKNOWN"
    dataset_id: str  # Socrata dataset ID for provenance
    # CMS verbatim measure definition (DEC-037). Sourced from CMS data dictionary,
    # measure information forms, or technical specifications. Must not be paraphrased.
    # None = not yet sourced (REVIEW_NEEDED).
    cms_measure_definition: Optional[str] = None
    # Interval estimation fields (DEC-029, measure-registry.md)
    risk_adjustment_model: Optional[str] = None  # "HGLM", "SIR", "PATIENT_MIX_ADJUSTMENT", "NONE", "OTHER", or None (REVIEW_NEEDED)
    cms_ci_published: Optional[bool] = None  # True/False/None (REVIEW_NEEDED)
    numerator_denominator_published: Optional[bool] = None  # True/False/None (REVIEW_NEEDED)


# ═══════════════════════════════════════════════════════════════════════════
# MEASURE_REGISTRY
# ═══════════════════════════════════════════════════════════════════════════
#
# Authoritative registry of all CMS quality measures in scope.
# Total: 207 measures (143 hospital + 64 nursing home) across 12 datasets.
#
# Hospital (143):
#   Complications and Deaths (ynj2-r877):  20 measures
#   Healthcare-Associated Infections (77hc-ibv8):  6 measures (SIR only)
#   HCAHPS Patient Survey (dgck-syfz):  68 measures
#   Unplanned Hospital Visits / Readmissions (632h-zaca):  14 measures
#   Timely and Effective Care (yv7e-xc69):  30 measures
#   Outpatient Imaging Efficiency (wkfw-kthe):  4 measures
#   Medicare Spending Per Patient (rrqw-56er):  1 measure
#
# Nursing Home (64):
#   MDS Quality Measures (djen-97ju):  17 measures
#   Medicare Claims Quality Measures (ijh5-nb2v):  4 measures
#   Five-Star Sub-Ratings (4pq5-n9py):  6 ratings
#   SNF QRP (fykj-qjee):  15 measures
#   Staffing (4pq5-n9py):  9 measures (6 Five-Star + 3 reported)
#   Inspection + Penalties (4pq5-n9py + r5ix-sfxw):  13 measures
#
# ═══════════════════════════════════════════════════════════════════════════

_REGISTRY_LIST: list[MeasureEntry] = [

    # ───────────────────────────────────────────────────────────────────
    # Complications and Deaths (ynj2-r877) — 20 measures
    # Phase 0 reference: docs/phase_0_findings.md §5
    # ───────────────────────────────────────────────────────────────────

    # -- Mortality (7) --

    MeasureEntry(
        measure_id="MORT_30_AMI",
        name="Death rate for heart attack patients",
        group="MORTALITY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare heart attack patients who died within "
            "30 days of being admitted to this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "The 30-day death measures are estimates of deaths within 30 days of the start "
            "of a hospital admission from any cause related to medical conditions, "
            "including heart attack (AMI), heart failure (HF), pneumonia (PN), chronic "
            "obstructive pulmonary disease (COPD), and stroke; as well as surgical "
            "procedures, including coronary artery bypass graft (CABG); additionally, "
            "hospital wide mortality (HWM) is also reported. Hospitals' rates are compared "
            "to the national rate to determine if hospitals' performance on these measures "
            "is better than the national rate (lower), no different than the national rate, "
            "or worse than the national rate (higher). For some hospitals, the number of "
            "cases is too small to reliably compare their results to the national average "
            "rate. CMS chose to measure death within 30 days instead of inpatient deaths to "
            "use a more consistent measurement time window because length of hospital stay "
            "varies across patients and hospitals. Rates are provided in the downloadable "
            "databases and presented on the Care Compare on Medicare.gov website as "
            "percentages. Lower rates for mortality are better."
        ),
    ),
    MeasureEntry(
        measure_id="MORT_30_CABG",
        name="Death rate for CABG surgery patients",
        group="MORTALITY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare patients who died within 30 days of "
            "coronary artery bypass graft (open-heart) surgery at this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "The 30-day death measures are estimates of deaths within 30 days of the start "
            "of a hospital admission from any cause related to medical conditions, "
            "including heart attack (AMI), heart failure (HF), pneumonia (PN), chronic "
            "obstructive pulmonary disease (COPD), and stroke; as well as surgical "
            "procedures, including coronary artery bypass graft (CABG); additionally, "
            "hospital wide mortality (HWM) is also reported. Hospitals' rates are compared "
            "to the national rate to determine if hospitals' performance on these measures "
            "is better than the national rate (lower), no different than the national rate, "
            "or worse than the national rate (higher). For some hospitals, the number of "
            "cases is too small to reliably compare their results to the national average "
            "rate. CMS chose to measure death within 30 days instead of inpatient deaths to "
            "use a more consistent measurement time window because length of hospital stay "
            "varies across patients and hospitals. Rates are provided in the downloadable "
            "databases and presented on the Care Compare on Medicare.gov website as "
            "percentages. Lower rates for mortality are better."
        ),
    ),
    MeasureEntry(
        measure_id="MORT_30_COPD",
        name="Death rate for COPD patients",
        group="MORTALITY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare patients admitted for a COPD flare-up "
            "who died within 30 days of being admitted to this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "The 30-day death measures are estimates of deaths within 30 days of the start "
            "of a hospital admission from any cause related to medical conditions, "
            "including heart attack (AMI), heart failure (HF), pneumonia (PN), chronic "
            "obstructive pulmonary disease (COPD), and stroke; as well as surgical "
            "procedures, including coronary artery bypass graft (CABG); additionally, "
            "hospital wide mortality (HWM) is also reported. Hospitals' rates are compared "
            "to the national rate to determine if hospitals' performance on these measures "
            "is better than the national rate (lower), no different than the national rate, "
            "or worse than the national rate (higher). For some hospitals, the number of "
            "cases is too small to reliably compare their results to the national average "
            "rate. CMS chose to measure death within 30 days instead of inpatient deaths to "
            "use a more consistent measurement time window because length of hospital stay "
            "varies across patients and hospitals. Rates are provided in the downloadable "
            "databases and presented on the Care Compare on Medicare.gov website as "
            "percentages. Lower rates for mortality are better."
        ),
    ),
    MeasureEntry(
        measure_id="MORT_30_HF",
        name="Death rate for heart failure patients",
        group="MORTALITY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare heart failure patients who died within "
            "30 days of being admitted to this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "The 30-day death measures are estimates of deaths within 30 days of the start "
            "of a hospital admission from any cause related to medical conditions, "
            "including heart attack (AMI), heart failure (HF), pneumonia (PN), chronic "
            "obstructive pulmonary disease (COPD), and stroke; as well as surgical "
            "procedures, including coronary artery bypass graft (CABG); additionally, "
            "hospital wide mortality (HWM) is also reported. Hospitals' rates are compared "
            "to the national rate to determine if hospitals' performance on these measures "
            "is better than the national rate (lower), no different than the national rate, "
            "or worse than the national rate (higher). For some hospitals, the number of "
            "cases is too small to reliably compare their results to the national average "
            "rate. CMS chose to measure death within 30 days instead of inpatient deaths to "
            "use a more consistent measurement time window because length of hospital stay "
            "varies across patients and hospitals. Rates are provided in the downloadable "
            "databases and presented on the Care Compare on Medicare.gov website as "
            "percentages. Lower rates for mortality are better."
        ),
    ),
    MeasureEntry(
        measure_id="MORT_30_PN",
        name="Death rate for pneumonia patients",
        group="MORTALITY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare pneumonia patients who died within "
            "30 days of being admitted to this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "The 30-day death measures are estimates of deaths within 30 days of the start "
            "of a hospital admission from any cause related to medical conditions, "
            "including heart attack (AMI), heart failure (HF), pneumonia (PN), chronic "
            "obstructive pulmonary disease (COPD), and stroke; as well as surgical "
            "procedures, including coronary artery bypass graft (CABG); additionally, "
            "hospital wide mortality (HWM) is also reported. Hospitals' rates are compared "
            "to the national rate to determine if hospitals' performance on these measures "
            "is better than the national rate (lower), no different than the national rate, "
            "or worse than the national rate (higher). For some hospitals, the number of "
            "cases is too small to reliably compare their results to the national average "
            "rate. CMS chose to measure death within 30 days instead of inpatient deaths to "
            "use a more consistent measurement time window because length of hospital stay "
            "varies across patients and hospitals. Rates are provided in the downloadable "
            "databases and presented on the Care Compare on Medicare.gov website as "
            "percentages. Lower rates for mortality are better."
        ),
    ),
    MeasureEntry(
        measure_id="MORT_30_STK",
        name="Death rate for stroke patients",
        group="MORTALITY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare stroke patients who died within "
            "30 days of being admitted to this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "The 30-day death measures are estimates of deaths within 30 days of the start "
            "of a hospital admission from any cause related to medical conditions, "
            "including heart attack (AMI), heart failure (HF), pneumonia (PN), chronic "
            "obstructive pulmonary disease (COPD), and stroke; as well as surgical "
            "procedures, including coronary artery bypass graft (CABG); additionally, "
            "hospital wide mortality (HWM) is also reported. Hospitals' rates are compared "
            "to the national rate to determine if hospitals' performance on these measures "
            "is better than the national rate (lower), no different than the national rate, "
            "or worse than the national rate (higher). For some hospitals, the number of "
            "cases is too small to reliably compare their results to the national average "
            "rate. CMS chose to measure death within 30 days instead of inpatient deaths to "
            "use a more consistent measurement time window because length of hospital stay "
            "varies across patients and hospitals. Rates are provided in the downloadable "
            "databases and presented on the Care Compare on Medicare.gov website as "
            "percentages. Lower rates for mortality are better."
        ),
    ),
    MeasureEntry(
        measure_id="Hybrid_HWM",
        name="Hybrid Hospital-Wide All-Cause Risk Standardized Mortality Rate",
        group="MORTALITY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The overall percentage of Medicare patients who died during or "
            "shortly after a stay at this hospital, adjusted for how sick "
            "the patients were."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "The 30-day death measures are estimates of deaths within 30 days of the start "
            "of a hospital admission from any cause related to medical conditions, "
            "including heart attack (AMI), heart failure (HF), pneumonia (PN), chronic "
            "obstructive pulmonary disease (COPD), and stroke; as well as surgical "
            "procedures, including coronary artery bypass graft (CABG); additionally, "
            "hospital wide mortality (HWM) is also reported. Hospitals' rates are compared "
            "to the national rate to determine if hospitals' performance on these measures "
            "is better than the national rate (lower), no different than the national rate, "
            "or worse than the national rate (higher). For some hospitals, the number of "
            "cases is too small to reliably compare their results to the national average "
            "rate. CMS chose to measure death within 30 days instead of inpatient deaths to "
            "use a more consistent measurement time window because length of hospital stay "
            "varies across patients and hospitals. Rates are provided in the downloadable "
            "databases and presented on the Care Compare on Medicare.gov website as "
            "percentages. Lower rates for mortality are better."
        ),
    ),

    # -- Complications (1) --

    MeasureEntry(
        measure_id="COMP_HIP_KNEE",
        name="Rate of complications for hip/knee replacement patients",
        group="COMPLICATIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare patients who had a serious complication "
            "within 90 days of an elective hip or knee replacement at this "
            "hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "The Centers for Medicare & Medicaid Services' (CMS's) publicly reported "
            "risk-standardized complication measure for elective primary total hip "
            "arthroplasty (THA) and/or total knee arthroplasty (TKA) assesses a broad set "
            "of healthcare activities that affect patients' well-being. The hip/knee "
            "complication rate is an estimate of complications within an applicable time "
            "period, for patients electively admitted for primary total hip and/or knee "
            "replacement. CMS measures the likelihood that at least 1 of 8 complications "
            "occurs within a specified time period: heart attack, (acute myocardial "
            "infarction [AMI]), pneumonia, or sepsis/septicemia/shock during the index "
            "admission or within 7 days of admission, surgical site bleeding, pulmonary "
            "embolism, or death during the index admission or within 30 days of admission, "
            "or mechanical complications or periprosthetic joint infection/wound infection "
            "during the index admission or within 90 days of admission. Hospitals' rates of "
            "hip/knee complications are compared to the national rate to determine if "
            "hospitals' performance on this measure is better than the national rate "
            "(lower), no different than the national rate, or worse than the national rate "
            "(higher). For some hospitals, the number of cases is too small to reliably "
            "compare their results to the national average rate. Rates are provided in the "
            "downloadable databases and presented on the Care Compare on Medicare.gov "
            "website as percentages. Lower rates for surgical complications are better. CMS "
            "chose to measure these complications within the specified times because "
            "complications over a longer period may be impacted by factors outside the "
            "hospitals' control like other complicating illnesses, patients' own behavior, "
            "or care provided to patients after discharge. This measure is separate from "
            "the serious complications measure (also reported on Care Compare on "
            "Medicare.gov)."
        ),
    ),

    # -- Patient Safety Indicators (12) --

    MeasureEntry(
        measure_id="PSI_03",
        name="Pressure ulcer rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often patients developed serious bed sores during their "
            "stay at this hospital, compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_04",
        name="Death rate among surgical inpatients with serious treatable complications",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often surgical patients who developed a serious but treatable "
            "complication died at this hospital, compared to what would be "
            "expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_06",
        name="Iatrogenic pneumothorax rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often a medical procedure accidentally caused a patient's "
            "lung to collapse at this hospital, compared to what would be "
            "expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_08",
        name="In-hospital fall-associated hip fracture rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often patients fell and broke a hip during their stay at "
            "this hospital, compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_09",
        name="Postoperative hemorrhage or hematoma rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often surgical patients had serious bleeding after their "
            "operation at this hospital, compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_10",
        name="Postoperative acute kidney injury requiring dialysis rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often surgical patients developed kidney failure requiring "
            "dialysis after their operation at this hospital, compared to "
            "what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_11",
        name="Postoperative respiratory failure rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often surgical patients had serious breathing problems "
            "requiring a ventilator after their operation at this hospital, "
            "compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_12",
        name="Perioperative pulmonary embolism or deep vein thrombosis rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often surgical patients developed a blood clot in the lungs "
            "or legs around the time of their operation at this hospital, "
            "compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_13",
        name="Postoperative sepsis rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often surgical patients developed a serious bloodstream "
            "infection after their operation at this hospital, compared to "
            "what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_14",
        name="Postoperative wound dehiscence rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often a surgical wound reopened after an abdominal or pelvic "
            "operation at this hospital, compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_15",
        name="Abdominopelvic accidental puncture or laceration rate",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often a surgeon accidentally cut or punctured an organ "
            "during an abdominal or pelvic operation at this hospital, "
            "compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),
    MeasureEntry(
        measure_id="PSI_90",
        name="CMS Medicare PSI 90: Patient safety and adverse events composite",
        group="SAFETY",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "An overall score combining multiple patient safety measures to "
            "show whether this hospital had more or fewer serious "
            "complications than expected, where a score below 1.0 is better."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="ynj2-r877",
        cms_measure_definition=(
            "Measures of serious complications are drawn from the Agency for Healthcare "
            "Research and Quality (AHRQ) Patient Safety Indicators (PSIs). The overall "
            "score for serious complications is based on how often adult patients had "
            "certain serious, but potentially preventable, complications related to medical "
            "or surgical inpatient hospital care. The CMS PSIs reflect quality of care for "
            "hospitalized adults and focus on potentially avoidable complications and "
            "iatrogenic events. CMS PSIs only apply to Medicare beneficiaries who were "
            "discharged from a hospital paid through the IPPS. These indicators are risk "
            "adjusted to account for differences in hospital patients' characteristics. CMS "
            "calculates rates for CMS PSIs using Medicare claims data and a statistical "
            "model that determines the interval estimates for the PSIs. CMS publicly "
            "reports data on two PSIs—PSI-4 (death rate among surgical patients with "
            "serious treatable complications) and the composite measure PSI-90. PSI-90 is "
            "composed of 11 NQF-endorsed measures, including PSI-3 (pressure ulcer rate), "
            "PSI-6 (iatrogenic pneumothorax rate), PSI-8 (postoperative hip fracture rate), "
            "PSI-9 (postoperative hemorrhage or hematoma rate), PSI-10 (postoperative "
            "physiologic and metabolic derangement rate), PSI-11 (postoperative respiratory "
            "failure rate), PSI-12 (postoperative pulmonary embolism or deep vein "
            "thrombosis rate), PSI-13 (postoperative sepsis rate), PSI-14 (postoperative "
            "wound dehiscence rate), and PSI-15 (accidental puncture or laceration rate). "
            "PSI-90's composite rate is the weighted average of its component indicators. "
            "Hospitals' PSI rates are compared to the national rate to determine if "
            "hospitals' performance on PSIs is better than the national rate (lower), no "
            "different than the national rate, or worse than the national rate (higher)."
        ),
    ),

    # ───────────────────────────────────────────────────────────────────
    # Healthcare-Associated Infections (77hc-ibv8) — 6 SIR measures
    # Phase 0 reference: docs/phase_0_findings.md §6
    #
    # 30 companion sub-measures (CILOWER, CIUPPER, DOPC, ELIGCASES,
    # NUMERATOR) are handled by the normalizer via pattern matching —
    # they do NOT get MEASURE_REGISTRY entries.
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="HAI_1_SIR",
        name="Central Line Associated Bloodstream Infection (ICU + select Wards)",
        group="INFECTIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's rate of bloodstream infections from central "
            "line IVs compares to what would be expected, where a number "
            "below 1.0 means fewer infections than expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="77hc-ibv8",
        cms_measure_definition=(
            "To receive payment from CMS, hospitals are required to report data about some "
            "infections to the Centers for Disease Control and Prevention's (CDC's) "
            "National Healthcare Safety Network (NHSN). The HAI measures show how often "
            "patients in a particular hospital contract certain infections during the "
            "course of their medical treatment, when compared to like hospitals. HAI "
            "measures provide information on infections that occur while the patient is in "
            "the hospital and include: central line-associated bloodstream infections "
            "(CLABSI), catheter-associated urinary tract infections (CAUTI), surgical site "
            "infection (SSI) from colon surgery or abdominal hysterectomy, "
            "methicillin-resistant Staphylococcus Aureus (MRSA) blood laboratory-identified "
            "events (bloodstream infections), and Clostridium difficile (C.diff.) "
            "laboratory-identified events (intestinal infections). The HAI measures show "
            "how often patients in a particular hospital contract certain infections during "
            "the course of their medical treatment, when compared to like hospitals. The "
            "CDC calculates a Standardized Infection Ratio (SIR) which may take into "
            "account the type of patient care location, number of patients with an existing "
            "infection, laboratory methods, hospital affiliation with a medical school, bed "
            "size of the hospital, patient age, and classification of patient health. SIRs "
            "are calculated for the hospital, the state, and the nation. Hospitals' SIRs "
            "are compared to the national benchmark to determine if hospitals' performance "
            "on these measures is better than the national benchmark (lower), no different "
            "than the national benchmark, or worse than the national benchmark (higher). "
            "The HAI measures apply to all patients treated in acute care hospitals, "
            "including adult, pediatric, neonatal, Medicare, and non-Medicare patients."
        ),
    ),
    MeasureEntry(
        measure_id="HAI_2_SIR",
        name="Catheter Associated Urinary Tract Infections (ICU + select Wards)",
        group="INFECTIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's rate of urinary tract infections from "
            "catheters compares to what would be expected, where a number "
            "below 1.0 means fewer infections than expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="77hc-ibv8",
        cms_measure_definition=(
            "To receive payment from CMS, hospitals are required to report data about some "
            "infections to the Centers for Disease Control and Prevention's (CDC's) "
            "National Healthcare Safety Network (NHSN). The HAI measures show how often "
            "patients in a particular hospital contract certain infections during the "
            "course of their medical treatment, when compared to like hospitals. HAI "
            "measures provide information on infections that occur while the patient is in "
            "the hospital and include: central line-associated bloodstream infections "
            "(CLABSI), catheter-associated urinary tract infections (CAUTI), surgical site "
            "infection (SSI) from colon surgery or abdominal hysterectomy, "
            "methicillin-resistant Staphylococcus Aureus (MRSA) blood laboratory-identified "
            "events (bloodstream infections), and Clostridium difficile (C.diff.) "
            "laboratory-identified events (intestinal infections). The HAI measures show "
            "how often patients in a particular hospital contract certain infections during "
            "the course of their medical treatment, when compared to like hospitals. The "
            "CDC calculates a Standardized Infection Ratio (SIR) which may take into "
            "account the type of patient care location, number of patients with an existing "
            "infection, laboratory methods, hospital affiliation with a medical school, bed "
            "size of the hospital, patient age, and classification of patient health. SIRs "
            "are calculated for the hospital, the state, and the nation. Hospitals' SIRs "
            "are compared to the national benchmark to determine if hospitals' performance "
            "on these measures is better than the national benchmark (lower), no different "
            "than the national benchmark, or worse than the national benchmark (higher). "
            "The HAI measures apply to all patients treated in acute care hospitals, "
            "including adult, pediatric, neonatal, Medicare, and non-Medicare patients."
        ),
    ),
    MeasureEntry(
        measure_id="HAI_3_SIR",
        name="SSI - Colon Surgery",
        group="INFECTIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's rate of surgical wound infections after "
            "colon surgery compares to what would be expected, where a "
            "number below 1.0 means fewer infections than expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="77hc-ibv8",
        cms_measure_definition=(
            "To receive payment from CMS, hospitals are required to report data about some "
            "infections to the Centers for Disease Control and Prevention's (CDC's) "
            "National Healthcare Safety Network (NHSN). The HAI measures show how often "
            "patients in a particular hospital contract certain infections during the "
            "course of their medical treatment, when compared to like hospitals. HAI "
            "measures provide information on infections that occur while the patient is in "
            "the hospital and include: central line-associated bloodstream infections "
            "(CLABSI), catheter-associated urinary tract infections (CAUTI), surgical site "
            "infection (SSI) from colon surgery or abdominal hysterectomy, "
            "methicillin-resistant Staphylococcus Aureus (MRSA) blood laboratory-identified "
            "events (bloodstream infections), and Clostridium difficile (C.diff.) "
            "laboratory-identified events (intestinal infections). The HAI measures show "
            "how often patients in a particular hospital contract certain infections during "
            "the course of their medical treatment, when compared to like hospitals. The "
            "CDC calculates a Standardized Infection Ratio (SIR) which may take into "
            "account the type of patient care location, number of patients with an existing "
            "infection, laboratory methods, hospital affiliation with a medical school, bed "
            "size of the hospital, patient age, and classification of patient health. SIRs "
            "are calculated for the hospital, the state, and the nation. Hospitals' SIRs "
            "are compared to the national benchmark to determine if hospitals' performance "
            "on these measures is better than the national benchmark (lower), no different "
            "than the national benchmark, or worse than the national benchmark (higher). "
            "The HAI measures apply to all patients treated in acute care hospitals, "
            "including adult, pediatric, neonatal, Medicare, and non-Medicare patients."
        ),
    ),
    MeasureEntry(
        measure_id="HAI_4_SIR",
        name="SSI - Abdominal Hysterectomy",
        group="INFECTIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's rate of surgical wound infections after "
            "abdominal hysterectomy compares to what would be expected, "
            "where a number below 1.0 means fewer infections than expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="77hc-ibv8",
        cms_measure_definition=(
            "To receive payment from CMS, hospitals are required to report data about some "
            "infections to the Centers for Disease Control and Prevention's (CDC's) "
            "National Healthcare Safety Network (NHSN). The HAI measures show how often "
            "patients in a particular hospital contract certain infections during the "
            "course of their medical treatment, when compared to like hospitals. HAI "
            "measures provide information on infections that occur while the patient is in "
            "the hospital and include: central line-associated bloodstream infections "
            "(CLABSI), catheter-associated urinary tract infections (CAUTI), surgical site "
            "infection (SSI) from colon surgery or abdominal hysterectomy, "
            "methicillin-resistant Staphylococcus Aureus (MRSA) blood laboratory-identified "
            "events (bloodstream infections), and Clostridium difficile (C.diff.) "
            "laboratory-identified events (intestinal infections). The HAI measures show "
            "how often patients in a particular hospital contract certain infections during "
            "the course of their medical treatment, when compared to like hospitals. The "
            "CDC calculates a Standardized Infection Ratio (SIR) which may take into "
            "account the type of patient care location, number of patients with an existing "
            "infection, laboratory methods, hospital affiliation with a medical school, bed "
            "size of the hospital, patient age, and classification of patient health. SIRs "
            "are calculated for the hospital, the state, and the nation. Hospitals' SIRs "
            "are compared to the national benchmark to determine if hospitals' performance "
            "on these measures is better than the national benchmark (lower), no different "
            "than the national benchmark, or worse than the national benchmark (higher). "
            "The HAI measures apply to all patients treated in acute care hospitals, "
            "including adult, pediatric, neonatal, Medicare, and non-Medicare patients."
        ),
    ),
    MeasureEntry(
        measure_id="HAI_5_SIR",
        name="MRSA Bacteremia",
        group="INFECTIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's rate of drug-resistant MRSA bloodstream "
            "infections compares to what would be expected, where a number "
            "below 1.0 means fewer infections than expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="77hc-ibv8",
        cms_measure_definition=(
            "To receive payment from CMS, hospitals are required to report data about some "
            "infections to the Centers for Disease Control and Prevention's (CDC's) "
            "National Healthcare Safety Network (NHSN). The HAI measures show how often "
            "patients in a particular hospital contract certain infections during the "
            "course of their medical treatment, when compared to like hospitals. HAI "
            "measures provide information on infections that occur while the patient is in "
            "the hospital and include: central line-associated bloodstream infections "
            "(CLABSI), catheter-associated urinary tract infections (CAUTI), surgical site "
            "infection (SSI) from colon surgery or abdominal hysterectomy, "
            "methicillin-resistant Staphylococcus Aureus (MRSA) blood laboratory-identified "
            "events (bloodstream infections), and Clostridium difficile (C.diff.) "
            "laboratory-identified events (intestinal infections). The HAI measures show "
            "how often patients in a particular hospital contract certain infections during "
            "the course of their medical treatment, when compared to like hospitals. The "
            "CDC calculates a Standardized Infection Ratio (SIR) which may take into "
            "account the type of patient care location, number of patients with an existing "
            "infection, laboratory methods, hospital affiliation with a medical school, bed "
            "size of the hospital, patient age, and classification of patient health. SIRs "
            "are calculated for the hospital, the state, and the nation. Hospitals' SIRs "
            "are compared to the national benchmark to determine if hospitals' performance "
            "on these measures is better than the national benchmark (lower), no different "
            "than the national benchmark, or worse than the national benchmark (higher). "
            "The HAI measures apply to all patients treated in acute care hospitals, "
            "including adult, pediatric, neonatal, Medicare, and non-Medicare patients."
        ),
    ),
    MeasureEntry(
        measure_id="HAI_6_SIR",
        name="Clostridium Difficile (C.Diff)",
        group="INFECTIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's rate of C. diff intestinal infections "
            "compares to what would be expected, where a number below 1.0 "
            "means fewer infections than expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="77hc-ibv8",
        cms_measure_definition=(
            "To receive payment from CMS, hospitals are required to report data about some "
            "infections to the Centers for Disease Control and Prevention's (CDC's) "
            "National Healthcare Safety Network (NHSN). The HAI measures show how often "
            "patients in a particular hospital contract certain infections during the "
            "course of their medical treatment, when compared to like hospitals. HAI "
            "measures provide information on infections that occur while the patient is in "
            "the hospital and include: central line-associated bloodstream infections "
            "(CLABSI), catheter-associated urinary tract infections (CAUTI), surgical site "
            "infection (SSI) from colon surgery or abdominal hysterectomy, "
            "methicillin-resistant Staphylococcus Aureus (MRSA) blood laboratory-identified "
            "events (bloodstream infections), and Clostridium difficile (C.diff.) "
            "laboratory-identified events (intestinal infections). The HAI measures show "
            "how often patients in a particular hospital contract certain infections during "
            "the course of their medical treatment, when compared to like hospitals. The "
            "CDC calculates a Standardized Infection Ratio (SIR) which may take into "
            "account the type of patient care location, number of patients with an existing "
            "infection, laboratory methods, hospital affiliation with a medical school, bed "
            "size of the hospital, patient age, and classification of patient health. SIRs "
            "are calculated for the hospital, the state, and the nation. Hospitals' SIRs "
            "are compared to the national benchmark to determine if hospitals' performance "
            "on these measures is better than the national benchmark (lower), no different "
            "than the national benchmark, or worse than the national benchmark (higher). "
            "The HAI measures apply to all patients treated in acute care hospitals, "
            "including adult, pediatric, neonatal, Medicare, and non-Medicare patients."
        ),
    ),

    # ───────────────────────────────────────────────────────────────────
    # Unplanned Hospital Visits / Readmissions (632h-zaca) — 14 measures
    # Phase 0 reference: docs/phase_0_findings.md §7
    # ───────────────────────────────────────────────────────────────────

    # -- 30-Day Readmissions (6) --

    MeasureEntry(
        measure_id="READM_30_AMI",
        name="Acute Myocardial Infarction (AMI) 30-Day Readmission Rate",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare heart attack patients who had to "
            "return to a hospital within 30 days of leaving this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "The 30-day unplanned readmission measures are estimates of unplanned "
            "readmission to any acute care hospital within 30 days of discharge from a "
            "hospitalization for any cause related to medical conditions, including heart "
            "attack (AMI), heart failure (HF), pneumonia (PN), and chronic obstructive "
            "pulmonary disease (COPD). Hospitals' rates are compared to the national rate "
            "to determine if hospitals' performance on these measures is better than the "
            "national rate (lower), no different than the national rate (the same), or "
            "worse than the national rate (higher). For some hospitals, the number of cases "
            "is too small to reliably compare their results to the national average rate. "
            "The hospital return days measures (excess days in acute care or EDAC measures) "
            "add up the number of days patients spent back in the hospital (in the "
            "emergency department, under observation, or in an inpatient unit) within 30 "
            "days after they were first treated and released for AMI, HF, and pneumonia. "
            "The measures compare each hospital's return days to zero, which reflects the "
            "expectation that the hospital's \"days\" will be no different than an average "
            "performing hospital with a similar case mix. Readmission rates are provided in "
            "the downloadable databases and presented on the Care Compare on Medicare.gov "
            "website as percentages. Lower rates for readmission are better. Hospital "
            "return (EDAC) results are also provided in the downloadable databases but are "
            "presented in days per 100 discharges and can be negative, zero, or positive. A "
            "negative EDAC result is better and indicates that a hospital's patients spent "
            "fewer days in acute care than would be expected if admitted to an average "
            "performing hospital with the same case mix. A positive EDAC indicates a "
            "hospital's patients spent more days in acute care than would be expected, and "
            "an EDAC of zero indicates a hospital is performing exactly as expected."
        ),
    ),
    MeasureEntry(
        measure_id="READM_30_CABG",
        name="Rate of readmission for CABG",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare patients who had to return to a "
            "hospital within 30 days of coronary artery bypass graft "
            "(open-heart) surgery at this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "Measures of unplanned hospital visits show how often patients visit the "
            "hospital (in the emergency department, under observation, or in an inpatient "
            "hospital unit) after a procedure like coronary artery bypass graft (CABG) "
            "surgery, hip/knee replacement, colonoscopy, chemotherapy, and surgical "
            "procedures. The CABG surgery and hip/knee replacement readmission measures are "
            "estimates of unplanned readmission to any acute care hospital within 30 days "
            "after discharge from a hospitalization. The outpatient colonoscopy, "
            "chemotherapy and surgery measures are the risk-standardized hospital visit "
            "rates (ratio for surgery) after outpatient colonoscopy (per 1000 "
            "colonoscopies), chemotherapy (per 100 chemotherapy patients), and surgery "
            "procedures respectively. Hospitals' rates for the colonoscopy, chemotherapy, "
            "CABG surgery, and hip/knee replacement measures are compared to the national "
            "rate to determine if hospitals' performance is better than the national rate "
            "(lower), no different than the national rate (the same), or worse than the "
            "national rate (higher). Performance on the surgery measure is categorized as "
            "better, no different, or worse than expected by comparing against a ratio of "
            "one. Results are provided in the downloadable databases as decimals and "
            "typically indicate information that is presented on the Care Compare website. "
            "Lower percentages or ratios are better."
        ),
    ),
    MeasureEntry(
        measure_id="READM_30_COPD",
        name="Rate of readmission for chronic obstructive pulmonary disease (COPD) patients",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare COPD patients who had to return to "
            "a hospital within 30 days of leaving this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "The 30-day unplanned readmission measures are estimates of unplanned "
            "readmission to any acute care hospital within 30 days of discharge from a "
            "hospitalization for any cause related to medical conditions, including heart "
            "attack (AMI), heart failure (HF), pneumonia (PN), and chronic obstructive "
            "pulmonary disease (COPD). Hospitals' rates are compared to the national rate "
            "to determine if hospitals' performance on these measures is better than the "
            "national rate (lower), no different than the national rate (the same), or "
            "worse than the national rate (higher). For some hospitals, the number of cases "
            "is too small to reliably compare their results to the national average rate. "
            "The hospital return days measures (excess days in acute care or EDAC measures) "
            "add up the number of days patients spent back in the hospital (in the "
            "emergency department, under observation, or in an inpatient unit) within 30 "
            "days after they were first treated and released for AMI, HF, and pneumonia. "
            "The measures compare each hospital's return days to zero, which reflects the "
            "expectation that the hospital's \"days\" will be no different than an average "
            "performing hospital with a similar case mix. Readmission rates are provided in "
            "the downloadable databases and presented on the Care Compare on Medicare.gov "
            "website as percentages. Lower rates for readmission are better. Hospital "
            "return (EDAC) results are also provided in the downloadable databases but are "
            "presented in days per 100 discharges and can be negative, zero, or positive. A "
            "negative EDAC result is better and indicates that a hospital's patients spent "
            "fewer days in acute care than would be expected if admitted to an average "
            "performing hospital with the same case mix. A positive EDAC indicates a "
            "hospital's patients spent more days in acute care than would be expected, and "
            "an EDAC of zero indicates a hospital is performing exactly as expected."
        ),
    ),
    MeasureEntry(
        measure_id="READM_30_HF",
        name="Heart failure (HF) 30-Day Readmission Rate",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare heart failure patients who had to "
            "return to a hospital within 30 days of leaving this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "The 30-day unplanned readmission measures are estimates of unplanned "
            "readmission to any acute care hospital within 30 days of discharge from a "
            "hospitalization for any cause related to medical conditions, including heart "
            "attack (AMI), heart failure (HF), pneumonia (PN), and chronic obstructive "
            "pulmonary disease (COPD). Hospitals' rates are compared to the national rate "
            "to determine if hospitals' performance on these measures is better than the "
            "national rate (lower), no different than the national rate (the same), or "
            "worse than the national rate (higher). For some hospitals, the number of cases "
            "is too small to reliably compare their results to the national average rate. "
            "The hospital return days measures (excess days in acute care or EDAC measures) "
            "add up the number of days patients spent back in the hospital (in the "
            "emergency department, under observation, or in an inpatient unit) within 30 "
            "days after they were first treated and released for AMI, HF, and pneumonia. "
            "The measures compare each hospital's return days to zero, which reflects the "
            "expectation that the hospital's \"days\" will be no different than an average "
            "performing hospital with a similar case mix. Readmission rates are provided in "
            "the downloadable databases and presented on the Care Compare on Medicare.gov "
            "website as percentages. Lower rates for readmission are better. Hospital "
            "return (EDAC) results are also provided in the downloadable databases but are "
            "presented in days per 100 discharges and can be negative, zero, or positive. A "
            "negative EDAC result is better and indicates that a hospital's patients spent "
            "fewer days in acute care than would be expected if admitted to an average "
            "performing hospital with the same case mix. A positive EDAC indicates a "
            "hospital's patients spent more days in acute care than would be expected, and "
            "an EDAC of zero indicates a hospital is performing exactly as expected."
        ),
    ),
    MeasureEntry(
        measure_id="READM_30_HIP_KNEE",
        name="Rate of readmission after hip/knee replacement",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare patients who had to return to a "
            "hospital within 30 days of an elective hip or knee replacement "
            "at this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "Measures of unplanned hospital visits show how often patients visit the "
            "hospital (in the emergency department, under observation, or in an inpatient "
            "hospital unit) after a procedure like coronary artery bypass graft (CABG) "
            "surgery, hip/knee replacement, colonoscopy, chemotherapy, and surgical "
            "procedures. The CABG surgery and hip/knee replacement readmission measures are "
            "estimates of unplanned readmission to any acute care hospital within 30 days "
            "after discharge from a hospitalization. The outpatient colonoscopy, "
            "chemotherapy and surgery measures are the risk-standardized hospital visit "
            "rates (ratio for surgery) after outpatient colonoscopy (per 1000 "
            "colonoscopies), chemotherapy (per 100 chemotherapy patients), and surgery "
            "procedures respectively. Hospitals' rates for the colonoscopy, chemotherapy, "
            "CABG surgery, and hip/knee replacement measures are compared to the national "
            "rate to determine if hospitals' performance is better than the national rate "
            "(lower), no different than the national rate (the same), or worse than the "
            "national rate (higher). Performance on the surgery measure is categorized as "
            "better, no different, or worse than expected by comparing against a ratio of "
            "one. Results are provided in the downloadable databases as decimals and "
            "typically indicate information that is presented on the Care Compare website. "
            "Lower percentages or ratios are better."
        ),
    ),
    MeasureEntry(
        measure_id="READM_30_PN",
        name="Pneumonia (PN) 30-Day Readmission Rate",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of Medicare pneumonia patients who had to return "
            "to a hospital within 30 days of leaving this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "The 30-day unplanned readmission measures are estimates of unplanned "
            "readmission to any acute care hospital within 30 days of discharge from a "
            "hospitalization for any cause related to medical conditions, including heart "
            "attack (AMI), heart failure (HF), pneumonia (PN), and chronic obstructive "
            "pulmonary disease (COPD). Hospitals' rates are compared to the national rate "
            "to determine if hospitals' performance on these measures is better than the "
            "national rate (lower), no different than the national rate (the same), or "
            "worse than the national rate (higher). For some hospitals, the number of cases "
            "is too small to reliably compare their results to the national average rate. "
            "The hospital return days measures (excess days in acute care or EDAC measures) "
            "add up the number of days patients spent back in the hospital (in the "
            "emergency department, under observation, or in an inpatient unit) within 30 "
            "days after they were first treated and released for AMI, HF, and pneumonia. "
            "The measures compare each hospital's return days to zero, which reflects the "
            "expectation that the hospital's \"days\" will be no different than an average "
            "performing hospital with a similar case mix. Readmission rates are provided in "
            "the downloadable databases and presented on the Care Compare on Medicare.gov "
            "website as percentages. Lower rates for readmission are better. Hospital "
            "return (EDAC) results are also provided in the downloadable databases but are "
            "presented in days per 100 discharges and can be negative, zero, or positive. A "
            "negative EDAC result is better and indicates that a hospital's patients spent "
            "fewer days in acute care than would be expected if admitted to an average "
            "performing hospital with the same case mix. A positive EDAC indicates a "
            "hospital's patients spent more days in acute care than would be expected, and "
            "an EDAC of zero indicates a hospital is performing exactly as expected."
        ),
    ),

    # -- Excess Days in Acute Care (3) --

    MeasureEntry(
        measure_id="EDAC_30_AMI",
        name="Hospital return days for heart attack patients",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="days_per_100",
        plain_language=(
            "The number of extra days per 100 patients that Medicare heart "
            "attack patients spent back in acute care within 30 days of "
            "leaving this hospital, compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "The 30-day unplanned readmission measures are estimates of unplanned "
            "readmission to any acute care hospital within 30 days of discharge from a "
            "hospitalization for any cause related to medical conditions, including heart "
            "attack (AMI), heart failure (HF), pneumonia (PN), and chronic obstructive "
            "pulmonary disease (COPD). Hospitals' rates are compared to the national rate "
            "to determine if hospitals' performance on these measures is better than the "
            "national rate (lower), no different than the national rate (the same), or "
            "worse than the national rate (higher). For some hospitals, the number of cases "
            "is too small to reliably compare their results to the national average rate. "
            "The hospital return days measures (excess days in acute care or EDAC measures) "
            "add up the number of days patients spent back in the hospital (in the "
            "emergency department, under observation, or in an inpatient unit) within 30 "
            "days after they were first treated and released for AMI, HF, and pneumonia. "
            "The measures compare each hospital's return days to zero, which reflects the "
            "expectation that the hospital's \"days\" will be no different than an average "
            "performing hospital with a similar case mix. Readmission rates are provided in "
            "the downloadable databases and presented on the Care Compare on Medicare.gov "
            "website as percentages. Lower rates for readmission are better. Hospital "
            "return (EDAC) results are also provided in the downloadable databases but are "
            "presented in days per 100 discharges and can be negative, zero, or positive. A "
            "negative EDAC result is better and indicates that a hospital's patients spent "
            "fewer days in acute care than would be expected if admitted to an average "
            "performing hospital with the same case mix. A positive EDAC indicates a "
            "hospital's patients spent more days in acute care than would be expected, and "
            "an EDAC of zero indicates a hospital is performing exactly as expected."
        ),
    ),
    MeasureEntry(
        measure_id="EDAC_30_HF",
        name="Hospital return days for heart failure patients",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="days_per_100",
        plain_language=(
            "The number of extra days per 100 patients that Medicare heart "
            "failure patients spent back in acute care within 30 days of "
            "leaving this hospital, compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "The 30-day unplanned readmission measures are estimates of unplanned "
            "readmission to any acute care hospital within 30 days of discharge from a "
            "hospitalization for any cause related to medical conditions, including heart "
            "attack (AMI), heart failure (HF), pneumonia (PN), and chronic obstructive "
            "pulmonary disease (COPD). Hospitals' rates are compared to the national rate "
            "to determine if hospitals' performance on these measures is better than the "
            "national rate (lower), no different than the national rate (the same), or "
            "worse than the national rate (higher). For some hospitals, the number of cases "
            "is too small to reliably compare their results to the national average rate. "
            "The hospital return days measures (excess days in acute care or EDAC measures) "
            "add up the number of days patients spent back in the hospital (in the "
            "emergency department, under observation, or in an inpatient unit) within 30 "
            "days after they were first treated and released for AMI, HF, and pneumonia. "
            "The measures compare each hospital's return days to zero, which reflects the "
            "expectation that the hospital's \"days\" will be no different than an average "
            "performing hospital with a similar case mix. Readmission rates are provided in "
            "the downloadable databases and presented on the Care Compare on Medicare.gov "
            "website as percentages. Lower rates for readmission are better. Hospital "
            "return (EDAC) results are also provided in the downloadable databases but are "
            "presented in days per 100 discharges and can be negative, zero, or positive. A "
            "negative EDAC result is better and indicates that a hospital's patients spent "
            "fewer days in acute care than would be expected if admitted to an average "
            "performing hospital with the same case mix. A positive EDAC indicates a "
            "hospital's patients spent more days in acute care than would be expected, and "
            "an EDAC of zero indicates a hospital is performing exactly as expected."
        ),
    ),
    MeasureEntry(
        measure_id="EDAC_30_PN",
        name="Hospital return days for pneumonia patients",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="days_per_100",
        plain_language=(
            "The number of extra days per 100 patients that Medicare "
            "pneumonia patients spent back in acute care within 30 days "
            "of leaving this hospital, compared to what would be expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "The 30-day unplanned readmission measures are estimates of unplanned "
            "readmission to any acute care hospital within 30 days of discharge from a "
            "hospitalization for any cause related to medical conditions, including heart "
            "attack (AMI), heart failure (HF), pneumonia (PN), and chronic obstructive "
            "pulmonary disease (COPD). Hospitals' rates are compared to the national rate "
            "to determine if hospitals' performance on these measures is better than the "
            "national rate (lower), no different than the national rate (the same), or "
            "worse than the national rate (higher). For some hospitals, the number of cases "
            "is too small to reliably compare their results to the national average rate. "
            "The hospital return days measures (excess days in acute care or EDAC measures) "
            "add up the number of days patients spent back in the hospital (in the "
            "emergency department, under observation, or in an inpatient unit) within 30 "
            "days after they were first treated and released for AMI, HF, and pneumonia. "
            "The measures compare each hospital's return days to zero, which reflects the "
            "expectation that the hospital's \"days\" will be no different than an average "
            "performing hospital with a similar case mix. Readmission rates are provided in "
            "the downloadable databases and presented on the Care Compare on Medicare.gov "
            "website as percentages. Lower rates for readmission are better. Hospital "
            "return (EDAC) results are also provided in the downloadable databases but are "
            "presented in days per 100 discharges and can be negative, zero, or positive. A "
            "negative EDAC result is better and indicates that a hospital's patients spent "
            "fewer days in acute care than would be expected if admitted to an average "
            "performing hospital with the same case mix. A positive EDAC indicates a "
            "hospital's patients spent more days in acute care than would be expected, and "
            "an EDAC of zero indicates a hospital is performing exactly as expected."
        ),
    ),

    # -- Hospital-Wide Readmission (1) --

    MeasureEntry(
        measure_id="Hybrid_HWR",
        name="Hybrid Hospital-Wide All-Cause Readmission Measure (HWR)",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The overall percentage of Medicare patients who had to return "
            "to a hospital within 30 days of leaving this hospital, across "
            "all conditions, adjusted for how sick the patients were."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "The 30-day unplanned hospital-wide readmission measure is an estimate of "
            "unplanned readmission to any acute care hospital within 30 days of discharge "
            "from a hospitalization for any cause. The hospital-wide readmission measure "
            "includes all eligible medical, surgical and gynecological, neurological, "
            "cardiovascular, and cardiorespiratory admissions. Hospitals' rates are "
            "compared to the national rate to determine if hospitals' performance on this "
            "measure is better than the national rate (lower), no different than the "
            "national rate (the same), or worse than the national rate (higher). For some "
            "hospitals, the number of cases is too small to reliably compare their results "
            "to the national average rate. Rates are provided in the downloadable databases "
            "and presented on the Care Compare website as percentages. Lower rates are "
            "better."
        ),
    ),

    # -- Outpatient Unplanned Visit Measures (4) --

    MeasureEntry(
        measure_id="OP_32",
        name="Rate of unplanned hospital visits after colonoscopy (per 1,000 colonoscopies)",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often patients had to make an unplanned visit to a hospital "
            "or emergency room after having a colonoscopy at this hospital, "
            "per 1,000 colonoscopies."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "Measures of unplanned hospital visits show how often patients visit the "
            "hospital (in the emergency department, under observation, or in an inpatient "
            "hospital unit) after a procedure like coronary artery bypass graft (CABG) "
            "surgery, hip/knee replacement, colonoscopy, chemotherapy, and surgical "
            "procedures. The CABG surgery and hip/knee replacement readmission measures are "
            "estimates of unplanned readmission to any acute care hospital within 30 days "
            "after discharge from a hospitalization. The outpatient colonoscopy, "
            "chemotherapy and surgery measures are the risk-standardized hospital visit "
            "rates (ratio for surgery) after outpatient colonoscopy (per 1000 "
            "colonoscopies), chemotherapy (per 100 chemotherapy patients), and surgery "
            "procedures respectively. Hospitals' rates for the colonoscopy, chemotherapy, "
            "CABG surgery, and hip/knee replacement measures are compared to the national "
            "rate to determine if hospitals' performance is better than the national rate "
            "(lower), no different than the national rate (the same), or worse than the "
            "national rate (higher). Performance on the surgery measure is categorized as "
            "better, no different, or worse than expected by comparing against a ratio of "
            "one. Results are provided in the downloadable databases as decimals and "
            "typically indicate information that is presented on the Care Compare website. "
            "Lower percentages or ratios are better."
        ),
    ),
    MeasureEntry(
        measure_id="OP_35_ADM",
        name="Rate of inpatient admissions for patients receiving outpatient chemotherapy",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "How often patients receiving outpatient chemotherapy at this "
            "hospital had to be admitted to the hospital for an unplanned "
            "stay."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "Measures of unplanned hospital visits show how often patients visit the "
            "hospital (in the emergency department, under observation, or in an inpatient "
            "hospital unit) after a procedure like coronary artery bypass graft (CABG) "
            "surgery, hip/knee replacement, colonoscopy, chemotherapy, and surgical "
            "procedures. The CABG surgery and hip/knee replacement readmission measures are "
            "estimates of unplanned readmission to any acute care hospital within 30 days "
            "after discharge from a hospitalization. The outpatient colonoscopy, "
            "chemotherapy and surgery measures are the risk-standardized hospital visit "
            "rates (ratio for surgery) after outpatient colonoscopy (per 1000 "
            "colonoscopies), chemotherapy (per 100 chemotherapy patients), and surgery "
            "procedures respectively. Hospitals' rates for the colonoscopy, chemotherapy, "
            "CABG surgery, and hip/knee replacement measures are compared to the national "
            "rate to determine if hospitals' performance is better than the national rate "
            "(lower), no different than the national rate (the same), or worse than the "
            "national rate (higher). Performance on the surgery measure is categorized as "
            "better, no different, or worse than expected by comparing against a ratio of "
            "one. Results are provided in the downloadable databases as decimals and "
            "typically indicate information that is presented on the Care Compare website. "
            "Lower percentages or ratios are better."
        ),
    ),
    MeasureEntry(
        measure_id="OP_35_ED",
        name="Rate of emergency department (ED) visits for patients receiving outpatient chemotherapy",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "How often patients receiving outpatient chemotherapy at this "
            "hospital had to visit an emergency room."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "Measures of unplanned hospital visits show how often patients visit the "
            "hospital (in the emergency department, under observation, or in an inpatient "
            "hospital unit) after a procedure like coronary artery bypass graft (CABG) "
            "surgery, hip/knee replacement, colonoscopy, chemotherapy, and surgical "
            "procedures. The CABG surgery and hip/knee replacement readmission measures are "
            "estimates of unplanned readmission to any acute care hospital within 30 days "
            "after discharge from a hospitalization. The outpatient colonoscopy, "
            "chemotherapy and surgery measures are the risk-standardized hospital visit "
            "rates (ratio for surgery) after outpatient colonoscopy (per 1000 "
            "colonoscopies), chemotherapy (per 100 chemotherapy patients), and surgery "
            "procedures respectively. Hospitals' rates for the colonoscopy, chemotherapy, "
            "CABG surgery, and hip/knee replacement measures are compared to the national "
            "rate to determine if hospitals' performance is better than the national rate "
            "(lower), no different than the national rate (the same), or worse than the "
            "national rate (higher). Performance on the surgery measure is categorized as "
            "better, no different, or worse than expected by comparing against a ratio of "
            "one. Results are provided in the downloadable databases as decimals and "
            "typically indicate information that is presented on the Care Compare website. "
            "Lower percentages or ratios are better."
        ),
    ),
    MeasureEntry(
        measure_id="OP_36",
        name="Ratio of unplanned hospital visits after hospital outpatient surgery",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's rate of unplanned hospital visits after "
            "outpatient surgery compares to what would be expected, where "
            "a number below 1.0 means fewer unplanned visits than expected."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="632h-zaca",
        cms_measure_definition=(
            "Measures of unplanned hospital visits show how often patients visit the "
            "hospital (in the emergency department, under observation, or in an inpatient "
            "hospital unit) after a procedure like coronary artery bypass graft (CABG) "
            "surgery, hip/knee replacement, colonoscopy, chemotherapy, and surgical "
            "procedures. The CABG surgery and hip/knee replacement readmission measures are "
            "estimates of unplanned readmission to any acute care hospital within 30 days "
            "after discharge from a hospitalization. The outpatient colonoscopy, "
            "chemotherapy and surgery measures are the risk-standardized hospital visit "
            "rates (ratio for surgery) after outpatient colonoscopy (per 1000 "
            "colonoscopies), chemotherapy (per 100 chemotherapy patients), and surgery "
            "procedures respectively. Hospitals' rates for the colonoscopy, chemotherapy, "
            "CABG surgery, and hip/knee replacement measures are compared to the national "
            "rate to determine if hospitals' performance is better than the national rate "
            "(lower), no different than the national rate (the same), or worse than the "
            "national rate (higher). Performance on the surgery measure is categorized as "
            "better, no different, or worse than expected by comparing against a ratio of "
            "one. Results are provided in the downloadable databases as decimals and "
            "typically indicate information that is presented on the Care Compare website. "
            "Lower percentages or ratios are better."
        ),
    ),

    # ───────────────────────────────────────────────────────────────────
    # Timely and Effective Care (yv7e-xc69) — 30 measures
    # Phase 0 reference: docs/phase_0_findings.md §3
    # ───────────────────────────────────────────────────────────────────

    # -- Emergency Department Volume (1) --

    MeasureEntry(
        measure_id="EDV",
        name="Emergency department volume",
        group="TIMELY_EFFECTIVE_CARE",
        direction=None,  # contextual volume classification, not quality
        unit="category",
        plain_language=(
            "Whether this hospital's emergency department sees a very high, "
            "high, medium, or low number of patients."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- ED Wait Time Measures (4) --

    MeasureEntry(
        measure_id="OP_18a",
        name="Average (median) time all patients spent in the emergency department before leaving",
        group="TIMELY_EFFECTIVE_CARE",
        direction="LOWER_IS_BETTER",
        unit="minutes",
        plain_language=(
            "The typical number of minutes all patients spent in this "
            "hospital's emergency department before leaving."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="OP_18b",
        name="Average (median) time patients spent in the emergency department before leaving from the visit — patients admitted",
        group="TIMELY_EFFECTIVE_CARE",
        direction="LOWER_IS_BETTER",
        unit="minutes",
        plain_language=(
            "The typical number of minutes patients who were admitted to "
            "this hospital spent waiting in the emergency department."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="OP_18c",
        name="Average (median) time patients spent in the emergency department before leaving from the visit — patients discharged",
        group="TIMELY_EFFECTIVE_CARE",
        direction="LOWER_IS_BETTER",
        unit="minutes",
        plain_language=(
            "The typical number of minutes patients who were sent home "
            "spent in this hospital's emergency department."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="OP_18d",
        name="Average (median) time transfer patients spent in the emergency department before leaving",
        group="TIMELY_EFFECTIVE_CARE",
        direction="LOWER_IS_BETTER",
        unit="minutes",
        plain_language=(
            "The typical number of minutes patients who were transferred "
            "to another hospital spent waiting in this hospital's "
            "emergency department."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- ED Process Measures (2) --

    MeasureEntry(
        measure_id="OP_22",
        name="Left before being seen",
        group="TIMELY_EFFECTIVE_CARE",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients who left this hospital's emergency "
            "department without being seen by a doctor or other provider."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="OP_23",
        name="Head CT results",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients with stroke symptoms who received "
            "brain imaging results within 45 minutes of arriving at this "
            "hospital's emergency department."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- Hospital Harm Measures (3) --

    MeasureEntry(
        measure_id="HH_HYPER",
        name="Hospital Harm - Severe Hyperglycemia",
        group="TIMELY_EFFECTIVE_CARE",
        direction="LOWER_IS_BETTER",
        unit="percent",  # TODO: Confirm unit — rate per 1,000 patient-days or percentage
        plain_language=(
            "How often patients at this hospital experienced dangerously "
            "high blood sugar levels during their stay."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="HH_HYPO",
        name="Hospital Harm - Severe Hypoglycemia",
        group="TIMELY_EFFECTIVE_CARE",
        direction="LOWER_IS_BETTER",
        unit="percent",  # TODO: Confirm unit — rate per 1,000 patient-days or percentage
        plain_language=(
            "How often patients at this hospital experienced dangerously "
            "low blood sugar levels during their stay."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="HH_ORAE",
        name="Hospital Harm - Opioid Related Adverse Events",
        group="TIMELY_EFFECTIVE_CARE",
        direction="LOWER_IS_BETTER",
        unit="percent",  # TODO: Confirm unit — same as HH_HYPER/HH_HYPO
        plain_language=(
            "How often patients at this hospital experienced serious side "
            "effects from opioid pain medications during their stay, such "
            "as difficulty breathing."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- Safe Use of Opioids (1) --

    MeasureEntry(
        measure_id="SAFE_USE_OF_OPIOIDS",
        name="Safe Use of Opioids - Concurrent Prescribing",
        group="TIMELY_EFFECTIVE_CARE",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients at this hospital who were given "
            "multiple opioid prescriptions at the same time, which "
            "increases the risk of overdose."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- Sepsis Treatment Measures (5) --

    MeasureEntry(
        measure_id="SEP_1",
        name="Appropriate care for severe sepsis and septic shock",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients with severe sepsis or septic shock "
            "who received all recommended treatments within the required "
            "timeframes at this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="SEP_SH_3HR",
        name="Septic Shock 3-Hour Bundle",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of septic shock patients who received critical "
            "treatments — blood tests, antibiotics — within 3 hours at "
            "this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="SEP_SH_6HR",
        name="Septic Shock 6-Hour Bundle",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of septic shock patients who received all "
            "recommended follow-up treatments within 6 hours at this "
            "hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="SEV_SEP_3HR",
        name="Severe Sepsis 3-Hour Bundle",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of severe sepsis patients who received critical "
            "initial treatments within 3 hours at this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="SEV_SEP_6HR",
        name="Severe Sepsis 6-Hour Bundle",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of severe sepsis patients who received all "
            "recommended follow-up treatments within 6 hours at this "
            "hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- Stroke Treatment Measures (3) --

    MeasureEntry(
        measure_id="STK_02",
        name="Discharged on Antithrombotic Therapy",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of stroke patients who were prescribed blood "
            "clot prevention medication when they left this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="STK_03",
        name="Anticoagulation Therapy for Atrial Fibrillation/Flutter",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of stroke patients with an irregular heartbeat "
            "(atrial fibrillation) who were prescribed blood-thinning "
            "medication when they left this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="STK_05",
        name="Antithrombotic Therapy by End of Hospital Day 2",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of stroke patients who received blood clot "
            "prevention medication within 2 days of being admitted to "
            "this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- VTE Prophylaxis Measures (2) --

    MeasureEntry(
        measure_id="VTE_1",
        name="Venous Thromboembolism Prophylaxis",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients at this hospital who received "
            "appropriate blood clot prevention measures during their stay."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="VTE_2",
        name="Intensive Care Unit Venous Thromboembolism Prophylaxis",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of ICU patients at this hospital who received "
            "appropriate blood clot prevention measures."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- STEMI Treatment (1) --

    MeasureEntry(
        measure_id="OP_40",
        name="ST-Segment Elevation Myocardial Infarction (STEMI)",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",  # TODO: Confirm exact measure definition from CMS technical specs
        plain_language=(
            "The percentage of heart attack (STEMI) patients who received "
            "emergency artery-opening treatment within the recommended "
            "timeframe at this hospital."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- Vaccination (1) --

    MeasureEntry(
        measure_id="IMM_3",
        name="Healthcare workers given influenza vaccination",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of healthcare workers at this hospital who "
            "received an influenza (flu) vaccination."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- Outpatient Procedure Measures (2) --

    MeasureEntry(
        measure_id="OP_29",
        name="Endoscopy/polyp surveillance: appropriate follow-up interval for normal colonoscopy",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients with a normal colonoscopy result "
            "who were recommended an appropriate follow-up timeframe, "
            "rather than being brought back too soon."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="OP_31",
        name="Improvement in Patient's Visual Function within 90 Days Following Cataract Surgery",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients whose vision improved within 90 "
            "days after cataract surgery at this hospital."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # -- Global Malnutrition Composite Score (5) --

    MeasureEntry(
        measure_id="GMCS",
        name="Global Malnutrition Composite Score",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "An overall score for how well this hospital screens patients "
            "for malnutrition and provides nutritional care to those who "
            "need it."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="GMCS_Malnutrition_Screening",
        name="Global Malnutrition Composite Score: Malnutrition Risk Screening",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients at this hospital who were screened "
            "for malnutrition risk during their stay."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="GMCS_Nutrition_Assessment",
        name="Global Malnutrition Composite Score: Nutrition Assessment",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients identified as at-risk for "
            "malnutrition who received a full nutrition assessment at "
            "this hospital."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="GMCS_Malnutrition_Diagnosis_Documented",
        name="Global Malnutrition Composite Score: Malnutrition Diagnosis Documented",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients with malnutrition at this hospital "
            "who had a malnutrition diagnosis formally documented in their "
            "medical record."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),
    MeasureEntry(
        measure_id="GMCS_Nutritional_Care_Plan",
        name="Global Malnutrition Composite Score: Nutritional Care Plan",
        group="TIMELY_EFFECTIVE_CARE",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients diagnosed with malnutrition at "
            "this hospital who received a nutritional care plan."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="yv7e-xc69",
        cms_measure_definition=(
            "The measures of timely and effective care (also known as \"process of care\" "
            "measures) show the percentage of hospital patients who got treatments known to "
            "get the best results for certain common, serious medical conditions or "
            "surgical procedures; how quickly hospitals treat patients who come to the "
            "hospital with certain medical emergencies; and how well hospitals provide "
            "preventive services. These measures only apply to patients for whom the "
            "recommended treatment would be appropriate. The measures of timely and "
            "effective care apply to adults and children treated at hospitals paid under "
            "the Inpatient Prospective Payment System (IPPS) or the Outpatient Prospective "
            "Payment System (OPPS), as well as those that voluntarily report data on "
            "measures for whom the recommended treatments would be appropriate including: "
            "Medicare patients, Medicare managed care patients, and non-Medicare patients. "
            "Timely and effective care measures include severe sepsis and septic shock, "
            "COVID-19 Vaccination, cataract care follow-up, colonoscopy follow-up, heart "
            "attack care, preventive care, cancer care measures, stroke, venous "
            "thromboembolism, hospital harm, and ST-Segment Elevation Myocardial "
            "Infarction."
        ),
    ),

    # ───────────────────────────────────────────────────────────────────
    # HCAHPS Patient Survey (dgck-syfz) — 68 measures
    # Phase 0 reference: docs/phase_0_findings.md §4
    #
    # API uses `hcahps_measure_id` (not `measure_id`).
    # Middlebox measures (*_U_P, *_PY, *_7_8) have direction=None.
    # All: ses_sensitivity=LOW, tail_risk_flag=False.
    # ───────────────────────────────────────────────────────────────────

    # === Nurse Communication (H_COMP_1) ===

    MeasureEntry(
        measure_id="H_COMP_1_A_P",
        name='Patients who reported that their nurses "Always" communicated well',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their nurses always communicated well at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_1_U_P",
        name='Patients who reported that their nurses "Usually" communicated well',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said their nurses usually communicated well at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_1_SN_P",
        name='Patients who reported that their nurses "Sometimes" or "Never" communicated well',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their nurses sometimes or never communicated well at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_1_LINEAR_SCORE",
        name="Nurse communication - linear mean score",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="An overall score for how well nurses communicated with patients at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_1_STAR_RATING",
        name="Nurse communication - star rating",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="The star rating (1-5) for how well nurses communicated with patients at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Doctor Communication (H_COMP_2) ===

    MeasureEntry(
        measure_id="H_COMP_2_A_P",
        name='Patients who reported that their doctors "Always" communicated well',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their doctors always communicated well at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_2_U_P",
        name='Patients who reported that their doctors "Usually" communicated well',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said their doctors usually communicated well at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_2_SN_P",
        name='Patients who reported that their doctors "Sometimes" or "Never" communicated well',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their doctors sometimes or never communicated well at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_2_LINEAR_SCORE",
        name="Doctor communication - linear mean score",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="An overall score for how well doctors communicated with patients at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_2_STAR_RATING",
        name="Doctor communication - star rating",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="The star rating (1-5) for how well doctors communicated with patients at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Communication about Medicines (H_COMP_5) ===

    MeasureEntry(
        measure_id="H_COMP_5_A_P",
        name='Patients who reported that staff "Always" explained about medicines before giving them',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said staff always explained their medications before giving them at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_5_U_P",
        name='Patients who reported that staff "Usually" explained about medicines before giving them',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said staff usually explained their medications before giving them at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_5_SN_P",
        name='Patients who reported that staff "Sometimes" or "Never" explained about medicines',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said staff sometimes or never explained their medications before giving them at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_5_LINEAR_SCORE",
        name="Communication about medicines - linear mean score",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="An overall score for how well staff communicated about medications at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_5_STAR_RATING",
        name="Communication about medicines - star rating",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="The star rating (1-5) for how well staff communicated about medications at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Discharge Information (H_COMP_6) ===

    MeasureEntry(
        measure_id="H_COMP_6_Y_P",
        name="Patients who reported YES, they were given information about what to do during recovery",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said they were given information about what to do during their recovery at home.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_6_N_P",
        name="Patients who reported NO, they were not given information about what to do during recovery",
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said they were not given information about what to do during their recovery at home.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_6_LINEAR_SCORE",
        name="Discharge information - linear mean score",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="An overall score for how well this hospital provided discharge information to patients.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_COMP_6_STAR_RATING",
        name="Discharge information - star rating",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="The star rating (1-5) for how well this hospital provided discharge information to patients.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Discharge Help (H_DISCH_HELP) ===

    MeasureEntry(
        measure_id="H_DISCH_HELP_Y_P",
        name="Patients who reported YES, they did discuss whether they would need help after discharge",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said staff discussed whether they would need help after leaving this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_DISCH_HELP_N_P",
        name="Patients who reported NO, they did not discuss whether they would need help after discharge",
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said staff did not discuss whether they would need help after leaving this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Symptoms Information (H_SYMPTOMS) ===

    MeasureEntry(
        measure_id="H_SYMPTOMS_Y_P",
        name="Patients who reported YES, they did receive written information about possible symptoms",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said they received written information about symptoms to watch for after leaving this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_SYMPTOMS_N_P",
        name="Patients who reported NO, they did not receive written information about possible symptoms",
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said they did not receive written information about symptoms to watch for after leaving this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Cleanliness (H_CLEAN) ===

    MeasureEntry(
        measure_id="H_CLEAN_HSP_A_P",
        name='Patients who reported that their room and bathroom were "Always" clean',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their room and bathroom were always clean at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_CLEAN_HSP_U_P",
        name='Patients who reported that their room and bathroom were "Usually" clean',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said their room and bathroom were usually clean at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_CLEAN_HSP_SN_P",
        name='Patients who reported that their room and bathroom were "Sometimes" or "Never" clean',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their room and bathroom were sometimes or never clean at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_CLEAN_LINEAR_SCORE",
        name="Cleanliness - linear mean score",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="An overall score for the cleanliness of rooms and bathrooms at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_CLEAN_STAR_RATING",
        name="Cleanliness - star rating",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="The star rating (1-5) for the cleanliness of rooms and bathrooms at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Quietness (H_QUIET) ===

    MeasureEntry(
        measure_id="H_QUIET_HSP_A_P",
        name='Patients who reported that the area around their room was "Always" quiet at night',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said the area around their room was always quiet at night at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_QUIET_HSP_U_P",
        name='Patients who reported that the area around their room was "Usually" quiet at night',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said the area around their room was usually quiet at night at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_QUIET_HSP_SN_P",
        name='Patients who reported that the area around their room was "Sometimes" or "Never" quiet at night',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said the area around their room was sometimes or never quiet at night at this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_QUIET_LINEAR_SCORE",
        name="Quietness - linear mean score",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="An overall score for how quiet the hospital was at night.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_QUIET_STAR_RATING",
        name="Quietness - star rating",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="The star rating (1-5) for how quiet the hospital was at night.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Overall Hospital Rating (H_HSP_RATING) ===

    MeasureEntry(
        measure_id="H_HSP_RATING_9_10",
        name="Patients who gave their hospital a rating of 9 or 10 (high)",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who gave this hospital a rating of 9 or 10 out of 10.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_HSP_RATING_7_8",
        name="Patients who gave their hospital a rating of 7 or 8 (medium)",
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who gave this hospital a rating of 7 or 8 out of 10.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_HSP_RATING_0_6",
        name="Patients who gave their hospital a rating of 6 or lower (low)",
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who gave this hospital a rating of 6 or lower out of 10.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_HSP_RATING_LINEAR_SCORE",
        name="Overall hospital rating - linear mean score",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="An overall score for how patients rated this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_HSP_RATING_STAR_RATING",
        name="Overall hospital rating - star rating",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="The star rating (1-5) for how patients rated this hospital overall.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Recommend Hospital (H_RECMND) ===

    MeasureEntry(
        measure_id="H_RECMND_DY",
        name="Patients who reported YES, they would definitely recommend the hospital",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said they would definitely recommend this hospital to friends and family.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_RECMND_PY",
        name="Patients who reported YES, they would probably recommend the hospital",
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said they would probably recommend this hospital to friends and family.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_RECMND_DN",
        name="Patients who reported NO, they would probably not or definitely not recommend the hospital",
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said they would probably not or definitely not recommend this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_RECMND_LINEAR_SCORE",
        name="Recommend hospital - linear mean score",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="An overall score for how likely patients would be to recommend this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_RECMND_STAR_RATING",
        name="Recommend hospital - star rating",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="The star rating (1-5) for how likely patients would be to recommend this hospital.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Doctor Sub-Questions (H_DOCTOR_EXPLAIN, LISTEN, RESPECT) ===

    MeasureEntry(
        measure_id="H_DOCTOR_EXPLAIN_A_P",
        name='Patients who reported that their doctors "Always" explained things in a way they could understand',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their doctors always explained things in a way they could understand.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_DOCTOR_EXPLAIN_U_P",
        name='Patients who reported that their doctors "Usually" explained things in a way they could understand',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said their doctors usually explained things in a way they could understand.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_DOCTOR_EXPLAIN_SN_P",
        name='Patients who reported that their doctors "Sometimes" or "Never" explained things in a way they could understand',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their doctors sometimes or never explained things in a way they could understand.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_DOCTOR_LISTEN_A_P",
        name='Patients who reported that their doctors "Always" listened carefully to them',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their doctors always listened carefully to them.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_DOCTOR_LISTEN_U_P",
        name='Patients who reported that their doctors "Usually" listened carefully to them',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said their doctors usually listened carefully to them.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_DOCTOR_LISTEN_SN_P",
        name='Patients who reported that their doctors "Sometimes" or "Never" listened carefully to them',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their doctors sometimes or never listened carefully to them.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_DOCTOR_RESPECT_A_P",
        name='Patients who reported that their doctors "Always" treated them with courtesy and respect',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their doctors always treated them with courtesy and respect.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_DOCTOR_RESPECT_U_P",
        name='Patients who reported that their doctors "Usually" treated them with courtesy and respect',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said their doctors usually treated them with courtesy and respect.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_DOCTOR_RESPECT_SN_P",
        name='Patients who reported that their doctors "Sometimes" or "Never" treated them with courtesy and respect',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their doctors sometimes or never treated them with courtesy and respect.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Nurse Sub-Questions (H_NURSE_EXPLAIN, LISTEN, RESPECT) ===

    MeasureEntry(
        measure_id="H_NURSE_EXPLAIN_A_P",
        name='Patients who reported that their nurses "Always" explained things in a way they could understand',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their nurses always explained things in a way they could understand.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_NURSE_EXPLAIN_U_P",
        name='Patients who reported that their nurses "Usually" explained things in a way they could understand',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said their nurses usually explained things in a way they could understand.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_NURSE_EXPLAIN_SN_P",
        name='Patients who reported that their nurses "Sometimes" or "Never" explained things in a way they could understand',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their nurses sometimes or never explained things in a way they could understand.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_NURSE_LISTEN_A_P",
        name='Patients who reported that their nurses "Always" listened carefully to them',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their nurses always listened carefully to them.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_NURSE_LISTEN_U_P",
        name='Patients who reported that their nurses "Usually" listened carefully to them',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said their nurses usually listened carefully to them.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_NURSE_LISTEN_SN_P",
        name='Patients who reported that their nurses "Sometimes" or "Never" listened carefully to them',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their nurses sometimes or never listened carefully to them.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_NURSE_RESPECT_A_P",
        name='Patients who reported that their nurses "Always" treated them with courtesy and respect',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their nurses always treated them with courtesy and respect.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_NURSE_RESPECT_U_P",
        name='Patients who reported that their nurses "Usually" treated them with courtesy and respect',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said their nurses usually treated them with courtesy and respect.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_NURSE_RESPECT_SN_P",
        name='Patients who reported that their nurses "Sometimes" or "Never" treated them with courtesy and respect',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said their nurses sometimes or never treated them with courtesy and respect.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Medication Communication Sub-Questions (H_MED_FOR, H_SIDE_EFFECTS) ===

    MeasureEntry(
        measure_id="H_MED_FOR_A_P",
        name='Patients who reported that when receiving new medication the staff "Always" communicated what it was for',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said staff always told them what new medications were for.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_MED_FOR_U_P",
        name='Patients who reported that when receiving new medication the staff "Usually" communicated what it was for',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said staff usually told them what new medications were for.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_MED_FOR_SN_P",
        name='Patients who reported that when receiving new medication the staff "Sometimes" or "Never" communicated what it was for',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said staff sometimes or never told them what new medications were for.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_SIDE_EFFECTS_A_P",
        name='Patients who reported that when receiving new medication the staff "Always" discussed possible side effects',
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said staff always told them about possible side effects of new medications.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_SIDE_EFFECTS_U_P",
        name='Patients who reported that when receiving new medication the staff "Usually" discussed possible side effects',
        group="PATIENT_EXPERIENCE", direction=None, unit="percent",
        plain_language="The percentage of patients who said staff usually told them about possible side effects of new medications.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),
    MeasureEntry(
        measure_id="H_SIDE_EFFECTS_SN_P",
        name='Patients who reported that when receiving new medication the staff "Sometimes" or "Never" discussed possible side effects',
        group="PATIENT_EXPERIENCE", direction="LOWER_IS_BETTER", unit="percent",
        plain_language="The percentage of patients who said staff sometimes or never told them about possible side effects of new medications.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # === Summary Star Rating (H_STAR_RATING) ===

    MeasureEntry(
        measure_id="H_STAR_RATING",
        name="Summary star rating",
        group="PATIENT_EXPERIENCE", direction="HIGHER_IS_BETTER", unit="score",
        plain_language="The overall patient experience star rating (1-5) for this hospital based on all HCAHPS survey responses.",
        tail_risk_flag=False, ses_sensitivity="MODERATE", dataset_id="dgck-syfz",
        cms_measure_definition=(
            "The HCAHPS Patient Survey, also known as the CAHPS Hospital Survey or Hospital "
            "CAHPS, is a survey instrument and data collection methodology for measuring "
            "patients' perceptions of their hospital experience. The survey is administered "
            "to a random sample of adult inpatients after discharge. The HCAHPS survey "
            "contains patient perspectives on care and patient rating items that encompass "
            "key topics: communication with hospital staff, responsiveness of hospital "
            "staff, communication about medicines, discharge information, cleanliness of "
            "hospital environment, quietness of hospital environment, and transition of "
            "care. The survey also includes screening questions and demographic items, "
            "which are used for adjusting the mix of patients across hospitals and for "
            "analytic purposes."
        ),
    ),

    # ───────────────────────────────────────────────────────────────────
    # Outpatient Imaging Efficiency (wkfw-kthe) — 4 measures
    # Phase 0 reference: docs/phase_0_findings.md §8
    # Note: measure_id uses hyphen format (OP-8, OP-10, OP-13, OP-39)
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="OP-8",
        name="MRI Lumbar Spine for Low Back Pain",
        group="IMAGING_EFFICIENCY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of lower back MRI scans at this hospital that "
            "may have been done too soon, before trying simpler treatments "
            "first."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="wkfw-kthe",
        cms_measure_definition=(
            "CMS has adopted three measures which capture the quality of outpatient care in "
            "the area of imaging. CMS notes that the purpose of these measures is to "
            "promote high-quality efficient care. Each of the measures currently utilize "
            "both the Hospital OPPS claims and Physician Part B claims in the calculations. "
            "These calculations are based on the administrative claims of the Medicare "
            "fee-for-service population. Hospitals do not submit additional data for these "
            "measures. The measures on the use of medical imaging show how often a hospital "
            "provides specific imaging tests for Medicare beneficiaries under circumstances "
            "where they may not be medically appropriate. Lower percentages suggest more "
            "efficient use of medical imaging. The purpose of reporting these measures is "
            "to reduce unnecessary exposure to contrast materials and/or radiation, to "
            "ensure adherence to evidence-based medicine and practice guidelines, and to "
            "prevent wasteful use of Medicare resources. The measures only apply to "
            "Medicare patients treated in hospital outpatient departments."
        ),
    ),
    MeasureEntry(
        measure_id="OP-10",
        name="Abdomen CT Use of Contrast Material",
        group="IMAGING_EFFICIENCY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of abdominal CT scans at this hospital where "
            "the scan was done twice — once with and once without contrast "
            "dye — which may expose patients to unnecessary radiation."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="wkfw-kthe",
        cms_measure_definition=(
            "CMS has adopted three measures which capture the quality of outpatient care in "
            "the area of imaging. CMS notes that the purpose of these measures is to "
            "promote high-quality efficient care. Each of the measures currently utilize "
            "both the Hospital OPPS claims and Physician Part B claims in the calculations. "
            "These calculations are based on the administrative claims of the Medicare "
            "fee-for-service population. Hospitals do not submit additional data for these "
            "measures. The measures on the use of medical imaging show how often a hospital "
            "provides specific imaging tests for Medicare beneficiaries under circumstances "
            "where they may not be medically appropriate. Lower percentages suggest more "
            "efficient use of medical imaging. The purpose of reporting these measures is "
            "to reduce unnecessary exposure to contrast materials and/or radiation, to "
            "ensure adherence to evidence-based medicine and practice guidelines, and to "
            "prevent wasteful use of Medicare resources. The measures only apply to "
            "Medicare patients treated in hospital outpatient departments."
        ),
    ),
    MeasureEntry(
        measure_id="OP-13",
        name="Outpatients who got cardiac imaging stress tests before low-risk outpatient surgery",
        group="IMAGING_EFFICIENCY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients who had a heart stress test before "
            "low-risk outpatient surgery at this hospital, when guidelines "
            "say one was likely not needed."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="wkfw-kthe",
        cms_measure_definition=(
            "CMS has adopted three measures which capture the quality of outpatient care in "
            "the area of imaging. CMS notes that the purpose of these measures is to "
            "promote high-quality efficient care. Each of the measures currently utilize "
            "both the Hospital OPPS claims and Physician Part B claims in the calculations. "
            "These calculations are based on the administrative claims of the Medicare "
            "fee-for-service population. Hospitals do not submit additional data for these "
            "measures. The measures on the use of medical imaging show how often a hospital "
            "provides specific imaging tests for Medicare beneficiaries under circumstances "
            "where they may not be medically appropriate. Lower percentages suggest more "
            "efficient use of medical imaging. The purpose of reporting these measures is "
            "to reduce unnecessary exposure to contrast materials and/or radiation, to "
            "ensure adherence to evidence-based medicine and practice guidelines, and to "
            "prevent wasteful use of Medicare resources. The measures only apply to "
            "Medicare patients treated in hospital outpatient departments."
        ),
    ),
    MeasureEntry(
        measure_id="OP-39",
        name="Breast Cancer Screening Recall Rates",
        group="IMAGING_EFFICIENCY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of breast cancer screening mammograms at this "
            "hospital that led to a recommendation for additional imaging "
            "or testing."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="wkfw-kthe",
        cms_measure_definition=(
            "CMS has adopted three measures which capture the quality of outpatient care in "
            "the area of imaging. CMS notes that the purpose of these measures is to "
            "promote high-quality efficient care. Each of the measures currently utilize "
            "both the Hospital OPPS claims and Physician Part B claims in the calculations. "
            "These calculations are based on the administrative claims of the Medicare "
            "fee-for-service population. Hospitals do not submit additional data for these "
            "measures. The measures on the use of medical imaging show how often a hospital "
            "provides specific imaging tests for Medicare beneficiaries under circumstances "
            "where they may not be medically appropriate. Lower percentages suggest more "
            "efficient use of medical imaging. The purpose of reporting these measures is "
            "to reduce unnecessary exposure to contrast materials and/or radiation, to "
            "ensure adherence to evidence-based medicine and practice guidelines, and to "
            "prevent wasteful use of Medicare resources. The measures only apply to "
            "Medicare patients treated in hospital outpatient departments."
        ),
    ),

    # ───────────────────────────────────────────────────────────────────
    # Medicare Spending Per Patient (rrqw-56er) — 1 measure
    # Phase 0 reference: docs/phase_0_findings.md §9
    # Note: measure_id uses hyphen format (MSPB-1)
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="MSPB-1",
        name="Medicare hospital spending per patient (Medicare Spending per Beneficiary)",
        group="SPENDING",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's Medicare spending per patient compares "
            "to the national median, where a number below 1.0 means the "
            "hospital spends less than typical."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="rrqw-56er",
        cms_measure_definition=(
            "The Medicare Spending Per Beneficiary (MSPB-1) Measure assesses Medicare Part "
            "A and Part B payments for services provided to a Medicare beneficiary during a "
            "spending-per-beneficiary episode that spans from three days prior to an "
            "inpatient hospital admission through 30 days after discharge. The payments "
            "included in this measure are price-standardized and risk-adjusted."
        ),
    ),

    # ───────────────────────────────────────────────────────────────────
    # HRRP Condition-Specific Excess Readmission Ratios (9n3s-kdb3)
    # Phase 0 reference: docs/phase_0_findings.md §9
    # These are hospital-level performance measures stored in
    # provider_measure_values, not program-level outcomes.
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="HRRP_AMI",
        name="Excess Readmission Ratio — AMI (HRRP)",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's heart attack readmission rate compares "
            "to what would be expected given its patient mix. A ratio below "
            "1.0 means fewer readmissions than expected."
        ),
        tail_risk_flag=False,
        ses_sensitivity="HIGH",
        dataset_id="9n3s-kdb3",
        cms_measure_definition=(
            "In October 2012, CMS began reducing Medicare payments for subsection(d) "
            "hospitals with excess readmissions. Excess readmissions are measured by a "
            "ratio, calculated by dividing a hospital's predicted rate of readmission for "
            "heart attack (AMI), heart failure (HF), pneumonia, chronic obstructive "
            "pulmonary disease (COPD), hip/knee replacement (THA/TKA), and coronary artery "
            "bypass graft (CABG) surgery by the expected rate of readmission, based on an "
            "average hospital with similar patients."
        ),
    ),
    MeasureEntry(
        measure_id="HRRP_CABG",
        name="Excess Readmission Ratio — CABG (HRRP)",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's coronary artery bypass surgery readmission "
            "rate compares to what would be expected given its patient mix."
        ),
        tail_risk_flag=False,
        ses_sensitivity="HIGH",
        dataset_id="9n3s-kdb3",
        cms_measure_definition=(
            "In October 2012, CMS began reducing Medicare payments for subsection(d) "
            "hospitals with excess readmissions. Excess readmissions are measured by a "
            "ratio, calculated by dividing a hospital's predicted rate of readmission for "
            "heart attack (AMI), heart failure (HF), pneumonia, chronic obstructive "
            "pulmonary disease (COPD), hip/knee replacement (THA/TKA), and coronary artery "
            "bypass graft (CABG) surgery by the expected rate of readmission, based on an "
            "average hospital with similar patients."
        ),
    ),
    MeasureEntry(
        measure_id="HRRP_COPD",
        name="Excess Readmission Ratio — COPD (HRRP)",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's COPD readmission rate compares to what "
            "would be expected given its patient mix."
        ),
        tail_risk_flag=False,
        ses_sensitivity="HIGH",
        dataset_id="9n3s-kdb3",
        cms_measure_definition=(
            "In October 2012, CMS began reducing Medicare payments for subsection(d) "
            "hospitals with excess readmissions. Excess readmissions are measured by a "
            "ratio, calculated by dividing a hospital's predicted rate of readmission for "
            "heart attack (AMI), heart failure (HF), pneumonia, chronic obstructive "
            "pulmonary disease (COPD), hip/knee replacement (THA/TKA), and coronary artery "
            "bypass graft (CABG) surgery by the expected rate of readmission, based on an "
            "average hospital with similar patients."
        ),
    ),
    MeasureEntry(
        measure_id="HRRP_HF",
        name="Excess Readmission Ratio — Heart Failure (HRRP)",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's heart failure readmission rate compares "
            "to what would be expected given its patient mix."
        ),
        tail_risk_flag=False,
        ses_sensitivity="HIGH",
        dataset_id="9n3s-kdb3",
        cms_measure_definition=(
            "In October 2012, CMS began reducing Medicare payments for subsection(d) "
            "hospitals with excess readmissions. Excess readmissions are measured by a "
            "ratio, calculated by dividing a hospital's predicted rate of readmission for "
            "heart attack (AMI), heart failure (HF), pneumonia, chronic obstructive "
            "pulmonary disease (COPD), hip/knee replacement (THA/TKA), and coronary artery "
            "bypass graft (CABG) surgery by the expected rate of readmission, based on an "
            "average hospital with similar patients."
        ),
    ),
    MeasureEntry(
        measure_id="HRRP_HIP_KNEE",
        name="Excess Readmission Ratio — Hip/Knee Replacement (HRRP)",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's hip and knee replacement readmission rate "
            "compares to what would be expected given its patient mix."
        ),
        tail_risk_flag=False,
        ses_sensitivity="HIGH",
        dataset_id="9n3s-kdb3",
        cms_measure_definition=(
            "In October 2012, CMS began reducing Medicare payments for subsection(d) "
            "hospitals with excess readmissions. Excess readmissions are measured by a "
            "ratio, calculated by dividing a hospital's predicted rate of readmission for "
            "heart attack (AMI), heart failure (HF), pneumonia, chronic obstructive "
            "pulmonary disease (COPD), hip/knee replacement (THA/TKA), and coronary artery "
            "bypass graft (CABG) surgery by the expected rate of readmission, based on an "
            "average hospital with similar patients."
        ),
    ),
    MeasureEntry(
        measure_id="HRRP_PN",
        name="Excess Readmission Ratio — Pneumonia (HRRP)",
        group="READMISSIONS",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this hospital's pneumonia readmission rate compares to "
            "what would be expected given its patient mix."
        ),
        tail_risk_flag=False,
        ses_sensitivity="HIGH",
        dataset_id="9n3s-kdb3",
        cms_measure_definition=(
            "In October 2012, CMS began reducing Medicare payments for subsection(d) "
            "hospitals with excess readmissions. Excess readmissions are measured by a "
            "ratio, calculated by dividing a hospital's predicted rate of readmission for "
            "heart attack (AMI), heart failure (HF), pneumonia, chronic obstructive "
            "pulmonary disease (COPD), hip/knee replacement (THA/TKA), and coronary artery "
            "bypass graft (CABG) surgery by the expected rate of readmission, based on an "
            "average hospital with similar patients."
        ),
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # NURSING HOME MEASURES
    # ═══════════════════════════════════════════════════════════════════════
    #
    # 42 nursing home measures across 4 source datasets + Five-Star ratings:
    #
    #   MDS Quality Measures (djen-97ju):  17 measures (9 long-stay, 8 short-stay)
    #   Medicare Claims Quality Measures (ijh5-nb2v):  4 measures
    #   Five-Star Sub-Ratings (4pq5-n9py):  6 ratings
    #   SNF QRP (fykj-qjee):  15 measures
    #
    # Phase 0 reference: docs/phase_0_findings.md §13-22, §Confirmed Nursing
    #   Home Measure Code Catalog, §Five-Star Quality Rating System
    # Direction/SES basis: docs/data_dictionary.md §Nursing Home Measures
    #
    # ═══════════════════════════════════════════════════════════════════════

    # ───────────────────────────────────────────────────────────────────
    # MDS Quality Measures — Long Stay (djen-97ju) — 9 measures
    # 7 used in Five-Star QM rating, 2 not used
    # Phase 0 reference: docs/phase_0_findings.md §13, §Confirmed NH
    #   Measure Code Catalog
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="NH_MDS_401",
        name="Percentage of long-stay residents whose need for help with daily activities has increased",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who needed "
            "more help with everyday activities like eating, bathing, and "
            "dressing compared to a prior assessment."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_451",
        name="Percentage of long-stay residents whose ability to walk independently worsened",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents whose "
            "ability to walk on their own got worse compared to a prior "
            "assessment."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_479",
        name="Percentage of long-stay residents with pressure ulcers",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who had "
            "pressure sores (bed sores) at stage II or higher, which are "
            "open wounds that can lead to serious infections."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_406",
        name="Percentage of long-stay residents with a catheter inserted and left in their bladder",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who had a "
            "urinary catheter left in place, which increases the risk of "
            "infection and discomfort."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_407",
        name="Percentage of long-stay residents with a urinary tract infection",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who had a "
            "urinary tract infection, a common but potentially serious "
            "condition in elderly residents."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_410",
        name="Percentage of long-stay residents experiencing one or more falls with major injury",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who fell "
            "and suffered a major injury such as a broken bone or head "
            "injury."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_481",
        name="Percentage of long-stay residents who got an antipsychotic medication",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who "
            "received an antipsychotic drug, which can cause serious side "
            "effects and is often used as a chemical restraint."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="djen-97ju",
    ),

    # -- Long-stay MDS: NOT in Five-Star rating --

    MeasureEntry(
        measure_id="NH_MDS_404",
        name="Percentage of long-stay residents who lose too much weight",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who lost a "
            "concerning amount of weight, which can signal poor nutrition "
            "or untreated illness."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_408",
        name="Percentage of long-stay residents who have depressive symptoms",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents showing "
            "signs of depression based on a standardized screening tool."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_409",
        name="Percentage of long-stay residents who were physically restrained",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who were "
            "physically restrained, such as with belts or bed rails that "
            "prevent free movement."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_415",
        name="Percentage of long-stay residents assessed and appropriately given the pneumococcal vaccine",
        group="NH_QUALITY_LONG_STAY",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who were "
            "checked for and given the pneumonia vaccine when appropriate."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_454",
        name="Percentage of long-stay residents assessed and appropriately given the seasonal influenza vaccine",
        group="NH_QUALITY_LONG_STAY",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who were "
            "checked for and given the seasonal flu vaccine when appropriate."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_452",
        name="Percentage of long-stay residents who received an antianxiety or hypnotic medication",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who "
            "received anti-anxiety or sleep medications, which carry "
            "increased fall and sedation risks for elderly residents."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_480",
        name="Percentage of long-stay residents with new or worsened bowel or bladder incontinence",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of long-stay nursing home residents who "
            "developed new or worsening loss of bowel or bladder control."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="djen-97ju",
    ),

    # ───────────────────────────────────────────────────────────────────
    # MDS Quality Measures — Short Stay (djen-97ju) — 4 measures
    # 1 used in Five-Star QM rating (434), 3 not used (vaccines)
    # Phase 0 reference: docs/phase_0_findings.md §13
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="NH_MDS_434",
        name="Percentage of short-stay residents who newly received an antipsychotic medication",
        group="NH_QUALITY_SHORT_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of short-stay nursing home residents who were "
            "started on an antipsychotic drug for the first time during "
            "their stay."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_430",
        name="Percentage of short-stay residents assessed and appropriately given the pneumococcal vaccine",
        group="NH_QUALITY_SHORT_STAY",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of short-stay nursing home residents who were "
            "checked for and given the pneumonia vaccine when appropriate."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="djen-97ju",
    ),
    MeasureEntry(
        measure_id="NH_MDS_472",
        name="Percentage of short-stay residents who were assessed and appropriately given the seasonal influenza vaccine",
        group="NH_QUALITY_SHORT_STAY",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of short-stay nursing home residents who were "
            "checked for and given the seasonal flu vaccine when appropriate."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="djen-97ju",
    ),

    # ───────────────────────────────────────────────────────────────────
    # Medicare Claims Quality Measures (ijh5-nb2v) — 4 measures
    # All 4 used in Five-Star QM rating
    # Phase 0 reference: docs/phase_0_findings.md §14, §Confirmed NH
    #   Measure Code Catalog
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="NH_CLAIMS_551",
        name="Number of hospitalizations per 1,000 long-stay resident days",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often long-stay nursing home residents are sent to the "
            "hospital, measured per 1,000 days of care provided at the "
            "facility."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="ijh5-nb2v",
    ),
    MeasureEntry(
        measure_id="NH_CLAIMS_552",
        name="Number of outpatient emergency department visits per 1,000 long-stay resident days",
        group="NH_QUALITY_LONG_STAY",
        direction="LOWER_IS_BETTER",
        unit="rate",
        plain_language=(
            "How often long-stay nursing home residents visit a hospital "
            "emergency department without being admitted, measured per "
            "1,000 days of care."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="ijh5-nb2v",
    ),
    MeasureEntry(
        measure_id="NH_CLAIMS_521",
        name="Percentage of short-stay residents who were rehospitalized after a nursing home admission",
        group="NH_QUALITY_SHORT_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of short-stay nursing home residents who had "
            "to go back to the hospital within 30 days of entering the "
            "nursing home."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="ijh5-nb2v",
    ),
    MeasureEntry(
        measure_id="NH_CLAIMS_522",
        name="Percentage of short-stay residents who had an outpatient emergency department visit",
        group="NH_QUALITY_SHORT_STAY",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of short-stay nursing home residents who "
            "visited a hospital emergency department without being "
            "admitted during their stay."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="ijh5-nb2v",
    ),

    # ───────────────────────────────────────────────────────────────────
    # Five-Star Sub-Ratings (4pq5-n9py — Provider Information) — 6 ratings
    # These are composite ratings derived by CMS, not raw measures.
    # Phase 0 reference: docs/phase_0_findings.md §Five-Star Quality
    #   Rating System — Confirmed Methodology
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="NH_STAR_OVERALL",
        name="Overall Five-Star Rating",
        group="NH_STAR_RATING",
        direction="HIGHER_IS_BETTER",
        unit="score",
        plain_language=(
            "The overall quality rating CMS assigns to this nursing home "
            "on a 1 to 5 star scale, based on health inspections, "
            "staffing, and quality measures."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAR_HEALTH_INSP",
        name="Health Inspection Rating",
        group="NH_STAR_RATING",
        direction="HIGHER_IS_BETTER",
        unit="score",
        plain_language=(
            "This nursing home's health inspection rating on a 1 to 5 "
            "star scale, based on the number, severity, and scope of "
            "problems found during onsite inspections."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAR_QM",
        name="Quality Measure Rating",
        group="NH_STAR_RATING",
        direction="HIGHER_IS_BETTER",
        unit="score",
        plain_language=(
            "This nursing home's quality measure rating on a 1 to 5 star "
            "scale, combining performance on 15 measures of resident "
            "health and safety."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAR_LS_QM",
        name="Long-Stay QM Rating",
        group="NH_STAR_RATING",
        direction="HIGHER_IS_BETTER",
        unit="score",
        plain_language=(
            "This nursing home's quality rating for long-stay residents "
            "on a 1 to 5 star scale, based on 9 measures of care for "
            "residents living at the facility long-term."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAR_SS_QM",
        name="Short-Stay QM Rating",
        group="NH_STAR_RATING",
        direction="HIGHER_IS_BETTER",
        unit="score",
        plain_language=(
            "This nursing home's quality rating for short-stay residents "
            "on a 1 to 5 star scale, based on 6 measures of care for "
            "residents receiving temporary rehabilitation."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAR_STAFFING",
        name="Staffing Rating",
        group="NH_STAR_RATING",
        direction="HIGHER_IS_BETTER",
        unit="score",
        plain_language=(
            "This nursing home's staffing rating on a 1 to 5 star scale, "
            "based on nurse staffing levels, turnover rates, and "
            "administrator stability."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),

    # ───────────────────────────────────────────────────────────────────
    # SNF Quality Reporting Program (fykj-qjee) — 15 measures
    # 3 measures (S_005_02, S_038_02, S_042_02) are also used in the
    # Five-Star QM rating — tracked here with SNF QRP as primary source
    # since they provide richer data (CI bounds, numerator/denominator).
    # Phase 0 reference: docs/phase_0_findings.md §21, §Confirmed NH
    #   Measure Code Catalog §SNF QRP
    # SNF QM manual: docs/snf-qm-calculations-and-reporting-users-manual-v7.0.txt
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="S_004_01",
        name="Potentially Preventable 30-Day Post-Discharge Readmission Measure for SNF (PPR)",
        group="NH_SNF_QRP",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "How often patients are readmitted to the hospital within "
            "30 days of leaving this nursing facility, counting only "
            "readmissions that might have been prevented."
        ),
        tail_risk_flag=True,
        ses_sensitivity="HIGH",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_005_02",
        name="Discharge to Community Measure for SNF (DTC)",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients who successfully returned home "
            "or to the community after a stay at this nursing facility."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_006_01",
        name="Medicare Spending Per Beneficiary for SNF (MSPB)",
        group="NH_SNF_QRP",
        direction="LOWER_IS_BETTER",
        unit="ratio",
        plain_language=(
            "How this nursing facility's Medicare spending per patient "
            "compares to the national median, where a number below 1.0 "
            "means the facility spends less than typical."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_007_02",
        name="Drug Regimen Review Conducted with Follow-Up for Identified Issues (DRR)",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of nursing home stays where staff reviewed "
            "the patient's medications and followed up on any problems "
            "found."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_013_02",
        name="Application of Falls with Major Injury Measure for SNF",
        group="NH_SNF_QRP",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "How often patients at this nursing facility fell and "
            "suffered a major injury such as a broken bone or head "
            "injury during their stay."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_024_06",
        name="Discharge Self-Care Score for SNF",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "How well patients could care for themselves (eating, "
            "grooming, dressing) when they left this nursing facility "
            "compared to what was expected based on their condition."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_025_06",
        name="Discharge Mobility Score for SNF",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "How well patients could move around (walking, using stairs, "
            "transferring) when they left this nursing facility compared "
            "to what was expected based on their condition."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_038_02",
        name="Changes in Skin Integrity Post-Acute Care: Pressure Ulcer/Injury",
        group="NH_SNF_QRP",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of patients who developed new or worsening "
            "pressure sores (bed sores) during their stay at this "
            "nursing facility."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_039_01",
        name="SNF Healthcare-Associated Infections Requiring Hospitalization (SNF HAI)",
        group="NH_SNF_QRP",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "How often patients at this nursing facility got an infection "
            "during their stay that was serious enough to require "
            "hospitalization."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_040_02",
        name="COVID-19 Vaccination Coverage Among Healthcare Personnel (HCP)",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of staff at this nursing facility who are "
            "up to date on their COVID-19 vaccination."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_041_01",
        name="Influenza Vaccination Coverage Among Healthcare Personnel (HCP)",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of staff at this nursing facility who "
            "received the seasonal flu vaccine."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_042_02",
        name="Discharge Function Score for SNF (composite self-care + mobility)",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "A composite score measuring how well patients could perform "
            "self-care and mobility tasks at discharge compared to what "
            "was expected, combining multiple functional assessments."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_043_02",
        name="Transfer of Health Information to the Provider — Post-Acute Care (TOH-Provider)",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "How often this nursing facility sent a complete medical "
            "summary to the next care provider when a patient was "
            "discharged or transferred."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_044_02",
        name="Transfer of Health Information to the Patient — Post-Acute Care (TOH-Patient)",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "How often this nursing facility gave patients or their "
            "family a written summary of their care and follow-up "
            "instructions at discharge."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="fykj-qjee",
    ),
    MeasureEntry(
        measure_id="S_045_01",
        name="COVID-19 Vaccine: Percent of Residents Who Are Up to Date",
        group="NH_SNF_QRP",
        direction="HIGHER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of residents at this nursing facility who "
            "are up to date on their COVID-19 vaccination."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="fykj-qjee",
    ),

    # ───────────────────────────────────────────────────────────────────
    # Nursing Home Staffing Measures (4pq5-n9py — Provider Information)
    # — 6 Five-Star staffing sub-measures + 3 reported staffing measures
    #
    # The Five-Star staffing rating uses 6 specific sub-measures scored
    # on decile or fixed-point scales, totaling 380 max points.
    # PBJ = Payroll-Based Journal (CMS mandatory staffing reporting).
    #
    # Additionally, 3 reported (unadjusted) staffing measures are stored
    # as measures because consumers need to see actual hours alongside
    # case-mix adjusted values.
    #
    # Phase 0 reference: docs/phase_0_findings.md §12,
    #   §Five-Star Quality Rating System — Staffing Domain
    # ───────────────────────────────────────────────────────────────────

    # -- Five-Star staffing sub-measures (case-mix adjusted, scored) --

    MeasureEntry(
        measure_id="NH_STAFF_ADJ_TOTAL_HPRD",
        name="Case-mix adjusted total nurse staffing hours per resident per day",
        group="NH_STAFFING",
        direction="HIGHER_IS_BETTER",
        unit="hours_per_resident_day",
        plain_language=(
            "The total hours of nursing care (registered nurses, licensed "
            "practical nurses, and nurse aides combined) each resident "
            "receives per day, adjusted for how sick the residents are."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAFF_ADJ_RN_HPRD",
        name="Case-mix adjusted RN staffing hours per resident per day",
        group="NH_STAFFING",
        direction="HIGHER_IS_BETTER",
        unit="hours_per_resident_day",
        plain_language=(
            "The hours of registered nurse care each resident receives "
            "per day, adjusted for how sick the residents are. RN hours "
            "are critical for clinical oversight and complex care needs."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAFF_ADJ_WEEKEND_HPRD",
        name="Case-mix adjusted weekend total nurse staffing hours per resident per day",
        group="NH_STAFFING",
        direction="HIGHER_IS_BETTER",
        unit="hours_per_resident_day",
        plain_language=(
            "The total hours of nursing care each resident receives per "
            "day on weekends, adjusted for how sick the residents are. "
            "Weekend staffing is often lower than weekday staffing."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAFF_TOTAL_TURNOVER",
        name="Total nursing staff turnover rate",
        group="NH_STAFFING",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of nursing staff (registered nurses, licensed "
            "practical nurses, and nurse aides) who left this facility "
            "over the past 6 quarters. High turnover can affect "
            "continuity of care."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAFF_RN_TURNOVER",
        name="Registered nurse turnover rate",
        group="NH_STAFFING",
        direction="LOWER_IS_BETTER",
        unit="percent",
        plain_language=(
            "The percentage of registered nurses who left this facility "
            "over the past 6 quarters. RN turnover is particularly "
            "important because RNs provide clinical leadership."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAFF_ADMIN_DEPARTURES",
        name="Number of administrators who have left the nursing home",
        group="NH_STAFFING",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "How many administrators have left this nursing home over "
            "the past 6 quarters. Frequent administrator changes can "
            "disrupt facility management and quality oversight."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),

    # -- Reported (unadjusted) PBJ staffing for transparency --

    MeasureEntry(
        measure_id="NH_STAFF_REPORTED_TOTAL_HPRD",
        name="Reported total nurse staffing hours per resident per day",
        group="NH_STAFFING",
        direction="HIGHER_IS_BETTER",
        unit="hours_per_resident_day",
        plain_language=(
            "The total hours of nursing care each resident actually "
            "receives per day as reported by the facility, before any "
            "adjustment for resident health conditions."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAFF_REPORTED_RN_HPRD",
        name="Reported RN staffing hours per resident per day",
        group="NH_STAFFING",
        direction="HIGHER_IS_BETTER",
        unit="hours_per_resident_day",
        plain_language=(
            "The hours of registered nurse care each resident actually "
            "receives per day as reported by the facility, before any "
            "adjustment for resident health conditions."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_STAFF_REPORTED_AIDE_HPRD",
        name="Reported nurse aide staffing hours per resident per day",
        group="NH_STAFFING",
        direction="HIGHER_IS_BETTER",
        unit="hours_per_resident_day",
        plain_language=(
            "The hours of nurse aide care each resident actually "
            "receives per day as reported by the facility. Nurse aides "
            "provide most of the direct daily care to residents."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),

    # ───────────────────────────────────────────────────────────────────
    # Nursing Home Inspection Measures (derived from Provider Information
    # and Health Deficiencies datasets)
    #
    # These are aggregate measures derived from inspection data that
    # surface tail risk. The raw deficiency citations with scope/severity
    # codes are stored in provider_inspection_events — these measures
    # provide summary-level signals for the primary profile view.
    #
    # Phase 0 reference: docs/phase_0_findings.md §12, §15, §16, §17
    # Scope/severity scoring: Five-Star Technical Users' Guide Table 1
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="NH_INSP_TOTAL_HEALTH_DEF",
        name="Total number of health deficiencies (most recent cycle)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The total number of health problems found during the most "
            "recent standard inspection of this nursing home by state "
            "health inspectors."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_INSP_TOTAL_FIRE_DEF",
        name="Total number of fire safety deficiencies (most recent cycle)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The total number of fire safety problems found during the "
            "most recent fire safety inspection of this nursing home."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_INSP_IJ_CITATIONS",
        name="Immediate jeopardy citations (most recent 3 cycles)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The number of inspection findings where state inspectors "
            "determined residents were in immediate danger of serious "
            "harm or death. These are the most serious type of citation "
            "a nursing home can receive."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="r5ix-sfxw",
    ),
    MeasureEntry(
        measure_id="NH_INSP_HARM_CITATIONS",
        name="Actual harm citations (most recent 3 cycles)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The number of inspection findings where state inspectors "
            "determined that residents suffered actual harm that was not "
            "immediately life-threatening. These are serious citations "
            "indicating real injury or impairment."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="r5ix-sfxw",
    ),
    MeasureEntry(
        measure_id="NH_INSP_ABUSE_CITATIONS",
        name="Abuse, neglect, and exploitation deficiency citations (most recent 3 cycles)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The number of inspection findings related to abuse, neglect, "
            "or exploitation of residents. CMS caps the health inspection "
            "rating at 2 stars when abuse citations reach the harm level."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="r5ix-sfxw",
    ),
    MeasureEntry(
        measure_id="NH_INSP_INFECTION_CTRL",
        name="Infection control deficiency citations (most recent 3 cycles)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The number of inspection findings related to infection "
            "prevention and control practices at this nursing home, "
            "including from focused infection control inspections."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="r5ix-sfxw",
    ),
    MeasureEntry(
        measure_id="NH_INSP_WEIGHTED_SCORE",
        name="Total weighted health inspection score",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="score",
        plain_language=(
            "A combined score reflecting the number and severity of "
            "health deficiencies found across the two most recent "
            "inspection cycles, weighted so that the most recent "
            "inspection counts more heavily."
        ),
        tail_risk_flag=False,
        ses_sensitivity="MODERATE",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_INSP_REVISIT_SCORE",
        name="Health inspection revisit score (most recent cycle)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="score",
        plain_language=(
            "Penalty points added when state inspectors had to return "
            "to check whether this nursing home corrected previously "
            "cited problems. Higher scores mean the facility needed "
            "multiple follow-up visits."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_INSP_COMPLAINT_DEF",
        name="Deficiency citations from complaint investigations (most recent 3 cycles)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The number of problems found when state inspectors "
            "investigated complaints filed against this nursing home. "
            "Unlike routine inspections, complaint investigations are "
            "triggered by specific concerns reported by residents, "
            "families, or staff."
        ),
        tail_risk_flag=True,
        ses_sensitivity="MODERATE",
        dataset_id="r5ix-sfxw",
    ),

    # ───────────────────────────────────────────────────────────────────
    # Nursing Home Penalty Measures (4pq5-n9py + g6vv-u9sr)
    #
    # CMS imposes fines and payment denials on nursing homes with
    # serious or persistent quality failures. These are among the
    # strongest enforcement signals available — payment denials in
    # particular mean CMS stopped paying the facility for new
    # admissions, which is reserved for the most serious situations.
    #
    # Aggregate counts come from Provider Information (4pq5-n9py).
    # Individual penalty records with dates and amounts are in the
    # Penalties dataset (g6vv-u9sr) and stored in provider_penalties.
    #
    # Phase 0 reference: docs/phase_0_findings.md §19 (Penalties),
    #   §12 (Provider Info penalty fields)
    # ───────────────────────────────────────────────────────────────────

    MeasureEntry(
        measure_id="NH_PENALTY_FINE_TOTAL",
        name="Total amount of fines in dollars (last 3 years)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="dollars",
        plain_language=(
            "The total dollar amount of fines CMS has imposed on this "
            "nursing home over the past three years for failing to meet "
            "federal quality and safety standards."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_PENALTY_COUNT",
        name="Total number of penalties (last 3 years)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The total number of penalties (fines and payment denials "
            "combined) CMS has imposed on this nursing home over the "
            "past three years."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_PENALTY_PAYMENT_DENIALS",
        name="Number of payment denials (last 3 years)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The number of times CMS stopped paying this nursing home "
            "for new Medicare or Medicaid admissions due to serious "
            "quality failures. Payment denials are among the most severe "
            "enforcement actions available."
        ),
        tail_risk_flag=True,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
    MeasureEntry(
        measure_id="NH_PENALTY_FINE_COUNT",
        name="Number of fines (last 3 years)",
        group="NH_INSPECTION",
        direction="LOWER_IS_BETTER",
        unit="count",
        plain_language=(
            "The number of fines CMS has imposed on this nursing home "
            "over the past three years for failing to meet federal "
            "quality and safety standards."
        ),
        tail_risk_flag=False,
        ses_sensitivity="LOW",
        dataset_id="4pq5-n9py",
    ),
]


# ---------------------------------------------------------------------------
# Lookup structures (built once at import time)
# ---------------------------------------------------------------------------

MEASURE_REGISTRY: dict[str, MeasureEntry] = {
    entry.measure_id: entry for entry in _REGISTRY_LIST
}
"""measure_id → MeasureEntry lookup. This is the primary access point."""

assert len(MEASURE_REGISTRY) == len(_REGISTRY_LIST), (
    f"Duplicate measure_id detected: {len(_REGISTRY_LIST)} entries but "
    f"{len(MEASURE_REGISTRY)} unique IDs"
)


# ---------------------------------------------------------------------------
# HAI companion measure patterns
# ---------------------------------------------------------------------------
# These 30 sub-measures are NOT in MEASURE_REGISTRY. The normalizer
# recognizes them by suffix pattern and maps them to columns on the
# parent SIR row in provider_measure_values.
#
# Pattern: HAI_{1-6}_{CILOWER|CIUPPER|DOPC|ELIGCASES|NUMERATOR}

HAI_COMPANION_SUFFIXES = frozenset({
    "CILOWER", "CIUPPER", "DOPC", "ELIGCASES", "NUMERATOR",
})

HAI_SIR_IDS = frozenset(
    entry.measure_id for entry in _REGISTRY_LIST
    if entry.measure_id.startswith("HAI_") and entry.measure_id.endswith("_SIR")
)


# ---------------------------------------------------------------------------
# Payment adjustment programs (not MEASURE_REGISTRY — stored separately)
# ---------------------------------------------------------------------------

PAYMENT_PROGRAMS = {
    "HRRP": {
        "dataset_id": "9n3s-kdb3",
        "name": "Hospital Readmissions Reduction Program",
    },
    "HACRP": {
        "dataset_id": "yq43-i98g",
        "name": "Hospital-Acquired Condition Reduction Program",
    },
    "VBP": {
        "dataset_id": "pudb-wetr",
        "name": "Hospital Value-Based Purchasing Program",
    },
    "SNF_VBP": {
        "dataset_id": "284v-j9fz",
        "name": "Skilled Nursing Facility Value-Based Purchasing Program",
    },
}
