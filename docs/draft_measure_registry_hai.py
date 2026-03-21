"""
MEASURE_REGISTRY Draft — Healthcare-Associated Infections (77hc-ibv8)

Drafted: 2026-03-15
Source: scripts/recon/raw_samples/77hc-ibv8.json (1000 rows, 10 pages)
Phase 0 reference: docs/phase_0_findings.md §6 (Healthcare-Associated Infections)

36 distinct measure_id values confirmed against live CMS API.
6 infections × 6 sub-measures each (SIR, CILOWER, CIUPPER, DOPC,
ELIGCASES, NUMERATOR).

PIPELINE DESIGN DECISION NEEDED:
    The 6 SIR measures are the primary quality measures. The other 30
    measure_ids are companion data that should be collapsed into the SIR
    row during normalization:
      - HAI_n_SIR       → numeric_value (the O/E ratio)
      - HAI_n_CILOWER   → confidence_interval_lower
      - HAI_n_CIUPPER   → confidence_interval_upper
      - HAI_n_NUMERATOR → sample_size (observed infection count)
      - HAI_n_ELIGCASES → denominator (predicted/expected cases)
      - HAI_n_DOPC      → stored as additional context (device days /
                           patient days — the exposure denominator)

    The provider_measure_values schema has columns for CI bounds,
    sample_size, and denominator, so the companion data maps naturally.

    However, DOPC (device days / patient days) does not have a direct
    column in provider_measure_values. Options:
      a) Store in denominator (it IS the population at risk)
      b) Store in a metadata jsonb column (no such column currently)
      c) Add a dedicated column

    # TODO: Document pipeline design decision for HAI companion measure
    # collapse in docs/pipeline_decisions.md. Decide on DOPC storage.
    # Decide whether companion measure_ids need MEASURE_REGISTRY entries
    # or whether the normalizer handles them as known sub-measure patterns.

    DESIGN PRINCIPLE (2026-03-15): Prefer CMS-provided values over own
    calculations whenever possible. The HAI sub-measures (CILOWER, CIUPPER,
    DOPC, ELIGCASES, NUMERATOR) are CMS-calculated values — store them
    directly rather than attempting to derive them from the SIR. This
    reduces the risk of calculation errors in safety-critical data.

    This draft creates full entries for the 6 SIR measures only.
    Companion measures are documented in the COMPANION MEASURES section
    below with their field mappings but do NOT get MEASURE_REGISTRY
    entries — they are structural sub-components, not independent quality
    measures. The normalizer will recognize HAI_n_CILOWER etc. by pattern
    matching on the measure_id suffix and map them to the appropriate
    provider_measure_values columns.

Direction reasoning:
    All SIR measures are LOWER_IS_BETTER. SIR (Standardized Infection
    Ratio) is an observed-to-expected ratio where:
      - SIR < 1.0 → fewer infections than predicted (better)
      - SIR = 1.0 → infections match national baseline (expected)
      - SIR > 1.0 → more infections than predicted (worse)
    A lower SIR is unambiguously better. This is definitional.

SES sensitivity reasoning:
    All HAI measures are classified LOW. Healthcare-associated infections
    are primarily driven by infection prevention and control practices
    (hand hygiene, central line insertion protocols, environmental
    cleaning, antibiotic stewardship). Published literature shows minimal
    SES effects — HAI rates are not substantially influenced by patient
    socioeconomic mix. SIR methodology already adjusts for facility type
    and patient population characteristics.

    References:
    - CDC NHSN Risk Adjustment methodology (facility-level adjustments)
    - Krein et al. (2015) "Preventing Hospital-Acquired Infections:
      A National Survey" — infection prevention practices are the
      dominant predictor, not patient demographics
    - CMS Star Rating methodology treats HAI as a distinct domain
      without SES adjustment, acknowledging low SES sensitivity

    Note: ses-context.md guidance lists "HAI rates" as LOW sensitivity.

tail_risk_flag reasoning:
    All HAI measures are tail_risk_flag = True. Healthcare-associated
    infections are serious adverse events:
    - CLABSI: 12–25% attributable mortality
    - CAUTI: Leads to bloodstream infection in ~3% of cases
    - SSI: Doubles length of stay, 2–11x increased mortality
    - MRSA bacteremia: 20–30% mortality
    - C. diff: 5–10% mortality in elderly; high recurrence rate
    These are preventable infections acquired during medical care.
    They are the definition of tail-risk events.

Reporting period: 12 months, refreshed quarterly.

CI methodology classification:
    risk_adjustment_model: SIR for all 6 measures. CDC NHSN Standardized
    Infection Ratio methodology uses facility-level risk adjustment based
    on facility type, patient characteristics, and procedure types. This
    is NOT hierarchical generalized linear modeling — it is a distinct
    methodology maintained by CDC.

    cms_ci_published: True for all. CMS publishes CI bounds as companion
    measures (HAI_n_CILOWER, HAI_n_CIUPPER) in the HAI dataset (77hc-ibv8).
    These are CMS/CDC-calculated exact Poisson confidence intervals.

    numerator_denominator_published: True for all. CMS publishes observed
    infection count (HAI_n_NUMERATOR) and predicted/expected cases
    (HAI_n_ELIGCASES) as companion measures. Additionally, DOPC
    (device-days or procedure counts) is published.

    CI calculability: AVAILABLE (CMS-provided). The companion CILOWER and
    CIUPPER measures provide CMS-calculated CIs. Additionally, CIs could
    be independently verified from NUMERATOR and ELIGCASES using exact
    Poisson methods, though CMS-provided values should be preferred.
"""

