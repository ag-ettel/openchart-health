// Architectural contract. See CLAUDE.md: Frontend Specification: Constants.
// No component may inline these values. All verbatim required strings live here.
// Sync thresholds with pipeline/config.py and document any change in docs/decisions.md.

// Must stay in sync with SMALL_SAMPLE_THRESHOLD in pipeline/config.py.
export const SMALL_SAMPLE_THRESHOLD = 30;

// National average total nurse staffing HPRD.
// Source: CMS NH_ProviderInfo Feb 2026 (14,294 facilities with reported staffing).
// Mean: 3.89, Median: 3.71, 25th: 3.35, 75th: 4.22.
// Used as benchmark line on the staffing trend chart.
export const NATIONAL_AVG_TOTAL_NURSE_HPRD = 3.89;

// CMS minimum nursing home staffing thresholds (HPRD). Must match
// pipeline/config.py NH_MIN_*_HPRD. Source: CMS-3442-F, Minimum Staffing
// Standards for Long-Term Care Facilities Rule, finalized May 2024 (phased
// implementation 2026-2029). Used in OwnershipGroupStats and per-facility
// staffing template (text-templates.md sub-type 2c).
export const NH_MIN_TOTAL_NURSE_HPRD = 3.48;
export const NH_MIN_RN_HPRD = 0.55;
export const NH_MIN_NURSE_AIDE_HPRD = 2.45;

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
  "by chance alone. Focus on measures flagged as critical safety indicators and on " +
  "patterns across multiple measures rather than any single result in isolation.";

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
  // Nursing home measure groups
  NH_STAR_RATING: "Five-Star Ratings",
  NH_QUALITY_LONG_STAY: "Quality Measures — Long Stay",
  NH_QUALITY_SHORT_STAY: "Quality Measures — Short Stay",
  NH_QUALITY_CLAIMS: "Quality Measures — Claims-Based",
  NH_STAFFING: "Staffing",
  NH_SNF_QRP: "SNF Quality Reporting",
  NH_INSPECTION: "Inspection-Derived Measures",
  NH_PENALTIES: "Penalty Measures",
};

// Render order for measure groups on the nursing home profile page.
// Separate from hospital order per frontend-spec.md.
export const NH_MEASURE_GROUP_RENDER_ORDER: readonly string[] = [
  // NH_STAR_RATING excluded — displayed in NursingHomeSummaryDashboard + FiveStarDisplay
  "NH_QUALITY_LONG_STAY",
  "NH_QUALITY_SHORT_STAY",
  "NH_QUALITY_CLAIMS",
  "NH_STAFFING",
  "NH_SNF_QRP",
  "NH_INSPECTION",
  "NH_PENALTIES",
  "SPENDING",
];

// Scope/severity code descriptions (A-L scale).
// Source: CMS State Operations Manual, Appendix P.
export const SCOPE_SEVERITY_DESCRIPTIONS: Readonly<Record<string, string>> = {
  A: "Isolated, no actual harm, potential for minimal harm",
  B: "Pattern, no actual harm, potential for minimal harm",
  C: "Widespread, no actual harm, potential for minimal harm",
  D: "Isolated, no actual harm, potential for more than minimal harm",
  E: "Pattern, no actual harm, potential for more than minimal harm",
  F: "Widespread, no actual harm, potential for more than minimal harm",
  G: "Isolated, actual harm that is not immediate jeopardy",
  H: "Pattern, actual harm that is not immediate jeopardy",
  I: "Widespread, actual harm that is not immediate jeopardy",
  J: "Isolated, immediate jeopardy to resident health or safety",
  K: "Pattern, immediate jeopardy to resident health or safety",
  L: "Widespread, immediate jeopardy to resident health or safety",
};

// Severity tiers for visual hierarchy (display-philosophy.md NH-8).
export type SeverityTier = "low" | "moderate" | "high" | "immediate_jeopardy";
export function scopeSeverityTier(code: string | null): SeverityTier {
  if (!code) return "low";
  const c = code.toUpperCase();
  if ("JKL".includes(c)) return "immediate_jeopardy";
  if ("GHI".includes(c)) return "high";
  if ("DEF".includes(c)) return "moderate";
  return "low";
}

// Plain-language scope and severity explanations (8th-grade reading level).
// These decompose the A-L code into its two dimensions so consumers can
// understand what the code means without memorizing a 12-cell matrix.
// Source: CMS State Operations Manual, Appendix P — same source as above,
// rephrased for consumer readability.

/** How many residents were affected. */
export function scopePlain(code: string | null): string {
  if (!code) return "";
  const c = code.toUpperCase();
  if ("ADG J".includes(c)) return "Affected one or a few residents";
  if ("BEH K".includes(c)) return "Affected multiple residents";
  if ("CFI L".includes(c)) return "Found across the facility";
  return "";
}

/** How serious the finding was. */
export function severityPlain(code: string | null): string {
  if (!code) return "";
  const c = code.toUpperCase();
  if ("ABC".includes(c)) return "No harm occurred — low risk of harm";
  if ("DEF".includes(c)) return "No harm occurred — could have caused harm";
  if ("GHI".includes(c)) return "Harm occurred to one or more residents";
  if ("JKL".includes(c)) return "Immediate threat to resident health or safety";
  return "";
}

/** One-sentence summary combining scope + severity for consumer display. */
export function scopeSeveritySummary(code: string | null): string {
  if (!code) return "Severity not classified";
  const scope = scopePlain(code);
  const severity = severityPlain(code);
  if (!scope || !severity) return "Severity not classified";
  return `${severity}. ${scope}.`;
}

