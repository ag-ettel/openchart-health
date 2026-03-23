// MeasureCard — the atomic unit of measure display.
//
// Layout (top to bottom):
//   1. Title in blue (measure_name)
//   2. Category tag badges (clickable to filter)
//   3. CMS Definition (only when available)
//   4. "What this means" collapsible (plain language)
//   5. Reporting period
//   6. Stat block with context-aware labels, CMS comparison, direction arrow
//   7. O/E ratio with interpretation
//   8. Benchmark, footnotes, trend, full summary, source

"use client";

import type { Measure } from "@/types/provider";
import { formatValue, formatPeriodLabel, titleCase } from "@/lib/utils";
import { getTagsForMeasure, MEASURE_TAGS } from "@/lib/measure-tags";
import { useDistribution } from "@/lib/use-distributions";
import { DistributionHistogram } from "./DistributionHistogram";
import {
  SMALL_SAMPLE_THRESHOLD,
  SMALL_SAMPLE_CAVEAT,
} from "@/lib/constants";
import { BenchmarkBar } from "./BenchmarkBar";
import { FootnoteDisclosure } from "./FootnoteDisclosure";
import { SuppressionIndicator } from "./SuppressionIndicator";
import { NonReporterIndicator } from "./NonReporterIndicator";
import { TrendChart } from "./TrendChart";

interface MeasureCardProps {
  measure: Measure;
  providerLastUpdated: string;
  providerName?: string;
  inlineTrend?: boolean;
  onTagClick?: (tagId: string) => void;
}

const RELIABILITY_LABELS: Record<string, string> = {
  RELIABLE: "Reliable estimate",
  LIMITED_SAMPLE: "Limited sample size",
  NOT_REPORTED: "Not reported",
  SUPPRESSED: "Suppressed",
};

const CMS_COMPARISON_LABELS: Record<string, string> = {
  BETTER: "CMS rates this hospital as better than the national rate.",
  NO_DIFFERENT: "CMS rates this hospital as no different from the national rate.",
  WORSE: "CMS rates this hospital as worse than the national rate.",
  TOO_FEW_CASES: "Too few cases for CMS to compare to the national rate.",
  NOT_AVAILABLE: "CMS national comparison not available.",
};

function formatInterval(lower: number, upper: number, unit: string): string {
  return `${formatValue(lower, unit)} to ${formatValue(upper, unit)}`;
}

/** Append interval context to a punchline when CI data is available. */
function withInterval(m: Measure, punchline: string): string {
  const unit = m.unit ?? "";
  if (m.confidence_interval_lower !== null && m.confidence_interval_upper !== null) {
    return `${punchline}, with a plausible range of ${formatValue(m.confidence_interval_lower, unit)} to ${formatValue(m.confidence_interval_upper, unit)} given the available data.`;
  }
  return `${punchline}.`;
}

/** Check if the interval straddles a neutral point (0 or 1.0). */
function intervalStraddlesNeutral(m: Measure, neutral: number): boolean {
  return m.confidence_interval_lower !== null &&
    m.confidence_interval_upper !== null &&
    m.confidence_interval_lower < neutral &&
    m.confidence_interval_upper > neutral;
}

/** Build an uncertainty-acknowledging punchline when the interval crosses the neutral point. */
function uncertaintyPunchline(m: Measure, suggestion: string, neutral: string, betterWord: string, worseWord: string): string {
  const unit = m.unit ?? "";
  const val = formatValue(m.numeric_value!, unit);
  const low = formatValue(m.confidence_interval_lower!, unit);
  const high = formatValue(m.confidence_interval_upper!, unit);
  return `The result of ${val} suggests ${suggestion}, but the plausible range of ${low} to ${high} includes both ${betterWord} and ${worseWord} than ${neutral} outcomes — this result is consistent with average performance given the available data.`;
}

