// Architectural contract. See CLAUDE.md: Frontend Specification: Types.
// If the JSON export schema changes, this file changes in the same commit.
// Do not redefine or widen these types in component files.
//
// Last synced with pipeline/export/build_json.py: 2026-03-21

export type ReliabilityFlag =
  | "RELIABLE"
  | "LIMITED_SAMPLE"
  | "NOT_REPORTED"
  | "SUPPRESSED";

export type MeasureDirection = "LOWER_IS_BETTER" | "HIGHER_IS_BETTER";
export type DirectionSource  = "CMS_API" | "CMS_DATA_DICTIONARY" | "CMS_MEASURE_SPEC" | "CMS_MEASURE_DEFINITION";
export type SesSensitivity   = "HIGH" | "MODERATE" | "LOW" | "UNKNOWN";
export type ProviderType     = "HOSPITAL" | "NURSING_HOME" | "HOME_HEALTH" | "HOSPICE";
export type PaymentProgram   = "HRRP" | "HACRP" | "VBP" | "SNF_VBP";

export interface TrendPeriod {
  period_label:            string;
  numeric_value:           number | null;
  suppressed:              boolean;
  not_reported:            boolean;
  methodology_change_flag: boolean;  // footnote 29 detected (Rule 11)
  sample_size:             number | null;
  ci_lower:                number | null;
  ci_upper:                number | null;
  compared_to_national:    string | null;
  footnote_codes:          number[] | null;
}

export interface Measure {
  measure_id:                string;
  measure_name:              string | null;
  measure_plain_language:    string | null;
  cms_measure_definition:    string | null;  // DEC-037: verbatim CMS definition
  measure_group:             string;
  source_dataset_id:         string | null;
  source_dataset_name:       string;  // CMS dataset display name for attribution
  direction:                 MeasureDirection | null;  // null for EDV, HCAHPS middlebox
  direction_source:          DirectionSource | null;  // DEC-032: governs [DIRECTION_NOTE] rendering
  unit:                      string | null;
  tail_risk_flag:            boolean;
  ses_sensitivity:           SesSensitivity;
  stratification:            string | null;  // null = non-stratified
  numeric_value:             number | null;
  score_text:                string | null;  // DEC-024: EDV categorical ("very high", etc.)
  confidence_interval_lower: number | null;  // CMS-published or Bayesian credible (DEC-029)
  confidence_interval_upper: number | null;
  ci_source:                 string | null;  // DEC-029: "cms_published" | "calculated" | null
  prior_source:              string | null;  // DEC-029: "state average" | "national average" | "minimally informative" | null
  observed_value:            number | null;  // DEC-016: NH claims O/E observed
  expected_value:            number | null;  // DEC-016: NH claims O/E expected
  compared_to_national:      string | null;  // DEC-022: BETTER/NO_DIFFERENT/WORSE/etc.
  suppressed:                boolean;
  suppression_reason:        string | null;
  not_reported:              boolean;
  not_reported_reason:       string | null;
  count_suppressed:          boolean;  // DEC-023: counts hidden but value populated
  footnote_codes:            number[] | null;
  footnote_text:             string[] | null;
  period_label:              string;
  period_start:              string | null;  // ISO8601
  period_end:                string | null;  // ISO8601
  sample_size:               number | null;
  denominator:               number | null;
  reliability_flag:          ReliabilityFlag | null;
  national_avg:              number | null;
  national_avg_period:       string | null;
  state_avg:                 number | null;
  state_avg_period:          string | null;
  ci_level:                  string | null;  // e.g. "95%"; null when no interval
  overlap_flag:              boolean | null; // CI contains national avg; null when no CI or no avg
  trend:                     TrendPeriod[] | null;  // null if only 1 period; oldest first
  trend_valid:               boolean;  // Rule 12: true when 3+ periods
  trend_period_count:        number;
}

export interface PaymentAdjustment {
  program:                PaymentProgram;
  program_year:           number;
  penalty_flag:           boolean | null;  // null = excluded from program (e.g., HACRP N/A)
  payment_adjustment_pct: number | null;
  total_score:            number | null;
  score_percentile:       number | null;
}