// Consumer-friendly deficiency category names.
// CMS categories use regulatory terminology. These mappings provide shorter,
// more understandable labels. The CMS category name is always available as
// attributed secondary text.
export const DEFICIENCY_CATEGORY_PLAIN: Readonly<Record<string, string>> = {
  "Freedom from Abuse, Neglect, and Exploitation Deficiencies": "Resident Protection",
  "Administration Deficiencies": "Facility Management",
  "Quality of Care Deficiencies": "Care Quality",
  "Quality of Life Deficiencies": "Quality of Life",
  "Resident Rights Deficiencies": "Resident Rights",
  "Nutrition and Dietary Deficiencies": "Nutrition and Food",
  "Pharmacy Service Deficiencies": "Medication Management",
  "Infection Control Deficiencies": "Infection Control",
  "Environmental Deficiencies": "Environment and Safety",
  "Resident Assessment and Care Planning Deficiencies": "Care Planning",
  "Nursing Services Deficiencies": "Nursing Care",
  "Physical Environment Deficiencies": "Physical Environment",
  "Dental Services Deficiencies": "Dental Care",
  "Laboratory Services Deficiencies": "Lab Services",
};

// Birthing-Friendly designation description (8th-grade reading level).
// Source: CMS "Birthing-Friendly" designation criteria.
export const BIRTHING_FRIENDLY_DESCRIPTION =
  "\"Birthing-Friendly\" is a CMS designation for hospitals that meet standards " +
  "for high-quality maternity care. To earn this designation, a hospital must " +
  "take part in a state or national program to improve care for mothers and put " +
  "in place proven practices to reduce serious complications during and after " +
  "childbirth.";

// HCAHPS survey response count caution thresholds and text.
// CMS footnote 6 = fewer than 100 completed surveys.
// CMS footnote 10 = fewer than 50 completed surveys.
export const HCAHPS_LOW_SURVEY_FOOTNOTE = 6;
export const HCAHPS_VERY_LOW_SURVEY_FOOTNOTE = 10;

export const HCAHPS_LOW_SURVEY_CAUTION =
  "Fewer than 100 patients completed this survey at this hospital. With this " +
  "few responses, these scores may not fully reflect the typical patient experience.";

export const HCAHPS_VERY_LOW_SURVEY_CAUTION =
  "Very few patients completed this survey at this hospital — fewer than 50. " +
  "These scores may not reliably reflect the typical patient experience.";

// Template 3f: Population context warning for the compare page.
// Fires unconditionally until dual_eligible_proportion is available (deferred).
export const POPULATION_CONTEXT_WARNING =
  "Socioeconomic population data is not yet available for one or both facilities. " +
  "Differences in patient populations may affect comparability.";

// Ownership-quality disclaimer (legal-compliance.md § Ownership Data).
export const OWNERSHIP_QUALITY_DISCLAIMER =
  "This panel displays CMS-published ownership data. Ownership structure and quality " +
  "outcomes are sourced from separate CMS datasets. Association does not establish a " +
  "causal relationship between facility ownership and quality outcomes.";

// External CMS reference: official Medicare.gov publication for nursing home
// selection. Linked at the top of NH profile and NH compare pages as a
// CMS-attributed reference (legal-compliance.md positioning: we point to CMS
// resources, we do not editorialize the choosing).
export const CMS_NH_GUIDE_URL =
  "https://www.medicare.gov/publications/02174-your-guide-to-choosing-a-nursing-home"; // compliance-ok
export const CMS_NH_GUIDE_TITLE = "Your Guide to Choosing a Nursing Home"; // compliance-ok

// ─── SEO Constants ────────────────────────────────────────────────────
//
// Subject to legal-compliance.md § Positioning constraints — review with
// the same care as disclaimer text. See legal-compliance.md for the full
// list of prohibited framings (advisory, superlative, predictive,
// personalized, etc.). Acceptable framing follows CMS's own
// "find and compare" precedent (medicare.gov/care-compare). Constants
// are referenced by lib/seo.ts and generateMetadata callers — components
// must not inline these strings.

export const SITE_NAME = "OpenChart Health";

// Used on the OG image and PWA manifest. Keep a comma — build-og-image.ts
// splits the tagline at the first comma for two-line wrapping.
export const SITE_TAGLINE =
  "See what CMS reports about every certified hospital and nursing home, " +
  "with statistical uncertainty made visible.";

export const SITE_DESCRIPTION =
  "What CMS reports on every certified hospital and nursing home: quality " +
  "measures, inspections, staffing, and statistical uncertainty made visible.";

// Default base URL for canonical links and structured data. Override via
// NEXT_PUBLIC_SITE_URL at build time. No trailing slash.
export const DEFAULT_SITE_URL = "https://openchart.health";

// Path to the default Open Graph image (served from /public). A neutral
// placeholder until per-provider OG images are generated.
export const DEFAULT_OG_IMAGE_PATH = "/og-default.png";
export const DEFAULT_OG_IMAGE_WIDTH = 1200;
export const DEFAULT_OG_IMAGE_HEIGHT = 630;
export const DEFAULT_OG_IMAGE_ALT = "OpenChart Health — CMS quality data";

// Title cap: search engines truncate around 60 chars. Description cap: ~160.
export const SEO_TITLE_MAX = 60;
export const SEO_DESCRIPTION_MAX = 160;

// Title suffix appended to per-page titles, e.g. "Methodology | OpenChart Health".
export const TITLE_SUFFIX = ` | ${SITE_NAME}`;

// Per-route static metadata. Keep titles ≤ SEO_TITLE_MAX once the suffix is
// applied; descriptions ≤ SEO_DESCRIPTION_MAX. The values below were sized
// against those caps.

export const HOME_TITLE_BASE = "Find and Compare CMS Quality Data";
export const HOME_DESCRIPTION =
  "See what CMS reports on every certified hospital and nursing home: quality " +
  "measures, inspections, staffing, and statistical uncertainty made visible.";