/** Plain-English punchline translating the raw number into concrete meaning. */
function valueInterpretation(m: Measure): string | null {
  const val = m.numeric_value;
  if (val === null) return null;
  const id = m.measure_id;
  const unit = m.unit ?? "";

  if (id.startsWith("EDAC_")) {
    // Check if interval straddles zero
    if (intervalStraddlesNeutral(m, 0)) {
      const dir = val < 0 ? "slightly fewer days back in acute care than expected" : "slightly more days back in acute care than expected";
      return uncertaintyPunchline(m, dir, "expected", "better", "worse");
    }
    const abs = formatValue(Math.abs(val), unit);
    if (val < 0) return withInterval(m, `${abs} fewer days back in acute care than expected per 100 patients`);
    if (val > 0) return withInterval(m, `${abs} more days back in acute care than expected per 100 patients`);
    return "Exactly as many days as expected.";
  }
  if (id.startsWith("HAI_") && id.endsWith("_SIR")) {
    if (intervalStraddlesNeutral(m, 1.0)) {
      const dir = val < 1.0 ? "slightly fewer infections than expected" : "slightly more infections than expected";
      return uncertaintyPunchline(m, dir, "expected", "fewer", "more");
    }
    if (val < 1.0) return withInterval(m, `${((1.0 - val) * 100).toFixed(0)}% fewer infections than the expected rate`);
    if (val > 1.0) return withInterval(m, `${((val - 1.0) * 100).toFixed(0)}% more infections than the expected rate`);
    return "Exactly the expected infection rate.";
  }
  if (id === "PSI_90") {
    if (intervalStraddlesNeutral(m, 1.0)) {
      const dir = val < 1.0 ? "slightly fewer complications than expected" : "slightly more complications than expected";
      return uncertaintyPunchline(m, dir, "expected", "fewer", "more");
    }
    if (val < 1.0) return withInterval(m, `${((1.0 - val) * 100).toFixed(0)}% fewer complications than expected`);
    if (val > 1.0) return withInterval(m, `${((val - 1.0) * 100).toFixed(0)}% more complications than expected`);
    return null;
  }
  if (id.startsWith("HRRP_")) {
    if (intervalStraddlesNeutral(m, 1.0)) {
      const dir = val < 1.0 ? "slightly fewer readmissions than expected" : "slightly more readmissions than expected";
      return uncertaintyPunchline(m, dir, "expected", "fewer", "more");
    }
    if (val < 1.0) return withInterval(m, `${((1.0 - val) * 100).toFixed(0)}% fewer readmissions than expected`);
    if (val > 1.0) return withInterval(m, `${((val - 1.0) * 100).toFixed(0)}% more readmissions than expected`);
    return null;
  }
  if (m.measure_group === "MORTALITY" || id.startsWith("MORT_")) {
    return withInterval(m, `${formatValue(val, unit)} of Medicare patients died within 30 days of admission`);
  }
  if (id.startsWith("READM_")) {
    return withInterval(m, `${formatValue(val, unit)} of Medicare patients were readmitted within 30 days`);
  }
  if (id.startsWith("COMP_")) {
    return withInterval(m, `${formatValue(val, unit)} of patients experienced a serious complication`);
  }
  if (id.startsWith("PSI_") && id !== "PSI_90") {
    return withInterval(m, `${formatValue(val, unit)} of eligible patients experienced this safety event`);
  }
  if (unit === "percent" && m.measure_plain_language) {
    const desc = m.measure_plain_language.charAt(0).toLowerCase() + m.measure_plain_language.slice(1);
    return withInterval(m, `${formatValue(val, unit)} — ${desc}`);
  }
  return null;
}