# ─────────────────────────────────────────────────────────────────────
# SIR Measures (6) — Primary Quality Measures
#
# Each SIR represents a Standardized Infection Ratio for a specific
# type of healthcare-associated infection. SIR = observed / expected.
# ─────────────────────────────────────────────────────────────────────

HAI_1_SIR = {
    "measure_id": "HAI_1_SIR",
    "name": "Central Line Associated Bloodstream Infection (ICU + select Wards)",
    "group": "INFECTIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: CLABSI SIR < 1.0 means fewer central-line bloodstream
    # infections than expected. Central line infections are preventable
    # with proper insertion and maintenance protocols (central line
    # bundle). Lower is unambiguously better.
    "unit": "ratio",
    # SIR is an observed-to-expected ratio. 1.0 = national baseline.
    "plain_language": (
        "How this hospital's rate of bloodstream infections from central "
        "line IVs compares to what would be expected, where a number "
        "below 1.0 means fewer infections than expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: CLABSI has 12–25% attributable mortality. A single
    # preventable CLABSI can kill a patient. This is a core patient
    # safety measure.
    "ses_sensitivity": "LOW",
    # Reasoning: Infection prevention is process-driven. SIR methodology
    # adjusts for facility characteristics. Published literature shows
    # minimal residual SES effect on HAI rates.
    "risk_adjustment_model": "SIR",
    "cms_ci_published": True,
    "numerator_denominator_published": True,
}

HAI_2_SIR = {
    "measure_id": "HAI_2_SIR",
    "name": "Catheter Associated Urinary Tract Infections (ICU + select Wards)",
    "group": "INFECTIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: CAUTI SIR < 1.0 means fewer catheter-associated UTIs
    # than expected. Preventable through appropriate catheter use,
    # timely removal, and insertion technique. Lower is unambiguously
    # better.
    "unit": "ratio",
    "plain_language": (
        "How this hospital's rate of urinary tract infections from "
        "catheters compares to what would be expected, where a number "
        "below 1.0 means fewer infections than expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: CAUTI can progress to bloodstream infection (~3% of
    # cases) and contributes to antibiotic resistance. High volume of
    # preventable harm events nationally.
    "ses_sensitivity": "LOW",
    # Reasoning: Same basis as HAI_1_SIR. Infection prevention practice
    # adherence is the dominant predictor.
    "risk_adjustment_model": "SIR",
    "cms_ci_published": True,
    "numerator_denominator_published": True,
}

HAI_3_SIR = {
    "measure_id": "HAI_3_SIR",
    "name": "SSI - Colon Surgery",
    "group": "INFECTIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Surgical site infection SIR < 1.0 after colon surgery
    # means fewer infections than expected. Colon surgery has inherently
    # higher SSI risk due to bowel contamination — prevention protocols
    # (antibiotic timing, skin prep, normothermia) are critical.
    # Lower is unambiguously better.
    "unit": "ratio",
    "plain_language": (
        "How this hospital's rate of surgical wound infections after "
        "colon surgery compares to what would be expected, where a "
        "number below 1.0 means fewer infections than expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: SSI after colon surgery doubles length of stay and
    # increases mortality 2–11x. Deep surgical site infections can
    # require reoperation and long-term IV antibiotics.
    "ses_sensitivity": "LOW",
    # Reasoning: SSI prevention is process-driven (antibiotic prophylaxis
    # timing, surgical technique, glucose control). SIR methodology
    # adjusts for procedure type and risk category.
    "risk_adjustment_model": "SIR",
    "cms_ci_published": True,
    "numerator_denominator_published": True,
}

HAI_4_SIR = {
    "measure_id": "HAI_4_SIR",
    "name": "SSI - Abdominal Hysterectomy",
    "group": "INFECTIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: Surgical site infection SIR < 1.0 after abdominal
    # hysterectomy means fewer infections than expected. Lower is
    # unambiguously better.
    "unit": "ratio",
    "plain_language": (
        "How this hospital's rate of surgical wound infections after "
        "abdominal hysterectomy compares to what would be expected, "
        "where a number below 1.0 means fewer infections than expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: SSI after hysterectomy can cause pelvic abscess,
    # sepsis, and require reoperation. Significant patient harm.
    "ses_sensitivity": "LOW",
    # Reasoning: Same process-driven basis as HAI_3_SIR.
    "risk_adjustment_model": "SIR",
    "cms_ci_published": True,
    "numerator_denominator_published": True,
}

HAI_5_SIR = {
    "measure_id": "HAI_5_SIR",
    "name": "MRSA Bacteremia",
    "group": "INFECTIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: MRSA bacteremia SIR < 1.0 means fewer MRSA
    # bloodstream infections than expected. MRSA is an antibiotic-
    # resistant pathogen — infections are harder to treat and carry
    # high mortality. Lower is unambiguously better.
    "unit": "ratio",
    "plain_language": (
        "How this hospital's rate of drug-resistant MRSA bloodstream "
        "infections compares to what would be expected, where a number "
        "below 1.0 means fewer infections than expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: MRSA bacteremia carries 20–30% mortality. It is a
    # sentinel marker of infection control culture — MRSA transmission
    # is strongly linked to hand hygiene compliance and environmental
    # cleaning.
    "ses_sensitivity": "LOW",
    # Reasoning: MRSA prevention is driven by infection control practices
    # (contact precautions, hand hygiene, active surveillance cultures).
    # SIR adjusts for facility characteristics.
    "risk_adjustment_model": "SIR",
    "cms_ci_published": True,
    "numerator_denominator_published": True,
}

HAI_6_SIR = {
    "measure_id": "HAI_6_SIR",
    "name": "Clostridium Difficile (C.Diff)",
    "group": "INFECTIONS",
    "direction": "LOWER_IS_BETTER",
    # Reasoning: C. diff SIR < 1.0 means fewer C. difficile infections
    # than expected. C. diff is strongly linked to antibiotic overuse
    # and environmental contamination. Lower is unambiguously better.
    "unit": "ratio",
    "plain_language": (
        "How this hospital's rate of C. diff intestinal infections "
        "compares to what would be expected, where a number below 1.0 "
        "means fewer infections than expected."
    ),
    "tail_risk_flag": True,
    # Reasoning: C. diff causes severe diarrhea, toxic megacolon, and
    # death (5–10% mortality in elderly). High recurrence rate (~25%).
    # It is a key antibiotic stewardship outcome measure.
    "ses_sensitivity": "LOW",
    # Reasoning: C. diff is primarily driven by antibiotic prescribing
    # patterns and environmental cleaning. SIR adjusts for facility
    # characteristics. Minimal documented SES effect.
    "risk_adjustment_model": "SIR",
    "cms_ci_published": True,
    "numerator_denominator_published": True,
}


# ─────────────────────────────────────────────────────────────────────
# Companion Measures (30) — NOT Standalone Quality Measures
#
# These are structural sub-components of the SIR measures above.
# They are returned as separate rows in the CMS API with their own
# measure_id values, but they should be collapsed into the parent SIR
# row during normalization.
#
# The normalizer must recognize these by measure_id suffix pattern:
#   HAI_n_CILOWER   → confidence_interval_lower column
#   HAI_n_CIUPPER   → confidence_interval_upper column
#   HAI_n_NUMERATOR → sample_size column (observed infection count)
#   HAI_n_ELIGCASES → denominator column (predicted/expected cases)
#   HAI_n_DOPC      → TODO: decide storage column (device days /
#                      patient days = exposure denominator)
#
# These do NOT get MEASURE_REGISTRY entries. The pipeline normalizer
# handles them as known companion patterns for the HAI dataset.
#
# Full list of companion measure_ids (for reference):
#   HAI_1_CILOWER, HAI_1_CIUPPER, HAI_1_DOPC, HAI_1_ELIGCASES, HAI_1_NUMERATOR
#   HAI_2_CILOWER, HAI_2_CIUPPER, HAI_2_DOPC, HAI_2_ELIGCASES, HAI_2_NUMERATOR
#   HAI_3_CILOWER, HAI_3_CIUPPER, HAI_3_DOPC, HAI_3_ELIGCASES, HAI_3_NUMERATOR
#   HAI_4_CILOWER, HAI_4_CIUPPER, HAI_4_DOPC, HAI_4_ELIGCASES, HAI_4_NUMERATOR
#   HAI_5_CILOWER, HAI_5_CIUPPER, HAI_5_DOPC, HAI_5_ELIGCASES, HAI_5_NUMERATOR
#   HAI_6_CILOWER, HAI_6_CIUPPER, HAI_6_DOPC, HAI_6_ELIGCASES, HAI_6_NUMERATOR
#
# Suppression note for companions:
#   - CILOWER may carry score = "N/A" (not "Not Available") when zero
#     infections were observed (CI lower bound is mathematically undefined).
#     This is NOT suppression — store as not_applicable. The parent SIR
#     IS populated in these cases. See phase_0_findings.md §6.
#   - DOPC, ELIGCASES, NUMERATOR carry integer values (not rates).
#     Decimal precision rule does not apply.
#
# ─────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────
# Summary: Healthcare-Associated Infections (77hc-ibv8)
# ─────────────────────────────────────────────────────────────────────
#
# MEASURE_REGISTRY entries: 6 SIR measures
# Companion data handled by normalizer: 30 sub-measures
# Total API measure_ids in dataset: 36
#
# Outstanding TODOs:
#   1. Document pipeline design decision for HAI companion measure
#      collapse in docs/pipeline_decisions.md.
#   2. Decide DOPC (device days / patient days) storage column.
#      Recommendation: store DOPC in denominator column (it IS the
#      exposure denominator), NUMERATOR in sample_size (observed cases),
#      ELIGCASES (predicted/expected cases) — may need a dedicated column
#      or metadata field. All values are CMS-provided; do not recalculate.
#      Design principle: prefer CMS-provided values over own calculations.
#   3. Confirm MeasureGroup enum includes "INFECTIONS".
#   4. Verify whether the measure-registry rule "every measure in that
#      dataset" requires companion entries or whether normalizer pattern
#      matching is sufficient. Document in pipeline_decisions.md.
