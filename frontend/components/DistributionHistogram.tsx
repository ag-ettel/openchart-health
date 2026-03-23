"use client";

// National distribution histogram for a measure.
// 25 bins with:
// - Blue shading for this hospital's interval estimate range
// - Blue dashed line for this hospital's observed value ("This hospital")
// - Orange dashed line for national average ("National avg")
// - CMS direction labels at appropriate x-axis ends
// - X-axis tick marks: min, national avg, max
// - Legend explaining blue shading and uncertainty

import type { MeasureDirection } from "@/types/provider";
import { formatValue } from "@/lib/utils";

interface DistributionData {
  counts: number[];
  bin_edges: number[];
  total: number;
  mean: number;
  median: number;
}

interface DistributionHistogramProps {
  distribution: DistributionData;
  value: number;
  ciLower: number | null;
  ciUpper: number | null;
  nationalAvg: number | null;
  direction: MeasureDirection | null;
  unit: string;
  showSmallSampleLink?: boolean;
  /** CMS's own assessment — used first when available */
  comparedToNational?: string | null;
}

export function DistributionHistogram({
  distribution,
  value,
  ciLower,
  ciUpper,
  nationalAvg,
  direction,
  unit,
  showSmallSampleLink = false,
  comparedToNational = null,
}: DistributionHistogramProps): React.JSX.Element {
  const { counts, bin_edges } = distribution;
  const maxCount = Math.max(...counts);

  // Full range — always show the complete distribution
  const rangeMin = bin_edges[0];
  const rangeMax = bin_edges[bin_edges.length - 1];
  const rangeSpan = rangeMax - rangeMin;

  const toPercent = (v: number): number => {
    if (rangeSpan === 0) return 50;
    return Math.max(0, Math.min(100, ((v - rangeMin) / rangeSpan) * 100));
  };

  const valuePos = toPercent(value);

  // Use distribution mean as fallback when nationalAvg not available from benchmarks
  const effectiveAvg = nationalAvg ?? distribution.mean;
  const avgPos = toPercent(effectiveAvg);
  const hasExplicitNationalAvg = nationalAvg !== null;

  // Direction labels — x-axis goes from low values (left) to high values (right)
  // LOWER_IS_BETTER: left end is better, right end is worse
  // HIGHER_IS_BETTER: left end is worse, right end is better
  const leftLabel = direction === "LOWER_IS_BETTER"
    ? "← CMS: Better"
    : direction === "HIGHER_IS_BETTER"
      ? "← CMS: Worse"
      : null;
  const rightLabel = direction === "LOWER_IS_BETTER"
    ? "CMS: Worse →"
    : direction === "HIGHER_IS_BETTER"
      ? "CMS: Better →"
      : null;

  const isInCIRange = (binIndex: number): boolean => {
    if (ciLower === null || ciUpper === null) return false;
    const binLeft = bin_edges[binIndex];
    const binRight = bin_edges[binIndex + 1];
    return binRight >= ciLower && binLeft <= ciUpper;
  };

  return (
    <div className="mt-3">
      {/* Histogram bars */}
      <div className="relative" style={{ height: 72 }}>
        <div className="flex h-full items-end gap-px">
          {counts.map((count, i) => {
            const heightPct = maxCount > 0 ? (count / maxCount) * 100 : 0;
            const inCI = isInCIRange(i);
            const binLow = formatValue(bin_edges[i], unit);
            const binHigh = formatValue(bin_edges[i + 1], unit);
            return (
              <div
                key={i}
                className="group relative flex-1 cursor-default rounded-t-sm transition-opacity hover:z-10 hover:opacity-80"
                style={{
                  height: `${heightPct}%`,
                  minHeight: count > 0 ? 2 : 0,
                  backgroundColor: inCI ? "#93c5fd" : "#e5e7eb",
                }}
              >
                <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1.5 hidden -translate-x-1/2 whitespace-nowrap rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 shadow-sm group-hover:block">
                  {binLow} to {binHigh}: {count} hospital{count !== 1 ? "s" : ""}
                </div>
              </div>
            );
          })}
        </div>

        {/* National avg line — orange dashed */}
        <div
          className="absolute top-0 bottom-0"
          style={{ left: `${avgPos}%` }}
        >
          <div className="h-full border-l-2 border-dashed border-orange-400" />
        </div>

        {/* Hospital value line — blue dashed */}
        <div
          className="absolute top-0 bottom-0"
          style={{ left: `${valuePos}%` }}
        >
          <div className="h-full border-l-2 border-dashed border-blue-600" />
        </div>
      </div>

      {/* X-axis: min and max only — line labels below show hospital + avg values */}
      <div className="relative mt-0.5 border-t border-gray-200" style={{ height: 14 }}>
        <span className="absolute left-0 text-xs text-gray-400" style={{ transform: "translateY(1px)" }}>
          {formatValue(rangeMin, unit)}
        </span>
        <span className="absolute right-0 text-xs text-gray-400" style={{ transform: "translateY(1px)" }}>
          {formatValue(rangeMax, unit)}
        </span>
      </div>

      {/* Legend — fixed layout, no positioning issues */}
      <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-0.5 text-xs">
        <span className="flex items-center gap-1.5 font-medium text-blue-600">
          <span className="inline-block h-3 w-0 border-l-2 border-dashed border-blue-600" />
          {formatValue(value, unit)} · This hospital
        </span>
        <span className="flex items-center gap-1.5 font-medium text-orange-500">
          <span className="inline-block h-3 w-0 border-l-2 border-dashed border-orange-400" />
          {formatValue(effectiveAvg, unit)} · National average
        </span>
      </div>

      {/* Direction labels */}
      {(leftLabel || rightLabel) && (
        <div className="flex justify-between text-xs text-gray-400">
          <span>{leftLabel}</span>
          <span>{rightLabel}</span>
        </div>
      )}

      {/* Footer: count + legend + overlap interpretation */}
      <div className="mt-1.5 space-y-1">
        <p className="text-center text-xs text-gray-400">
          Distribution across {distribution.total.toLocaleString("en-US")} hospitals
        </p>
        <p className="text-xs text-gray-400">
          <span className="mr-1 inline-block h-2.5 w-4 rounded-sm bg-blue-300 align-middle" />
          Blue shading shows the plausible range for this hospital&apos;s result.
          {(() => {
            // Use CMS assessment first when available
            if (comparedToNational === "NO_DIFFERENT" || comparedToNational === "TOO_FEW_CASES") {
              return " CMS assesses this hospital as no different from the national rate. The plausible range overlaps with the national average.";
            }
            if (comparedToNational === "BETTER") {
              return " CMS assesses this hospital as better than the national rate.";
            }
            if (comparedToNational === "WORSE") {
              return " CMS assesses this hospital as worse than the national rate.";
            }
            // Fall back to interval/average overlap when CMS doesn't provide assessment
            if (ciLower !== null && ciUpper !== null) {
              const avgInCI = ciLower <= effectiveAvg && ciUpper >= effectiveAvg;
              if (avgInCI) {
                return " The national average falls within this range, meaning the difference may not be statistically meaningful.";
              }
              return " The national average falls outside this range, suggesting a meaningful difference from average.";
            }
            return " A wider blue zone reflects greater uncertainty, often due to fewer cases.";
          })()}
          {showSmallSampleLink && (
            <span className="ml-1 font-medium text-amber-700">
              With a small number of cases, the true rate could fall anywhere within the shaded range.
            </span>
          )}
        </p>
      </div>
    </div>
  );
}