// Non-null when provider_type is "HOSPITAL". Null for all other provider types.
export interface HospitalContext {
  is_critical_access:             boolean | null;
  is_emergency_services:          boolean | null;
  birthing_friendly_designation:  boolean | null;  // DEC-007
  hospital_overall_rating:        number | null;   // 1-5
  hospital_overall_rating_footnote: string | null;
}

// Quarterly staffing snapshot from PBJ (Payroll-Based Journal) via Provider Information.
// Deduplicated to one row per quarter (CMS publishes same values for 3 consecutive months).
export interface StaffingTrendPeriod {
  quarter_label:        string;         // e.g. "Q1 2024"
  reported_total_hprd:  number | null;  // Reported total nurse hours per resident per day
  reported_rn_hprd:     number | null;  // Reported RN hours per resident per day
  adjusted_total_hprd:  number | null;  // Case-mix adjusted total nurse hours
  total_turnover:       number | null;  // Total nursing staff turnover rate (%)
}

// Non-null when provider_type is "NURSING_HOME". Null for all other provider types.
export interface NursingHomeContext {
  certified_beds:                          number | null;
  average_daily_census:                    number | null;
  is_continuing_care_retirement_community: boolean | null;
  is_special_focus_facility:               boolean | null;
  is_special_focus_facility_candidate:     boolean | null;
  is_hospital_based:                       boolean | null;
  is_abuse_icon:                           boolean | null;
  is_urban:                                boolean | null;
  chain_name:                              string | null;
  chain_id:                                string | null;
  // Current staffing snapshot (DEC-018)
  reported_total_hprd:                     number | null;
  reported_rn_hprd:                        number | null;
  reported_aide_hprd:                      number | null;
  reported_lpn_hprd:                       number | null;
  adjusted_total_hprd:                     number | null;
  adjusted_rn_hprd:                        number | null;
  adjusted_aide_hprd:                      number | null;
  adjusted_lpn_hprd:                       number | null;
  casemix_total_hprd:                      number | null;
  casemix_rn_hprd:                         number | null;
  weekend_rn_hprd:                         number | null;
  weekend_total_hprd:                      number | null;
  pt_hprd:                                 number | null;
  nursing_casemix_index:                   number | null;
  total_turnover:                          number | null;
  rn_turnover:                             number | null;
  administrator_departures:                number | null;
  staffing_rating:                         number | null;  // 1-5 star
  // Inspection scoring
  total_weighted_health_survey_score:      number | null;  // CMS composite deficiency score (higher = worse)
  cycle_1_total_health_deficiencies:       number | null;
  cycle_1_health_deficiency_score:         number | null;
  // Quarterly staffing trend from PBJ archives
  staffing_trend:                          StaffingTrendPeriod[] | null;
  // Standard survey dates from Provider Info (Rating Cycle fields).
  standard_survey_dates:                   string[] | null;
}

// DEC-028: inspection events with contested citation transparency
export interface InspectionEvent {
  survey_date:                          string | null;  // ISO8601
  survey_type:                          string | null;
  deficiency_tag:                       string;
  deficiency_description:               string | null;
  deficiency_category:                  string | null;
  scope_severity_code:                  string | null;  // A-L; current CMS classification
  is_immediate_jeopardy:                boolean;
  is_complaint_deficiency:              boolean;
  correction_date:                      string | null;  // ISO8601
  inspection_cycle:                     number | null;
  // Contested citation fields (DEC-028)
  is_contested:                         boolean;
  originally_published_scope_severity:  string | null;  // original finding before revision
  scope_severity_history:               ScopeSeverityChange[] | null;
}

export interface ScopeSeverityChange {
  code:     string;   // new scope/severity code
  vintage:  string;   // CMS release date when change observed
  previous: string;   // previous code
  idr:      boolean;  // DEC-028: true if IDR was active at time of change
}

