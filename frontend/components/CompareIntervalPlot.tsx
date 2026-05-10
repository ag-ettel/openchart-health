// CompareIntervalPlot — paired horizontal bars for side-by-side provider
// comparison on a shared scale. Visual language matches CompareStaffing,
// CompareInspectionSummary, and OwnershipGroupStats.
//
// Each row: identity dot + name, a bar from the zero line to the value, and
// the formatted value at the right. Credible interval (when available) shown
// as a thin whisker extending from ci_lower to ci_upper above the value bar
// with caps at each end. National average rendered as its own neutral row
// plus a dashed vertical reference line through the two provider rows so
// position-vs-average is immediate.
//
// Scale handling:
//  - When all values/CIs/national avg are non-negative, zero anchors at the
//    left and bars grow rightward (the common case: percentages, rates).
//  - When any value/CI/national avg is negative (e.g. "days vs expected"
//    measures), the scale is centered symmetrically on zero, with a thin
//    gray zero reference line in the middle. Positive bars grow right of
//    zero, negative bars grow left.
//
// No directional color coding (DEC-030). Provider A is blue (identity),
// Provider B is dark gray (identity), National avg is light gray (reference).

import { formatValue } from "@/lib/utils";

export interface ProviderPoint {
  value: number;
  ciLower: number | null;
  ciUpper: number | null;
  label: string;
  sampleSize: number | null;
  sampleLabel: string;
}

interface CompareIntervalPlotProps {
  providerA: ProviderPoint | null;
  providerB: ProviderPoint | null;
  nationalAvg: number | null;
  unit: string;
}

/** Do the two CI ranges overlap? */
function intervalsOverlap(a: ProviderPoint | null, b: ProviderPoint | null): boolean | null {
  if (!a || !b) return null;
  if (a.ciLower === null || a.ciUpper === null || b.ciLower === null || b.ciUpper === null) return null;
  return a.ciLower <= b.ciUpper && b.ciLower <= a.ciUpper;
}

interface BarRowProps {
  label: string;
  value: number;
  unit: string;
  pos: (v: number) => number;
  zeroPos: number;
  ciLower: number | null;
  ciUpper: number | null;
  identity: "A" | "B" | "nat";
}

function BarRow({ label, value, unit, pos, zeroPos, ciLower, ciUpper, identity }: BarRowProps): React.JSX.Element {
  const barColor = identity === "A" ? "bg-blue-500" : identity === "B" ? "bg-gray-600" : "bg-gray-300";
  const dotColor = identity === "A" ? "bg-blue-600" : identity === "B" ? "bg-gray-700" : "bg-gray-400";
  const ciStroke = identity === "A" ? "#2563eb" : "#374151";

  // Bar runs from the zero line to the value position. For negative values
  // the bar extends leftward; for positive values it extends rightward.
  const valuePos = pos(value);
  const barLeft = Math.min(zeroPos, valuePos);
  const barWidth = Math.abs(valuePos - zeroPos);

  const ciLowerPos = ciLower !== null ? pos(ciLower) : null;
  const ciUpperPos = ciUpper !== null ? pos(ciUpper) : null;
  const showCi = identity !== "nat" && ciLowerPos !== null && ciUpperPos !== null;

  const labelColorCls = identity === "A"
    ? "text-blue-700"
    : identity === "B"
      ? "text-gray-700"
      : "text-gray-500";

  // Two stacked tracks inside the row so the CI whisker can never be
  // obscured by the bar fill: top 10px holds the whisker, bottom 16px
  // holds the bar. Total inner height 26px.
  return (
    <div className="flex items-center gap-2">
      <span className={`w-32 shrink-0 truncate text-xs ${labelColorCls}`} title={label}>
        <span className={`mr-1 inline-block h-2 w-2 rounded-full align-middle ${dotColor}`} />
        {label}
      </span>
      <div className="relative h-[26px] flex-1">
        {/* Whisker track — top 10px, dedicated space above the bar */}
        {showCi && (
          <svg
            className="pointer-events-none absolute left-0 top-0 h-[10px] w-full"
            preserveAspectRatio="none"
            viewBox="0 0 100 10"
          >
            <line
              x1={ciLowerPos!} y1={6} x2={ciUpperPos!} y2={6}
              stroke={ciStroke} strokeWidth={1} vectorEffect="non-scaling-stroke"
            />
            <line
              x1={ciLowerPos!} y1={2} x2={ciLowerPos!} y2={9}
              stroke={ciStroke} strokeWidth={1} vectorEffect="non-scaling-stroke"
            />
            <line
              x1={ciUpperPos!} y1={2} x2={ciUpperPos!} y2={9}
              stroke={ciStroke} strokeWidth={1} vectorEffect="non-scaling-stroke"
            />
          </svg>
        )}
        {/* Bar track — bottom 16px, with neutral gray rail */}
        <div className="absolute bottom-0 left-0 h-4 w-full rounded bg-gray-50">
          <div
            className={`absolute top-0 h-4 rounded ${barColor}`}
            style={{ left: `${barLeft}%`, width: `${barWidth}%`, transition: "left 0.4s ease, width 0.4s ease" }}
          />
        </div>
      </div>
      <span className={`w-20 shrink-0 text-right text-sm tabular-nums ${identity === "nat" ? "text-gray-500" : "font-semibold text-gray-800"}`}>
        {formatValue(value, unit)}
      </span>
    </div>
  );
}