// OG description on the home page. Slightly longer / more compelling than
// the meta description because it's social-share copy, not a Google snippet.
// Kept under SEO_DESCRIPTION_MAX so the same string also works as a fallback.
export const HOME_OG_DESCRIPTION =
  "CMS publishes detailed quality data on every certified hospital and " +
  "nursing home. OpenChart Health republishes it with uncertainty visible.";

// Page H1 + intro tagline. Rendered in app/page.tsx; the H1 itself remains
// HOME_TITLE_BASE so search engines, OG preview, and the visible heading
// match. The intro paragraph carries the positioning angle: this site is
// republication of CMS data, not an editorial ordering. // compliance-ok
export const HOME_INTRO_TEXT =
  "CMS publishes detailed quality data on every certified hospital and " +
  "nursing home in the country. Most facilities only highlight the best of " +
  "it. This site republishes the full record — quality measures, " +
  "inspections, staffing, and ownership — with statistical uncertainty " +
  "made visible.";

export const METHODOLOGY_TITLE_BASE = "Methodology";
export const METHODOLOGY_DESCRIPTION =
  "How OpenChart Health republishes CMS hospital and nursing home data: " +
  "interval estimates, uncertainty visualization, sources, and direction attribution.";

export const COMPARE_TITLE_BASE = "Compare Two Providers";
export const COMPARE_DESCRIPTION =
  "Side-by-side CMS quality data for two hospitals or nursing homes, with " +
  "reporting periods, sample sizes, and population-context flags surfaced.";

export const FILTER_EXPLORE_TITLE_BASE = "Explore Hospitals by Measure";
export const FILTER_EXPLORE_DESCRIPTION =
  "Sort and filter every reporting hospital by any CMS quality measure — " +
  "factual ordering with footnotes, sample sizes, and intervals preserved.";

export const FILTER_EXPLORE_NH_TITLE_BASE = "Explore Nursing Homes by Measure";
export const FILTER_EXPLORE_NH_DESCRIPTION =
  "Sort and filter every certified nursing home by any CMS quality measure: " +
  "staffing, inspections, and resident outcomes with full context preserved.";

// Twitter handle (optional). Empty string disables the @site card metadata.
export const SITE_TWITTER_HANDLE = "";

// ─── Per-provider meta description builders ──────────────────────────
//
// These return the literal copy used in <meta name="description"> for
// hospital and nursing home profile pages. They live here so the entire
// SEO copy surface lives in constants.ts; lib/seo.ts assembles the
// Metadata object from them and applies the SEO_DESCRIPTION_MAX clamp.
//
// Constraints:
//   - Factual republication framing only. No advisory, no superlatives,
//     no predictive language. See legal-compliance.md § Positioning.
//   - "What CMS reports on …" is the canonical opening. It is literally
//     true — that is exactly what each profile page contains.
//   - For nursing homes, surface SFF / SFF-candidate / abuse-citation
//     status when present. These are public CMS designations; the
//     disclosure on the profile page is appropriate at the search-result
//     blurb level too.
//   - Total length is enforced by the clamp() in lib/seo.ts; these
//     templates aim to fit under 160 chars in normal cases without
//     relying on truncation.

export interface HospitalMetaDescriptionVars {
  name: string;
  location: string | null;
  measureCount: number;
  periodRange: string | null;
}

/**
 * Per-hospital meta description. Builds a baseline that always fits under
 * SEO_DESCRIPTION_MAX (160) for typical names, and appends the reporting
 * period range only when there is room. The lib/seo.ts clamp() backstops
 * any unusually long facility name.
 */
export function HOSPITAL_META_DESCRIPTION(
  v: HospitalMetaDescriptionVars
): string {
  const where = v.location ? `${v.name} in ${v.location}` : v.name;
  const baseline =
    `What CMS reports on ${where}: ${v.measureCount} quality measures ` +
    `with intervals, footnotes, sample sizes.`;
  if (!v.periodRange) return baseline;

  const withPeriods = baseline.replace(
    /\.$/,
    `. Periods ${v.periodRange}.`
  );
  return withPeriods.length <= SEO_DESCRIPTION_MAX ? withPeriods : baseline;
}

export interface NursingHomeMetaDescriptionVars {
  name: string;
  location: string | null;
  measureCount: number;
  inspectionCount: number;
  periodRange: string | null;
  isSpecialFocusFacility: boolean;
  isSpecialFocusFacilityCandidate: boolean;
  isAbuseIcon: boolean;
}

/**
 * Per-nursing-home meta description. Surfaces CMS-published designations
 * (SFF, SFF candidate, abuse-citation flag) when present — these are
 * public CMS facts, and surfacing them at the search-result level is
 * republication, not editorial characterization.
 *
 * Fits under SEO_DESCRIPTION_MAX in normal cases; the lib/seo.ts clamp()
 * backstops outliers. The period range is dropped before the body is
 * truncated when an SFF/abuse prefix consumes the budget.
 */
export function NURSING_HOME_META_DESCRIPTION(
  v: NursingHomeMetaDescriptionVars
): string {
  const where = v.location ? `${v.name} in ${v.location}` : v.name;

  let prefix = "";
  if (v.isSpecialFocusFacility) {
    prefix = "CMS Special Focus Facility. ";
  } else if (v.isSpecialFocusFacilityCandidate) {
    prefix = "CMS Special Focus Facility candidate. ";
  } else if (v.isAbuseIcon) {
    prefix = "CMS abuse-citation flag. ";
  }

  const baseline =
    `${prefix}What CMS reports on ${where}: ${v.measureCount} measures, ` +
    `${v.inspectionCount} inspections, staffing, ownership.`;
  if (!v.periodRange) return baseline;

  const withPeriods = baseline.replace(
    /\.$/,
    `. Periods ${v.periodRange}.`
  );
  return withPeriods.length <= SEO_DESCRIPTION_MAX ? withPeriods : baseline;
}

