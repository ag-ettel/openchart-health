// The atomic unit of measure display. All measure-level display obligations flow
// through here. Handles: numeric values, categorical scores (DEC-024), full
// suppression, non-reporting, count-only suppression (DEC-023), CMS comparisons
// (DEC-022), CI bounds, O/E ratios, footnotes, sample size caveats, reliability
// flags, and per-measure attribution.
//
// No directional color encoding (DEC-030). No computed comparison verdicts.
// CMS's own compared_to_national is displayed as attributed CMS data.

import type { Measure } from "@/types/provider";
import { formatValue } from "@/lib/utils";
import {
  SMALL_SAMPLE_THRESHOLD,
  SMALL_SAMPLE_CAVEAT,
  DIRECTION_NOTE,
  EXPLICIT_DIRECTION_SOURCES,
} from "@/lib/constants";
import { AttributionLine } from "./AttributionLine";
import { BenchmarkBar } from "./BenchmarkBar";
import { ComparisonBadge } from "./ComparisonBadge";
import { FootnoteDisclosure } from "./FootnoteDisclosure";
import { SuppressionIndicator } from "./SuppressionIndicator";
import { NonReporterIndicator } from "./NonReporterIndicator";

interface MeasureCardProps {
  measure: Measure;
  providerLastUpdated: string;
}

const RELIABILITY_LABELS: Record<string, string> = {
  RELIABLE: "Reliable estimate",
  LIMITED_SAMPLE: "Limited sample size",
  NOT_REPORTED: "Not reported",
  SUPPRESSED: "Suppressed",
};

