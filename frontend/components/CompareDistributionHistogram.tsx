"use client";

// CompareDistributionHistogram — paired-marker version of DistributionHistogram.
//
// Replaces the CompareIntervalPlot bar-chart for measures where a national
// distribution is available. Shows the full national distribution as a
// 25-bin histogram with up to two provider markers (blue for Provider A,
// dark gray for Provider B), each provider's plausible-range band rendered
// above the histogram, and the national average as an orange dashed line.
//
// Why a histogram instead of paired bars:
//  - Percentile context: the user can see where each facility falls in the
//    national distribution, not just whether one is higher than the other.
//  - Uncertainty stays visible without overlapping a colored bar fill.
//  - Single-marker fallback (when one provider is suppressed) remains
//    meaningful because the surviving provider still gets distribution
//    context.
//
// No directional color coding (DEC-030). Identity colors only (blue / gray).

import type { MeasureDirection } from "@/types/provider";
import { useDistribution } from "@/lib/use-distributions";
import { formatValue } from "@/lib/utils";

export interface CompareDistributionPoint {
  value: number;
  ciLower: number | null;
  ciUpper: number | null;
  label: string;
}

interface CompareDistributionHistogramProps {
  measureId: string;
  periodLabel: string;
  providerA: CompareDistributionPoint | null;
  providerB: CompareDistributionPoint | null;
  nationalAvg: number | null;
  direction: MeasureDirection | null;
  unit: string;
}