// ─── /filter-explore copy ────────────────────────────────────────────
//
// Subject to legal-compliance.md § Positioning. This view is factual  // compliance-ok
// ordering of CMS data — never labeled as a ranking, leaderboard, or  // compliance-ok
// "top/bottom" list. Every visible string lives here so the compliance
// review surface is one file.

// Provider-type-aware page copy. The /filter-explore page is rendered for
// either hospitals or nursing homes; copy resolves at render time.
export const FILTER_EXPLORE_HEADING_HOSPITAL = "Explore Hospitals by Measure";
export const FILTER_EXPLORE_HEADING_NURSING_HOME = "Explore Nursing Homes by Measure";
export const FILTER_EXPLORE_SUBHEADING_HOSPITAL =
  "Sort and filter CMS-reported quality measures across hospitals. " +
  "Select a measure to see all hospitals that report it.";
export const FILTER_EXPLORE_SUBHEADING_NURSING_HOME =
  "Sort and filter CMS-reported quality measures across nursing homes. " +
  "Select a measure to see all nursing homes that report it.";

// Legacy aliases for the hospital-default values. Page passes provider-type-
// specific strings explicitly; these remain for any caller that still imports
// the original names (e.g., SEO metadata).
export const FILTER_EXPLORE_HEADING = FILTER_EXPLORE_HEADING_HOSPITAL;
export const FILTER_EXPLORE_SUBHEADING = FILTER_EXPLORE_SUBHEADING_HOSPITAL;

export const FILTER_EXPLORE_PICKER_HEADING = "Select a Measure";
export const FILTER_EXPLORE_PICKER_SEARCH_PLACEHOLDER = "Search measures…";
export const FILTER_EXPLORE_EMPTY_STATE_HOSPITAL =
  "Select a measure to see all hospitals that report it.";
export const FILTER_EXPLORE_EMPTY_STATE_NURSING_HOME =
  "Select a measure to see all nursing homes that report it.";
export const FILTER_EXPLORE_EMPTY_STATE = FILTER_EXPLORE_EMPTY_STATE_HOSPITAL;
export const FILTER_EXPLORE_EMPTY_RESULTS_HOSPITAL =
  "No hospitals match the current filters.";
export const FILTER_EXPLORE_EMPTY_RESULTS_NURSING_HOME =
  "No nursing homes match the current filters.";
export const FILTER_EXPLORE_EMPTY_RESULTS = FILTER_EXPLORE_EMPTY_RESULTS_HOSPITAL;

export const FILTER_EXPLORE_LOADING = "Loading measure data…";
export const FILTER_EXPLORE_LOAD_ERROR =
  "Could not load measure data. Refresh to try again.";

// Filter row labels and helper copy.
export const FILTER_EXPLORE_STATE_LABEL = "State";
export const FILTER_EXPLORE_STATE_ALL = "All states";
export const FILTER_EXPLORE_SUBTYPE_LABEL_HOSPITAL = "Hospital type";
export const FILTER_EXPLORE_SUBTYPE_LABEL_NURSING_HOME = "Certification";
export const FILTER_EXPLORE_OWNERSHIP_LABEL = "Ownership";
export const FILTER_EXPLORE_OWNERSHIP_ALL = "All ownership";
export const FILTER_EXPLORE_SUBTYPE_LABEL = FILTER_EXPLORE_SUBTYPE_LABEL_HOSPITAL;
export const FILTER_EXPLORE_SUBTYPE_ALL = "All types";
export const FILTER_EXPLORE_NAME_SEARCH_LABEL_HOSPITAL = "Hospital name";
export const FILTER_EXPLORE_NAME_SEARCH_LABEL_NURSING_HOME = "Facility name";
export const FILTER_EXPLORE_NAME_SEARCH_LABEL = FILTER_EXPLORE_NAME_SEARCH_LABEL_HOSPITAL;
export const FILTER_EXPLORE_NAME_SEARCH_PLACEHOLDER = "Search by name…";
export const FILTER_EXPLORE_CLEAR_FILTERS = "Clear filters";

// Sort controls.
export const FILTER_EXPLORE_SORT_VALUE_ASC = "Value: low to high";
export const FILTER_EXPLORE_SORT_VALUE_DESC = "Value: high to low";

// Status labels for the table cells.
export const FILTER_EXPLORE_STATUS_SUPPRESSED = "Suppressed";
export const FILTER_EXPLORE_STATUS_NOT_REPORTED = "Not reported";
export const FILTER_EXPLORE_STATUS_COUNT_SUPPRESSED =
  "CMS suppressed the case count for this measure value to protect privacy.";

// Distribution histogram caption.
export const FILTER_EXPLORE_DISTRIBUTION_CAPTION = (
  n: number,
  providerType: FilterExploreProviderType = "HOSPITAL"
): string => {
  const noun = providerType === "NURSING_HOME" ? "nursing homes" : "hospitals";
  return `Distribution across ${n.toLocaleString("en-US")} reporting ${noun}.`;
};

// Count summary above the table.
export const FILTER_EXPLORE_COUNT_SUMMARY = (
  visible: number,
  total: number,
  providerType: FilterExploreProviderType = "HOSPITAL"
): string => {
  const noun = providerType === "NURSING_HOME" ? "nursing homes" : "hospitals";
  return `${visible.toLocaleString("en-US")} of ${total.toLocaleString("en-US")} ${noun}`;
};

// Nav bar label — non-advisory "Filter & Explore" rather than "Find" or "Choose".
export const FILTER_EXPLORE_NAV_LABEL = "Filter & Explore";

// Per-measure attribution prefix (matches Template 3b verbatim).
export const FILTER_EXPLORE_ATTRIBUTION_LABEL = "Source";