export function CompareIntervalPlot({
  providerA,
  providerB,
  nationalAvg,
  unit,
}: CompareIntervalPlotProps): React.JSX.Element | null {
  if (!providerA && !providerB) return null;
  const aVal = providerA?.value ?? null;
  const bVal = providerB?.value ?? null;
  if (aVal === null && bVal === null) return null;

  // All numeric points that need to fit on the shared scale (values, CI
  // bounds, national avg). CI lower bounds matter here too — for measures
  // that can swing negative they pull the lower edge of the domain.
  const candidates = [
    aVal, bVal, nationalAvg,
    providerA?.ciLower ?? null, providerA?.ciUpper ?? null,
    providerB?.ciLower ?? null, providerB?.ciUpper ?? null,
  ].filter((v): v is number => v !== null);

  const dataMin = Math.min(...candidates);
  const dataMax = Math.max(...candidates);
  const hasNegative = dataMin < 0;

  // For measures that can swing positive or negative (e.g. days vs. expected,
  // O/E differences), use a symmetric domain centered on zero so the zero
  // line sits in the middle and positive vs. negative reads at a glance.
  // For non-negative measures, keep zero anchored at the left.
  let pos: (v: number) => number;
  let zeroPos: number;
  if (hasNegative) {
    const absMax = Math.max(Math.abs(dataMin), Math.abs(dataMax));
    const scale = (absMax > 0 ? absMax : 1) * 1.15;
    zeroPos = 50;
    pos = (v: number) => Math.max(0, Math.min(100, 50 + (v / scale) * 50));
  } else {
    const scale = (dataMax > 0 ? dataMax : 1) * 1.15;
    zeroPos = 0;
    pos = (v: number) => Math.max(0, Math.min(100, (v / scale) * 100));
  }

  const overlap = intervalsOverlap(providerA, providerB);
  const natPos = nationalAvg !== null ? pos(nationalAvg) : null;
  const hasAnyCi =
    (providerA?.ciLower !== null && providerA?.ciUpper !== null) ||
    (providerB?.ciLower !== null && providerB?.ciUpper !== null);

  // Plain-language summary for AT users — exposes the value-vs-value-vs-natl
  // comparison and the CI overlap conclusion in a single sentence.
  const aSummary = providerA && aVal !== null
    ? `${providerA.label}: ${formatValue(aVal, unit)}${providerA.ciLower !== null && providerA.ciUpper !== null
      ? ` (interval ${formatValue(providerA.ciLower, unit)} to ${formatValue(providerA.ciUpper, unit)})` : ""}`
    : null;
  const bSummary = providerB && bVal !== null
    ? `${providerB.label}: ${formatValue(bVal, unit)}${providerB.ciLower !== null && providerB.ciUpper !== null
      ? ` (interval ${formatValue(providerB.ciLower, unit)} to ${formatValue(providerB.ciUpper, unit)})` : ""}`
    : null;
  const natSummary = nationalAvg !== null ? `National average: ${formatValue(nationalAvg, unit)}` : null;
  const overlapSummary = overlap === true
    ? "Plausible ranges overlap; the difference may not be meaningful."
    : overlap === false
      ? "Plausible ranges do not overlap, suggesting a meaningful difference."
      : null;
  const ariaSummary = [aSummary, bSummary, natSummary, overlapSummary]
    .filter(Boolean)
    .join(". ");

  return (
    <figure className="mt-3" aria-label={ariaSummary}>
      <figcaption className="sr-only">{ariaSummary}</figcaption>
      <div className="relative space-y-1.5">
        {/* Zero reference line — only when the scale spans across zero, so
            negative vs. positive bars are anchored to a visible baseline. */}
        {hasNegative && (
          <div
            className="pointer-events-none absolute inset-y-0 w-px bg-gray-300"
            style={{ left: `calc(8.5rem + ((100% - 8.5rem - 5rem) * ${zeroPos} / 100))` }}
            aria-hidden
          />
        )}
        {/* Dashed vertical reference line at national avg, spanning the
            provider rows but not the national row (which already shows the
            value as its own bar). Bottom inset matches the row height
            (h-[26px]) plus the inter-row gap (space-y-1.5 = 0.375rem). */}
        {natPos !== null && (
          <div
            className="pointer-events-none absolute bottom-[calc(26px+0.375rem)] top-0 w-px border-l border-dashed border-orange-400"
            style={{ left: `calc(8.5rem + ((100% - 8.5rem - 5rem) * ${natPos} / 100))` }}
            aria-hidden
          />
        )}

        {providerA && aVal !== null && (
          <BarRow
            label={providerA.label}
            value={aVal}
            unit={unit}
            pos={pos}
            zeroPos={zeroPos}
            ciLower={providerA.ciLower}
            ciUpper={providerA.ciUpper}
            identity="A"
          />
        )}
        {providerB && bVal !== null && (
          <BarRow
            label={providerB.label}
            value={bVal}
            unit={unit}
            pos={pos}
            zeroPos={zeroPos}
            ciLower={providerB.ciLower}
            ciUpper={providerB.ciUpper}
            identity="B"
          />
        )}
        {nationalAvg !== null && (
          <BarRow
            label="National avg"
            value={nationalAvg}
            unit={unit}
            pos={pos}
            zeroPos={zeroPos}
            ciLower={null}
            ciUpper={null}
            identity="nat"
          />
        )}
      </div>

      {/* CI legend */}
      {hasAnyCi && (
        <p className="mt-2 text-[10px] text-gray-600">
          Whiskers above each bar show the 95% credible interval where available.
        </p>
      )}

      {/* Overlap interpretation — preserves the existing template-3-style framing */}
      {overlap === true && (
        <p className="mt-1 text-xs text-gray-500">
          The plausible ranges overlap — the difference between these facilities may not be meaningful given the available data.
        </p>
      )}
      {overlap === false && (
        <p className="mt-1 text-xs text-gray-500">
          The plausible ranges do not overlap, suggesting a meaningful difference between these facilities on this measure.
        </p>
      )}
    </figure>
  );
}
