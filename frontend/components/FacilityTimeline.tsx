"use client";

// FacilityTimeline — horizontal left-to-right visual timeline combining
// inspection events, penalties, and PBJ staffing trend for nursing home profiles.
//
// Three synchronized panels sharing one time axis:
// 1. Event markers — inspections (circles, severity-colored) and penalties ($ icons)
// 2. Staffing trend — total nurse HPRD line chart
// 3. Shared year axis
//
// Display rules (display-philosophy.md NH-8, DEC-030):
// - J/K/L immediate jeopardy: orange-700 fill
// - G-I actual harm: gray-700 fill
// - D-F potential harm: gray-400 fill
// - A-C minimal harm: gray-300 fill
// - Clean inspections (0 citations): hollow outline circle
// - Penalties: blue-600 $ icon
// - Staffing trend: blue-600 line (neutral, non-directional)

import { useState, useMemo, useRef, useCallback } from "react";
import type { InspectionEvent, Penalty, StaffingTrendPeriod } from "@/types/provider";
import {
  scopeSeverityTier,
  severityPlain,
  scopePlain,
} from "@/lib/constants";

interface FacilityTimelineProps {
  inspectionEvents: InspectionEvent[];
  penalties: Penalty[];
  staffingTrend: StaffingTrendPeriod[] | null;
  standardSurveyDates?: string[] | null;
  /** National average total nurse HPRD for benchmark line. */
  nationalAvgHprd?: number | null;
  /** Force the time axis to a specific range (used by CompareFacilityTimeline
   *  to align two facilities on the same dates). When set, axis padding is
   *  skipped and the range is used verbatim. */
  forcedAxisRange?: { startMs: number; endMs: number } | null;
  /** Hide the legend (used when a parent component renders its own shared legend). */
  hideLegend?: boolean;
}

// ─── Data Model ───────────────────────────────────────────────────────────

interface CitationBlock {
  severityCode: string | null;
  tag: string;
  description: string | null;
  category: string | null;
  isIJ: boolean;
  isComplaint: boolean;
}

interface TimelineEvent {
  date: Date;
  dateStr: string;
  type: "inspection" | "fine" | "payment_denial" | "clean_inspection";
  // Inspection
  citationCount?: number;
  ijCount?: number;
  maxSeverity?: string | null;
  surveyType?: string | null;
  hasComplaint?: boolean;
  citationBlocks?: CitationBlock[];
  // Fine
  fineAmount?: number | null;
  fineChanged?: boolean;
  originalFine?: number | null;
  // Payment denial
  denialStartDate?: Date | null;
  denialEndDate?: Date | null;
  paymentDenialDays?: number | null;
}