export function MeasureCard({
  measure,
  providerLastUpdated,
}: MeasureCardProps): JSX.Element {
  const displayName =
    measure.measure_plain_language ?? measure.measure_name ?? "Unnamed measure";
  const unit = measure.unit ?? "";
  const hasCI =
    measure.confidence_interval_lower !== null &&
    measure.confidence_interval_upper !== null;
  const showSmallSample =
    measure.sample_size !== null &&
    measure.sample_size < SMALL_SAMPLE_THRESHOLD &&
    !measure.suppressed &&
    !measure.not_reported;

  // DEC-032: only render explicit direction note when CMS source warrants it.
  // For CMS_MEASURE_DEFINITION or null, plain_language carries directionality.
  const showDirectionNote =
    measure.direction !== null &&
    measure.direction_source !== null &&
    EXPLICIT_DIRECTION_SOURCES.includes(measure.direction_source);
  const cmsDirection =
    measure.direction === "LOWER_IS_BETTER" ? "lower" : "higher";

  return (
    <div className="rounded border border-gray-200 bg-white px-4 py-4">
      {/* Header: plain-language name and reporting period */}
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-gray-900">{displayName}</h3>
        <p className="text-xs text-gray-500">{measure.period_label}</p>
      </div>

      {/* Value display — mutually exclusive paths */}
      <div className="mb-3">
        {measure.suppressed ? (
          <SuppressionIndicator
            suppression_reason={measure.suppression_reason}
            footnote_codes={measure.footnote_codes}
            footnote_text={measure.footnote_text}
          />
        ) : measure.not_reported ? (
          <NonReporterIndicator
            not_reported_reason={measure.not_reported_reason}
            trend={measure.trend ?? []}
          />
        ) : measure.score_text !== null ? (
          // DEC-024: categorical score (e.g., EDV "very high", "high", "medium", "low")
          <span className="text-lg font-medium capitalize text-gray-700">
            {measure.score_text}
          </span>
        ) : measure.numeric_value !== null ? (
          <div>
            <span className="text-lg font-medium text-gray-700">
              {formatValue(measure.numeric_value, unit)}
            </span>
            {/* CI bounds — always visible when available, never behind a toggle */}
            {hasCI && (
              <span className="ml-2 text-xs text-gray-500">
                ({formatValue(measure.confidence_interval_lower!, unit)}
                {" – "}
                {formatValue(measure.confidence_interval_upper!, unit)})
              </span>
            )}
          </div>
        ) : (
          // Edge case: no value, not suppressed, not non-reported, no score_text
          <span className="text-sm text-gray-500">Value not available</span>
        )}
      </div>

      {/* Count suppression note (DEC-023) — value is valid but counts are hidden */}
      {measure.count_suppressed && (
        <p className="mb-2 text-xs text-gray-500">
          Sample size and count data are suppressed by CMS for patient privacy.
          The measure value above remains valid.
        </p>
      )}

      {/* O/E ratio context — NH claims measures (DEC-016) */}
      {measure.observed_value !== null && measure.expected_value !== null && (
        <p className="mb-2 text-xs text-gray-500">
          Observed: {measure.observed_value.toFixed(2)} · Expected:{" "}
          {measure.expected_value.toFixed(2)} · O/E ratio:{" "}
          {(measure.observed_value / measure.expected_value).toFixed(2)}
        </p>
      )}

      {/* Benchmark context — numeric measures only, not suppressed/not-reported */}
      {!measure.suppressed &&
        !measure.not_reported &&
        measure.numeric_value !== null && (
          <div className="mb-2">
            {measure.national_avg !== null ? (
              <>
                {/* BenchmarkBar: neutral position indicator, no directional color (DEC-030) */}
                <BenchmarkBar
                  value={measure.numeric_value}
                  nationalAvg={measure.national_avg}
                  stateAvg={measure.state_avg}
                  unit={unit}
                  ciLower={measure.confidence_interval_lower}
                  ciUpper={measure.confidence_interval_upper}
                />
                <p className="mt-1 text-xs text-gray-500">
                  National avg: {formatValue(measure.national_avg, unit)}
                  {measure.national_avg_period &&
                    measure.national_avg_period !== measure.period_label && (
                      <> ({measure.national_avg_period})</>
                    )}
                  {measure.state_avg !== null && (
                    <>
                      {" · "}State avg:{" "}
                      {formatValue(measure.state_avg, unit)}
                      {measure.state_avg_period &&
                        measure.state_avg_period !== measure.period_label && (
                          <> ({measure.state_avg_period})</>
                        )}
                    </>
                  )}
                </p>
              </>
            ) : (
              <p className="text-xs text-gray-500">
                National average not available for this measure.
              </p>
            )}
          </div>
        )}

      {/* Direction note — CMS attribution only, not our assertion (DEC-032) */}
      {showDirectionNote && !measure.suppressed && !measure.not_reported && (
        <p className="mb-2 text-xs text-gray-500">
          {DIRECTION_NOTE(cmsDirection)}
        </p>
      )}

      {/* CMS comparison — republished CMS assessment, not our computation (DEC-022) */}
      {!measure.suppressed && !measure.not_reported && (
        <div className="mb-2">
          <ComparisonBadge
            comparedToNational={measure.compared_to_national}
          />
        </div>
      )}

      {/* Reliability flag — visible label, not tooltip-only */}
      {measure.reliability_flag !== null && !measure.suppressed && !measure.not_reported && (
        <p className="mb-2 text-xs text-gray-500">
          {RELIABILITY_LABELS[measure.reliability_flag] ??
            measure.reliability_flag}
        </p>
      )}

      {/* Sample size and small sample caveat */}
      {measure.sample_size !== null && !measure.suppressed && !measure.not_reported && !measure.count_suppressed && (
        <p className="mb-2 text-xs text-gray-500">
          Based on {measure.sample_size.toLocaleString("en-US")} cases
          {measure.denominator !== null && (
            <> (denominator: {measure.denominator.toLocaleString("en-US")})</>
          )}
        </p>
      )}
      {showSmallSample && (
        <p className="mb-2 rounded border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-700">
          {SMALL_SAMPLE_CAVEAT(measure.sample_size!)}
        </p>
      )}

      {/* Footnotes — first-class data per Principle 3. Never discard codes (Rule 2).
          Show footnotes if codes exist even when text lookup failed (text=null). */}
      {measure.footnote_codes !== null && (
        <FootnoteDisclosure
          footnote_codes={measure.footnote_codes}
          footnote_text={measure.footnote_text}
        />
      )}

      {/* Per-measure attribution — required by Template 3b / legal-compliance.md */}
      <AttributionLine
        sourceDatasetName={measure.source_dataset_name}
        periodLabel={measure.period_label}
        providerLastUpdated={providerLastUpdated}
      />
    </div>
  );
}