export function CompareDistributionHistogram({
  measureId,
  periodLabel,
  providerA,
  providerB,
  nationalAvg,
  direction,
  unit,
}: CompareDistributionHistogramProps): React.JSX.Element | null {
  const distribution = useDistribution(measureId, periodLabel);

  if (!distribution) return null;
  if (!providerA && !providerB) return null;

  const dist = distribution;
  const { counts, bin_edges } = dist;
  const maxCount = Math.max(...counts);
  const rangeMin = bin_edges[0];
  const rangeMax = bin_edges[bin_edges.length - 1];
  const rangeSpan = rangeMax - rangeMin;

  const toPercent = (v: number): number => {
    if (rangeSpan === 0) return 50;
    return Math.max(0, Math.min(100, ((v - rangeMin) / rangeSpan) * 100));
  };

  const effectiveAvg = nationalAvg ?? dist.mean;
  const avgPos = toPercent(effectiveAvg);
  const hasExplicitNationalAvg = nationalAvg !== null;

  const aPos = providerA ? toPercent(providerA.value) : null;
  const bPos = providerB ? toPercent(providerB.value) : null;

  const aCiL =
    providerA && providerA.ciLower !== null ? toPercent(providerA.ciLower) : null;
  const aCiU =
    providerA && providerA.ciUpper !== null ? toPercent(providerA.ciUpper) : null;
  const bCiL =
    providerB && providerB.ciLower !== null ? toPercent(providerB.ciLower) : null;
  const bCiU =
    providerB && providerB.ciUpper !== null ? toPercent(providerB.ciUpper) : null;

  const showACi = aCiL !== null && aCiU !== null;
  const showBCi = bCiL !== null && bCiU !== null;

  // Direction labels — x-axis goes from low values (left) to high values (right)
  const leftLabel =
    direction === "LOWER_IS_BETTER"
      ? "← CMS: Better"
      : direction === "HIGHER_IS_BETTER"
        ? "← CMS: Worse"
        : null;
  const rightLabel =
    direction === "LOWER_IS_BETTER"
      ? "CMS: Worse →"
      : direction === "HIGHER_IS_BETTER"
        ? "CMS: Better →"
        : null;

  // Approximate percentile of each provider in the distribution. Counts cumulative
  // facilities up through the value's bin so the user gets a "X is at the Nth
  // percentile" signal without needing per-facility data.
  function approxPercentile(value: number): number | null {
    if (rangeSpan === 0) return null;
    if (value <= rangeMin) return 0;
    if (value >= rangeMax) return 100;
    let cumulative = 0;
    for (let i = 0; i < counts.length; i++) {
      const binLeft = bin_edges[i];
      const binRight = bin_edges[i + 1];
      if (value < binRight) {
        const within = (value - binLeft) / (binRight - binLeft);
        cumulative += counts[i] * within;
        return Math.round((cumulative / dist.total) * 100);
      }
      cumulative += counts[i];
    }
    return 100;
  }

  const aPercentile = providerA ? approxPercentile(providerA.value) : null;
  const bPercentile = providerB ? approxPercentile(providerB.value) : null;

  // Two stacked CI bands above the histogram so neither is hidden behind the
  // other. Band height 4px, gap 2px, total reserved space depends on which
  // bands are present.
  const bandsHeight = (showACi ? 4 : 0) + (showBCi ? 4 : 0) + (showACi && showBCi ? 2 : 0);

  return (
    <div className="mt-3">
      {/* Plausible-range bands above the histogram */}
      {(showACi || showBCi) && (
        <div className="relative mb-1" style={{ height: bandsHeight }}>
          {showACi && (
            <div
              className="absolute h-1 rounded-full bg-blue-300"
              style={{
                left: `${aCiL}%`,
                width: `${Math.max(0.5, aCiU! - aCiL!)}%`,
                top: 0,
              }}
              title={`${providerA!.label}: plausible range ${formatValue(providerA!.ciLower!, unit)} to ${formatValue(providerA!.ciUpper!, unit)}`}
            />
          )}
          {showBCi && (
            <div
              className="absolute h-1 rounded-full bg-gray-400"
              style={{
                left: `${bCiL}%`,
                width: `${Math.max(0.5, bCiU! - bCiL!)}%`,
                top: showACi ? 6 : 0,
              }}
              title={`${providerB!.label}: plausible range ${formatValue(providerB!.ciLower!, unit)} to ${formatValue(providerB!.ciUpper!, unit)}`}
            />
          )}
        </div>
      )}

      {/* Histogram */}
      <div className="relative" style={{ height: 72 }}>
        <div className="flex h-full items-end gap-px">
          {counts.map((count, i) => {
            const heightPct = maxCount > 0 ? (count / maxCount) * 100 : 0;
            const binLow = formatValue(bin_edges[i], unit);
            const binHigh = formatValue(bin_edges[i + 1], unit);
            return (
              <div
                key={i}
                className="group relative flex-1 cursor-default rounded-t-sm bg-gray-200 transition-opacity hover:z-10 hover:opacity-80"
                style={{
                  height: `${heightPct}%`,
                  minHeight: count > 0 ? 2 : 0,
                }}
              >
                <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1.5 hidden -translate-x-1/2 whitespace-nowrap rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 shadow-sm group-hover:block">
                  {binLow} to {binHigh}: {count} facilit{count !== 1 ? "ies" : "y"}
                </div>
              </div>
            );
          })}
        </div>

        {/* National avg line — orange dashed */}
        <div className="pointer-events-none absolute bottom-0 top-0" style={{ left: `${avgPos}%` }}>
          <div className="h-full border-l-[6px] border-dashed border-orange-400" />
        </div>

        {/* Provider A line — blue dashed */}
        {aPos !== null && (
          <div className="pointer-events-none absolute bottom-0 top-0" style={{ left: `${aPos}%` }}>
            <div className="h-full border-l-[6px] border-dashed border-blue-600" />
          </div>
        )}

        {/* Provider B line — dark gray dashed */}
        {bPos !== null && (
          <div className="pointer-events-none absolute bottom-0 top-0" style={{ left: `${bPos}%` }}>
            <div className="h-full border-l-[6px] border-dashed border-gray-700" />
          </div>
        )}
      </div>

      {/* X-axis: min and max */}
      <div className="relative mt-0.5 border-t border-gray-200" style={{ height: 14 }}>
        <span
          className="absolute left-0 text-xs text-gray-400"
          style={{ transform: "translateY(1px)" }}
        >
          {formatValue(rangeMin, unit)}
        </span>
        <span
          className="absolute right-0 text-xs text-gray-400"
          style={{ transform: "translateY(1px)" }}
        >
          {formatValue(rangeMax, unit)}
        </span>
      </div>

      {/* Direction labels */}
      {(leftLabel || rightLabel) && (
        <div className="mt-0.5 flex justify-between text-xs text-gray-400">
          <span>{leftLabel}</span>
          <span>{rightLabel}</span>
        </div>
      )}

      {/* Legend — provider values + national avg */}
      <div className="mt-2 flex flex-wrap items-center justify-center gap-x-4 gap-y-0.5 text-xs">
        {providerA && (
          <span className="flex items-center gap-1.5 font-medium text-blue-700">
            <span className="inline-block h-3 w-0 border-l-[6px] border-dashed border-blue-600" />
            {formatValue(providerA.value, unit)} · {providerA.label}
            {aPercentile !== null && (
              <span className="font-normal text-gray-400">({aPercentile}th pct)</span>
            )}
          </span>
        )}
        {providerB && (
          <span className="flex items-center gap-1.5 font-medium text-gray-700">
            <span className="inline-block h-3 w-0 border-l-[6px] border-dashed border-gray-700" />
            {formatValue(providerB.value, unit)} · {providerB.label}
            {bPercentile !== null && (
              <span className="font-normal text-gray-400">({bPercentile}th pct)</span>
            )}
          </span>
        )}
        <span className="flex items-center gap-1.5 font-medium text-orange-500">
          <span className="inline-block h-3 w-0 border-l-[6px] border-dashed border-orange-400" />
          {formatValue(effectiveAvg, unit)} ·{" "}
          {hasExplicitNationalAvg ? "National average" : "Distribution mean"}
        </span>
      </div>

      {/* Footer */}
      <p className="mt-1.5 text-center text-xs text-gray-400">
        Distribution across {dist.total.toLocaleString("en-US")} facilities
      </p>
    </div>
  );
}
