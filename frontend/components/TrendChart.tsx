"use client";

// TrendChart — temporal trajectory of a measure across reporting periods.
//
// Design:
//   - X-axis shows period end date only (simplified from full range)
//   - CI shaded band when per-period CI available; fallback to current-period-only
//   - Custom tooltip shows value, cases, interval estimate, CMS comparison
//   - Segmented lines break at methodology changes (Rule 11)
//   - Rule 12: < 3 periods → dots only, no connecting line
//   - Suppressed/not-reported periods create natural gaps
//   - O/E reference line at 1.0 for infection/ratio measures
//   - No directional color encoding (DEC-030)

import { useMemo } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
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

const DATA_COLOR = "#2563eb";
const DATA_COLOR_LIGHT = "#93c5fd";
const NATIONAL_AVG_COLOR = "#9ca3af";
const STATE_AVG_COLOR = "#d1d5db";
const CI_BAND_COLOR = "#dbeafe";

interface TrendChartProps {
  trend: TrendPeriod[] | null;
  trendValid: boolean;
  trendPeriodCount: number;
  unit: string;
  nationalAvg: number | null;
  stateAvg: number | null;
  showOEReference?: boolean;
  /** Show a custom reference line at a specific value (e.g. 0 for EDAC, 1.0 for ratios) */
  referenceValue?: number | null;
  referenceLabel?: string;
  ciLower?: number | null;
  ciUpper?: number | null;
  /** Label for sample count in tooltip (e.g. "Patients", "Procedures") */
  sampleLabelText?: string;
  /** Zoom y-axis to data range instead of starting from 0. Better for trends where
   *  data lives in a narrow band (e.g. 70-80%). Uses distribution range as baseline,
   *  expanded if hospital history exceeds it. */
  zoomToData?: boolean;
  /** Distribution min/max for anchoring the zoomed y-axis to national context */
  distributionMin?: number | null;
  distributionMax?: number | null;
  /** CMS direction for the visual arrow indicator */
  direction?: "LOWER_IS_BETTER" | "HIGHER_IS_BETTER" | null;
  /** Y-axis label for the chart */
  yAxisLabel?: string;
}

interface ChartPoint {
  period: string;
  periodShort: string;
  value: number | null;
  ciLow: number | null;
  ciHigh: number | null;
  cases: number | null;
  cmsComparison: string | null;
  suppressed: boolean;
  notReported: boolean;
  methodologyChange: boolean;
}

const MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function shortenPeriod(label: string): string {
  const match = label.match(/to\s+(\d{4})-(\d{2})/);
  if (match) {
    const [, y, m] = match;
    return `${MONTH_ABBR[parseInt(m, 10) - 1]} ${y}`;
  }
  const parts = label.split(" to ");
  return parts[parts.length - 1] ?? label;
}

const CMS_COMPARISON_SHORT: Record<string, string> = {
  BETTER: "Better than national",
  NO_DIFFERENT: "No different from national",
  WORSE: "Worse than national",
  TOO_FEW_CASES: "Too few cases to compare",
  NOT_AVAILABLE: "Comparison not available",
};

function buildSegmentedData(points: ChartPoint[]): {
  data: Record<string, unknown>[];
  segmentKeys: string[];
} {
  const segmentIndex: number[] = [];
  let seg = 0;
  for (let i = 0; i < points.length; i++) {
    if (i > 0 && points[i].methodologyChange) seg++;
    segmentIndex.push(seg);
  }
  const segmentCount = seg + 1;
  const segmentKeys = Array.from({ length: segmentCount }, (_, i) => `seg_${i}`);

  const data = points.map((p, i) => {
    const row: Record<string, unknown> = {
      period: p.period,
      periodShort: p.periodShort,
      _suppressed: p.suppressed,
      _notReported: p.notReported,
      _methodologyChange: p.methodologyChange,
      _hasValue: p.value !== null,
      _cases: p.cases,
      _ciLow: p.ciLow,
      _ciHigh: p.ciHigh,
      _cmsComparison: p.cmsComparison,
      ciBand: (p.ciLow !== null && p.ciHigh !== null && p.value !== null)
        ? [p.ciLow, p.ciHigh]
        : null,
    };
    for (let s = 0; s < segmentCount; s++) {
      row[segmentKeys[s]] = segmentIndex[i] === s ? p.value : null;
    }
    return row;
  });

  return { data, segmentKeys };
}

