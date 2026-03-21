"""
MeasureGroup Enum Values — Finalized 2026-03-15

These are the confirmed measure_group enum values for the PostgreSQL
enum type and the MEASURE_REGISTRY `group` field.

Design rationale:
    CMS star ratings use 5 broad domains (Mortality, Safety, Readmission,
    Patient Experience, Timely & Effective Care). This project uses
    finer-grained groups to support the display philosophy of surfacing
    tail-risk measures (infections, complications) as distinct categories
    rather than burying them under a generic "Safety" umbrella.

    The display layer can always aggregate groups into CMS star rating
    domains using the mapping below, but cannot disaggregate if the
    enum is too coarse.

Hospital Measure Groups (9):

    MORTALITY
        CMS star domain: Mortality
        Measures: MORT_30_AMI, MORT_30_CABG, MORT_30_COPD, MORT_30_HF,
                  MORT_30_PN, MORT_30_STK, Hybrid_HWM

    SAFETY
        CMS star domain: Safety of Care
        Measures: PSI_03, PSI_04, PSI_06, PSI_08, PSI_09, PSI_10,
                  PSI_11, PSI_12, PSI_13, PSI_14, PSI_15, PSI_90

    COMPLICATIONS
        CMS star domain: Safety of Care (subset)
        Measures: COMP_HIP_KNEE
        Note: CMS groups this with Safety, but surgical complication
        rates are conceptually distinct from Patient Safety Indicators.
        Keeping separate enables targeted display for surgical patients.

    INFECTIONS
        CMS star domain: Safety of Care (subset)
        Measures: HAI_1_SIR through HAI_6_SIR
        Note: HAI measures are reported as a separate CMS dataset and
        have distinct methodology (SIR vs rate). Keeping separate enables
        infection-specific display and allows the display layer to show
        infection control as a distinct quality dimension.

    READMISSIONS
        CMS star domain: Readmission
        Measures: READM_30_AMI, READM_30_CABG, READM_30_COPD,
                  READM_30_HF, READM_30_HIP_KNEE, READM_30_PN,
                  EDAC_30_AMI, EDAC_30_HF, EDAC_30_PN, Hybrid_HWR,
                  OP_32, OP_35_ADM, OP_35_ED, OP_36

    TIMELY_EFFECTIVE_CARE
        CMS star domain: Timely and Effective Care
        Measures: EDV, OP_18a-d, OP_22, OP_23, OP_29, OP_31, OP_40,
                  HH_HYPER, HH_HYPO, HH_ORAE, SAFE_USE_OF_OPIOIDS,
                  SEP_1, SEP_SH_3HR, SEP_SH_6HR, SEV_SEP_3HR,
                  SEV_SEP_6HR, STK_02, STK_03, STK_05, VTE_1, VTE_2,
                  IMM_3, GMCS (+ 4 sub-components)

    PATIENT_EXPERIENCE
        CMS star domain: Patient Experience
        Measures: All 68 HCAHPS measures (H_COMP_*, H_CLEAN_*, etc.)

    IMAGING_EFFICIENCY
        CMS star domain: (separate — not part of star rating)
        Measures: OP-8, OP-10, OP-13, OP-39

    SPENDING
        CMS star domain: Efficiency and Cost Reduction
        Measures: MSPB-1

Nursing Home Measure Groups (8, confirmed 2026-03-19):

    NH_QUALITY_LONG_STAY
        MDS Quality Measures — Long-stay residents (djen-97ju)
        Measures: 10 long-stay MDS measures (codes 401-481)

    NH_QUALITY_SHORT_STAY
        MDS Quality Measures — Short-stay residents (djen-97ju)
        Measures: 7 short-stay MDS measures (codes 424-471)

    NH_QUALITY_CLAIMS
        Medicare Claims Quality Measures (ijh5-nb2v)
        Measures: 4 claims-based measures (codes 521, 522, 551, 552)

    NH_STAFFING
        Five-Star staffing sub-measures + reported staffing (DEC-012)
        Measures: 9 measures (6 Five-Star rated + 3 reported/unadjusted)

    NH_STAR_RATING
        Five-Star sub-ratings (DEC-017)
        Measures: 6 ratings (overall, health inspection, QM, long/short stay QM, staffing)

    NH_INSPECTION
        Inspection-derived measures (DEC-013)
        Measures: 8 measures (4 tail-risk + 4 context)

    NH_PENALTIES
        Penalty and complaint measures (DEC-014)
        Measures: 5 measures (complaint citations, fine total, penalty count,
                  payment denials, fine count)

    NH_SNF_QRP
        SNF Quality Reporting Program (fykj-qjee)
        Measures: 15 measures (3 claims-based + 11 process/MDS + 1 MSPB)

CMS Star Rating Domain Mapping (for display aggregation):

    CMS Domain                      | MeasureGroup values
    --------------------------------|-------------------------------------
    Mortality                       | MORTALITY
    Safety of Care                  | SAFETY, COMPLICATIONS, INFECTIONS
    Readmission                     | READMISSIONS
    Patient Experience              | PATIENT_EXPERIENCE
    Timely and Effective Care       | TIMELY_EFFECTIVE_CARE
    Efficiency and Cost Reduction   | SPENDING, IMAGING_EFFICIENCY

Schema implication:
    The measure_direction enum column must be NULLABLE to accommodate
    EDV (no direction) and HCAHPS middlebox measures (no direction).
    This is a change from the current database-schema.md which specifies
    `direction enum: measure_direction` without nullable annotation.
    Update database-schema.md before writing the Alembic migration.
"""
