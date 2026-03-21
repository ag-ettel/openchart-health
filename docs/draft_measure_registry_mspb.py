"""
MEASURE_REGISTRY Draft — Medicare Spending Per Patient (rrqw-56er)

Drafted: 2026-03-15
Source: scripts/recon/raw_samples/rrqw-56er.json (1000 rows, 10 pages)
Phase 0 reference: docs/phase_0_findings.md §9 (Medicare Hospital Spending Per Patient)

1 distinct measure_id confirmed against live CMS API.

Note: CMS API title is "Medicare Spending Per Beneficiary" (MSPB).
The downloadable CSV uses "Medicare Hospital Spending Per Patient".
The measure_id in the API uses a hyphen: "MSPB-1" (not "MSPB_1").

Reporting period: 12 months, refreshed annually.

CI methodology classification:
    risk_adjustment_model: OTHER. MSPB-1 uses CMS's payment standardization
    methodology combined with HCC (Hierarchical Condition Category) risk
    adjustment. This is not HGLM — it is a spending ratio with price
    standardization and clinical risk adjustment. The specific methodology
    is documented in CMS MSPB technical reports.

    cms_ci_published: True. The rrqw-56er dataset includes lower_estimate
    and higher_estimate fields for MSPB-1.

    numerator_denominator_published: False. The score is a risk-adjusted
    spending ratio, not a simple numerator/denominator rate.

    CI calculability: AVAILABLE (CMS-provided).
"""

MSPB_1 = {
    "measure_id": "MSPB-1",
    "name": "Medicare hospital spending per patient (Medicare Spending per Beneficiary)",
    "group": "SPENDING",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: MSPB-1 is a ratio of a hospital's Medicare spending
    # per episode to the national median. A value of 1.0 means the
    # hospital's spending equals the national median. Values below 1.0
    # mean lower-than-median spending; values above 1.0 mean higher.
    #
    # Lower spending per episode is generally better — it indicates
    # more efficient resource use without excess utilization. However,
    # this is the most nuanced direction assignment in the registry:
    #
    # Caveats:
    # - Very low spending could indicate under-treatment or inadequate
    #   resource allocation, though published evidence does not show
    #   a strong correlation between lower MSPB and worse outcomes.
    # - CMS treats this as LOWER_IS_BETTER in its star rating and
    #   VBP calculations.
    # - The measure captures spending across 3 periods: pre-admission,
    #   during hospitalization, and 30 days post-discharge.
    # - Risk-adjusted for age, sex, comorbidities, and HCC scores.
    #
    # LOWER_IS_BETTER is the correct CMS-aligned assignment.
    "unit": "ratio",
    # Ratio where 1.0 = national median Medicare spending per episode.
    # Example: 0.97 = 3% below national median spending.
    "plain_language": (
        "How this hospital's Medicare spending per patient compares "
        "to the national median, where a number below 1.0 means the "
        "hospital spends less than typical."
    ),
    "tail_risk_flag": False,
    # Reasoning: Spending is an efficiency measure, not a patient
    # safety or adverse event measure. High spending is a resource
    # utilization concern, not a tail-risk event.
    "ses_sensitivity": "MODERATE",
    # Reasoning: MSPB is risk-adjusted for clinical factors (HCC
    # scores) but not fully for patient socioeconomic characteristics.
    # Hospitals serving higher-SES populations may have different
    # utilization patterns (more elective procedures, more post-acute
    # care). Hospitals serving lower-SES populations may have higher
    # readmission-driven spending that inflates the 30-day post-
    # discharge component.
    #
    # Published evidence: MedPAC reports document moderate SES effects
    # on MSPB. The measure is used in VBP but has been criticized for
    # disproportionately penalizing safety-net hospitals.
    #
    # ses-context.md guidance: Spending per beneficiary is listed as
    # MODERATE sensitivity.
    "risk_adjustment_model": "OTHER",  # Payment standardization + HCC risk adjustment
    "cms_ci_published": True,
    "numerator_denominator_published": False,
}


# ─────────────────────────────────────────────────────────────────────
# Summary: Medicare Spending Per Patient (rrqw-56er)
# ─────────────────────────────────────────────────────────────────────
#
# MEASURE_REGISTRY entries: 1 measure
#
# Outstanding TODOs:
#   1. Note measure_id uses hyphen: "MSPB-1" (confirmed from API).
#      Same hyphen convention as OIE measures (OP-8, etc.).
#   2. Confirm MeasureGroup enum includes "SPENDING".
#   3. Verify whether CMS provides a national median value alongside
#      the ratio. If so, store in national_avg column for display.
