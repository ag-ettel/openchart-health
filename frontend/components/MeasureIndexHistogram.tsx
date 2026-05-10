// Distribution histogram for /filter-explore. Bins all reported numeric values
// for a measure across all reporting providers (after filters apply). Reuses
// the same neutral-gray bar treatment as DistributionHistogram — no directional
// color coding (DEC-030).

"use client";

import { useMemo } from "react";
import {
  FILTER_EXPLORE_DISTRIBUTION_CAPTION,
  type FilterExploreProviderType,
} from "@/lib/constants";
import type { MeasureIndexRow } from "@/lib/measure-index";
import { formatValue } from "@/lib/utils";

interface MeasureIndexHistogramProps {
  rows: MeasureIndexRow[];
  unit: string;
  nationalAvg: number | null;
  binCount?: number;
  providerType?: FilterExploreProviderType;
}

interface Bin {
  lo: number;
  hi: number;
  count: number;
}

export function MeasureIndexHistogram({
  rows,
  unit,
  nationalAvg,
  binCount = 25,
  providerType = "HOSPITAL",
}: MeasureIndexHistogramProps): React.JSX.Element | null {
  const { bins, total, min, max } = useMemo(() => {
    const values = rows
      .filter((r) => !r.suppressed && !r.not_reported && r.numeric_value !== null)
      .map((r) => r.numeric_value as number);
    if (values.length === 0) return { bins: [] as Bin[], total: 0, min: 0, max: 0 };

    const lo = Math.min(...values);
    const hi = Math.max(...values);
    if (lo === hi) {
      return { bins: [{ lo, hi, count: values.length }], total: values.length, min: lo, max: hi };
    }
    const span = hi - lo;
    const step = span / binCount;
    const out: Bin[] = [];
    for (let i = 0; i < binCount; i++) {
      out.push({ lo: lo + i * step, hi: lo + (i + 1) * step, count: 0 });
    }
    for (const v of values) {
      const idx = Math.min(binCount - 1, Math.floor((v - lo) / step));
      out[idx].count++;
    }
    return { bins: out, total: values.length, min: lo, max: hi };
  }, [rows, binCount]);

  if (total === 0) return null;
  const maxCount = Math.max(...bins.map((b) => b.count));
  const span = max - min;

  const toPercent = (v: number): number => {
    if (span === 0) return 50;
    return Math.max(0, Math.min(100, ((v - min) / span) * 100));
  };

  const avgPos = nationalAvg !== null ? toPercent(nationalAvg) : null;

  return (
    <div className="my-4">
      <div className="relative" style={{ height: 64 }}>
        <div className="flex h-full items-end gap-px">
          {bins.map((b, i) => {
            const heightPct = maxCount > 0 ? (b.count / maxCount) * 100 : 0;
            const lo = formatValue(b.lo, unit);
            const hi = formatValue(b.hi, unit);
            return (
              <div
                key={i}
                className="group relative flex-1 cursor-default rounded-t-sm bg-gray-300 transition-opacity hover:opacity-80"
                style={{
                  height: `${heightPct}%`,
                  minHeight: b.count > 0 ? 2 : 0,
                }}
              >
                <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 shadow-sm group-hover:block">
                  {lo} to {hi}: {b.count} hospital{b.count !== 1 ? "s" : ""}
                </div>
              </div>
            );
          })}
        </div>
        {avgPos !== null && (
          <div className="absolute top-0 bottom-0" style={{ left: `${avgPos}%` }}>
            <div className="h-full border-l-2 border-dashed border-orange-400" />
          </div>
        )}
      </div>
      <div className="relative mt-0.5 border-t border-gray-200" style={{ height: 14 }}>
        <span className="absolute left-0 text-xs text-gray-400" style={{ transform: "translateY(1px)" }}>
          {formatValue(min, unit)}
        </span>
        <span className="absolute right-0 text-xs text-gray-400" style={{ transform: "translateY(1px)" }}>
          {formatValue(max, unit)}
        </span>
      </div>
      <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-gray-500">
          {FILTER_EXPLORE_DISTRIBUTION_CAPTION(total, providerType)}
        </p>
        {nationalAvg !== null && (
          <span className="flex items-center gap-1 text-xs text-orange-500">
            <span className="inline-block h-3 w-0 border-l-2 border-dashed border-orange-400" />
            {formatValue(nationalAvg, unit)} · National average
          </span>
        )}
      </div>
    </div>
  );
}
