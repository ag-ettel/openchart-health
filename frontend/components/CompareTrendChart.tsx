"use client";

// CompareTrendChart — overlaid trend lines for two providers on a single chart.
//
// Shows both providers' trajectories on the same axes so differences in direction
// and magnitude are immediately visible without left-right visual scanning.
//
// Provider A: blue-600 (matches CompareIntervalPlot identity)
// Provider B: gray-700 (matches CompareIntervalPlot identity)
// National avg: orange reference line (matches CompareIntervalPlot)
//
// Simpler than the full TrendChart — no methodology segmentation, no CI bands.
// Those features are available in the per-provider expandable detail if needed.

import { useMemo } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { TrendPeriod } from "@/types/provider";
import { formatValue, periodEndKey } from "@/lib/utils";
import { TREND_MINIMUM_PERIODS_TEXT } from "@/lib/constants";

const COLOR_A = "#2563eb"; // blue-600
const COLOR_B = "#374151"; // gray-700
const NATIONAL_AVG_COLOR = "#f97316"; // orange-500

const MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function shortenPeriod(label: string): string {
  const hospMatch = label.match(/to\s+(\d{4})-(\d{2})/);
  if (hospMatch) return `${MONTH_ABBR[parseInt(hospMatch[2], 10) - 1]} ${hospMatch[1]}`;
  const nhDate = label.match(/^\d{8}-(\d{4})(\d{2})\d{2}$/);
  if (nhDate) return `${MONTH_ABBR[parseInt(nhDate[2], 10) - 1]} ${nhDate[1]}`;
  const nhQtr = label.match(/\d{4}Q\d-(\d{4})(Q\d)/);
  if (nhQtr) return `${nhQtr[2]} ${nhQtr[1]}`;
  const singleQtr = label.match(/^(\d{4})(Q\d)$/);
  if (singleQtr) return `${singleQtr[2]} ${singleQtr[1]}`;
  const parts = label.split(" to ");
  return parts[parts.length - 1] ?? label;
}

interface CompareTrendChartProps {
  trendA: TrendPeriod[] | null;
  trendB: TrendPeriod[] | null;
  trendValidA: boolean;
  trendValidB: boolean;
  trendPeriodCountA: number;
  trendPeriodCountB: number;
  unit: string;
  nationalAvg: number | null;
  nameA: string;
  nameB: string;
  yAxisLabel?: string;
  referenceValue?: number | null;
  referenceLabel?: string;
}

interface ChartRow {
  periodShort: string;
  sortKey: string;
  valueA: number | null;
  valueB: number | null;
  _nameA: string;
  _nameB: string;
}

function CompareTooltip({
  active,
  payload,
  unit,
}: {
  active?: boolean;
  payload?: Array<{ payload?: ChartRow; dataKey?: string; color?: string }>;
  unit: string;
  label?: string;
}): React.JSX.Element | null {
  if (!active || !payload || payload.length === 0) return null;
  const row = payload[0]?.payload;
  if (!row) return null;

  return (
    <div className="rounded border border-gray-200 bg-white px-3 py-2 text-xs shadow-sm">
      <p className="mb-1 font-medium">{row.periodShort}</p>
      {row.valueA !== null && (
        <p className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: COLOR_A }} />
          <span className="text-gray-500">{row._nameA}:</span>{" "}
          <span className="font-semibold">{formatValue(row.valueA, unit)}</span>
        </p>
      )}
      {row.valueB !== null && (
        <p className="flex items-center gap-1.5">
          <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: COLOR_B }} />
          <span className="text-gray-500">{row._nameB}:</span>{" "}
          <span className="font-semibold">{formatValue(row.valueB, unit)}</span>
        </p>
      )}
    </div>
  );
}

