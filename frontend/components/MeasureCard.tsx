// Phase 1: implement. The atomic unit of the measure display.
// All measure-level display obligations flow through here.
// See .claude/rules/frontend-spec.md before implementing.

import type { Measure } from "@/types/provider";
import { compareToAverage } from "@/lib/utils";

interface MeasureCardProps {
  measure:             Measure;
  providerLastUpdated: string;
  onSESSensitive?:     () => void;
}

export function MeasureCard(_props: MeasureCardProps): JSX.Element {
  // TODO Phase 1: implement
  //
  // Primary label: measure_plain_language. Never measure_name.
  // period_label: always visible below the primary label.
  //
  // Value display:
  //   numeric_value non-null:
  //     - formatValue(numeric_value, unit)
  //     - BenchmarkBar (when national_avg non-null, suppressed false,
  //       not_reported false)
  //     - CI bounds always visible when both non-null. Never behind a toggle.
  //   numeric_value null + suppressed: SuppressionIndicator
  //   numeric_value null + not_reported: NonReporterIndicator
  //
  // Comparison badges (render below the value, above AttributionLine):
  //   National comparison (when national_avg non-null):
  //     const nationalResult = compareToAverage(
  //       numeric_value, national_avg, direction,
  //       confidence_interval_lower, confidence_interval_upper,
  //       reliability_flag
  //     );
  //     <ComparisonBadge result={nationalResult} referenceLabel="national average" />
  //
  //   State comparison (when state_avg non-null):
  //     const stateResult = compareToAverage(
  //       numeric_value, state_avg, direction,
  //       confidence_interval_lower, confidence_interval_upper,
  //       reliability_flag
  //     );
  //     <ComparisonBadge result={stateResult} referenceLabel="state average" />
  //
  //   If national_avg is null: render labeled placeholder:
  //     "National average not available for this measure."
  //   A card showing a value with no benchmark context is a display error.
  //
  // reliability_flag: visible label, not tooltip-only.
  //
  // sample_size: accessible via expandable row or tooltip.
  // When sample_size non-null and < SMALL_SAMPLE_THRESHOLD:
  //   SMALL_SAMPLE_CAVEAT(sample_size) inline below CI. Never tooltip-only.
  //
  // FootnoteDisclosure: when footnote_codes.length > 0.
  //
  // Stratified sub-measures: grouped sub-table via groupByMeasureId().
  //
  // AttributionLine: always at card bottom.
  //
  // Call onSESSensitive() when ses_sensitivity is HIGH or MODERATE.
  return <div data-component="MeasureCard" />;
}