function parseDate(iso: string | null): Date | null {
  if (!iso) return null;
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

function formatDateFull(d: Date): string {
  return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

function parseQuarterLabel(label: string): Date | null {
  const m = label.match(/^Q(\d)\s+(\d{4})$/);
  if (!m) return null;
  const q = parseInt(m[1], 10);
  const y = parseInt(m[2], 10);
  const month = (q - 1) * 3 + 1;
  return new Date(y, month, 15);
}

function buildTimelineEvents(
  inspections: InspectionEvent[],
  penalties: Penalty[],
  standardSurveyDates: string[] | null
): TimelineEvent[] {
  const events: TimelineEvent[] = [];
  const datesWithCitations = new Set<string>();

  // Group inspections by survey_date
  const inspByDate = new Map<string, InspectionEvent[]>();
  for (const e of inspections) {
    const key = e.survey_date ?? "";
    if (!key) continue;
    if (!inspByDate.has(key)) inspByDate.set(key, []);
    inspByDate.get(key)!.push(e);
    datesWithCitations.add(key);
  }

  for (const [dateStr, cits] of inspByDate) {
    const d = parseDate(dateStr);
    if (!d) continue;
    const ijCount = cits.filter((c) => c.is_immediate_jeopardy).length;
    const maxSev = cits.reduce((max: string | null, c) => {
      if (!c.scope_severity_code) return max;
      if (!max) return c.scope_severity_code;
      return c.scope_severity_code > max ? c.scope_severity_code : max;
    }, null);

    // Build citation blocks sorted: most severe first (bottom of visual stack)
    const citationBlocks: CitationBlock[] = [...cits]
      .sort((a, b) => {
        // Most severe first (will be at bottom of stack = closest to axis)
        const aCode = a.scope_severity_code ?? "";
        const bCode = b.scope_severity_code ?? "";
        return bCode.localeCompare(aCode);
      })
      .map((c) => ({
        severityCode: c.scope_severity_code,
        tag: c.deficiency_tag,
        description: c.deficiency_description,
        category: c.deficiency_category,
        isIJ: c.is_immediate_jeopardy,
        isComplaint: c.is_complaint_deficiency,
      }));

    events.push({
      date: d,
      dateStr,
      type: "inspection",
      citationCount: cits.length,
      ijCount,
      maxSeverity: maxSev,
      citationBlocks,
      surveyType: cits[0].survey_type,
      hasComplaint: cits.some((c) => c.is_complaint_deficiency),
    });
  }

  // Add clean inspections (standard survey dates with no citations)
  if (standardSurveyDates) {
    for (const dateStr of standardSurveyDates) {
      if (datesWithCitations.has(dateStr)) continue;
      const d = parseDate(dateStr);
      if (!d) continue;
      events.push({
        date: d,
        dateStr,
        type: "clean_inspection",
        citationCount: 0,
        surveyType: "Health",
      });
    }
  }

  // Add fines and payment denials as separate event types
  for (const p of penalties) {
    const d = parseDate(p.penalty_date);
    if (!d) continue;
    if (p.penalty_type === "Payment Denial") {
      const start = parseDate(p.payment_denial_start_date);
      const days = p.payment_denial_length_days ?? 0;
      const end = start ? new Date(start.getTime() + days * 24 * 3600 * 1000) : null;
      events.push({
        date: start ?? d,
        dateStr: p.payment_denial_start_date ?? p.penalty_date ?? "",
        type: "payment_denial",
        denialStartDate: start,
        denialEndDate: end,
        paymentDenialDays: p.payment_denial_length_days,
      });
    } else {
      events.push({
        date: d,
        dateStr: p.penalty_date ?? "",
        type: "fine",
        fineAmount: p.fine_amount,
        fineChanged: p.fine_amount_changed,
        originalFine: p.originally_published_fine_amount,
      });
    }
  }

  events.sort((a, b) => a.date.getTime() - b.date.getTime());
  return events;
}

// ─── Marker colors ────────────────────────────────────────────────────────

function markerFill(event: TimelineEvent): string {
  if (event.type === "fine" || event.type === "payment_denial") return "#2563eb";
  if (event.type === "clean_inspection") return "white";
  const tier = scopeSeverityTier(event.maxSeverity ?? null);
  switch (tier) {
    case "immediate_jeopardy": return "#c2410c";
    case "high": return "#374151";
    case "moderate": return "#9ca3af";
    default: return "#d1d5db";
  }
}

function markerStroke(event: TimelineEvent): string {
  if (event.type === "fine" || event.type === "payment_denial") return "#1d4ed8";
  if (event.type === "clean_inspection") return "#9ca3af";
  const tier = scopeSeverityTier(event.maxSeverity ?? null);
  if (tier === "immediate_jeopardy") return "#9a3412";
  return "#6b7280";
}

// ─── Tooltips ─────────────────────────────────────────────────────────────

const TIER_BADGE_STYLE: Record<string, string> = {
  immediate_jeopardy: "bg-orange-100 text-orange-700",
  high: "bg-gray-300 text-gray-800",
  moderate: "bg-gray-200 text-gray-600",
  low: "bg-gray-100 text-gray-500",
};

/** Tooltip for a single citation block within a stacked inspection. */
function CitationBlockTooltip({ block, event }: { block: CitationBlock; event: TimelineEvent }): React.JSX.Element {
  const tier = scopeSeverityTier(block.severityCode);
  const sev = severityPlain(block.severityCode);
  const scope = scopePlain(block.severityCode);
  const badgeStyle = TIER_BADGE_STYLE[tier] ?? TIER_BADGE_STYLE.low;

  // Cap long CMS descriptions — some are 200+ chars of regulatory language
  const desc = block.description ?? null;
  const descDisplay = desc && desc.length > 100 ? desc.slice(0, 100) + "…" : desc;

  return (
    <div className="max-w-[240px]">
      {/* CMS requirement first — the substance */}
      {descDisplay && (
        <p className="text-[11px] font-medium leading-snug text-gray-700">{descDisplay}</p>
      )}
      {/* Severity badge + short plain description */}
      <div className="mt-1.5 flex items-center gap-1.5">
        {block.severityCode && (
          <span className={`inline-block shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${badgeStyle}`}>
            {block.severityCode}
          </span>
        )}
        <span className="text-[11px] text-gray-500">
          {sev}{scope ? ` · ${scope.toLowerCase()}` : ""}
        </span>
      </div>
      {/* Meta line */}
      <p className="mt-1 text-[10px] text-gray-400">
        {formatDateFull(event.date)} · Tag {block.tag}{block.isComplaint ? " · complaint" : ""}
      </p>
    </div>
  );
}

function CleanInspectionTooltip({ event }: { event: TimelineEvent }): React.JSX.Element {
  return (
    <div>
      <p className="font-semibold text-gray-800">{formatDateFull(event.date)}</p>
      <p className="text-gray-500">{event.surveyType ?? "Health"} inspection</p>
      <p className="mt-1 font-medium text-gray-700">No deficiency citations</p>
    </div>
  );
}

function FineTooltip({ event }: { event: TimelineEvent }): React.JSX.Element {
  return (
    <div>
      <p className="font-medium text-gray-700">CMS Fine</p>
      {event.fineAmount != null && (
        <p className="mt-0.5 font-semibold text-gray-800">
          ${event.fineAmount.toLocaleString("en-US")}
          {event.fineChanged && event.originalFine != null && (
            <span className="ml-1 font-normal text-gray-400">
              (originally ${event.originalFine.toLocaleString("en-US")})
            </span>
          )}
        </p>
      )}
      <p className="mt-0.5 text-[10px] text-gray-400">{formatDateFull(event.date)}</p>
    </div>
  );
}

function DenialTooltip({ event }: { event: TimelineEvent }): React.JSX.Element {
  const startStr = event.denialStartDate ? formatDateFull(event.denialStartDate) : null;
  const endStr = event.denialEndDate ? formatDateFull(event.denialEndDate) : null;
  return (
    <div className="max-w-[240px]">
      <p className="font-medium text-gray-700">Payment Denial</p>
      <p className="mt-0.5 text-[11px] text-gray-600">
        CMS stopped paying for new Medicare/Medicaid admissions
        {event.paymentDenialDays != null && ` for ${event.paymentDenialDays} days`}.
      </p>
      {startStr && (
        <p className="mt-0.5 text-[10px] text-gray-400">
          {startStr}{endStr ? ` — ${endStr}` : ""}
        </p>
      )}
    </div>
  );
}

// ─── Layout constants ─────────────────────────────────────────────────────

const SVG_WIDTH = 700;
const PL = 50;
const PR = 20;
const DRAW_W = SVG_WIDTH - PL - PR;

const MARKER_ZONE_H = 150;  // taller to fit stacked citation blocks
const AXIS_H = 20;
const CHART_LABEL_H = 14; // space for chart title above the chart area
const CHART_H = 80;
const GAP = 4;

const MARKER_Y = MARKER_ZONE_H - 10; // axis line near bottom of marker zone
const BLOCK_W = 18;   // width of each citation block
const BLOCK_H = 15;   // height of each citation block
const BLOCK_GAP = 1;  // gap between stacked blocks

// ─── Shared time axis ─────────────────────────────────────────────────────

interface TimeAxis {
  startMs: number;
  endMs: number;
  totalMs: number;
  toX: (ms: number) => number;
  yearLabels: { year: number; x: number }[];
}

function buildTimeAxis(
  events: TimelineEvent[],
  staffing: StaffingTrendPeriod[] | null,
  forced: { startMs: number; endMs: number } | null = null,
): TimeAxis {
  let startMs: number;
  let endMs: number;

  if (forced) {
    startMs = forced.startMs;
    endMs = forced.endMs;
  } else {
    let minMs = Infinity;
    let maxMs = -Infinity;

    for (const e of events) {
      const ms = e.date.getTime();
      if (ms < minMs) minMs = ms;
      if (ms > maxMs) maxMs = ms;
    }
    if (staffing) {
      for (const s of staffing) {
        const d = parseQuarterLabel(s.quarter_label);
        if (!d) continue;
        const ms = d.getTime();
        if (ms < minMs) minMs = ms;
        if (ms > maxMs) maxMs = ms;
      }
    }

    if (minMs === Infinity) {
      // Only staffing, no events
      minMs = new Date(2020, 0, 1).getTime();
      maxMs = new Date().getTime();
    }

    const rangeMs = maxMs - minMs;
    const padMs = Math.max(rangeMs * 0.04, 60 * 24 * 3600 * 1000);
    startMs = minMs - padMs;
    endMs = maxMs + padMs;
  }

  const totalMs = endMs - startMs;

  const toX = (ms: number) => PL + ((ms - startMs) / totalMs) * DRAW_W;

  const startYear = new Date(startMs).getFullYear();
  const endYear = new Date(endMs).getFullYear();
  const yearLabels: { year: number; x: number }[] = [];
  for (let y = startYear; y <= endYear + 1; y++) {
    const jan1 = new Date(y, 0, 1).getTime();
    if (jan1 >= startMs && jan1 <= endMs) {
      yearLabels.push({ year: y, x: toX(jan1) });
    }
  }

  return { startMs, endMs, totalMs, toX, yearLabels };
}

// ─── Component ────────────────────────────────────────────────────────────

// Hover state: event index + optional citation index within that event
type HoverTarget =
  | { kind: "event"; eventIdx: number; citationIdx: number | null }
  | { kind: "staffing"; pointIdx: number };

export function FacilityTimeline({
  inspectionEvents,
  penalties,
  staffingTrend,
  standardSurveyDates,
  nationalAvgHprd,
  forcedAxisRange,
  hideLegend,
}: FacilityTimelineProps): React.JSX.Element | null {
  const [hovered, setHovered] = useState<HoverTarget | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const events = useMemo(
    () => buildTimelineEvents(inspectionEvents, penalties, standardSurveyDates ?? null),
    [inspectionEvents, penalties, standardSurveyDates]
  );

  const hasStaffing = staffingTrend && staffingTrend.length >= 2;

  const axis = useMemo(
    () => buildTimeAxis(events, staffingTrend, forcedAxisRange ?? null),
    [events, staffingTrend, forcedAxisRange]
  );

  const handleLeave = useCallback(() => setHovered(null), []);

  if (events.length === 0 && !hasStaffing) return null;

  // Event positions on x axis — nudge overlapping events apart
  const rawPositions = events.map((e) => axis.toX(e.date.getTime()));
  const positions = [...rawPositions];
  const MIN_SPACING = BLOCK_W + 6; // minimum px between event centers
  for (let i = 1; i < positions.length; i++) {
    const diff = positions[i] - positions[i - 1];
    if (diff < MIN_SPACING) {
      // Spread symmetrically
      const nudge = (MIN_SPACING - diff) / 2;
      positions[i - 1] -= nudge;
      positions[i] += nudge;
    }
  }

  // Compute inspection-event clusters using the same 120-day window as
  // InspectionSummary / CompareInspectionSummary (anchored at the most recent
  // date in the cluster). Renders as shaded background bands so the visual
  // grouping matches the count shown in the summary panels.
  const CLUSTER_DAYS = 120;
  const surveyEventsForClustering = events
    .filter((e) => e.type === "inspection" || e.type === "clean_inspection")
    .sort((a, b) => b.date.getTime() - a.date.getTime()); // newest first
  interface SurveyCluster {
    latestMs: number;
    earliestMs: number;
    eventCount: number;
  }
  const surveyClusters: SurveyCluster[] = [];
  for (const e of surveyEventsForClustering) {
    const last = surveyClusters[surveyClusters.length - 1];
    const ms = e.date.getTime();
    if (last && (last.latestMs - ms) / (24 * 3600 * 1000) <= CLUSTER_DAYS) {
      // Within window of cluster's most recent survey — extend earliest backward
      last.earliestMs = Math.min(last.earliestMs, ms);
      last.eventCount += 1;
    } else {
      surveyClusters.push({ latestMs: ms, earliestMs: ms, eventCount: 1 });
    }
  }
  // Only multi-survey clusters need a visual band
  const visibleClusters = surveyClusters.filter((c) => c.eventCount >= 2);

  // Detect notable gaps between inspection events (>18 months)
  const GAP_THRESHOLD_MS = 18 * 30 * 24 * 3600 * 1000; // ~18 months
  const inspectionEvents_sorted = events
    .filter((e) => e.type === "inspection" || e.type === "clean_inspection")
    .sort((a, b) => a.date.getTime() - b.date.getTime());
  const gaps: { startDate: Date; endDate: Date; x1: number; x2: number; months: number }[] = [];
  for (let i = 1; i < inspectionEvents_sorted.length; i++) {
    const prevMs = inspectionEvents_sorted[i - 1].date.getTime();
    const currMs = inspectionEvents_sorted[i].date.getTime();
    const diffMs = currMs - prevMs;
    if (diffMs > GAP_THRESHOLD_MS) {
      const months = Math.round(diffMs / (30 * 24 * 3600 * 1000));
      gaps.push({
        startDate: inspectionEvents_sorted[i - 1].date,
        endDate: inspectionEvents_sorted[i].date,
        x1: axis.toX(prevMs),
        x2: axis.toX(currMs),
        months,
      });
    }
  }

  // Staffing chart data
  const staffingPoints: { x: number; y: number; value: number }[] = [];
  let staffMin = Infinity;
  let staffMax = -Infinity;
  if (hasStaffing) {
    for (const s of staffingTrend) {
      if (s.reported_total_hprd === null) continue;
      if (s.reported_total_hprd < staffMin) staffMin = s.reported_total_hprd;
      if (s.reported_total_hprd > staffMax) staffMax = s.reported_total_hprd;
    }
    // Extend range to include national average if provided
    if (nationalAvgHprd != null) {
      if (nationalAvgHprd < staffMin) staffMin = nationalAvgHprd;
      if (nationalAvgHprd > staffMax) staffMax = nationalAvgHprd;
    }
    const staffRange = staffMax - staffMin || 0.5;
    staffMin -= staffRange * 0.1;
    staffMax += staffRange * 0.1;

    for (const s of staffingTrend) {
      const d = parseQuarterLabel(s.quarter_label);
      if (!d || s.reported_total_hprd === null) continue;
      const x = axis.toX(d.getTime());
      const yNorm = (s.reported_total_hprd - staffMin) / (staffMax - staffMin);
      const y = CHART_H - yNorm * (CHART_H - 8) - 4;
      staffingPoints.push({ x, y, value: s.reported_total_hprd });
    }
  }

  const totalH = MARKER_ZONE_H + AXIS_H + (hasStaffing ? CHART_LABEL_H + CHART_H + GAP : 0);
  const axisLineY = MARKER_Y;
  const chartLabelTop = MARKER_ZONE_H + AXIS_H + GAP;
  const chartTop = chartLabelTop + CHART_LABEL_H;

  // Block fill color per severity
  function blockFill(code: string | null): string {
    const tier = scopeSeverityTier(code);
    switch (tier) {
      case "immediate_jeopardy": return "#c2410c";
      case "high": return "#374151";
      case "moderate": return "#9ca3af";
      default: return "#d1d5db";
    }
  }
  function blockTextColor(code: string | null): string {
    const tier = scopeSeverityTier(code);
    return tier === "immediate_jeopardy" || tier === "high" ? "white" : "#374151";
  }

  // Tooltip position — to the side of the hovered element
  const tooltipStyle = useMemo((): { top: string; left?: string; right?: string; transform: string } | null => {
    if (!hovered) return null;

    let px: number;
    let centerY: number;

    if (hovered.kind === "staffing") {
      const pt = staffingPoints[hovered.pointIdx];
      if (!pt) return null;
      px = pt.x;
      centerY = chartTop + pt.y;
    } else {
      // Negative eventIdx = gap hover (rendered via foreignObject, no tooltip needed here)
      if (hovered.eventIdx < 0 || hovered.eventIdx >= events.length) return null;
      px = positions[hovered.eventIdx];
      centerY = axisLineY;
      const evt = events[hovered.eventIdx];
      if (evt.type === "inspection" && hovered.citationIdx !== null) {
        centerY = axisLineY - (hovered.citationIdx + 0.5) * (BLOCK_H + BLOCK_GAP);
      }
    }

    const pxPct = px / SVG_WIDTH;
    const topPct = (centerY / totalH) * 100;

    if (pxPct < 0.55) {
      return {
        top: `${topPct}%`,
        left: `${pxPct * 100 + 3}%`,
        transform: "translateY(-50%)",
      };
    }
    return {
      top: `${topPct}%`,
      right: `${100 - pxPct * 100 + 3}%`,
      transform: "translateY(-50%)",
    };
  }, [hovered, positions, events, staffingPoints, totalH, axisLineY, chartTop]);

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${SVG_WIDTH} ${totalH}`}
        className="w-full"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Facility event timeline with inspections, penalties, and staffing trend"
      >
        {/* ── Cluster bands ── render first so citation blocks and axis sit on top.
            Shows the same 120-day grouping that drives the count in
            InspectionSummary / CompareInspectionSummary. */}
        {visibleClusters.map((c, ci) => {
          const xLeft = axis.toX(c.earliestMs) - (BLOCK_W / 2 + 6);
          const xRight = axis.toX(c.latestMs) + (BLOCK_W / 2 + 6);
          // Vertical extent: top of marker zone (above tallest stack) to slightly
          // below the axis line (covers axis-level markers like fines/denials).
          const yTop = 0;
          const height = (axisLineY + 14) - yTop;
          return (
            <g key={`cluster-${ci}`} className="pointer-events-none">
              <rect
                x={xLeft}
                y={yTop}
                width={Math.max(xRight - xLeft, 0)}
                height={height}
                rx={6}
                fill="#dbeafe"
                opacity={0.45}
              />
              <rect
                x={xLeft}
                y={yTop}
                width={Math.max(xRight - xLeft, 0)}
                height={height}
                rx={6}
                fill="none"
                stroke="#93c5fd"
                strokeWidth={0.75}
                strokeDasharray="3,3"
                opacity={0.8}
              />
            </g>
          );
        })}

        {/* ── Marker zone ── */}
        <line
          x1={PL} y1={axisLineY} x2={SVG_WIDTH - PR} y2={axisLineY}
          stroke="#d1d5db" strokeWidth={1.5}
        />

        {/* Gap annotations — periods with no inspections */}
        {gaps.map((gap, gi) => {
          const midX = (gap.x1 + gap.x2) / 2;
          const gapWidth = gap.x2 - gap.x1;
          const gapLabel = gap.months > 12
            ? `No inspections for ${Math.floor(gap.months / 12)}yr ${gap.months % 12}mo`
            : `No inspections for ${gap.months}mo`;
          // Determine if gap overlaps COVID moratorium (Mar 2020 - ~Dec 2021)
          const covidStart = new Date(2020, 2, 1).getTime();
          const covidEnd = new Date(2021, 11, 31).getTime();
          const overlapsCovid = gap.startDate.getTime() < covidEnd && gap.endDate.getTime() > covidStart;
          return (
            <g
              key={`gap-${gi}`}
              className="cursor-help"
              onMouseEnter={() => setHovered({ kind: "event", eventIdx: -1 - gi, citationIdx: null })}
              onMouseLeave={handleLeave}
            >
              <rect
                x={gap.x1 + 8}
                y={axisLineY - 20}
                width={Math.max(gapWidth - 16, 0)}
                height={18}
                rx={4}
                fill="#fef3c7"
                opacity={0.5}
              />
              {gapWidth > 60 && (
                <text
                  x={midX}
                  y={axisLineY - 8}
                  textAnchor="middle"
                  className="fill-amber-600 text-[8px] font-medium"
                  style={{ pointerEvents: "none" }}
                >
                  {gapLabel}
                </text>
              )}
              {/* Invisible hover target if gap label is too narrow */}
              <rect
                x={gap.x1 + 8}
                y={axisLineY - 20}
                width={Math.max(gapWidth - 16, 0)}
                height={18}
                fill="transparent"
              />
              {/* Gap tooltip rendered as SVG foreignObject for HTML content */}
              {hovered?.kind === "event" && hovered.eventIdx === -1 - gi && (
                <foreignObject
                  x={Math.max(midX - 130, PL)}
                  y={axisLineY - 80}
                  width={260}
                  height={60}
                >
                  <div className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs shadow-lg">
                    <p className="font-medium text-gray-700">{gapLabel}</p>
                    <p className="mt-0.5 text-[10px] text-gray-500">
                      CMS requires annual standard inspections.
                      {overlapsCovid
                        ? " This gap overlaps with the COVID-19 inspection moratorium (March 2020), but extends beyond the typical resumption period."
                        : " A gap this long is unusual and may indicate delayed oversight."}
                    </p>
                  </div>
                </foreignObject>
              )}
            </g>
          );
        })}

        {/* Event markers */}
        {events.map((event, i) => {
          const px = positions[i];

          // ── Fine: $ circle ──
          if (event.type === "fine") {
            const isH = hovered?.kind === "event" && hovered.eventIdx === i;
            const r = 10 * (isH ? 1.3 : 1);
            return (
              <g
                key={`${event.dateStr}-fine-${i}`}
                onMouseEnter={() => setHovered({ kind: "event", eventIdx: i, citationIdx: null })}
                onMouseLeave={handleLeave}
                className="cursor-pointer"
              >
                <circle
                  cx={px} cy={axisLineY} r={r}
                  fill="#2563eb" stroke="#1d4ed8" strokeWidth={1}
                  opacity={isH ? 1 : 0.9}
                />
                <text
                  x={px} y={axisLineY + 4}
                  textAnchor="middle"
                  className="text-[11px] font-bold"
                  fill="white"
                  style={{ pointerEvents: "none" }}
                >
                  $
                </text>
              </g>
            );
          }

          // ── Payment denial: orange circle + horizontal line showing duration ──
          if (event.type === "payment_denial") {
            const isH = hovered?.kind === "event" && hovered.eventIdx === i;
            const endX = event.denialEndDate
              ? axis.toX(event.denialEndDate.getTime())
              : px + 20;
            const r = 10 * (isH ? 1.3 : 1);
            return (
              <g
                key={`${event.dateStr}-denial-${i}`}
                onMouseEnter={() => setHovered({ kind: "event", eventIdx: i, citationIdx: null })}
                onMouseLeave={handleLeave}
                className="cursor-pointer"
              >
                {/* Duration line from start to end */}
                <line
                  x1={px} y1={axisLineY}
                  x2={endX} y2={axisLineY}
                  stroke="#ea580c"
                  strokeWidth={3}
                  opacity={isH ? 1 : 0.6}
                  strokeLinecap="round"
                />
                {/* End cap dot */}
                <circle cx={endX} cy={axisLineY} r={3} fill="#ea580c" opacity={isH ? 1 : 0.6} />
                {/* Start circle with ✕ */}
                <circle
                  cx={px} cy={axisLineY} r={r}
                  fill="#ea580c" stroke="#c2410c" strokeWidth={1}
                  opacity={isH ? 1 : 0.9}
                />
                <text
                  x={px} y={axisLineY + 4}
                  textAnchor="middle"
                  className="text-[10px] font-bold"
                  fill="white"
                  style={{ pointerEvents: "none" }}
                >
                  ✕
                </text>
              </g>
            );
          }

          // ── Clean inspection: hollow dashed circle ──
          if (event.type === "clean_inspection") {
            const isH = hovered?.kind === "event" && hovered.eventIdx === i;
            const r = 7 * (isH ? 1.3 : 1);
            return (
              <g
                key={`${event.dateStr}-clean-${i}`}
                onMouseEnter={() => setHovered({ kind: "event", eventIdx: i, citationIdx: null })}
                onMouseLeave={handleLeave}
                className="cursor-pointer"
              >
                <circle
                  cx={px} cy={axisLineY} r={r}
                  fill="white" stroke="#9ca3af"
                  strokeWidth={1.5}
                  strokeDasharray="3,2"
                  opacity={isH ? 1 : 0.7}
                />
                <text
                  x={px} y={axisLineY + 3}
                  textAnchor="middle"
                  className="text-[8px]"
                  fill="#9ca3af"
                  style={{ pointerEvents: "none" }}
                >
                  ✓
                </text>
              </g>
            );
          }

          // ── Inspection: stacked citation blocks ──
          const blocks = event.citationBlocks ?? [];
          const halfW = BLOCK_W / 2;

          return (
            <g key={`${event.dateStr}-insp-${i}`}>
              {blocks.map((block, bi) => {
                // Stack upward from axis: block 0 at bottom (most severe)
                const by = axisLineY - (bi + 1) * (BLOCK_H + BLOCK_GAP);
                const bx = px - halfW;
                const fill = blockFill(block.severityCode);
                const textColor = blockTextColor(block.severityCode);
                const isBlockHovered = hovered?.kind === "event" && hovered.eventIdx === i && hovered.citationIdx === bi;

                return (
                  <g
                    key={`${event.dateStr}-b-${bi}`}
                    onMouseEnter={() => setHovered({ kind: "event", eventIdx: i, citationIdx: bi })}
                    onMouseLeave={handleLeave}
                    className="cursor-pointer"
                  >
                    <rect
                      x={bx}
                      y={by}
                      width={BLOCK_W}
                      height={BLOCK_H}
                      rx={2}
                      fill={fill}
                      stroke={isBlockHovered ? "#111827" : "white"}
                      strokeWidth={isBlockHovered ? 1.5 : 0.5}
                      opacity={isBlockHovered ? 1 : 0.9}
                    />
                    <text
                      x={px}
                      y={by + BLOCK_H / 2 + 3.5}
                      textAnchor="middle"
                      fill={textColor}
                      className="text-[9px] font-bold"
                      style={{ pointerEvents: "none" }}
                    >
                      {block.severityCode ?? "?"}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* Hover crosshair into staffing chart */}
        {hovered !== null && hovered.kind === "event" && hasStaffing && (
          <line
            x1={positions[hovered.eventIdx]}
            y1={axisLineY + 6}
            x2={positions[hovered.eventIdx]}
            y2={chartTop + CHART_H}
            stroke="#9ca3af"
            strokeWidth={0.75}
            strokeDasharray="3,3"
            style={{ pointerEvents: "none" }}
          />
        )}

        {/* ── Year axis ── */}
        {axis.yearLabels.map(({ year, x }) => (
          <g key={year}>
            <line
              x1={x} y1={MARKER_ZONE_H - 2}
              x2={x} y2={MARKER_ZONE_H + 4}
              stroke="#9ca3af" strokeWidth={1}
            />
            <text
              x={x} y={MARKER_ZONE_H + 15}
              textAnchor="middle"
              className="fill-gray-400 text-[9px]"
            >
              {year}
            </text>
          </g>
        ))}

        {/* ── Staffing trend chart title (above chart area) ── */}
        {hasStaffing && staffingPoints.length >= 2 && (
          <text
            x={PL + 4}
            y={chartLabelTop + 10}
            className="fill-gray-500 text-[9px] font-medium"
          >
            Total Nurse Hours per Resident per Day (HPRD)
          </text>
        )}

        {/* ── Staffing trend chart ── */}
        {hasStaffing && staffingPoints.length >= 2 && (() => {
          const staffMid = (staffMin + staffMax) / 2;
          const midY = CHART_H / 2;
          const lastPt = staffingPoints[staffingPoints.length - 1];
          return (
            <g transform={`translate(0, ${chartTop})`}>
              {/* Background */}
              <rect
                x={PL} y={0}
                width={DRAW_W} height={CHART_H}
                fill="#f9fafb" rx={4}
              />

              {/* "No data" zone — distinct background + label */}
              {staffingPoints[0].x - PL > 10 && (
                <rect
                  x={PL} y={0}
                  width={staffingPoints[0].x - PL}
                  height={CHART_H}
                  fill="#f3f4f6"
                  rx={4}
                />
              )}
              {staffingPoints[0].x - PL > 40 && (
                <text
                  x={PL + (staffingPoints[0].x - PL) / 2}
                  y={CHART_H / 2 + 3}
                  textAnchor="middle"
                  className="fill-gray-400 text-[8px]"
                >
                  No staffing data
                </text>
              )}

              {/* Horizontal gridlines */}
              <line x1={PL} y1={4} x2={SVG_WIDTH - PR} y2={4} stroke="#e5e7eb" strokeWidth={0.5} />
              <line x1={PL} y1={midY} x2={SVG_WIDTH - PR} y2={midY} stroke="#e5e7eb" strokeWidth={0.5} strokeDasharray="4,3" />
              <line x1={PL} y1={CHART_H - 4} x2={SVG_WIDTH - PR} y2={CHART_H - 4} stroke="#e5e7eb" strokeWidth={0.5} />

              {/* Left y-axis labels with unit */}
              <text x={PL - 4} y={8} textAnchor="end" className="fill-gray-400 text-[8px]">
                {staffMax.toFixed(1)}
              </text>
              <text x={PL - 4} y={midY + 3} textAnchor="end" className="fill-gray-400 text-[8px]">
                {staffMid.toFixed(1)}
              </text>
              <text x={PL - 4} y={CHART_H - 2} textAnchor="end" className="fill-gray-400 text-[8px]">
                {staffMin.toFixed(1)}
              </text>

              {/* Right side: current value annotation */}
              <text
                x={lastPt.x + 6} y={lastPt.y + 3}
                className="fill-blue-600 text-[9px] font-semibold"
              >
                {lastPt.value.toFixed(1)}
              </text>

              {/* National average benchmark line — prominent orange */}
              {nationalAvgHprd != null && nationalAvgHprd >= staffMin && nationalAvgHprd <= staffMax && (() => {
                const avgYNorm = (nationalAvgHprd - staffMin) / (staffMax - staffMin);
                const avgY = CHART_H - avgYNorm * (CHART_H - 8) - 4;
                return (
                  <>
                    <line
                      x1={PL}
                      y1={avgY}
                      x2={SVG_WIDTH - PR}
                      y2={avgY}
                      stroke="#ea580c"
                      strokeWidth={1.5}
                      strokeDasharray="8,4"
                      opacity={0.7}
                    />
                    <rect
                      x={SVG_WIDTH - PR - 72}
                      y={avgY - 9}
                      width={72}
                      height={14}
                      rx={3}
                      fill="white"
                      opacity={0.85}
                    />
                    <text
                      x={SVG_WIDTH - PR - 36}
                      y={avgY + 2}
                      textAnchor="middle"
                      className="text-[8px] font-medium"
                      fill="#ea580c"
                    >
                      Nat&apos;l avg {nationalAvgHprd.toFixed(1)}
                    </text>
                  </>
                );
              })()}

              {/* Area fill */}
              <path
                d={
                  `M ${staffingPoints[0].x},${CHART_H} ` +
                  staffingPoints.map((p) => `L ${p.x},${p.y}`).join(" ") +
                  ` L ${lastPt.x},${CHART_H} Z`
                }
                fill="#2563eb"
                opacity={0.08}
              />

              {/* Line */}
              <polyline
                points={staffingPoints.map((p) => `${p.x},${p.y}`).join(" ")}
                fill="none"
                stroke="#2563eb"
                strokeWidth={2}
                strokeLinejoin="round"
              />

              {/* Hoverable dots */}
              {staffingPoints.map((p, si) => {
                const isH = hovered?.kind === "staffing" && hovered.pointIdx === si;
                return (
                  <circle
                    key={si}
                    cx={p.x} cy={p.y}
                    r={isH ? 5 : 2.5}
                    fill="#2563eb"
                    stroke={isH ? "white" : "none"}
                    strokeWidth={isH ? 2 : 0}
                    className="cursor-pointer"
                    onMouseEnter={() => setHovered({ kind: "staffing", pointIdx: si })}
                    onMouseLeave={handleLeave}
                  />
                );
              })}

              {/* Chart title rendered above chart area — see chartLabelTop */}

              {/* Vertical y-axis label */}
              <text
                x={10} y={CHART_H / 2}
                textAnchor="middle"
                transform={`rotate(-90, 10, ${CHART_H / 2})`}
                className="fill-gray-400 text-[8px]"
              >
                Nurse hours
              </text>
            </g>
          );
        })()}
      </svg>

      {/* Legend — letter ranges included for interpretability */}
      {!hideLegend && (
      <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-gray-400">
        <span className="flex items-center gap-1">
          <svg width="12" height="12"><rect x="1" y="1" width="10" height="10" rx="1.5" fill="#c2410c" /></svg>
          J–L Immediate jeopardy
        </span>
        <span className="flex items-center gap-1">
          <svg width="12" height="12"><rect x="1" y="1" width="10" height="10" rx="1.5" fill="#374151" /></svg>
          G–I Actual harm
        </span>
        <span className="flex items-center gap-1">
          <svg width="12" height="12"><rect x="1" y="1" width="10" height="10" rx="1.5" fill="#9ca3af" /></svg>
          D–F Potential harm
        </span>
        <span className="flex items-center gap-1">
          <svg width="12" height="12"><rect x="1" y="1" width="10" height="10" rx="1.5" fill="#d1d5db" /></svg>
          A–C Low risk
        </span>
        <span className="flex items-center gap-1">
          <svg width="10" height="10"><circle cx="5" cy="5" r="4" fill="white" stroke="#9ca3af" strokeWidth="1.5" strokeDasharray="2,1.5" /></svg>
          No deficiencies
        </span>
        <span className="flex items-center gap-1">
          <svg width="12" height="12"><circle cx="6" cy="6" r="5" fill="#2563eb" /><text x="6" y="9.5" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold">$</text></svg>
          Fine
        </span>
        <span className="flex items-center gap-1">
          <svg width="18" height="12"><circle cx="6" cy="6" r="5" fill="#ea580c" /><line x1="11" y1="6" x2="18" y2="6" stroke="#ea580c" strokeWidth="2" /></svg>
          Admission denial
        </span>
        {hasStaffing && (
          <span className="flex items-center gap-1">
            <svg width="16" height="10"><line x1="0" y1="5" x2="16" y2="5" stroke="#2563eb" strokeWidth="2" /></svg>
            Staffing HPRD
          </span>
        )}
        {hasStaffing && nationalAvgHprd != null && (
          <span className="flex items-center gap-1">
            <svg width="16" height="10"><line x1="0" y1="5" x2="16" y2="5" stroke="#ea580c" strokeWidth="1.5" strokeDasharray="4,3" opacity="0.7" /></svg>
            National avg
          </span>
        )}
      </div>
      )}

      {/* Tooltip — per-citation-block for inspections, per-event for penalties/clean */}
      {hovered && tooltipStyle && (() => {
        let content: React.JSX.Element;
        if (hovered.kind === "staffing") {
          const pt = staffingPoints[hovered.pointIdx];
          const trend = staffingTrend![hovered.pointIdx];
          content = (
            <div>
              <p className="font-medium text-gray-700">{pt.value.toFixed(2)} hours per resident per day</p>
              <p className="mt-0.5 text-[10px] text-gray-400">{trend.quarter_label}</p>
            </div>
          );
        } else {
          const event = events[hovered.eventIdx];
          if (event.type === "inspection" && hovered.citationIdx !== null && event.citationBlocks) {
            content = <CitationBlockTooltip block={event.citationBlocks[hovered.citationIdx]} event={event} />;
          } else if (event.type === "clean_inspection") {
            content = <CleanInspectionTooltip event={event} />;
          } else if (event.type === "payment_denial") {
            content = <DenialTooltip event={event} />;
          } else {
            content = <FineTooltip event={event} />;
          }
        }
        return (
          <div
            className="pointer-events-none absolute z-50 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs shadow-lg"
            style={tooltipStyle}
          >
            {content}
          </div>
        );
      })()}
    </div>
  );
}
