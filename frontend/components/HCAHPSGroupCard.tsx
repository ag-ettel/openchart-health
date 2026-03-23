"use client";

// HCAHPS question group card — rich display with:
// - Headline "Always" or "Definitely Yes" percentage
// - Horizontal stacked bar (response distribution)
// - Trend line for the primary response over time
// - Distribution histogram (via useDistribution)
// - Survey count
// Retired measures are hidden.

import type { HCAHPSGroup } from "@/lib/measure-tags";
import type { Measure, TrendPeriod } from "@/types/provider";
import { formatValue, formatPeriodLabel } from "@/lib/utils";
import { useDistribution } from "@/lib/use-distributions";
import { DistributionHistogram } from "./DistributionHistogram";
import { TrendChart } from "./TrendChart";

interface HCAHPSGroupCardProps {
  group: HCAHPSGroup;
  providerLastUpdated: string;
}

// Response type patterns and their consumer labels + colors
interface ResponseSlice {
  measure: Measure;
  label: string;
  color: string;
  isPrimary: boolean; // The "best" response (Always, Definitely Yes, 9-10)
}

function categorizeResponses(responses: Measure[]): ResponseSlice[] {
  const slices: ResponseSlice[] = [];

  for (const m of responses) {
    const id = m.measure_id;
    if (id.endsWith("_A_P")) {
      slices.push({ measure: m, label: "Always", color: "#2563eb", isPrimary: true });
    } else if (id.endsWith("_U_P")) {
      slices.push({ measure: m, label: "Usually", color: "#93c5fd", isPrimary: false });
    } else if (id.endsWith("_SN_P")) {
      slices.push({ measure: m, label: "Sometimes/Never", color: "#e5e7eb", isPrimary: false });
    } else if (id.endsWith("_DY")) {
      slices.push({ measure: m, label: "Definitely Yes", color: "#2563eb", isPrimary: true });
    } else if (id.endsWith("_PY")) {
      slices.push({ measure: m, label: "Probably Yes", color: "#93c5fd", isPrimary: false });
    } else if (id.endsWith("_DN")) {
      slices.push({ measure: m, label: "Probably/Definitely No", color: "#e5e7eb", isPrimary: false });
    } else if (id.endsWith("_Y_P")) {
      slices.push({ measure: m, label: "Yes", color: "#2563eb", isPrimary: true });
    } else if (id.endsWith("_N_P")) {
      slices.push({ measure: m, label: "No", color: "#e5e7eb", isPrimary: false });
    } else if (id.endsWith("_9_10")) {
      slices.push({ measure: m, label: "9-10 (High)", color: "#2563eb", isPrimary: true });
    } else if (id.endsWith("_7_8")) {
      slices.push({ measure: m, label: "7-8 (Medium)", color: "#93c5fd", isPrimary: false });
    } else if (id.endsWith("_0_6")) {
      slices.push({ measure: m, label: "6 or lower", color: "#e5e7eb", isPrimary: false });
    }
  }

  // Sort: primary first, then by value descending
  return slices.sort((a, b) => {
    if (a.isPrimary && !b.isPrimary) return -1;
    if (!a.isPrimary && b.isPrimary) return 1;
    return (b.measure.numeric_value ?? 0) - (a.measure.numeric_value ?? 0);
  });
}

