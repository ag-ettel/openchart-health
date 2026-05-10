"use client";

// CompareMeasureRow — compact side-by-side display of one measure across two providers.
//
// Shows the essential comparison data for each provider in a paired layout:
// - Value + unit with context-aware label
// - CMS comparison badge
// - Confidence interval
// - Sample size
// - Benchmark bar (value vs national avg)
// - Period mismatch flag when reporting periods differ
//
// Trend charts and full templates are available via expandable detail.
// No directional color coding (DEC-030). All values neutral gray.

import type { Measure } from "@/types/provider";
import {
  formatValue,
  formatPeriodLabel,
  effectivePeriodLabel,
  effectiveNumericValue,
  measureHasData,
} from "@/lib/utils";
import { SMALL_SAMPLE_THRESHOLD, SMALL_SAMPLE_CAVEAT } from "@/lib/constants";
import { useDistribution } from "@/lib/use-distributions";
import { ComparisonBadge } from "./ComparisonBadge";
import { CompareIntervalPlot } from "./CompareIntervalPlot";
import { CompareDistributionHistogram } from "./CompareDistributionHistogram";
import { CompareTrendChart } from "./CompareTrendChart";

interface CompareMeasureRowProps {
  measureA: Measure | null;
  measureB: Measure | null;
  providerNameA: string;
  providerNameB: string;
}

/** Context-aware metric label for the stat block. */
function metricLabel(m: Measure): string {
  const id = m.measure_id;
  if (id.startsWith("EDAC_")) return "Days vs. Expected";
  if (id.startsWith("HAI_") && id.endsWith("_SIR")) return "Infection Ratio (SIR)";
  if (id === "PSI_90") return "Safety Composite";
  if (id.startsWith("PSI_")) return "Safety Rate";
  if (m.measure_group === "MORTALITY" || id.startsWith("MORT_")) return "Death Rate";
  if (id.startsWith("READM_")) return "Readmission Rate";
  if (id.startsWith("HRRP_")) return "Excess Readmission Ratio";
  if (id.startsWith("COMP_")) return "Complication Rate";
  if (id.startsWith("MSPB")) return "Spending per Patient";
  if (id.startsWith("OP_18")) return "Median Wait Time";
  const unit = m.unit ?? "";
  switch (unit) {
    case "percent": return "Rate";
    case "ratio": return "Ratio";
    case "minutes": return "Time";
    case "score": return "Score";
    default: return "Value";
  }
}

function sampleLabel(m: { measure_group: string; measure_id: string }): string {
  const id = m.measure_id;
  const group = m.measure_group;
  if (group === "INFECTIONS" || id.startsWith("HAI_")) return "Procedures";
  if (id.startsWith("H_")) return "Surveys";
  if (group === "SAFETY" || id.startsWith("PSI_")) return "Discharges";
  if (/HIP_KNEE|CABG|THA|TKA/.test(id)) return "Procedures";
  return "Patients";
}

/** One side of the comparison — a single provider's measure data. */
function MeasureSide({
  measure,
  otherHasMeasure,
}: {
  measure: Measure | null;
  otherHasMeasure: boolean;
}): React.JSX.Element {
  if (!measure) {
    return (
      <div className="flex-1 rounded border border-gray-100 bg-gray-50 px-4 py-3">
        <p className="text-xs text-gray-400">
          {otherHasMeasure
            ? "This measure is not reported at this facility."
            : "Measure data not available."}
        </p>
      </div>
    );
  }

  const effValue = effectiveNumericValue(measure);
  const showSmallSample =
    measure.sample_size !== null &&
    measure.sample_size < SMALL_SAMPLE_THRESHOLD &&
    !measure.suppressed &&
    !measure.not_reported;
  const hasNationalAvg = measure.national_avg !== null;
  const isValueCard =
    !measure.suppressed && !measure.not_reported && effValue !== null;

  return (
    <div className="flex-1 min-w-0">
      {/* Suppressed / not-reported / categorical states stay visible — these
          aren't representable as bars and the bar chart row just hides.
          Numeric values are NOT duplicated here; they appear in the
          CompareIntervalPlot bars below the side blocks. */}
      {measure.suppressed && (
        <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
          <p className="text-xs font-medium text-gray-500">Suppressed</p>
          {measure.suppression_reason && (
            <p className="mt-1 text-xs text-gray-400">{measure.suppression_reason}</p>
          )}
        </div>
      )}
      {!measure.suppressed && measure.not_reported && (
        <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
          <p className="text-xs font-medium text-gray-500">Not Reported</p>
          {measure.not_reported_reason && (
            <p className="mt-1 text-xs text-gray-400">{measure.not_reported_reason}</p>
          )}
        </div>
      )}
      {!measure.suppressed && !measure.not_reported && measure.score_text !== null && (
        <div className="text-xl font-semibold capitalize text-gray-800">{measure.score_text}</div>
      )}
      {!measure.suppressed && !measure.not_reported && measure.score_text === null && effValue === null && (
        <p className="text-xs text-gray-400">Value not available</p>
      )}

      {/* Sample size */}
      {isValueCard && (measure.sample_size !== null || measure.denominator !== null) && !measure.count_suppressed && (
        <p className="text-xs text-gray-400">
          {(measure.sample_size ?? measure.denominator)!.toLocaleString("en-US")} {sampleLabel(measure).toLowerCase()}
        </p>
      )}

      {/* CMS comparison badge */}
      {measure.compared_to_national && hasNationalAvg && (
        <div className="mt-1">
          <ComparisonBadge comparedToNational={measure.compared_to_national} />
        </div>
      )}

      {/* Small sample caveat */}
      {showSmallSample && (
        <div className="mt-2 rounded border border-amber-300 bg-amber-50 px-2 py-1.5 text-xs text-amber-800">
          {SMALL_SAMPLE_CAVEAT(measure.sample_size!)}
        </div>
      )}
    </div>
  );
}

