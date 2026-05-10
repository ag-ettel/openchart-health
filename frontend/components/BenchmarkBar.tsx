// Neutral horizontal position indicator showing a provider's value relative to
// national and state averages. No directional color encoding (DEC-030).
//
// National average is the primary reference axis (center). State average renders
// as a secondary marker. CI span renders as a translucent neutral overlay.
// All rendering in gray — the consumer sees numeric position and draws conclusions.
//
// Guard at call site (MeasureCard): do not render when:
//   - national_avg is null
//   - suppressed is true
//   - not_reported is true

import { formatValue } from "@/lib/utils";

interface BenchmarkBarProps {
  value: number;
  nationalAvg: number;
  stateAvg: number | null;
  unit: string;
  ciLower: number | null;
  ciUpper: number | null;
}

// Computes a percentage position on the bar axis given a value and the axis range.
function toPercent(val: number, min: number, max: number): number {
  if (max === min) return 50;
  return Math.max(0, Math.min(100, ((val - min) / (max - min)) * 100));
}

export function BenchmarkBar({
  value,
  nationalAvg,
  stateAvg,
  unit,
  ciLower,
  ciUpper,
}: BenchmarkBarProps): React.JSX.Element {
  // Determine axis range: encompass value, national avg, state avg, and CI bounds.
  const points = [value, nationalAvg];
  if (stateAvg !== null) points.push(stateAvg);
  if (ciLower !== null) points.push(ciLower);
  if (ciUpper !== null) points.push(ciUpper);
  const dataMin = Math.min(...points);
  const dataMax = Math.max(...points);
  // Add 10% padding on each side so markers aren't flush with edges.
  const padding = (dataMax - dataMin) * 0.1 || 1;
  const axisMin = dataMin - padding;
  const axisMax = dataMax + padding;

  const valuePct = toPercent(value, axisMin, axisMax);
  const nationalPct = toPercent(nationalAvg, axisMin, axisMax);
  const statePct = stateAvg !== null ? toPercent(stateAvg, axisMin, axisMax) : null;
  const ciLowerPct = ciLower !== null ? toPercent(ciLower, axisMin, axisMax) : null;
  const ciUpperPct = ciUpper !== null ? toPercent(ciUpper, axisMin, axisMax) : null;
  const hasCI = ciLowerPct !== null && ciUpperPct !== null;

  // Plain-language summary for screen readers — exposes the same comparison
  // sighted users see (value, national avg, state avg, CI bounds when present).
  const stateClause = stateAvg !== null ? `, state average ${formatValue(stateAvg, unit)}` : "";
  const ciClause = hasCI
    ? `; credible interval from ${formatValue(ciLower!, unit)} to ${formatValue(ciUpper!, unit)}`
    : "";
  const ariaSummary = `Value ${formatValue(value, unit)} compared to national average ${formatValue(nationalAvg, unit)}${stateClause}${ciClause}.`;

  return (
    <figure className="my-2" aria-label={ariaSummary}>
      <figcaption className="sr-only">{ariaSummary}</figcaption>
      {/* Bar track */}
      <div className="relative h-4 w-full rounded bg-gray-100" role="presentation">
        {/* CI span — translucent neutral overlay */}
        {hasCI && (
          <div
            className="absolute top-0 h-full rounded bg-gray-300/40"
            style={{
              left: `${ciLowerPct}%`,
              width: `${ciUpperPct! - ciLowerPct!}%`,
            }}
            aria-label={`Credible interval: ${formatValue(ciLower!, unit)} to ${formatValue(ciUpper!, unit)}`}
          />
        )}

        {/* National average reference line */}
        <div
          className="absolute top-0 h-full w-px bg-gray-400"
          style={{ left: `${nationalPct}%` }}
          aria-label={`National average: ${formatValue(nationalAvg, unit)}`}
        />

        {/* State average secondary marker */}
        {statePct !== null && (
          <div
            className="absolute top-0 h-full w-px border-l border-dashed border-gray-400"
            style={{ left: `${statePct}%` }}
            aria-label={`State average: ${formatValue(stateAvg!, unit)}`}
          />
        )}

        {/* Provider value marker */}
        <div
          className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border border-gray-400 bg-gray-700"
          style={{ left: `${valuePct}%` }}
          aria-label={`Provider value: ${formatValue(value, unit)}`}
        />
      </div>

      {/* Labels below bar */}
      <div className="mt-1 flex justify-between text-[10px] text-gray-500">
        <span>Natl avg: {formatValue(nationalAvg, unit)}</span>
        {stateAvg !== null && (
          <span>State avg: {formatValue(stateAvg, unit)}</span>
        )}
      </div>
    </figure>
  );
}