// DEC-028: penalties with fine amount change transparency
export interface Penalty {
  penalty_date:                    string | null;  // ISO8601
  penalty_type:                    string;         // "Fine" or "Payment Denial"
  fine_amount:                     number | null;  // current
  payment_denial_start_date:       string | null;  // ISO8601
  payment_denial_length_days:      number | null;
  originally_published_fine_amount: number | null;
  fine_amount_changed:             boolean;
}

export interface OwnershipEntry {
  owner_name:                       string;
  owner_type:                       string;  // "Individual" or "Organization"
  role:                             string;
  ownership_percentage:             number | null;
  ownership_percentage_not_provided: boolean;
  association_date:                 string | null;  // ISO8601
  parent_group_id:                  string | null;  // Entity resolution: slug of parent corporate group
  parent_group_name:                string | null;  // Entity resolution: display name of parent group
  entity_facility_count:            number | null;  // Total facilities this entity appears in (for viz sizing)
  parent_group_facility_count:      number | null;  // Total facilities in the parent corporate group (deduplicated)
}

export interface Address {
  street: string | null;
  city:   string | null;
  state:  string | null;
  zip:    string | null;
}

export interface ParentGroupStats {
  parent_group_name:                string;
  facility_count:                   number;
  // Inspection event aggregates (120-day clustering, most recent event per facility)
  avg_citations_per_event:          number | null;
  avg_jkl_per_event:                number | null;
  avg_ghi_per_event:                number | null;
  avg_df_per_event:                 number | null;
  avg_ac_per_event:                 number | null;
  facilities_with_recent_ij:        number | null;
  pct_facilities_with_recent_ij:    number | null;
  nat_pct_facilities_with_recent_ij: number | null;
  nat_avg_citations_per_event:      number;
  nat_avg_jkl_per_event:            number;
  nat_avg_ghi_per_event:            number;
  nat_avg_df_per_event:             number;
  nat_avg_ac_per_event:             number;
  // Provider-level aggregates
  avg_fines:                        number | null;
  nat_avg_fines:                    number | null;
  avg_penalties:                    number | null;
  nat_avg_penalties:                number | null;
  sff_count:                        number;
  abuse_icon_count:                 number;
  nat_pct_sff:                      number | null;
  nat_pct_abuse:                    number | null;
  avg_beds:                         number | null;
  // Staffing threshold rollups: share of group facilities (with a reported
  // value) below the CMS minimum HPRD. Numerator/denominator carried alongside
  // the percentage so the UI can show "N of M facilities" honestly.
  facilities_with_reported_total_hprd?:    number;
  facilities_below_total_nurse_threshold?: number;
  pct_below_total_nurse_threshold?:        number | null;
  facilities_with_reported_rn_hprd?:       number;
  facilities_below_rn_threshold?:          number;
  pct_below_rn_threshold?:                 number | null;
  nat_pct_below_total_nurse_threshold?:    number | null;
  nat_pct_below_rn_threshold?:             number | null;
  min_total_nurse_hprd_threshold?:         number;
  min_rn_hprd_threshold?:                  number;
}

export interface Provider {
  provider_id:          string;                       // CCN, 6-char zero-padded
  provider_type:        ProviderType;
  name:                 string;
  is_active:            boolean;
  phone:                string | null;
  address:              Address;
  provider_subtype:     string | null;
  ownership_type:       string | null;
  last_updated:         string;                       // ISO8601
  measures:             Measure[];
  payment_adjustments:  PaymentAdjustment[];
  hospital_context:     HospitalContext | null;        // non-null for HOSPITAL only
  nursing_home_context: NursingHomeContext | null;     // non-null for NURSING_HOME only
  inspection_events:    InspectionEvent[] | null;      // non-null for NURSING_HOME only
  penalties:            Penalty[] | null;              // non-null for NURSING_HOME only
  ownership:            OwnershipEntry[] | null;       // non-null for NURSING_HOME only
  parent_group_stats:   ParentGroupStats | null;       // non-null when parent group resolved
}