/** Build the full SEO text template. Returns { body, punchline }. */
function buildFullTemplate(m: Measure, providerName: string): { body: string; punchline: string | null } | null {
  if (m.suppressed || m.not_reported) return null;
  if (m.numeric_value === null && m.score_text === null) return null;

  const facilityName = titleCase(providerName);
  const name = m.measure_name ?? m.measure_id;
  const unit = m.unit ?? "";
  const value = m.numeric_value !== null ? formatValue(m.numeric_value, unit) : m.score_text ?? "";
  const parts: string[] = [];
  const punchline = valueInterpretation(m);

  // Opening sentence — use the punchline interpretation when available,
  // otherwise fall back to the raw value
  if (punchline) {
    parts.push(`For the reporting period ${formatPeriodLabel(m.period_label)}, ${facilityName} reported a ${name.toLowerCase()} of ${value}.`);
  } else {
    parts.push(`At ${facilityName}, the ${name.toLowerCase()} was ${value} for the reporting period ${formatPeriodLabel(m.period_label)}.`);
  }

  if (m.national_avg !== null) {
    parts.push(`The national average for this measure is ${formatValue(m.national_avg, unit)}.`);
  }
  if (m.state_avg !== null) {
    parts.push(`The state average for this measure is ${formatValue(m.state_avg, unit)}.`);
  }
  if (m.measure_plain_language) {
    parts.push(m.measure_plain_language);
  }
  if (m.cms_measure_definition) {
    parts.push(`CMS defines this measure as: "${m.cms_measure_definition}"`);
  }
  if (m.direction === "LOWER_IS_BETTER") {
    parts.push("CMS designates lower values as associated with better outcomes for this measure.");
  } else if (m.direction === "HIGHER_IS_BETTER") {
    parts.push("CMS designates higher values as associated with better outcomes for this measure.");
  }
  // Interval in body only when punchline doesn't already include it
  if (!punchline && m.confidence_interval_lower !== null && m.confidence_interval_upper !== null && m.sample_size !== null) {
    parts.push(`This estimate is based on ${m.sample_size.toLocaleString("en-US")} ${sampleLabel(m).toLowerCase()}; the interval estimate ranges from ${formatValue(m.confidence_interval_lower, unit)} to ${formatValue(m.confidence_interval_upper, unit)}.`);
  }
  if (m.overlap_flag === true) {
    parts.push("The facility value and national average fall within overlapping ranges of statistical uncertainty, meaning the difference may not be meaningful.");
  }
  if (m.compared_to_national && m.national_avg !== null) {
    const label = CMS_COMPARISON_LABELS[m.compared_to_national];
    if (label) parts.push(label);
  }

  return { body: parts.join(" "), punchline };
}

/** Context-aware metric label and value display. */
function metricDisplay(m: Measure): { label: string; displayValue: string; inverted: boolean } {
  const unit = m.unit ?? "";
  const val = m.numeric_value;
  if (val === null) return { label: "Rate", displayValue: "—", inverted: false };
  const id = m.measure_id;

  if (id.startsWith("EDAC_")) {
    return {
      label: val < 0 ? "Days Below Expected (per 100)" : val > 0 ? "Days Above Expected (per 100)" : "Days vs. Expected (per 100)",
      displayValue: formatValue(val, unit),
      inverted: false,
    };
  }
  if (id.startsWith("HAI_") && id.endsWith("_SIR")) {
    return { label: "Infection Ratio (SIR)", displayValue: formatValue(val, unit), inverted: false };
  }
  if (id.startsWith("PSI_")) {
    return { label: id === "PSI_90" ? "Safety Composite Score" : "Safety Indicator Rate", displayValue: formatValue(val, unit), inverted: false };
  }
  if (m.measure_group === "MORTALITY" || id.startsWith("MORT_")) {
    return { label: "Death Rate", displayValue: formatValue(val, unit), inverted: false };
  }
  if (id.startsWith("READM_")) {
    return { label: "Readmission Rate", displayValue: formatValue(val, unit), inverted: false };
  }
  if (id.startsWith("HRRP_")) {
    return { label: "Excess Readmission Ratio", displayValue: formatValue(val, unit), inverted: false };
  }
  if (id.startsWith("COMP_")) {
    return { label: "Complication Rate", displayValue: formatValue(val, unit), inverted: false };
  }
  if (id.startsWith("MSPB")) {
    return { label: "Spending per Patient", displayValue: formatValue(val, unit), inverted: false };
  }
  if (id.startsWith("OP_18")) {
    return { label: "Median Wait Time", displayValue: formatValue(val, unit), inverted: false };
  }
  switch (unit) {
    case "percent": return { label: "Rate", displayValue: formatValue(val, unit), inverted: false };
    case "ratio": return { label: "Ratio", displayValue: formatValue(val, unit), inverted: false };
    case "minutes": return { label: "Time", displayValue: formatValue(val, unit), inverted: false };
    case "score": return { label: "Score", displayValue: formatValue(val, unit), inverted: false };
    default: return { label: "Value", displayValue: formatValue(val, unit), inverted: false };
  }
}