// Compliance note rendered above the table when many hospitals are visible.
export const FILTER_EXPLORE_PERIOD_NOTE = "Reporting period";
export const FILTER_EXPLORE_SAMPLE_SIZE_LABEL = "Cases";
export const FILTER_EXPLORE_VALUE_LABEL = "Value";
export const FILTER_EXPLORE_INTERVAL_LABEL = "Interval";
export const FILTER_EXPLORE_HOSPITAL_LABEL = "Hospital";
export const FILTER_EXPLORE_STATE_COL_LABEL = "State";
export const FILTER_EXPLORE_STATUS_LABEL = "Status";

// Footnote count badge tooltip.
export const FILTER_EXPLORE_FOOTNOTE_COUNT = (n: number): string =>
  `${n} CMS footnote${n === 1 ? "" : "s"} attached to this value.`;

// One-line unit explanations for column-header tooltips. The raw `unit` value
// from MEASURE_REGISTRY is sometimes self-evident ("percent") and sometimes
// not ("ratio" — observed/expected? above/below 1?). These strings make the
// scale concrete without paraphrasing the measure definition itself.
export const UNIT_DESCRIPTION: Readonly<Record<string, string>> = {
  percent: "Percent (0–100). Higher numbers mean a larger share of cases.",
  ratio:
    "Standardized ratio. 1.0 means as expected; below 1.0 is fewer events than expected, above 1.0 is more.",
  rate: "Rate per 1,000 admissions or discharges, as published by CMS.",
  minutes: "Minutes.",
  count: "Count of events.",
  score: "Score (CMS-defined scale).",
  days: "Days.",
  hours_per_resident_day:
    "Nursing hours per resident per day. CMS staffing minimum is 0.55 RN hours and 3.48 total nurse hours.",
};

// CMS direction phrasings used on hover and inline indicators in preset tables.
export const DIRECTION_PHRASE = {
  LOWER_IS_BETTER: "CMS: lower values associated with better outcomes",
  HIGHER_IS_BETTER: "CMS: higher values associated with better outcomes",
} as const;

// ─── Preset views (multi-measure dashboards) ───────────────────────
//
// Presets surface related measures side-by-side in one row per hospital —
// the natural way to look at, e.g., 30-day mortality across heart attack,
// heart failure, pneumonia, COPD, CABG, and stroke at the same time.
// Aligned with the project ethos: tail risk is primary content, not a
// secondary tab. Tail-risk presets lead the list. Single-measure mode
// remains available below for deeper drill-in.
//
// Each preset is just a curated list of measure_ids — the table fetches
// all of them in parallel and merges by CCN.

export const FILTER_EXPLORE_PRESETS_HEADING = "Preset Views";
export const FILTER_EXPLORE_SINGLE_MEASURE_HEADING = "Single Measure";

export type FilterExploreProviderType = "HOSPITAL" | "NURSING_HOME";

export interface FilterExplorePreset {
  id: string;
  label: string;
  description: string;
  measure_ids: readonly string[];
  tail_risk: boolean;
  provider_type: FilterExploreProviderType;
  /**
   * Optional measure_id whose sample_size should be lifted into a dedicated
   * "shared sample" column at the front of the measure columns. Used for
   * presets where every measure shares a denominator — most notably HCAHPS,
   * where one survey count powers all topic-level response percentages.
   * The value is pulled from the merged row's cell for this measure_id.
   */
  shared_sample_measure_id?: string;
  /** Header label for the shared-sample column (e.g. "Surveys", "Cases"). */
  shared_sample_label?: string;
}

