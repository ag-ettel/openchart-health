"""
MEASURE_REGISTRY Draft — Outpatient Imaging Efficiency (wkfw-kthe)

Drafted: 2026-03-15
Source: scripts/recon/raw_samples/wkfw-kthe.json (1000 rows, 10 pages)
Phase 0 reference: docs/phase_0_findings.md §8 (Outpatient Imaging Efficiency)

4 distinct measure_id values confirmed against live CMS API.

NOTE: Phase 0 findings documented 3 active measures (OP-8, OP-10, OP-13).
The 1000-row sample also contains OP-39 (Breast Cancer Screening Recall
Rates). This measure was missed in the initial Phase 0 analysis.
RESOLVED (2026-03-15): OP-39 confirmed present in dataset. Phase 0
findings (docs/phase_0_findings.md §8) must be updated to include OP-39.
Direction is LOWER_IS_BETTER with clinical bounds context.

Direction reasoning:
    All measures in this dataset are LOWER_IS_BETTER. These measure the
    rate of potentially inappropriate or unnecessary imaging. A lower
    rate means more efficient, evidence-based use of imaging resources.
    Unnecessary imaging exposes patients to radiation, contrast agent
    risks, incidental findings requiring further workup, and healthcare
    cost without clinical benefit.

SES sensitivity: LOW for all.
    Imaging ordering patterns are driven by physician practice patterns,
    defensive medicine, and institutional culture — not patient SES.
    Published literature shows minimal SES effects on outpatient imaging
    efficiency measures.

tail_risk_flag: False for all.
    These are appropriateness/efficiency measures, not adverse event
    or mortality measures. Unnecessary imaging is a quality concern
    but does not directly measure patient harm events.

Unit: "percent" for all (rate of potentially inappropriate use).

Reporting period: 12 months, refreshed annually.

CI methodology classification:
    risk_adjustment_model: NONE for all. Outpatient imaging efficiency measures
    are unadjusted rates — the percentage of potentially inappropriate imaging
    studies out of total eligible studies. No risk adjustment is applied.

    cms_ci_published: False for all. CMS does not publish confidence intervals
    for imaging efficiency measures in the Provider Data download.

    numerator_denominator_published: True for all. CMS publishes the score
    (percentage rate) and sample size (denominator). The numerator can be
    derived as score * sample / 100.

    CI calculability: CALCULABLE. Standard binomial proportion confidence
    intervals can be computed from the published rate and sample size.

Note: No `compared_to_national` field in this dataset. No `denominator`
field. Score is the percentage rate.
"""

OP_8 = {
    "measure_id": "OP-8",
    "name": "MRI Lumbar Spine for Low Back Pain",
    "group": "IMAGING_EFFICIENCY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: This measures the percentage of outpatient MRI lumbar
    # spine exams performed for low back pain without a prior trial of
    # conservative therapy. Guidelines recommend 4-6 weeks of
    # conservative treatment before imaging for uncomplicated low back
    # pain. Early MRI without red flags is inappropriate — it doesn't
    # improve outcomes and exposes patients to unnecessary procedures
    # from incidental findings. Lower is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of lower back MRI scans at this hospital that "
        "may have been done too soon, before trying simpler treatments "
        "first."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

OP_10 = {
    "measure_id": "OP-10",
    "name": "Abdomen CT Use of Contrast Material",
    "group": "IMAGING_EFFICIENCY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: This measures the percentage of abdomen CT scans
    # performed with and without contrast on the same visit (dual-phase
    # scanning). In most clinical scenarios, a single-phase CT is
    # sufficient. Dual-phase doubles radiation exposure without clinical
    # benefit. Lower is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of abdominal CT scans at this hospital where "
        "the scan was done twice — once with and once without contrast "
        "dye — which may expose patients to unnecessary radiation."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

OP_13 = {
    "measure_id": "OP-13",
    "name": "Outpatients who got cardiac imaging stress tests before low-risk outpatient surgery",
    "group": "IMAGING_EFFICIENCY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Cardiac imaging stress tests before low-risk outpatient
    # surgery (e.g., cataract surgery, minor orthopedic procedures) are
    # not recommended by guidelines. They expose patients to unnecessary
    # radiation, contrast agents, and false-positive findings that can
    # delay needed surgery. Lower is better.
    "unit": "percent",
    "plain_language": (
        "The percentage of patients who had a heart stress test before "
        "low-risk outpatient surgery at this hospital, when guidelines "
        "say one was likely not needed."
    ),
    "tail_risk_flag": False,
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}

OP_39 = {
    "measure_id": "OP-39",
    "name": "Breast Cancer Screening Recall Rates",
    "group": "IMAGING_EFFICIENCY",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: The recall rate is the percentage of screening
    # mammograms that result in a recommendation for additional
    # imaging. While some recall is clinically appropriate, excessive
    # recall rates indicate over-reading — causing patient anxiety,
    # unnecessary follow-up procedures (biopsies), and healthcare cost.
    # The ACR recommends recall rates below 10%. Lower is better
    # (within clinically appropriate bounds).
    #
    # CONFIRMED (2026-03-15): LOWER_IS_BETTER. CMS treats lower recall
    # rates as better imaging quality. The ACR recommends recall rates
    # below 10% for screening mammography.
    #
    # IMPORTANT CLINICAL CONTEXT: While lower recall rates generally
    # indicate better reading quality, extremely low rates (<5%) could
    # indicate under-reading (missed cancers). The display layer should
    # note that an optimal recall rate balances sensitivity (catching
    # cancers) with specificity (avoiding unnecessary callbacks). This
    # measure has clinically appropriate bounds, not just a simple
    # "lower is always better" interpretation.
    "unit": "percent",
    "plain_language": (
        "The percentage of breast cancer screening mammograms at this "
        "hospital that led to a recommendation for additional imaging "
        "or testing."
    ),
    "tail_risk_flag": False,
    # Reasoning: Recall itself is not a harm event. However, false-
    # positive recalls cause anxiety and unnecessary biopsies.
    # Classified False because it's an appropriateness measure, not
    # a direct adverse event.
    "ses_sensitivity": "LOW",
    "risk_adjustment_model": "NONE",
    "cms_ci_published": False,
    "numerator_denominator_published": True,
}


# ─────────────────────────────────────────────────────────────────────
# Summary: Outpatient Imaging Efficiency (wkfw-kthe)
# ─────────────────────────────────────────────────────────────────────
#
# MEASURE_REGISTRY entries: 4 measures
# All LOWER_IS_BETTER, all tail_risk_flag = False, all SES LOW
#
# Outstanding TODOs:
#   1. RESOLVED: OP-39 was missed in Phase 0. Update phase_0_findings.md
#      §8 to document OP-39. Direction confirmed LOWER_IS_BETTER with
#      clinical bounds context note for the display layer.
#   2. RESOLVED: OP-39 direction confirmed (see entry above).
#   3. Note measure_id format uses hyphen (OP-8, OP-10, OP-13, OP-39),
#      unlike some other datasets that use underscore. Normalizer must
#      preserve exact CMS format.
#   4. Confirm MeasureGroup enum includes "IMAGING_EFFICIENCY".
