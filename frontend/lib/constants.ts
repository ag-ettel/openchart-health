// Architectural contract. See CLAUDE.md: Frontend Specification: Constants.
// No component may inline these values. All verbatim required strings live here.
// Sync thresholds with pipeline/config.py and document any change in docs/decisions.md.

// Must stay in sync with SMALL_SAMPLE_THRESHOLD in pipeline/config.py.
export const SMALL_SAMPLE_THRESHOLD = 30;

// Absolute difference in dual_eligible_proportion (percentage points) above which
// the comparison view renders the population comparability note.
// Must stay in sync with POPULATION_COMPARABILITY_THRESHOLD_PCT in pipeline/config.py.
export const POPULATION_COMPARABILITY_THRESHOLD_PCT = 10;

// Required verbatim strings. Do not paraphrase or split across components.
export const DISCLAIMER_TEXT =
  "This site displays publicly available data published by the Centers for Medicare " +
  "& Medicaid Services (CMS), a U.S. federal agency. This information is not medical " +
  "advice. It does not account for your individual health needs, insurance coverage, " +
  "or personal circumstances. Consult a qualified healthcare professional before " +
  "making any healthcare decision.";

export const SES_DISCLOSURE_TEXT =
  "Readmission and mortality rates are adjusted by CMS for clinical risk factors " +
  "such as age and diagnosis. They are not fully adjusted for patient socioeconomic " +
  "characteristics. Hospitals serving higher proportions of low-income or " +
  "dual-eligible patients may show higher rates on these measures partly due to " +
  "patient population factors, not care quality alone. This tool does not currently " +
  "include hospital-level socioeconomic population data that would aid direct " +
  "interpretation of these effects.";

export const MULTIPLE_COMPARISON_TEXT =
  "When many measures are shown together, some will appear above or below average " +
  "by chance alone. Focus on measures flagged as tail risk and on patterns " +
  "across multiple measures rather than any single result in isolation.";

export const SMALL_SAMPLE_CAVEAT = (n: number): string =>
  `This result is based on ${n} cases. With this few cases, this rate is highly ` +
  `uncertain and may not reflect the hospital's typical performance.`;

export const TREND_MINIMUM_PERIODS_TEXT = (available: number): string =>
  `Trend data requires at least three reporting periods. ` +
  `${available} period(s) available for this measure.`;

// Footnote 29 — methodology change warning (Data Integrity Rule 11).
export const METHODOLOGY_CHANGE_FOOTNOTE_TEXT =
  "CMS revised the statistical methodology for this measure. Values before and " +
  "after this change may not be directly comparable.";

// DEC-032: direction note rendered only when direction_source is CMS_API,
// CMS_DATA_DICTIONARY, or CMS_MEASURE_SPEC. For CMS_MEASURE_DEFINITION (or null),
// the plain_language field carries CMS's directional language implicitly.
export const DIRECTION_NOTE = (cmsDirection: string): string =>
  `CMS designates ${cmsDirection} values as associated with better outcomes for this measure.`;

// direction_source values that warrant an explicit direction note (DEC-032).
export const EXPLICIT_DIRECTION_SOURCES: readonly string[] = [
  "CMS_API",
  "CMS_DATA_DICTIONARY",
  "CMS_MEASURE_SPEC",
];

// Render order for measure groups on the hospital profile page,
// after PatientSafetyRecord (which renders independently via tail_risk_flag).
// Values MUST match the measure_group enum finalized in pipeline/config.py.
// When nursing home display is built, add NH_MEASURE_GROUP_RENDER_ORDER
// as a separate constant. Do not make this array provider-type-aware.
export const MEASURE_GROUP_RENDER_ORDER: readonly string[] = [
  "PATIENT_EXPERIENCE",
  "TIMELY_CARE",
  "READMISSIONS",
  "INFECTIONS",
  "PAYMENT",
  "SPENDING",
  "IMAGING",
];

// Consumer-facing display names for measure_group enum values.
// No component may inline these or derive them via string manipulation.
export const MEASURE_GROUP_DISPLAY_NAMES: Readonly<Record<string, string>> = {
  PATIENT_EXPERIENCE: "Patient Experience",
  TIMELY_CARE: "Timely and Effective Care",
  READMISSIONS: "Unplanned Hospital Visits",
  INFECTIONS: "Healthcare-Associated Infections",
  PAYMENT: "Payment and Value Programs",
  SPENDING: "Medicare Spending Per Patient",
  IMAGING: "Outpatient Imaging Efficiency",
  COMPLICATIONS_AND_DEATHS: "Complications and Deaths",
  MORTALITY: "Mortality",
  SAFETY: "Patient Safety",
};