// Short, scannable column labels per measure_id for use in multi-measure
// preset tables. CMS-published measure names are too verbose to render as
// table headers when 10+ columns are visible. These labels keep meaning
// intact (heart attack, MRSA, doctor respect) without paraphrasing CMS's
// authoritative definition — the full name remains accessible via tooltip
// and the per-measure detail view.
export const MEASURE_SHORT_LABEL: Readonly<Record<string, string>> = {
  // 30-day mortality
  MORT_30_AMI: "Heart attack",
  MORT_30_HF: "Heart failure",
  MORT_30_PN: "Pneumonia",
  MORT_30_COPD: "COPD",
  MORT_30_CABG: "CABG surgery",
  MORT_30_STK: "Stroke",
  // 30-day readmissions
  READM_30_AMI: "Heart attack",
  READM_30_HF: "Heart failure",
  READM_30_PN: "Pneumonia",
  READM_30_COPD: "COPD",
  READM_30_CABG: "CABG surgery",
  READM_30_HIP_KNEE: "Hip/knee replacement",
  // Excess days in acute care
  EDAC_30_AMI: "Heart attack",
  EDAC_30_HF: "Heart failure",
  EDAC_30_PN: "Pneumonia",
  // Healthcare-associated infections (CDC standardized infection ratios)
  HAI_1_SIR: "CLABSI",
  HAI_2_SIR: "CAUTI",
  HAI_3_SIR: "SSI — colon",
  HAI_4_SIR: "SSI — hysterectomy",
  HAI_5_SIR: "MRSA",
  HAI_6_SIR: "C. difficile",
  // AHRQ patient safety indicators
  PSI_90: "PSI 90 composite",
  PSI_03: "Pressure ulcer",
  PSI_04: "Death after surgery",
  PSI_06: "Collapsed lung",
  PSI_08: "Hip fracture",
  PSI_09: "Surgical bleeding",
  PSI_10: "Postop kidney injury",
  PSI_11: "Postop respiratory failure",
  PSI_12: "Postop blood clot",
  PSI_13: "Postop sepsis",
  PSI_14: "Wound dehiscence",
  PSI_15: "Accidental laceration",
  COMP_HIP_KNEE: "Hip/knee complication",
  // Sepsis care
  SEP_1: "Sepsis bundle",
  SEV_SEP_3HR: "Severe sepsis 3-hr",
  SEV_SEP_6HR: "Severe sepsis 6-hr",
  SEP_SH_3HR: "Septic shock 3-hr",
  SEP_SH_6HR: "Septic shock 6-hr",
  // Stroke care
  STK_02: "Antithrombotic",
  STK_03: "Anticoagulant",
  STK_05: "Antithrombotic by day 2",
  // HCAHPS — top responses (positive end of distribution)
  H_HSP_RATING_9_10: "Hospital rating 9–10",
  H_RECMND_DY: "Definitely recommend",  // compliance-ok (HCAHPS response label)
  H_NURSE_RESPECT_A_P: "Nurse respect",
  H_NURSE_LISTEN_A_P: "Nurse listening",
  H_NURSE_EXPLAIN_A_P: "Nurse explanation",
  H_DOCTOR_RESPECT_A_P: "Doctor respect",
  H_DOCTOR_LISTEN_A_P: "Doctor listening",
  H_DOCTOR_EXPLAIN_A_P: "Doctor explanation",
  H_CLEAN_HSP_A_P: "Room cleanliness",
  H_QUIET_HSP_A_P: "Quietness at night",
  // HCAHPS — adverse responses (negative end of distribution)
  H_HSP_RATING_0_6: "Hospital rating 0–6",
  H_RECMND_DN: "Would not recommend",  // compliance-ok (HCAHPS response label)
  H_NURSE_RESPECT_SN_P: "Nurse respect (low)",
  H_NURSE_LISTEN_SN_P: "Nurse listening (low)",
  H_NURSE_EXPLAIN_SN_P: "Nurse explanation (low)",
  H_DOCTOR_RESPECT_SN_P: "Doctor respect (low)",
  H_DOCTOR_LISTEN_SN_P: "Doctor listening (low)",
  H_DOCTOR_EXPLAIN_SN_P: "Doctor explanation (low)",
  H_CLEAN_HSP_SN_P: "Room cleanliness (low)",
  H_QUIET_HSP_SN_P: "Quietness at night (low)",
  // Outpatient imaging efficiency
  "OP-10": "Abdominal CT contrast",
  "OP-13": "Cardiac imaging pre-surgery",
  "OP-8": "MRI lumbar spine",
  OP_22: "ED left without seen",

  // ─── Nursing home short labels ────────────────────────────────────
  // Five-Star ratings
  NH_STAR_OVERALL: "Overall (★)",
  NH_STAR_HEALTH_INSP: "Health inspection (★)",
  NH_STAR_STAFFING: "Staffing (★)",
  NH_STAR_QM: "Quality measures (★)",
  NH_STAR_LS_QM: "Long-stay QM (★)",
  NH_STAR_SS_QM: "Short-stay QM (★)",
  // Long-stay MDS measures
  NH_MDS_401: "ADL decline",
  NH_MDS_404: "Weight loss",
  NH_MDS_406: "Catheter use",
  NH_MDS_407: "UTI",
  NH_MDS_408: "Depression",
  NH_MDS_409: "Restraints",
  NH_MDS_410: "Falls w/ major injury",
  NH_MDS_415: "Pneumococcal vaccine",
  NH_MDS_451: "Walking decline",
  NH_MDS_452: "Antianxiety/hypnotic",
  NH_MDS_454: "Flu vaccine",
  NH_MDS_479: "Pressure ulcers",
  NH_MDS_480: "Incontinence onset",
  NH_MDS_481: "Antipsychotic",
  // Short-stay MDS + claims
  NH_MDS_430: "Pneumococcal vaccine",
  NH_MDS_434: "New antipsychotic",
  NH_MDS_472: "Flu vaccine",
  NH_CLAIMS_521: "Rehospitalization",
  NH_CLAIMS_522: "ED visit",
  NH_CLAIMS_551: "Hospitalizations / 1k days",
  NH_CLAIMS_552: "ED visits / 1k days",
  // Staffing — labels show "what" (nurse/RN/aide/weekend), "which series"
  // (case-mix-adjusted vs reported), and units. The per-resident-per-day
  // measures get "hrs" so consumers can read the column at a glance without
  // hovering. Turnover (%) and admin departures (count) don't need it.
  NH_STAFF_ADJ_TOTAL_HPRD: "Adjusted nurse hrs",
  NH_STAFF_ADJ_RN_HPRD: "Adjusted RN hrs",
  NH_STAFF_ADJ_WEEKEND_HPRD: "Adjusted weekend hrs",
  NH_STAFF_REPORTED_TOTAL_HPRD: "Reported nurse hrs",
  NH_STAFF_REPORTED_RN_HPRD: "Reported RN hrs",
  NH_STAFF_REPORTED_AIDE_HPRD: "Reported aide hrs",
  NH_STAFF_TOTAL_TURNOVER: "Total turnover",
  NH_STAFF_RN_TURNOVER: "RN turnover",
  NH_STAFF_ADMIN_DEPARTURES: "Admin departures",
  // Inspection
  NH_INSP_WEIGHTED_SCORE: "Weighted health score",
  NH_INSP_TOTAL_HEALTH_DEF: "Total deficiencies",
  // Synthetic per-severity counts from most-recent inspection event
  // (120-day cluster matching the per-NH page rollup).
  NH_INSP_RECENT_JKL: "Immediate jeopardy (J–L)",
  NH_INSP_RECENT_GHI: "Actual harm (G–I)",
  NH_INSP_RECENT_DF: "Potential harm (D–F)",
  NH_INSP_RECENT_AC: "Low-risk (A–C)",
  NH_INSP_RECENT_TOTAL: "Total citations",
  NH_INSP_RECENT_COMPLAINT: "Complaint citations",
  // SNF QRP
  S_004_01: "Preventable readmission",
  S_005_02: "Discharge to community",
  S_006_01: "Medicare spending (MSPB)",
  S_007_02: "Drug regimen review",
  S_013_02: "Falls w/ major injury",
  S_024_06: "Discharge self-care score",
  S_025_06: "Discharge mobility score",
  S_038_02: "Pressure ulcer/injury",
  S_039_01: "SNF HAI hospitalization",
  S_040_02: "COVID staff vaccination",
  S_041_01: "Flu staff vaccination",
  S_042_02: "Discharge function score",
  S_043_02: "TOH to provider",
  S_044_02: "TOH to patient",
  S_045_01: "Resident COVID vaccine",
};