export function CompareMeasureRow({
  measureA,
  measureB,
  providerNameA,
  providerNameB,
}: CompareMeasureRowProps): React.JSX.Element {
  // Use whichever measure is present for the header info
  const ref = measureA ?? measureB;
  if (!ref) return <></>;

  const shortName = ref.measure_name ?? ref.measure_id;
  const label = metricLabel(ref);
  const unit = ref.unit ?? "";

  // Period mismatch detection
  const periodA = measureA ? effectivePeriodLabel(measureA) : null;
  const periodB = measureB ? effectivePeriodLabel(measureB) : null;
  const periodMismatch = periodA !== null && periodB !== null && periodA !== periodB;

  // Trend data for expandable detail
  const hasTrendA = measureA?.trend !== null && (measureA?.trend?.length ?? 0) > 0;
  const hasTrendB = measureB?.trend !== null && (measureB?.trend?.length ?? 0) > 0;
  const hasTrend = hasTrendA || hasTrendB;

  // National distribution lookup — drives histogram vs bar-chart fallback.
  const distribution = useDistribution(ref.measure_id, effectivePeriodLabel(ref));

  // Direction info
  const direction = ref.direction;
  const cmsDirectionText =
    direction === "LOWER_IS_BETTER"
      ? "CMS indicates: Lower is better."
      : direction === "HIGHER_IS_BETTER"
        ? "CMS indicates: Higher is better."
        : null;

  const borderAccent =
    (measureA?.suppressed || measureA?.not_reported) && (measureB?.suppressed || measureB?.not_reported)
      ? "border-l-gray-300"
      : "border-l-blue-400";

  return (
    <div className={`rounded-lg border border-gray-200 ${borderAccent} border-l-4 bg-white px-5 py-4 shadow-sm`}>
      {/* Measure header — spans full width */}
      <div className="mb-3">
        <h3 className="text-sm font-semibold leading-snug text-blue-800">
          {shortName}
        </h3>
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-400">
          <span>{label}</span>
          {cmsDirectionText && (
            <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
              {direction === "LOWER_IS_BETTER" ? (
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>
              ) : (
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>
              )}
              CMS: {direction === "LOWER_IS_BETTER" ? "Lower is better" : "Higher is better"}
            </span>
          )}
          {periodMismatch && (
            <span className="rounded bg-amber-50 px-2 py-0.5 text-amber-700 border border-amber-200">
              Reporting periods differ
            </span>
          )}
        </div>
        {/* Period labels when they differ */}
        {periodMismatch && (
          <div className="mt-1 flex gap-4 text-xs text-gray-400">
            <span>{providerNameA}: {formatPeriodLabel(periodA!)}</span>
            <span>{providerNameB}: {formatPeriodLabel(periodB!)}</span>
          </div>
        )}
        {!periodMismatch && periodA && (
          <p className="mt-1 text-xs text-gray-400">
            {formatPeriodLabel(periodA)}
          </p>
        )}
      </div>

      {/* Plain language description — always visible, bold */}
      {ref.measure_plain_language && (
        <p className="mb-3 text-sm font-semibold leading-snug text-gray-800">
          {ref.measure_plain_language}
        </p>
      )}

      {/* Side-by-side values — desktop: two columns, mobile: stacked */}
      <div className="flex flex-col gap-4 lg:flex-row lg:gap-6">
        {/* Provider A header — mobile only */}
        <div className="lg:hidden text-xs font-bold text-blue-700 border-b border-blue-100 pb-1">
          {providerNameA}
        </div>
        <MeasureSide
          measure={measureA}
          otherHasMeasure={measureB !== null && measureHasData(measureB)}
        />
        {/* Provider B header — mobile only */}
        <div className="lg:hidden text-xs font-bold text-gray-800 border-b border-gray-200 pb-1">
          {providerNameB}
        </div>
        <MeasureSide
          measure={measureB}
          otherHasMeasure={measureA !== null && measureHasData(measureA)}
        />
      </div>

      {/* National-distribution histogram with both provider markers if a
          distribution exists for this measure/period; otherwise fall back to
          the paired bar chart. The histogram gives percentile context the
          paired bars can't, while keeping the credible interval visible as a
          separate band above the bins. */}
      {(() => {
        const aVal = measureA ? effectiveNumericValue(measureA) : null;
        const bVal = measureB ? effectiveNumericValue(measureB) : null;
        if (aVal === null && bVal === null) return null;

        const histPeriod = effectivePeriodLabel(ref);
        if (distribution !== null) {
          return (
            <CompareDistributionHistogram
              measureId={ref.measure_id}
              periodLabel={histPeriod}
              providerA={measureA && aVal !== null ? {
                value: aVal,
                ciLower: measureA.confidence_interval_lower,
                ciUpper: measureA.confidence_interval_upper,
                label: providerNameA,
              } : null}
              providerB={measureB && bVal !== null ? {
                value: bVal,
                ciLower: measureB.confidence_interval_lower,
                ciUpper: measureB.confidence_interval_upper,
                label: providerNameB,
              } : null}
              nationalAvg={measureA?.national_avg ?? measureB?.national_avg ?? null}
              direction={ref.direction}
              unit={unit}
            />
          );
        }
        return (
          <CompareIntervalPlot
            providerA={measureA && aVal !== null ? {
              value: aVal,
              ciLower: measureA.confidence_interval_lower,
              ciUpper: measureA.confidence_interval_upper,
              label: providerNameA,
              sampleSize: measureA.sample_size ?? measureA.denominator ?? null,
              sampleLabel: sampleLabel(measureA),
            } : null}
            providerB={measureB && bVal !== null ? {
              value: bVal,
              ciLower: measureB.confidence_interval_lower,
              ciUpper: measureB.confidence_interval_upper,
              label: providerNameB,
              sampleSize: measureB.sample_size ?? measureB.denominator ?? null,
              sampleLabel: sampleLabel(measureB),
            } : null}
            nationalAvg={measureA?.national_avg ?? measureB?.national_avg ?? null}
            unit={unit}
          />
        );
      })()}

      {/* CMS definition — collapsed */}
      {ref.cms_measure_definition && (
        <details className="mt-3">
          <summary className="cursor-pointer text-xs font-medium text-gray-500 hover:text-gray-700">
            CMS Definition
          </summary>
          <p className="mt-1 text-xs leading-relaxed text-gray-600">
            {ref.cms_measure_definition}
          </p>
        </details>
      )}

      {/* Trend chart — overlaid on single axis */}
      {hasTrend && (
        <details className="mt-3 border-t border-gray-100 pt-3" open>
          <summary className="cursor-pointer text-xs font-semibold text-blue-600 hover:text-blue-800">
            Trend over time
          </summary>
          <CompareTrendChart
            trendA={measureA?.trend ?? null}
            trendB={measureB?.trend ?? null}
            trendValidA={measureA?.trend_valid ?? false}
            trendValidB={measureB?.trend_valid ?? false}
            trendPeriodCountA={measureA?.trend_period_count ?? 0}
            trendPeriodCountB={measureB?.trend_period_count ?? 0}
            unit={unit}
            nationalAvg={measureA?.national_avg ?? measureB?.national_avg ?? null}
            nameA={providerNameA}
            nameB={providerNameB}
            yAxisLabel={label}
            referenceValue={
              ref.measure_id.startsWith("EDAC_") ? 0
              : (ref.measure_id.startsWith("HRRP_") || ref.measure_id === "PSI_90") ? 1.0
              : null
            }
            referenceLabel={
              ref.measure_id.startsWith("EDAC_") ? "0 = expected"
              : (ref.measure_id.startsWith("HRRP_") || ref.measure_id === "PSI_90") ? "1.0 = expected"
              : undefined
            }
          />
        </details>
      )}

      {/* Source — collapsed */}
      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-600">
          Source
        </summary>
        <p className="mt-1 text-xs text-gray-400">
          Source: CMS {ref.source_dataset_name},{" "}
          {formatPeriodLabel(effectivePeriodLabel(ref))}.
        </p>
      </details>
    </div>
  );
}