function CustomTooltip({
  active,
  payload,
  unit,
  sampleLabelText = "Cases",
}: {
  active?: boolean;
  payload?: Array<{ payload?: Record<string, unknown> }>;
  unit: string;
  label?: string;
  sampleLabelText?: string;
}): React.JSX.Element | null {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0]?.payload;
  if (!point) return null;

  const period = point.period as string;
  const suppressed = point._suppressed as boolean;
  const notReported = point._notReported as boolean;
  const cases = point._cases as number | null;
  const ciLow = point._ciLow as number | null;
  const ciHigh = point._ciHigh as number | null;
  const cmsComp = point._cmsComparison as string | null;

  let value: number | null = null;
  for (const [k, v] of Object.entries(point)) {
    if (k.startsWith("seg_") && v !== null && typeof v === "number") {
      value = v;
      break;
    }
  }

  if (suppressed) {
    return (
      <div className="rounded border border-gray-200 bg-white px-3 py-2 text-xs shadow-sm">
        <p className="font-medium">{period}</p>
        <p className="text-gray-500">Suppressed by CMS</p>
      </div>
    );
  }
  if (notReported) {
    return (
      <div className="rounded border border-gray-200 bg-white px-3 py-2 text-xs shadow-sm">
        <p className="font-medium">{period}</p>
        <p className="text-gray-500">Not reported</p>
      </div>
    );
  }

  return (
    <div className="rounded border border-gray-200 bg-white px-3 py-2 text-xs shadow-sm">
      <p className="mb-1 font-medium">{period}</p>
      {value !== null && (
        <p>
          <span className="text-gray-500">Value:</span>{" "}
          <span className="font-semibold">{formatValue(value, unit)}</span>
        </p>
      )}
      {ciLow !== null && ciHigh !== null && (
        <p>
          <span className="text-gray-500">Interval:</span>{" "}
          {formatValue(ciLow, unit)} to {formatValue(ciHigh, unit)}
        </p>
      )}
      {cases !== null && (
        <p>
          <span className="text-gray-500">{sampleLabelText}:</span>{" "}
          {cases.toLocaleString("en-US")}
        </p>
      )}
      {cmsComp !== null && (
        <p className="mt-1 text-gray-400">
          CMS assessment: {CMS_COMPARISON_SHORT[cmsComp] ?? cmsComp}
        </p>
      )}
    </div>
  );
}