export function CompareTrendChart({
  trendA,
  trendB,
  trendValidA,
  trendValidB,
  trendPeriodCountA,
  trendPeriodCountB,
  unit,
  nationalAvg,
  nameA,
  nameB,
  yAxisLabel,
  referenceValue = null,
  referenceLabel,
}: CompareTrendChartProps): React.JSX.Element | null {
  const data = useMemo(() => {
    // Build a unified period axis from both providers' trend data
    const periodMap = new Map<string, { valueA: number | null; valueB: number | null }>();

    const processTrend = (trend: TrendPeriod[] | null, side: "A" | "B") => {
      if (!trend) return;
      for (const t of trend) {
        if (t.period_label === "unknown") continue;
        if (t.suppressed || t.not_reported) continue;
        if (t.numeric_value === null) continue;
        const key = periodEndKey(t.period_label);
        const short = shortenPeriod(t.period_label);
        if (!periodMap.has(key)) {
          periodMap.set(key, { valueA: null, valueB: null });
        }
        const entry = periodMap.get(key)!;
        if (side === "A") {
          entry.valueA = t.numeric_value;
        } else {
          entry.valueB = t.numeric_value;
        }
        // Store the short label on the key for later lookup
        (entry as Record<string, unknown>)._short = short;
      }
    };

    processTrend(trendA, "A");
    processTrend(trendB, "B");

    // Sort by period key (chronological)
    const sorted = Array.from(periodMap.entries())
      .sort(([a], [b]) => a.localeCompare(b));

    return sorted.map(([key, entry]): ChartRow => ({
      periodShort: (entry as Record<string, unknown>)._short as string ?? key,
      sortKey: key,
      valueA: entry.valueA,
      valueB: entry.valueB,
      _nameA: nameA,
      _nameB: nameB,
    }));
  }, [trendA, trendB, nameA, nameB]);

  if (data.length === 0) return null;

  const hasDataA = data.some((d) => d.valueA !== null);
  const hasDataB = data.some((d) => d.valueB !== null);
  if (!hasDataA && !hasDataB) return null;

  const showLineA = trendValidA && trendPeriodCountA >= 3;
  const showLineB = trendValidB && trendPeriodCountB >= 3;

  // Compute y-axis domain
  const allValues = data.flatMap((d) => [d.valueA, d.valueB]).filter((v): v is number => v !== null);
  if (nationalAvg !== null) allValues.push(nationalAvg);
  if (referenceValue !== null) allValues.push(referenceValue);
  const dataMin = Math.min(...allValues);
  const dataMax = Math.max(...allValues);
  const span = dataMax - dataMin;
  const pad = Math.max(span * 0.15, unit === "percent" ? 2 : 0.5);
  let yMin = dataMin - pad;
  let yMax = dataMax + pad;
  if (unit === "percent" || unit === "ratio" || unit === "count" || unit === "score" || unit === "minutes") {
    yMin = Math.max(0, yMin);
  } else if (dataMin >= 0) {
    yMin = Math.max(0, yMin);
  }
  const step = span > 10 ? 5 : span > 2 ? 1 : 0.5;
  yMin = Math.floor(yMin / step) * step;
  yMax = Math.ceil(yMax / step) * step;
  // Hard caps: percentages cannot exceed 0–100
  if (unit === "percent") {
    yMin = Math.max(0, yMin);
    yMax = Math.min(100, yMax);
  }

  return (
    <div className="mt-3">
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart
          data={data}
          margin={{ top: 8, right: 40, bottom: 4, left: yAxisLabel ? 12 : 4 }}
          accessibilityLayer
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
          <XAxis
            dataKey="periodShort"
            tick={{ fontSize: 10, fill: "#6b7280" }}
            tickLine={false}
            axisLine={{ stroke: "#e5e7eb" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#6b7280" }}
            tickLine={false}
            axisLine={false}
            width={yAxisLabel ? 70 : 48}
            domain={[yMin, yMax]}
            tickFormatter={(v: number) => formatValue(v, unit)}
            label={yAxisLabel ? {
              value: yAxisLabel,
              angle: -90,
              position: "insideLeft",
              offset: 10,
              style: { fontSize: 9, fill: "#6b7280", fontWeight: 600, textAnchor: "middle" },
            } : undefined}
          />

          <Tooltip content={<CompareTooltip unit={unit} />} />

          {/* Reference lines */}
          {referenceValue !== null && (
            <ReferenceLine
              y={referenceValue}
              stroke={NATIONAL_AVG_COLOR}
              strokeDasharray="6 3"
              label={{
                value: referenceLabel ?? `${referenceValue}`,
                position: "insideTopRight",
                fontSize: 10,
                fill: NATIONAL_AVG_COLOR,
              }}
            />
          )}
          {nationalAvg !== null && (
            <ReferenceLine
              y={nationalAvg}
              stroke={NATIONAL_AVG_COLOR}
              strokeWidth={1.5}
              strokeDasharray="6 3"
              label={{
                value: `Natl avg: ${formatValue(nationalAvg, unit)}`,
                position: "insideTopRight",
                fontSize: 10,
                fontWeight: 600,
                fill: NATIONAL_AVG_COLOR,
              }}
            />
          )}

          {/* Provider A line */}
          {hasDataA && (
            <Line
              dataKey="valueA"
              type="monotone"
              stroke={showLineA ? COLOR_A : "none"}
              strokeWidth={showLineA ? 2 : 0}
              dot={{ r: 3, fill: COLOR_A, stroke: "#fff", strokeWidth: 1 }}
              activeDot={{ r: 5, fill: COLOR_A, stroke: "#dbeafe", strokeWidth: 2 }}
              connectNulls={false}
              isAnimationActive={false}
              name={nameA}
            />
          )}

          {/* Provider B line */}
          {hasDataB && (
            <Line
              dataKey="valueB"
              type="monotone"
              stroke={showLineB ? COLOR_B : "none"}
              strokeWidth={showLineB ? 2 : 0}
              dot={{ r: 3, fill: COLOR_B, stroke: "#fff", strokeWidth: 1 }}
              activeDot={{ r: 5, fill: COLOR_B, stroke: "#d1d5db", strokeWidth: 2 }}
              connectNulls={false}
              isAnimationActive={false}
              name={nameB}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-1 flex flex-wrap items-center justify-center gap-x-5 gap-y-1 text-xs text-gray-500">
        {hasDataA && (
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLOR_A }} />
            {nameA}
          </span>
        )}
        {hasDataB && (
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLOR_B }} />
            {nameB}
          </span>
        )}
        {nationalAvg !== null && (
          <span className="flex items-center gap-1.5 text-orange-500">
            <svg className="h-2.5 w-2.5" viewBox="0 0 10 10"><polygon points="5,0 10,5 5,10 0,5" fill="#f97316" /></svg>
            Natl avg
          </span>
        )}
      </div>

      {/* Trend validity warnings */}
      {(!trendValidA || !trendValidB) && (
        <div className="mt-1 space-y-0.5">
          {!trendValidA && (
            <p className="text-xs text-gray-400">{nameA}: {TREND_MINIMUM_PERIODS_TEXT(trendPeriodCountA)}</p>
          )}
          {!trendValidB && (
            <p className="text-xs text-gray-400">{nameB}: {TREND_MINIMUM_PERIODS_TEXT(trendPeriodCountB)}</p>
          )}
        </div>
      )}
    </div>
  );
}