// Picker order is array order. Within each provider type the list is sorted
// by consumer relevance, not alphabet:
//   1. Patient experience first — most relatable for an ordinary consumer.
//   2. Cross-condition tail-risk views (mortality, readmissions, infections,
//      patient safety) next — the adverse-event lenses that align with the
//      project's tail-risk-is-primary philosophy.
//   3. Narrower process measures (sepsis, stroke, imaging) last — high
//      clinical relevance to specific patients but narrower audience for
//      hospital-shopping.
// MEASURE_GROUP_RENDER_ORDER above the registry encodes the same priority
// for the hospital profile page; this list mirrors it.
export const FILTER_EXPLORE_PRESETS: readonly FilterExplorePreset[] = [
  // ─── Hospital presets — relevance order ──────────────────────────
  {
    id: "patient-experience",
    label: "Patient Experience (Survey)",
    description: "Top-response rates across HCAHPS survey topics. Adjusted by CMS for patient mix. Survey counts apply to every topic — sort the Surveys column to find low-volume hospitals.",
    measure_ids: [
      "H_HSP_RATING_9_10",
      "H_RECMND_DY",
      "H_NURSE_RESPECT_A_P",
      "H_NURSE_LISTEN_A_P",
      "H_NURSE_EXPLAIN_A_P",
      "H_DOCTOR_RESPECT_A_P",
      "H_DOCTOR_LISTEN_A_P",
      "H_DOCTOR_EXPLAIN_A_P",
      "H_CLEAN_HSP_A_P",
      "H_QUIET_HSP_A_P",
    ],
    tail_risk: false,
    provider_type: "HOSPITAL",
    shared_sample_measure_id: "H_HSP_RATING_9_10",
    shared_sample_label: "Surveys",
  },
  {
    id: "patient-experience-adverse",
    label: "Patient Experience — Adverse Responses",
    description: "Negative-end response rates across HCAHPS topics. Higher values indicate worse-reported experience. Survey counts apply to every topic — sort the Surveys column to find low-volume hospitals.",
    measure_ids: [
      "H_HSP_RATING_0_6",
      "H_RECMND_DN",
      "H_NURSE_RESPECT_SN_P",
      "H_NURSE_LISTEN_SN_P",
      "H_NURSE_EXPLAIN_SN_P",
      "H_DOCTOR_RESPECT_SN_P",
      "H_DOCTOR_LISTEN_SN_P",
      "H_DOCTOR_EXPLAIN_SN_P",
      "H_CLEAN_HSP_SN_P",
      "H_QUIET_HSP_SN_P",
    ],
    tail_risk: true,
    provider_type: "HOSPITAL",
    shared_sample_measure_id: "H_HSP_RATING_0_6",
    shared_sample_label: "Surveys",
  },
  {
    id: "infections",
    label: "Healthcare-Associated Infections",
    description: "Standardized infection ratios for six CDC-tracked infection types.",
    measure_ids: [
      "HAI_1_SIR",
      "HAI_2_SIR",
      "HAI_3_SIR",
      "HAI_4_SIR",
      "HAI_5_SIR",
      "HAI_6_SIR",
    ],
    tail_risk: true,
    provider_type: "HOSPITAL",
  },
  {
    id: "mortality-30day",
    label: "30-Day Mortality",
    description: "Risk-adjusted death rate within 30 days for six conditions.",
    measure_ids: [
      "MORT_30_AMI",
      "MORT_30_HF",
      "MORT_30_PN",
      "MORT_30_COPD",
      "MORT_30_CABG",
      "MORT_30_STK",
    ],
    tail_risk: true,
    provider_type: "HOSPITAL",
  },
  {
    id: "readmissions-30day",
    label: "30-Day Readmissions",
    description: "Risk-adjusted unplanned readmission rate for six conditions.",
    measure_ids: [
      "READM_30_AMI",
      "READM_30_HF",
      "READM_30_PN",
      "READM_30_COPD",
      "READM_30_CABG",
      "READM_30_HIP_KNEE",
    ],
    tail_risk: true,
    provider_type: "HOSPITAL",
  },
  {
    id: "return-days",
    label: "Hospital Return Days (EDAC)",
    description: "Excess days in acute care after discharge — heart attack, heart failure, pneumonia.",
    measure_ids: ["EDAC_30_AMI", "EDAC_30_HF", "EDAC_30_PN"],
    tail_risk: true,
    provider_type: "HOSPITAL",
  },
  {
    id: "patient-safety",
    label: "Patient Safety Indicators",
    description: "AHRQ patient safety events: pressure ulcers, falls, sepsis, perioperative complications.",
    measure_ids: [
      "PSI_90",
      "PSI_03",
      "PSI_04",
      "PSI_06",
      "PSI_08",
      "PSI_09",
      "PSI_10",
      "PSI_11",
      "PSI_12",
      "PSI_13",
      "PSI_14",
      "PSI_15",
      "COMP_HIP_KNEE",
    ],
    tail_risk: true,
    provider_type: "HOSPITAL",
  },
  {
    id: "sepsis-care",
    label: "Sepsis Care",
    description: "Compliance with sepsis bundle protocols — early recognition and treatment.",
    measure_ids: ["SEP_1", "SEV_SEP_3HR", "SEV_SEP_6HR", "SEP_SH_3HR", "SEP_SH_6HR"],
    tail_risk: false,
    provider_type: "HOSPITAL",
  },
  {
    id: "stroke-care",
    label: "Stroke Care",
    description: "Process measures for stroke admission and recovery.",
    measure_ids: ["STK_02", "STK_03", "STK_05"],
    tail_risk: false,
    provider_type: "HOSPITAL",
  },
  {
    id: "imaging-efficiency",
    label: "Outpatient Imaging Efficiency",
    description: "Use of contrast and follow-up imaging — proxies for unnecessary radiation exposure.",
    measure_ids: ["OP-10", "OP-13", "OP-8", "OP_22"],
    tail_risk: false,
    provider_type: "HOSPITAL",
  },

  // ─── Nursing home presets — relevance order ──────────────────────
  // 1. Five-Star Ratings is the headline rating most consumers come for.
  // 2. Inspection Findings is the broad-relevance regulatory signal —
  //    severity-tier breakdown surfaces tail risk first.
  // 3. Resident Safety, Staffing, and Long-Stay Quality cover the
  //    full long-term-care population.
  // 4. Short-Stay and SNF QRP are narrower (post-acute audience).
  {
    id: "nh-five-star",
    label: "Five-Star Ratings",
    description: "CMS Five-Star overall rating and the three domain sub-ratings (Health Inspection, Staffing, Quality Measures).",
    measure_ids: [
      "NH_STAR_OVERALL",
      "NH_STAR_HEALTH_INSP",
      "NH_STAR_STAFFING",
      "NH_STAR_QM",
      "NH_STAR_LS_QM",
      "NH_STAR_SS_QM",
    ],
    tail_risk: false,
    provider_type: "NURSING_HOME",
  },
  {
    id: "nh-inspection",
    label: "Inspection Findings",
    description:
      "Most-recent inspection event broken out by CMS scope-and-severity tier (J–L immediate jeopardy, G–I actual harm, D–F potential harm, A–C low risk), plus the CMS weighted health inspection score. " +
      "A standard survey and any follow-up revisits or complaint investigations within 120 days are treated as one inspection event, matching the rollup used on individual nursing home pages and CMS Five-Star rating-cycle weighting. " +
      "Note: state inspection regimes vary substantially — citation counts and severity classifications reflect both facility quality and state inspection practice. Use the State filter to compare within a state.",
    measure_ids: [
      "NH_INSP_RECENT_JKL",
      "NH_INSP_RECENT_GHI",
      "NH_INSP_RECENT_DF",
      "NH_INSP_RECENT_AC",
      "NH_INSP_RECENT_TOTAL",
      "NH_INSP_RECENT_COMPLAINT",
      "NH_INSP_WEIGHTED_SCORE",
      "NH_INSP_TOTAL_HEALTH_DEF",
    ],
    tail_risk: true,
    provider_type: "NURSING_HOME",
  },
  {
    id: "nh-resident-safety",
    label: "Resident Safety (Long-Stay)",
    description: "Tail-risk events for long-stay residents: hospitalizations, falls with major injury, pressure ulcers, restraints, antipsychotic medication.",
    measure_ids: [
      "NH_CLAIMS_551",
      "NH_MDS_410",
      "NH_MDS_479",
      "NH_MDS_481",
      "NH_MDS_409",
      "NH_MDS_407",
    ],
    tail_risk: true,
    provider_type: "NURSING_HOME",
  },
  {
    id: "nh-staffing",
    label: "Staffing",
    description: "Reported and case-mix adjusted nurse staffing hours per resident per day, plus turnover.",
    measure_ids: [
      "NH_STAFF_ADJ_TOTAL_HPRD",
      "NH_STAFF_ADJ_RN_HPRD",
      "NH_STAFF_ADJ_WEEKEND_HPRD",
      "NH_STAFF_REPORTED_TOTAL_HPRD",
      "NH_STAFF_REPORTED_RN_HPRD",
      "NH_STAFF_REPORTED_AIDE_HPRD",
      "NH_STAFF_TOTAL_TURNOVER",
      "NH_STAFF_RN_TURNOVER",
      "NH_STAFF_ADMIN_DEPARTURES",
    ],
    tail_risk: false,
    provider_type: "NURSING_HOME",
  },
  {
    id: "nh-long-stay",
    label: "Long-Stay Quality Measures",
    description: "MDS-based quality measures for long-stay residents (functional decline, weight, infections, depression, falls, restraints).",
    measure_ids: [
      "NH_MDS_410",
      "NH_MDS_479",
      "NH_MDS_481",
      "NH_MDS_409",
      "NH_MDS_407",
      "NH_MDS_404",
      "NH_MDS_401",
      "NH_MDS_408",
      "NH_MDS_451",
      "NH_MDS_452",
      "NH_MDS_406",
      "NH_MDS_480",
    ],
    tail_risk: true,
    provider_type: "NURSING_HOME",
  },
  {
    id: "nh-short-stay",
    label: "Short-Stay Quality Measures",
    description: "Outcomes for residents on short-stay rehabilitative episodes (rehospitalization, ED visits, antipsychotics, vaccines).",
    measure_ids: [
      "NH_CLAIMS_521",
      "NH_CLAIMS_522",
      "NH_MDS_434",
      "NH_MDS_430",
      "NH_MDS_472",
    ],
    tail_risk: true,
    provider_type: "NURSING_HOME",
  },
  {
    id: "nh-snf-qrp",
    label: "SNF Quality Reporting (QRP)",
    description: "SNF QRP measures: preventable readmissions, discharge to community, falls with major injury, pressure ulcer/infection rates, function score.",
    measure_ids: [
      "S_004_01",
      "S_005_02",
      "S_013_02",
      "S_038_02",
      "S_039_01",
      "S_042_02",
      "S_006_01",
      "S_007_02",
      "S_045_01",
    ],
    tail_risk: true,
    provider_type: "NURSING_HOME",
  },
] as const;

export const FILTER_EXPLORE_PRESET_EMPTY_STATE =
  "No measures from this preset are available. Try another preset or pick a single measure.";

export const FILTER_EXPLORE_PRESET_LOADING = "Loading preset measures…";