export function TrendChart({
  trend,
  trendValid,
  trendPeriodCount,
  unit,
  nationalAvg,
  stateAvg,
  showOEReference = false,
  ciLower = null,
  ciUpper = null,
  sampleLabelText = "Cases",
  direction = null,
  yAxisLabel,
  referenceValue = null,
  referenceLabel,
  zoomToData = false,
  distributionMin = null,
  distributionMax = null,
}: TrendChartProps): React.JSX.Element | null {
  const chartData: ChartPoint[] = useMemo(
    () =>
      (trend ?? []).map((t, i, arr) => {
        const isLast = i === arr.length - 1;
        return {
          period: t.period_label,
          periodShort: shortenPeriod(t.period_label),
          value: t.numeric_value,
          ciLow: t.ci_lower ?? (isLast ? ciLower ?? null : null),
          ciHigh: t.ci_upper ?? (isLast ? ciUpper ?? null : null),
          cases: t.sample_size ?? null,
          cmsComparison: t.compared_to_national ?? null,
          suppressed: t.suppressed,
          notReported: t.not_reported,
          methodologyChange: t.methodology_change_flag,
        };
      }),
    [trend, ciLower, ciUpper]
  );

  const { data, segmentKeys } = useMemo(
    () => buildSegmentedData(chartData),
    [chartData]
  );

  if (!trend || trend.length === 0) return null;

  const hasNumericData = chartData.some((p) => p.value !== null);
  if (!hasNumericData) {
    return (
      <p className="mt-2 text-xs text-gray-500">
        Trend visualization is not available for this measure type.
      </p>
    );
  }

  const gapAnnotations = chartData.filter((p) => p.suppressed || p.notReported);
  const methodologyChanges = chartData.filter((p) => p.methodologyChange);
  const showLine = trendValid && trendPeriodCount >= 3;
  const dotRadius = showLine ? 3 : 4;
  const hasAnyCIData = chartData.some((p) => p.ciLow !== null && p.ciHigh !== null);

  // Compute y-axis domain when zooming to data.
  // For bounded measures (percent): use distribution range as baseline.
  // For unbounded measures: use hospital's own history — the histogram
  // already shows national context, the trend chart shows trajectory.
  const yDomain: [number, number] | undefined = (() => {
    if (!zoomToData) return undefined;
    const values = chartData
      .filter((p) => p.value !== null)
      .map((p) => p.value!);
    if (values.length === 0) return undefined;

    const histMin = Math.min(...values);
    const histMax = Math.max(...values);

    let min: number;
    let max: number;

    if (unit === "percent" && distributionMin !== null && distributionMax !== null) {
      // Bounded: use distribution range, expand if hospital exceeds it
      min = Math.min(distributionMin, histMin);
      max = Math.max(distributionMax, histMax);
      // Round to nearest 5%
      min = Math.max(0, Math.floor(min / 5) * 5 - 5);
      max = Math.min(100, Math.ceil(max / 5) * 5 + 5);
    } else {
      // Unbounded: use the full extent of values AND CI bands from trend data
      const ciLows = chartData.filter(p => p.ciLow !== null).map(p => p.ciLow!);
      const ciHighs = chartData.filter(p => p.ciHigh !== null).map(p => p.ciHigh!);
      min = Math.min(histMin, ...ciLows);
      max = Math.max(histMax, ...ciHighs);
      const span = max - min;
      const padding = Math.max(span * 0.1, 2);
      min -= padding;
      max += padding;
      // Round to clean multiples of 5
      min = Math.floor(min / 5) * 5;
      max = Math.ceil(max / 5) * 5;
    }

    return [min, max];
  })();

  return (
    <div className="mt-3">
      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart
          data={data}
          margin={{ top: 8, right: 40, bottom: 4, left: yAxisLabel ? 12 : 4 }}
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
            domain={yDomain}
            tickFormatter={(v: number) => formatValue(v, unit)}
            label={yAxisLabel ? {
              value: yAxisLabel,
              angle: -90,
              position: "insideLeft",
              offset: 10,
              style: { fontSize: 9, fill: "#2563eb", fontWeight: 600, textAnchor: "middle" },
            } : undefined}
          />

          <Tooltip content={<CustomTooltip unit={unit} sampleLabelText={sampleLabelText} />} />

          {hasAnyCIData && (
            <Area
              dataKey="ciBand"
              type="monotone"
              fill={CI_BAND_COLOR}
              stroke="none"
              fillOpacity={0.5}
              isAnimationActive={false}
              connectNulls={false}
            />
          )}

          {/* Reference line: O/E 1.0, or custom value (0 for EDAC, 1.0 for ratios) */}
          {showOEReference && (
            <ReferenceLine
              y={1.0}
              stroke={NATIONAL_AVG_COLOR}
              strokeDasharray="6 3"
              label={{
                value: "1.0 = expected",
                position: "insideTopRight",
                fontSize: 10,
                fill: NATIONAL_AVG_COLOR,
              }}
            />
          )}
          {!showOEReference && referenceValue !== null && (
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
              strokeDasharray="6 3"
              label={{
                value: `Natl avg: ${formatValue(nationalAvg, unit)}`,
                position: "insideTopRight",
                fontSize: 10,
                fill: NATIONAL_AVG_COLOR,
              }}
            />
          )}

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

          {segmentKeys.map((key) => (
            <Line
              key={key}
              dataKey={key}
              type="monotone"
              stroke={showLine ? DATA_COLOR : "none"}
              strokeWidth={showLine ? 1.5 : 0}
              dot={{ r: dotRadius, fill: DATA_COLOR, stroke: DATA_COLOR, strokeWidth: 1 }}
              activeDot={{ r: dotRadius + 2, fill: DATA_COLOR, stroke: DATA_COLOR_LIGHT, strokeWidth: 2 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>

      <p className="mt-0.5 text-center text-xs font-semibold text-blue-600">Period end date</p>

      <div className="mt-1 space-y-1">
        {!trendValid && (
          <p className="text-xs text-gray-500">{TREND_MINIMUM_PERIODS_TEXT(trendPeriodCount)}</p>
        )}

        {/* Collapse multiple suppressed/not-reported into summary lines */}
        {(() => {
          const suppressed = gapAnnotations.filter((g) => g.suppressed);
          const notReported = gapAnnotations.filter((g) => !g.suppressed);
          return (
            <>
              {suppressed.length === 1 && (
                <p className="text-xs text-gray-500">
                  <span className="font-medium">{suppressed[0].periodShort}:</span> Value suppressed by CMS.
                </p>
              )}
              {suppressed.length > 1 && (
                <p className="text-xs text-gray-500">
                  {suppressed.length} periods suppressed by CMS ({suppressed[0].periodShort} – {suppressed[suppressed.length - 1].periodShort}).
                </p>
              )}
              {notReported.length === 1 && (
                <p className="text-xs text-gray-500">
                  <span className="font-medium">{notReported[0].periodShort}:</span> Data not reported for this period.
                </p>
              )}
              {notReported.length > 1 && (
                <p className="text-xs text-gray-500">
                  {notReported.length} periods not reported ({notReported[0].periodShort} – {notReported[notReported.length - 1].periodShort}).
                </p>
              )}
            </>
          );
        })()}

        {methodologyChanges.map((mc) => (
          <p key={mc.period} className="text-xs text-gray-500">
            <span className="font-medium">{mc.periodShort}:</span>{" "}
            {METHODOLOGY_CHANGE_FOOTNOTE_TEXT}
          </p>
        ))}
      </div>
    </div>
  );
}