export function HCAHPSGroupCard({
  group,
  providerLastUpdated,
}: HCAHPSGroupCardProps): React.JSX.Element {
  const slices = categorizeResponses(group.responses);
  const primarySlice = slices.find((s) => s.isPrimary);
  const primaryMeasure = primarySlice?.measure ?? null;
  const primaryValue = primaryMeasure?.numeric_value ?? null;
  const primaryLabel = primarySlice?.label ?? "Top Response";

  // Period from any response measure
  const period = primaryMeasure
    ? formatPeriodLabel(primaryMeasure.period_label)
    : group.responses[0]
      ? formatPeriodLabel(group.responses[0].period_label)
      : "";

  // Survey count from star rating or any response measure
  const surveyCount =
    group.starRating?.sample_size ??
    primaryMeasure?.sample_size ??
    primaryMeasure?.denominator ??
    null;

  // Distribution for the primary response
  const distribution = useDistribution(
    primaryMeasure?.measure_id ?? "",
    primaryMeasure?.period_label ?? ""
  );

  // Check if all responses have data
  const hasResponseData = slices.some((s) => s.measure.numeric_value !== null);
  const total = slices.reduce((sum, s) => sum + (s.measure.numeric_value ?? 0), 0);

  return (
    <div className="rounded-lg border border-gray-200 border-l-4 border-l-blue-400 bg-white px-5 py-5 shadow-sm">
      {/* Category badge */}
      <div className="mb-2">
        <span className="inline-block rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          Patient Experience
        </span>
      </div>

      {/* Title */}
      <h3 className="mb-1 text-sm font-semibold text-blue-800">
        {group.label}
      </h3>

      {/* Reporting period */}
      {period && (
        <p className="mb-4 text-xs text-gray-400">
          <span className="font-medium text-gray-500">Reporting Period:</span> {period}
        </p>
      )}

      {/* Stat block */}
      {hasResponseData && (
        <div className="mb-4 rounded-md border border-gray-100 border-l-4 border-l-blue-400 bg-gray-50 px-4 py-3">
          {/* Headline: primary response percentage with full context from CMS name */}
          {primaryValue !== null && primaryMeasure && (
            <div className="mb-3">
              <div className="text-xs font-medium tracking-wide text-gray-500">
                {primaryMeasure.measure_name ?? `Patients who responded "${primaryLabel}"`}
              </div>
              <div className="mt-0.5 text-2xl font-semibold text-gray-800">
                {primaryValue}%
              </div>
            </div>
          )}

          {/* Stacked horizontal bar */}
          {total > 0 && (
            <div className="mb-3">
              <div className="flex h-6 overflow-hidden rounded-full">
                {slices
                  .filter((s) => (s.measure.numeric_value ?? 0) > 0)
                  .map((s) => (
                    <div
                      key={s.measure.measure_id}
                      className="relative"
                      style={{
                        width: `${((s.measure.numeric_value ?? 0) / total) * 100}%`,
                        backgroundColor: s.color,
                      }}
                      title={`${s.label}: ${s.measure.numeric_value}%`}
                    />
                  ))}
              </div>
              {/* Bar legend */}
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
                {slices
                  .filter((s) => (s.measure.numeric_value ?? 0) > 0)
                  .map((s) => (
                    <span key={s.measure.measure_id} className="flex items-center gap-1.5 text-xs text-gray-500">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-sm"
                        style={{ backgroundColor: s.color }}
                      />
                      {s.label}: {s.measure.numeric_value}%
                    </span>
                  ))}
              </div>
            </div>
          )}

          {/* Survey count */}
          {surveyCount !== null && (
            <p className="text-xs text-gray-400">
              Based on {surveyCount.toLocaleString("en-US")} completed surveys
            </p>
          )}

          {/* Distribution histogram for primary response */}
          {distribution && primaryValue !== null && primaryMeasure && (
            <>
            <p className="mt-3 mb-1 text-xs font-medium text-gray-500">
              National distribution of &quot;{primaryLabel}&quot; responses
            </p>
            <DistributionHistogram
              distribution={distribution}
              value={primaryValue}
              ciLower={primaryMeasure.confidence_interval_lower}
              ciUpper={primaryMeasure.confidence_interval_upper}
              nationalAvg={primaryMeasure.national_avg}
              direction="HIGHER_IS_BETTER"
              unit="percent"
            />
            </>
          )}
        </div>
      )}

      {/* Bold punchline */}
      {primaryValue !== null && surveyCount !== null && (
        <p className="mb-3 text-base font-bold leading-snug text-gray-900">
          {primaryValue}% of {surveyCount.toLocaleString("en-US")} surveyed patients
          gave the highest response for {group.label.toLowerCase()}.
        </p>
      )}

      {/* Full summary — collapsed for SEO */}
      {primaryValue !== null && (
        <details className="mb-3">
          <summary className="cursor-pointer text-xs font-medium text-gray-500 hover:text-gray-700">
            Full summary
          </summary>
          <p className="mt-2 text-xs leading-relaxed text-gray-600">
            In the HCAHPS patient survey for {group.label.toLowerCase()},{" "}
            {primaryValue}% of patients selected &quot;{primaryLabel}&quot;
            {slices.filter(s => !s.isPrimary && (s.measure.numeric_value ?? 0) > 0).length > 0 && (
              <>, while {slices.filter(s => !s.isPrimary && (s.measure.numeric_value ?? 0) > 0).map(s =>
                `${s.measure.numeric_value}% selected "${s.label}"`
              ).join(" and ")}</>
            )}.
            {surveyCount !== null && (
              <> This is based on {surveyCount.toLocaleString("en-US")} completed surveys.</>
            )}{" "}
            HCAHPS (Hospital Consumer Assessment of Healthcare Providers and Systems) is a
            standardized survey administered to a random sample of adult inpatients after
            discharge. Results are adjusted for patient mix to allow fair comparison across hospitals.
            CMS designates higher patient experience scores as associated with better outcomes.
          </p>
        </details>
      )}

      {/* Trend chart — collapsed by default */}
      {primaryMeasure && primaryMeasure.trend && primaryMeasure.trend.length > 0 && (
        <details className="mt-4 border-t border-gray-100 pt-3">
          <summary className="cursor-pointer text-xs font-semibold text-blue-600 hover:text-blue-800">
            Show trend over time
          </summary>
          <p className="mt-1 mb-1 text-xs font-semibold text-blue-600">
            {group.label}: &quot;{primaryLabel}&quot; Response — Trend Over Time
          </p>
          <TrendChart
            trend={primaryMeasure.trend}
            trendValid={primaryMeasure.trend_valid}
            trendPeriodCount={primaryMeasure.trend_period_count}
            unit="percent"
            nationalAvg={primaryMeasure.national_avg}
            stateAvg={primaryMeasure.state_avg}
            direction="HIGHER_IS_BETTER"
            yAxisLabel={`"${primaryLabel}" %`}
            zoomToData
            distributionMin={distribution?.bin_edges[0] ?? null}
            distributionMax={distribution?.bin_edges[distribution.bin_edges.length - 1] ?? null}
          />
        </details>
      )}

      {/* Source */}
      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-600">
          Source
        </summary>
        <p className="mt-1 text-xs text-gray-400">
          Source: CMS HCAHPS Patient Survey, {period}. Data reflects CMS
          reporting as of{" "}
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
