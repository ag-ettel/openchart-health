"use client";

// TrendChart — temporal trajectory of a measure across reporting periods.
//
// Design principles:
//   - Antifragile: handles every edge case CMS data produces as a first-class
//     rendering path, not an afterthought. Suppressed periods, non-reporting gaps,
//     methodology changes, and sub-threshold period counts all render explicitly.
//   - Fail loudly: categorical measures (score_text only, no numeric_value) get a
//     clear message rather than an empty chart.
//   - Data Integrity Rule 12: < 3 periods → individual observations (dots only, no
//     connecting line, no trend language). The floor is enforced here.
//   - Methodology change (footnote 29 / Rule 11): line breaks between segments.
//     The two sides of a methodology change are not visually connected because
//     the values are not methodologically comparable.
//   - Suppressed / not-reported: natural gaps in the line. The gap IS the signal;
//     annotations below the chart explain why. Absence displayed as presence.
//   - No directional color encoding (DEC-030). Data line and dots are a consistent
//     neutral blue — visually distinct from gray reference lines, with no
//     better/worse implication.
//   - National and state averages render as horizontal reference lines so the
//     consumer can see trajectory relative to benchmarks.
//
// Requires Recharts (client component).

import { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { TrendPeriod } from "@/types/provider";
import { formatValue } from "@/lib/utils";
import {
  TREND_MINIMUM_PERIODS_TEXT,
  METHODOLOGY_CHANGE_FOOTNOTE_TEXT,
} from "@/lib/constants";

// --- Constants ---

// Data line color: neutral blue. Does not encode direction or quality judgment.
// Visually distinct from the gray reference lines and chart furniture.
const DATA_COLOR = "#2563eb"; // blue-600
const DATA_COLOR_LIGHT = "#93c5fd"; // blue-300 — active dot ring
const NATIONAL_AVG_COLOR = "#9ca3af"; // gray-400
const STATE_AVG_COLOR = "#d1d5db"; // gray-300

// --- Types ---

interface TrendChartProps {
  trend: TrendPeriod[] | null;
  trendValid: boolean; // true when 3+ periods (Rule 12)
  trendPeriodCount: number;
  unit: string;
  nationalAvg: number | null;
  stateAvg: number | null;
}

interface ChartPoint {
  period: string;
  value: number | null;
  suppressed: boolean;
  notReported: boolean;
  methodologyChange: boolean;
}

// --- Data preparation ---

// Assigns each point to a methodology segment. A new segment starts at every
// point where methodology_change_flag is true. Each segment becomes its own
// <Line> so Recharts naturally breaks the visual connection at boundaries.
function buildSegmentedData(points: ChartPoint[]): {
  data: Record<string, unknown>[];
  segmentKeys: string[];
} {
  // Determine segment index for each point.
  const segmentIndex: number[] = [];
  let seg = 0;
  for (let i = 0; i < points.length; i++) {
    if (i > 0 && points[i].methodologyChange) {
      seg++;
    }
    segmentIndex.push(seg);
  }

  const segmentCount = seg + 1;
  const segmentKeys = Array.from(
    { length: segmentCount },
    (_, i) => `seg_${i}`
  );

  // Build unified data array. Each point carries its value under its segment's
  // key and null under all other segment keys. Recharts with connectNulls=false
  // renders each segment as an independent line.
  const data = points.map((p, i) => {
    const row: Record<string, unknown> = {
      period: p.period,
      _suppressed: p.suppressed,
      _notReported: p.notReported,
      _methodologyChange: p.methodologyChange,
      _hasValue: p.value !== null,
    };
    for (let s = 0; s < segmentCount; s++) {
      row[segmentKeys[s]] = segmentIndex[i] === s ? p.value : null;
    }
    return row;
  });

  return { data, segmentKeys };
}

// --- Component ---

export function TrendChart({
  trend,
  trendValid,
  trendPeriodCount,
  unit,
  nationalAvg,
  stateAvg,
}: TrendChartProps): JSX.Element | null {
  // All hooks must run unconditionally (React rules of hooks).
  const chartData: ChartPoint[] = useMemo(
    () =>
      (trend ?? []).map((t) => ({
        period: t.period_label,
        value: t.numeric_value,
        suppressed: t.suppressed,
        notReported: t.not_reported,
        methodologyChange: t.methodology_change_flag,
      })),
    [trend]
  );

  const { data, segmentKeys } = useMemo(
    () => buildSegmentedData(chartData),
    [chartData]
  );

  // Guards — after all hooks.
  if (!trend || trend.length === 0) return null;

  const hasNumericData = chartData.some((p) => p.value !== null);
  if (!hasNumericData) {
    return (
      <p className="mt-2 text-xs text-gray-500">
        Trend visualization is not available for this measure type.
      </p>
    );
  }

  // Collect annotations for rendering below the chart.
  const gapAnnotations = chartData.filter((p) => p.suppressed || p.notReported);
  const methodologyChanges = chartData.filter((p) => p.methodologyChange);

  // >= 3 periods: connected line. < 3: dots only (Rule 12).
  const showLine = trendValid && trendPeriodCount >= 3;
  // Larger dots when showing individual observations (< 3 periods).
  const dotRadius = showLine ? 3 : 4;

  return (
    <div className="mt-3">
      <ResponsiveContainer width="100%" height={180}>
        <LineChart
          data={data}
          margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
        >
          {/* Subtle horizontal grid only — no vertical lines, no chart border */}
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#f3f4f6"
            vertical={false}
          />

          <XAxis
            dataKey="period"
            tick={{ fontSize: 10, fill: "#6b7280" }}
            tickLine={false}
            axisLine={{ stroke: "#e5e7eb" }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#6b7280" }}
            tickLine={false}
            axisLine={false}
            width={48}
            tickFormatter={(v: number) => formatValue(v, unit)}
          />

          {/* Tooltip — clean, minimal, matches card styling */}
          <Tooltip
            contentStyle={{
              fontSize: 12,
              border: "1px solid #e5e7eb",
              borderRadius: 6,
              boxShadow: "none",
              padding: "6px 10px",
            }}
            formatter={(value: number | null, _name: string, props: Record<string, unknown>) => {
              const point = props.payload as Record<string, unknown>;
              if (point._suppressed) return ["Suppressed by CMS", "Status"];
              if (point._notReported) return ["Not reported", "Status"];
              if (value === null || value === undefined) return ["-", "Value"];
              return [formatValue(value as number, unit), "Value"];
            }}
            labelFormatter={(label: string) => label}
          />

          {/* National average — dashed reference line, darker gray */}
          {nationalAvg !== null && (
            <ReferenceLine
              y={nationalAvg}
              stroke={NATIONAL_AVG_COLOR}
              strokeDasharray="6 3"
              label={{
                value: `Natl avg: ${formatValue(nationalAvg, unit)}`,
                position: "insideTopRight",
                fontSize: 10,
                fill: NATIONAL_AVG_COLOR,
              }}
            />
          )}

          {/* State average — dotted reference line, lighter gray */}
          {stateAvg !== null && (
            <ReferenceLine
              y={stateAvg}
              stroke={STATE_AVG_COLOR}
              strokeDasharray="3 3"
              label={{
                value: `State avg: ${formatValue(stateAvg, unit)}`,
                position: "insideBottomRight",
                fontSize: 10,
                fill: STATE_AVG_COLOR,
              }}
            />
          )}

          {/* Data — one Line per methodology segment. connectNulls=false creates
              natural gaps at suppressed/not-reported periods. */}
          {segmentKeys.map((key) => (
            <Line
              key={key}
              dataKey={key}
              type="monotone"
              stroke={showLine ? DATA_COLOR : "none"}
              strokeWidth={showLine ? 1.5 : 0}
              dot={{
                r: dotRadius,
                fill: DATA_COLOR,
                stroke: DATA_COLOR,
                strokeWidth: 1,
              }}
              activeDot={{
                r: dotRadius + 2,
                fill: DATA_COLOR,
                stroke: DATA_COLOR_LIGHT,
                strokeWidth: 2,
              }}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {/* Annotations below chart — clean text, not cluttering the chart area */}
      <div className="mt-1 space-y-1">
        {/* Rule 12: trend minimum periods notice */}
        {!trendValid && (
          <p className="text-xs text-gray-500">
            {TREND_MINIMUM_PERIODS_TEXT(trendPeriodCount)}
          </p>
        )}

        {/* Gap annotations: suppressed and not-reported periods */}
        {gapAnnotations.map((gap) => (
          <p key={gap.period} className="text-xs text-gray-500">
            <span className="font-medium">{gap.period}:</span>{" "}
            {gap.suppressed
              ? "Value suppressed by CMS."
              : "Data not reported for this period."}
          </p>
        ))}

        {/* Methodology change annotations (Rule 11) */}
        {methodologyChanges.map((mc) => (
          <p key={mc.period} className="text-xs text-gray-500">
            <span className="font-medium">{mc.period}:</span>{" "}
            {METHODOLOGY_CHANGE_FOOTNOTE_TEXT}
          </p>
        ))}
      </div>
    </div>
  );
}