/** Bold + rest context for stat block inline interpretation. */
function valueContext(m: Measure): { bold: string; rest: string } | null {
  const val = m.numeric_value;
  if (val === null) return null;
  const id = m.measure_id;

  if (id.startsWith("EDAC_")) {
    if (val < 0) return { bold: "Negative value:", rest: "patients spent fewer days back in acute care than expected." };
    if (val > 0) return { bold: "Positive value:", rest: "patients spent more days back in acute care than expected." };
    return { bold: "Zero:", rest: "exactly as many days as expected." };
  }
  if (id.startsWith("HAI_") && id.endsWith("_SIR")) {
    if (val < 1.0) return { bold: "Below 1.0 means", rest: "fewer infections than expected." };
    if (val > 1.0) return { bold: "Above 1.0 means", rest: "more infections than expected." };
    return { bold: "1.0 means", rest: "exactly as expected." };
  }
  if (id === "PSI_90") {
    if (val < 1.0) return { bold: "Below 1.0 means", rest: "fewer complications than expected." };
    if (val > 1.0) return { bold: "Above 1.0 means", rest: "more complications than expected." };
    return null;
  }
  if (id.startsWith("HRRP_")) {
    if (val < 1.0) return { bold: "Below 1.0 means", rest: "fewer readmissions than expected." };
    if (val > 1.0) return { bold: "Above 1.0 means", rest: "more readmissions than expected." };
    return null;
  }
  return null;
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

export function MeasureCard({
  measure,
  providerLastUpdated,
  providerName = "This hospital",
  inlineTrend = false,
  onTagClick,
}: MeasureCardProps): React.JSX.Element {

  const shortName = measure.measure_name ?? measure.measure_id;
  const unit = measure.unit ?? "";
  const hasCI =
    measure.confidence_interval_lower !== null &&
    measure.confidence_interval_upper !== null;
  const showSmallSample =
    measure.sample_size !== null &&
    measure.sample_size < SMALL_SAMPLE_THRESHOLD &&
    !measure.suppressed &&
    !measure.not_reported;
  const hasNationalAvg = measure.national_avg !== null;
  const hasTrend = measure.trend !== null && measure.trend.length > 0;
  const isValueCard =
    !measure.suppressed && !measure.not_reported && measure.numeric_value !== null;
  const hasOE = measure.observed_value !== null && measure.expected_value !== null;
  const oeRatio = hasOE ? measure.observed_value! / measure.expected_value! : null;

  const cmsDirectionText =
    measure.direction === "LOWER_IS_BETTER"
      ? "CMS indicates: Lower is better for this measure."
      : measure.direction === "HIGHER_IS_BETTER"
        ? "CMS indicates: Higher is better for this measure."
        : null;

  const metric = metricDisplay(measure);
  const cmsComparisonText =
    measure.compared_to_national && hasNationalAvg
      ? CMS_COMPARISON_LABELS[measure.compared_to_national] ?? null
      : null;

  const distribution = useDistribution(measure.measure_id, measure.period_label);

  const borderAccent = showSmallSample
    ? "border-l-amber-400"
    : measure.suppressed || measure.not_reported
      ? "border-l-gray-300"
      : "border-l-blue-400";

  const tags = getTagsForMeasure(measure);
  const tagLabels = tags
    .map((id) => MEASURE_TAGS.find((t) => t.id === id))
    .filter(Boolean) as { id: string; label: string }[];

  return (
    <div className={`rounded-lg border border-gray-200 ${borderAccent} border-l-4 bg-white px-5 py-5 shadow-sm`}>
      {/* Title */}
      <h3 className="mb-2 text-sm font-semibold leading-snug text-blue-800">
        {shortName}
      </h3>

      {/* Category tags */}
      {tagLabels.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {tagLabels.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => onTagClick?.(t.id)}
              className="inline-block rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-xs text-gray-500 transition-colors hover:bg-blue-50 hover:text-blue-600"
              title={`Filter by ${t.label}`}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {/* CMS Definition — only when available */}
      {measure.cms_measure_definition && (
        <div className="mb-4 rounded border border-gray-100 bg-gray-50 px-4 py-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
            CMS Definition
          </p>
          <p className="text-xs leading-relaxed text-gray-700">
            {measure.cms_measure_definition}
          </p>
        </div>
      )}


      {/* Reporting period */}
      <p className="mb-4 text-xs text-gray-400">
        <span className="font-medium text-gray-500">Reporting Period:</span>{" "}
        {formatPeriodLabel(measure.period_label)}
      </p>

      {/* Value display */}
      <div className="mb-4">
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
          <div className="rounded-md border border-gray-100 border-l-4 border-l-blue-400 bg-gray-50 px-4 py-3">
            <div className="text-xs font-medium uppercase tracking-wide text-gray-400">Result</div>
            <div className="mt-1 text-2xl font-semibold capitalize text-gray-800">{measure.score_text}</div>
            {/* CMS direction + comparison */}
            <div className="mt-3 space-y-1">
              {measure.direction && (
                <div className="flex items-center gap-1.5">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-50">
                    {measure.direction === "LOWER_IS_BETTER" ? (
                      <svg className="h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>
                    ) : (
                      <svg className="h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>
                    )}
                  </div>
                  <span className="text-xs text-gray-400">{cmsDirectionText}</span>
                </div>
              )}
            </div>
          </div>
        ) : measure.numeric_value !== null ? (
          <div className="rounded-md border border-gray-100 border-l-4 border-l-blue-400 bg-gray-50 px-4 py-3">
            {/* CMS comparison — promoted to top */}
            {cmsComparisonText && (
              <p className="mb-3 text-sm font-medium text-blue-700">
                {cmsComparisonText}
              </p>
            )}
            <div className="flex flex-wrap items-baseline gap-x-6 gap-y-3">
              <div>
                <div className="text-xs font-medium uppercase tracking-wide text-gray-400">{metric.label}</div>
                <div className="mt-0.5 text-2xl font-semibold text-gray-800">
                  {metric.displayValue}
                </div>
                {/* Inline interpretation for tricky values */}
                {valueContext(measure) && (
                  <p className="mt-1 text-xs text-gray-500">
                    <span className="font-semibold text-gray-800">{valueContext(measure)!.bold}</span>{" "}
                    {valueContext(measure)!.rest}
                  </p>
                )}
              </div>
              {hasCI && (
                <div>
                  <div className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-gray-400">
                    Interval Estimate
                    <a href="/methodology/" className="text-blue-500 hover:text-blue-700" aria-label="About interval estimates" title="Interval estimates reflect uncertainty in this measure. Depending on the metric, these may be frequentist confidence intervals or Bayesian credible intervals. See Methodology for details.">
                      <svg className="inline h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><circle cx="12" cy="12" r="10" /><path d="M12 16v-4m0-4h.01" /></svg>
                    </a>
                  </div>
                  <div className="mt-0.5 text-base font-medium text-gray-600">
                    {formatInterval(measure.confidence_interval_lower!, measure.confidence_interval_upper!, unit)}
                  </div>
                </div>
              )}
              {(measure.sample_size !== null || measure.denominator !== null) && !measure.count_suppressed && (
                <div>
                  <div className="text-xs font-medium uppercase tracking-wide text-gray-400">
                    {sampleLabel(measure)}
                  </div>
                  <div className="mt-0.5 text-base font-medium text-gray-600">
                    {(measure.sample_size ?? measure.denominator)!.toLocaleString("en-US")}
                  </div>
                </div>
              )}
            </div>
            {/* CMS direction + comparison with arrow */}
            <div className="mt-3 space-y-1">
              {measure.direction && (
                <div className="flex items-center gap-1.5">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-50">
                    {measure.direction === "LOWER_IS_BETTER" ? (
                      <svg className="h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>
                    ) : (
                      <svg className="h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>
                    )}
                  </div>
                  <span className="text-xs text-gray-400">{cmsDirectionText}</span>
                </div>
              )}
            </div>

            {/* Distribution histogram */}
            {distribution && measure.numeric_value !== null && (
              <DistributionHistogram
                distribution={distribution}
                value={measure.numeric_value}
                ciLower={measure.confidence_interval_lower}
                ciUpper={measure.confidence_interval_upper}
                nationalAvg={measure.national_avg}
                direction={measure.direction}
                unit={unit}
                showSmallSampleLink={showSmallSample}
                comparedToNational={measure.compared_to_national}
              />
            )}
          </div>
        ) : (
          <span className="text-sm text-gray-500">Value not available</span>
        )}
      </div>

      {/* Count suppression */}
      {measure.count_suppressed && (
        <p className="mb-3 text-xs text-gray-500">
          Case count data is suppressed by CMS for patient privacy.
        </p>
      )}

      {/* O/E ratio with interpretation */}
      {hasOE && oeRatio !== null && (
        <div className="mb-3 rounded border border-gray-100 bg-gray-50 px-4 py-3">
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2 text-xs">
            <div>
              <span className="font-medium text-gray-500">Observed events:</span>{" "}
              <span className="text-gray-700">{measure.observed_value!.toFixed(0)}</span>
            </div>
            <div>
              <span className="font-medium text-gray-500">Expected events:</span>{" "}
              <span className="text-gray-700">{measure.expected_value!.toFixed(2)}</span>
            </div>
            <div>
              <span className="font-medium text-gray-500">Ratio (O/E):</span>{" "}
              <span className="font-semibold text-gray-800">{oeRatio.toFixed(2)}</span>
              <span className="ml-1 text-gray-400">
                — {oeRatio < 1.0
                  ? "below 1.0 means fewer events than expected"
                  : oeRatio > 1.0
                    ? "above 1.0 means more events than expected"
                    : "1.0 = exactly as expected"}
              </span>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-400">1.0 = national expected rate</p>
        </div>
      )}

      {/* Benchmark */}
      {isValueCard && hasNationalAvg && (
        <div className="mb-3">
          <BenchmarkBar
            value={measure.numeric_value!}
            nationalAvg={measure.national_avg!}
            stateAvg={measure.state_avg}
            unit={unit}
            ciLower={measure.confidence_interval_lower}
            ciUpper={measure.confidence_interval_upper}
          />
          <p className="mt-1 text-xs text-gray-500">
            National avg: {formatValue(measure.national_avg!, unit)}
            {measure.state_avg !== null && (
              <> · State avg: {formatValue(measure.state_avg, unit)}</>
            )}
          </p>
        </div>
      )}

      {/* Reliability flag */}
      {measure.reliability_flag !== null && !measure.suppressed && !measure.not_reported && (
        <p className="mb-3 text-xs text-gray-500">
          {RELIABILITY_LABELS[measure.reliability_flag] ?? measure.reliability_flag}
        </p>
      )}

      {/* Small sample caveat — amber */}
      {showSmallSample && (
        <div className="mb-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {SMALL_SAMPLE_CAVEAT(measure.sample_size!)}
        </div>
      )}

      {/* Footnotes */}
      {measure.footnote_codes !== null && (
        <FootnoteDisclosure
          footnote_codes={measure.footnote_codes}
          footnote_text={measure.footnote_text}
        />
      )}

      {/* Bold punchline + full summary — above trend chart */}
      {(() => {
        const punchline = valueInterpretation(measure);
        const template = buildFullTemplate(measure, providerName);
        if (!punchline && !template) return null;
        return (
          <div className="mb-3">
            {punchline && (
              <p className="text-sm font-semibold text-gray-800">
                {punchline}
              </p>
            )}
            {template && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs font-medium text-gray-500 hover:text-gray-700">
                  Full summary
                </summary>
                <p className="mt-2 text-xs leading-relaxed text-gray-600">
                  {template.body}
                </p>
              </details>
            )}
          </div>
        );
      })()}

      {/* Inline trend chart */}
      {hasTrend && (
        <div className="mt-4 border-t border-gray-100 pt-3">
          <p className="mb-1 text-xs font-semibold text-blue-600">
            {shortName} — Trend Over Time
          </p>
          <TrendChart
            trend={measure.trend}
            trendValid={measure.trend_valid}
            trendPeriodCount={measure.trend_period_count}
            unit={unit}
            nationalAvg={measure.national_avg}
            stateAvg={measure.state_avg}
            showOEReference={hasOE}
            referenceValue={
              measure.measure_id.startsWith("EDAC_") ? 0
              : (measure.measure_id.startsWith("HRRP_") || measure.measure_id === "PSI_90") ? 1.0
              : null
            }
            referenceLabel={
              measure.measure_id.startsWith("EDAC_") ? "0 = expected"
              : (measure.measure_id.startsWith("HRRP_") || measure.measure_id === "PSI_90") ? "1.0 = expected"
              : undefined
            }
            ciLower={measure.confidence_interval_lower}
            ciUpper={measure.confidence_interval_upper}
            sampleLabelText={sampleLabel(measure)}
            direction={measure.direction}
            yAxisLabel={metric.label}
            zoomToData
            distributionMin={distribution?.bin_edges[0] ?? null}
            distributionMax={distribution?.bin_edges[distribution?.bin_edges.length - 1] ?? null}
          />
        </div>
      )}


      {/* Source — collapsed */}
      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-600">
          Source
        </summary>
        <p className="mt-1 text-xs text-gray-400">
          Source: CMS {measure.source_dataset_name},{" "}
          {formatPeriodLabel(measure.period_label)}. Data reflects CMS reporting as of{" "}
          {new Date(providerLastUpdated).toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
          })}.
        </p>
      </details>
    </div>
  );
}
