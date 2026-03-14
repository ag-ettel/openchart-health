// Architectural contract. See CLAUDE.md: Frontend Specification: Types.
// If the JSON export schema changes, this file changes in the same commit.
// Do not redefine or widen these types in component files.

export type ReliabilityFlag =
  | "RELIABLE"
  | "LIMITED_SAMPLE"
  | "NOT_REPORTED"
  | "SUPPRESSED";

export type MeasureDirection = "LOWER_IS_BETTER" | "HIGHER_IS_BETTER";
export type SesSensitivity   = "HIGH" | "MODERATE" | "LOW" | "UNKNOWN";
export type ProviderType     = "HOSPITAL" | "NURSING_HOME" | "HOME_HEALTH" | "HOSPICE";
export type PaymentProgram   = "HRRP" | "HACRP" | "VBP" | "SNF_VBP";

// Add after the existing type declarations, before TrendPeriod.

// Result of a statistically honest comparison between a provider's measure
// value and a reference value (national average or another provider).
// Used by compareToAverage() and compareProviders() in lib/utils.ts.
// Color mapping in components:
//   BETTER                  → blue-700 text, blue-50 tint
//   WORSE                   → orange-700 text, orange-50 tint
//   NO_SIGNIFICANT_DIFFERENCE → gray-500 text, gray-50 tint
//   CANNOT_DETERMINE        → gray-500 text, gray-50 tint, distinct label
export type ComparisonResult =
  | "BETTER"
  | "WORSE"
  | "NO_SIGNIFICANT_DIFFERENCE"
  | "CANNOT_DETERMINE";


export interface TrendPeriod {
  period_label:            string;
  numeric_value:           number | null; // parsed from Decimal(12,4); use formatValue() for display
  suppressed:              boolean;
  not_reported:            boolean;
  methodology_change_flag: boolean;
}

export interface Measure {
  measure_id:                string;
  measure_name:              string;
  measure_plain_language:    string;  // primary display label; never use measure_name in UI
  measure_group:             string;  // must match measure_group enum in pipeline/config.py
  source_dataset_id:         string;
  source_dataset_name:       string;
  measure_spec_version:      string | null;
  methodology_revision_date: string | null; // ISO8601
  direction:                 MeasureDirection;
  unit:                      "percent" | "minutes" | "ratio" | "count" | "score" | string;
  tail_risk_flag:            boolean;
  ses_sensitivity:           SesSensitivity;
  stratification:            string | null; // null = non-stratified; primary measure
  numeric_value:             number | null;
  confidence_interval_lower: number | null;
  confidence_interval_upper: number | null;
  suppressed:                boolean;
  suppression_reason:        string | null;
  not_reported:              boolean;
  not_reported_reason:       string | null;
  footnote_codes:            number[];
  footnote_text:             string[];
  period_label:              string;
  period_start:              string | null; // ISO8601
  period_end:                string | null; // ISO8601
  sample_size:               number | null;
  denominator:               number | null;
  reliability_flag:          ReliabilityFlag;
  national_avg:              number | null;
  national_avg_period:       string | null;
  state_avg:                 number | null;
  state_avg_period:          string | null;
  trend:                     TrendPeriod[]; // ordered chronologically, oldest first
  trend_valid:               boolean;
  trend_period_count:        number;
}

export interface Summary {
  summary_scope:            "page" | "measure_group";
  measure_group:            string | null; // null when summary_scope is "page"
  summary_text:             string;
  fallback_used:            boolean;       // true = full template fallback; no LLM call made
  sentence_3_fallback_used: boolean;       // true = LLM call made but sentence 3 fell back
  prompt_version:           string;
  llm_model_id:             string;
  generation_timestamp:     string;        // ISO8601
}

export interface PaymentAdjustment {
  program:                PaymentProgram;
  program_year:           number;
  penalty_flag:           boolean;
  payment_adjustment_pct: number | null; // negative = penalty, positive = bonus
  total_score:            number | null;
  score_percentile:       number | null;
}

// Non-null when provider_type is "HOSPITAL". Null for all other provider types.
export interface HospitalContext {
  staffed_beds:                   number | null;
  is_critical_access:             boolean;
  is_teaching_hospital:           boolean;
  is_emergency_services:          boolean;
  dsh_status:                     boolean;
  dsh_percentage:                 number | null;
  dual_eligible_proportion:       number | null;
  urban_rural_classification:     string | null;
  cms_certification_date:         string | null; // ISO8601
  offers_cardiac_surgery:         boolean;
  offers_cardiac_catheterization: boolean;
  offers_emergency_cardiac_care:  boolean;
}

// Non-null when provider_type is "NURSING_HOME". Null for all other provider types.
// Pipeline population deferred to nursing home build phase.
export interface NursingHomeContext {
  resident_capacity:                       number | null;
  dual_eligible_proportion:                number | null;
  urban_rural_classification:              string | null;
  cms_certification_date:                  string | null; // ISO8601
  is_continuing_care_retirement_community: boolean;
  is_special_focus_facility:               boolean;
  is_special_focus_facility_candidate:     boolean; // mutually exclusive with is_special_focus_facility
  is_hospital_based:                       boolean;
  is_abuse_icon:                           boolean;
}

export interface Address {
  street: string | null;
  city:   string;
  state:  string; // 2-char
  zip:    string;
}

export interface Provider {
  provider_id:          string;          // CCN, 6-char zero-padded
  provider_type:        ProviderType;
  name:                 string;
  is_active:            boolean;
  phone:                string | null;
  address:              Address;
  provider_subtype:     string;          // enum values confirmed in docs/data_dictionary.md
  ownership_type:       string | null;
  last_updated:         string;          // ISO8601; use in all measure AttributionLine renders
  pipeline_run_id:      string;          // UUID
  measures:             Measure[];
  summaries:            Summary[];
  payment_adjustments:  PaymentAdjustment[];
  hospital_context:     HospitalContext | null;     // non-null for HOSPITAL only
  nursing_home_context: NursingHomeContext | null;  // non-null for NURSING_HOME only
}
