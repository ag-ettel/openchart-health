"use client";

// Nursing Home Summary Dashboard — narrative "at a glance" hook.
// Analogous to HospitalSummaryDashboard.
//
// Leads with:
// 1. Gate conditions (SFF, abuse icon) — NH-9
// 2. Horizontal facility timeline (inspections + penalties over time)
// 3. PBJ staffing trend sparklines
// 4. Five-Star ratings with sub-ratings
// 5. CMS quality assessment
//
// Display rules:
// - SFF and abuse icon are gate conditions (NH-9) — displayed before Five-Star
// - Five-Star shown prominently but always with sub-ratings (NH-4)
// - No directional color coding (DEC-030)
// - Orange threshold only for SFF, abuse icon, IJ citations

import { useState } from "react";
import type { Measure, NursingHomeContext, InspectionEvent, Penalty, PaymentAdjustment } from "@/types/provider";
import { NATIONAL_AVG_TOTAL_NURSE_HPRD } from "@/lib/constants";
import { FiveStarDisplay } from "./FiveStarDisplay";
import { FacilityTimeline } from "./FacilityTimeline";
import { InspectionSummary } from "./InspectionSummary";
import { OwnershipStructureViz } from "./OwnershipStructureViz";
import { OwnershipGroupStats } from "./OwnershipGroupStats";
import type { OwnershipEntry, ParentGroupStats } from "@/types/provider";

interface NursingHomeSummaryDashboardProps {
  measures: Measure[];
  nursingHomeContext: NursingHomeContext | null;
  inspectionEvents: InspectionEvent[] | null;
  penalties: Penalty[] | null;
  paymentAdjustments: PaymentAdjustment[];
  providerName: string;
  /** 2-char state code (provider.address.state) — passed to InspectionSummary
   *  so state-level averages can be loaded alongside the national baseline. */
  providerState?: string | null;
  ownership?: OwnershipEntry[] | null;
  parentGroupStats?: ParentGroupStats | null;
}

/** Inline SVG trend chart with national average line, axis labels, and hover tooltips. */
function StaffingTrendChart({ values, natAvg, natAvgLabel, label, unit }: {
  values: { label: string; value: number | null }[];
  natAvg: number;
  natAvgLabel: string;
  label: string;
  unit: string;
}): React.JSX.Element {
  const [hoveredPt, setHoveredPt] = useState<number | null>(null);
  const pts = values.filter((v) => v.value !== null) as { label: string; value: number }[];
  if (pts.length < 2) return <></>;

  const W = 600;
  const TITLE_H = 14;
  const CHART_H = 70;
  const XAXIS_H = 14;
  const H = TITLE_H + CHART_H + XAXIS_H;
  const PL_C = 40;
  const PR_C = 50;
  const DW = W - PL_C - PR_C;
  const chartY0 = TITLE_H;

  let min = Math.min(...pts.map((p) => p.value), natAvg);
  let max = Math.max(...pts.map((p) => p.value), natAvg);
  const range = max - min || 1;
  min -= range * 0.1;
  max += range * 0.1;
  const mid = (min + max) / 2;

  const toY = (v: number) => chartY0 + 4 + (CHART_H - 8) - ((v - min) / (max - min)) * (CHART_H - 8);
  const points = pts.map((p, i) => ({
    x: PL_C + (i / (pts.length - 1)) * DW,
    y: toY(p.value),
    label: p.label,
    value: p.value,
  }));
  const avgY = toY(natAvg);
  const lastPt = points[points.length - 1];

  // X-axis: show ~5 evenly spaced quarter labels
  const step = Math.max(1, Math.floor(pts.length / 5));
  const xLabels = pts.filter((_, i) => i % step === 0 || i === pts.length - 1);

  const formatUnit = (v: number) =>
    unit === "%" ? `${v.toFixed(0)}%` : v.toFixed(unit === "HPRD" ? 2 : 1);

  return (
    <div className="relative mt-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="xMidYMid meet">
        {/* Title above chart */}
        <text x={PL_C} y={11} className="fill-gray-500 text-[9px] font-medium">{label}</text>

        {/* Chart background */}
        <rect x={PL_C} y={chartY0} width={DW} height={CHART_H} fill="#f9fafb" rx={4} />

        {/* Gridlines */}
        <line x1={PL_C} y1={toY(mid)} x2={W - PR_C} y2={toY(mid)} stroke="#e5e7eb" strokeWidth={0.5} strokeDasharray="4,3" />

        {/* National avg line */}
        <line x1={PL_C} y1={avgY} x2={W - PR_C} y2={avgY} stroke="#ea580c" strokeWidth={1.5} strokeDasharray="8,4" opacity={0.8} />
        <rect x={W - PR_C - 78} y={avgY - 8} width={78} height={14} rx={3} fill="white" opacity={0.9} />
        <text x={W - PR_C - 39} y={avgY + 3} textAnchor="middle" className="text-[8px] font-medium" fill="#ea580c">
          Nat&apos;l avg {natAvgLabel}
        </text>

        {/* Y-axis labels */}
        <text x={PL_C - 3} y={chartY0 + 8} textAnchor="end" className="fill-gray-400 text-[7px]">{max.toFixed(unit === "%" ? 0 : 1)}{unit === "%" ? "%" : ""}</text>
        <text x={PL_C - 3} y={toY(mid) + 3} textAnchor="end" className="fill-gray-400 text-[7px]">{mid.toFixed(unit === "%" ? 0 : 1)}{unit === "%" ? "%" : ""}</text>
        <text x={PL_C - 3} y={chartY0 + CHART_H - 2} textAnchor="end" className="fill-gray-400 text-[7px]">{min.toFixed(unit === "%" ? 0 : 1)}{unit === "%" ? "%" : ""}</text>

        {/* Area */}
        <path
          d={`M ${points[0].x},${chartY0 + CHART_H} ${points.map((p) => `L ${p.x},${p.y}`).join(" ")} L ${lastPt.x},${chartY0 + CHART_H} Z`}
          fill="#2563eb" opacity={0.08}
        />
        {/* Line */}
        <polyline
          points={points.map((p) => `${p.x},${p.y}`).join(" ")}
          fill="none" stroke="#2563eb" strokeWidth={2} strokeLinejoin="round"
        />
        {/* Hoverable dots */}
        {points.map((p, i) => (
          <circle
            key={i} cx={p.x} cy={p.y}
            r={hoveredPt === i ? 5 : 2.5}
            fill="#2563eb"
            stroke={hoveredPt === i ? "white" : "none"}
            strokeWidth={hoveredPt === i ? 2 : 0}
            className="cursor-pointer"
            onMouseEnter={() => setHoveredPt(i)}
            onMouseLeave={() => setHoveredPt(null)}
          />
        ))}
        {/* End value */}
        <text x={lastPt.x + 5} y={lastPt.y + 3} className="fill-blue-600 text-[8px] font-semibold">
          {formatUnit(lastPt.value)}
        </text>

        {/* X-axis labels */}
        {xLabels.map((pt) => {
          const idx = pts.indexOf(pt);
          const x = PL_C + (idx / (pts.length - 1)) * DW;
          return (
            <text key={pt.label} x={x} y={chartY0 + CHART_H + 11} textAnchor="middle" className="fill-gray-400 text-[7px]">
              {pt.label}
            </text>
          );
        })}
      </svg>

      {/* Tooltip */}
      {hoveredPt !== null && (() => {
        const p = points[hoveredPt];
        const pxPct = (p.x / W) * 100;
        return (
          <div
            className="pointer-events-none absolute z-50 -translate-x-1/2 rounded border border-gray-200 bg-white px-2 py-1 text-xs shadow"
            style={{ left: `${pxPct}%`, top: 0 }}
          >
            <span className="font-medium text-gray-700">{formatUnit(p.value)}</span>
            <span className="ml-1 text-gray-400">{p.label}</span>
          </div>
        );
      })()}
    </div>
  );
}

/** Staffing + inspection key metrics — compact boxes with expandable trend charts.
 *
 * Reads current values and trend data from the measures array. When multiple
 * reporting periods exist, each box can expand to show a historical trend.
 */
function StaffingStats({
  ctx,
  measures,
}: {
  ctx: NursingHomeContext;
  measures: Measure[];
}): React.JSX.Element | null {
  // Look up measures by ID
  const findMeasure = (id: string): Measure | undefined =>
    measures.find((m) => m.measure_id === id && !m.stratification);

  const turnoverM = findMeasure("NH_STAFF_TOTAL_TURNOVER");
  const rnM = findMeasure("NH_STAFF_REPORTED_RN_HPRD");
  const totalM = findMeasure("NH_STAFF_REPORTED_TOTAL_HPRD");

  // Current values: prefer measure, fall back to context
  const turnover = turnoverM?.numeric_value ?? ctx.total_turnover;
  const rnHprd = rnM?.numeric_value ?? ctx.reported_rn_hprd;
  const totalHprd = totalM?.numeric_value ?? ctx.reported_total_hprd;

  // Default-expand Total Nurse Hours trend
  const [expanded, setExpanded] = useState<Set<string>>(new Set(["total"]));

  if (turnover === null && rnHprd === null && totalHprd === null) return null;

  const toggle = (key: string) => setExpanded((prev) => {
    const next = new Set(prev);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    return next;
  });

  // Extract trend data from a measure if 3+ periods available
  const trendFromMeasure = (m: Measure | undefined) => {
    if (!m?.trend || m.trend.length < 3) return null;
    return m.trend.map((t) => ({ label: t.period_label, value: t.numeric_value }));
  };

  const metrics: {
    key: string;
    label: string;
    value: string;
    subtitle: string | null;
    natAvg: number;
    natAvgLabel: string;
    unit: string;
    trendData: { label: string; value: number | null }[] | null;
  }[] = [];

  // Order: Total Nurse Hours, RN Hours, Turnover
  if (totalHprd !== null) {
    const totalMins = Math.round(totalHprd * 60);
    metrics.push({
      key: "total",
      label: "Total Nurse Hours",
      value: `${totalHprd.toFixed(1)}`,
      subtitle: `${totalMins} minutes of total nursing time per resident per day`,
      natAvg: 3.9,
      natAvgLabel: "3.9",
      unit: "HPRD",
      trendData: trendFromMeasure(totalM),
    });
  }
  if (rnHprd !== null) {
    const rnMins = Math.round(rnHprd * 60);
    metrics.push({
      key: "rn",
      label: "RN Hours",
      value: `${rnHprd.toFixed(2)}`,
      subtitle: `${rnMins} minutes of RN time per resident per day`,
      natAvg: 0.68,
      natAvgLabel: "0.68",
      unit: "HPRD",
      trendData: trendFromMeasure(rnM),
    });
  }
  if (turnover !== null) {
    metrics.push({
      key: "turnover",
      label: "Staff Turnover",
      value: `${turnover.toFixed(0)}%`,
      subtitle: `${turnover.toFixed(0)}% of nursing staff left in the reporting year`,
      natAvg: 46,
      natAvgLabel: "46%",
      unit: "%",
      trendData: trendFromMeasure(turnoverM),
    });
  }

  return (
    <div className="border-t border-gray-100 pt-4">
      <p className="mb-1 text-base font-semibold text-gray-800">Staffing</p>
      <p className="mb-3 text-sm text-gray-500">
        From CMS Payroll-Based Journal (PBJ). HPRD = hours per resident per day.
      </p>

      {/* Compact stat boxes — 3 across */}
      <div className="grid grid-cols-3 gap-2">
        {metrics.map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => m.trendData && toggle(m.key)}
            className={`group relative rounded-md px-3 py-2 text-center transition-colors ${
              expanded.has(m.key)
                ? "bg-blue-50 ring-1 ring-blue-200"
                : "bg-gray-50 hover:bg-gray-100"
            } ${m.trendData ? "cursor-pointer" : "cursor-default"}`}
          >
            <div className="text-xl font-bold text-gray-800">{m.value}</div>
            <div className="text-sm text-gray-600">{m.label}</div>
            <div className="text-xs text-gray-500">Nat&apos;l avg: {m.natAvgLabel}</div>
            {m.trendData && (
              <div className={`mt-1.5 text-xs font-medium ${expanded.has(m.key) ? "text-blue-600" : "text-blue-500"}`}>
                {expanded.has(m.key) ? "▲ Hide trend" : "▼ Show trend"}
              </div>
            )}
            {/* Plain-language tooltip */}
            {m.subtitle && (
              <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-60 -translate-x-1/2 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-normal leading-relaxed text-gray-600 opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                {m.subtitle}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Expanded trend charts */}
      {metrics.map((m) =>
        expanded.has(m.key) && m.trendData ? (
          <StaffingTrendChart
            key={m.key}
            values={m.trendData}
            natAvg={m.natAvg}
            natAvgLabel={m.natAvgLabel}
            label={m.label}
            unit={m.unit}
          />
        ) : null
      )}
    </div>
  );
}

export function NursingHomeSummaryDashboard({
  measures,
  nursingHomeContext,
  inspectionEvents,
  penalties,
  paymentAdjustments,
  providerName,
  providerState,
  ownership,
  parentGroupStats,
}: NursingHomeSummaryDashboardProps): React.JSX.Element {
  const ctx = nursingHomeContext;
  const events = inspectionEvents ?? [];
  const pens = penalties ?? [];
  void paymentAdjustments; // reserved for future SNF VBP summary signals

  // Safety gate conditions (NH-9)
  const isSFF = ctx?.is_special_focus_facility === true;
  const isSFFCandidate = ctx?.is_special_focus_facility_candidate === true;
  const isAbuseIcon = ctx?.is_abuse_icon === true;

  // Penalty summary
  const totalFines = pens
    .filter((p) => p.penalty_type === "Fine" && p.fine_amount !== null)
    .reduce((sum, p) => sum + (p.fine_amount ?? 0), 0);

  // Context badges with plain-language hover explanations (NH-9)
  const badges: { label: string; tooltip: string; variant: "neutral" | "orange" }[] = [];
  if (isSFF) badges.push({
    label: "Special Focus Facility",
    tooltip: "CMS designates this facility for intensive oversight due to a history of serious inspection findings.",
    variant: "orange",
  });
  if (isSFFCandidate && !isSFF) badges.push({
    label: "Special Focus Candidate",
    tooltip: "CMS has identified this facility as a candidate for its Special Focus program based on inspection history. It has not yet been designated.",
    variant: "orange",
  });
  if (isAbuseIcon) badges.push({
    label: "Abuse Finding",
    tooltip: "CMS has flagged this facility based on a substantiated finding of abuse, neglect, or exploitation.",
    variant: "orange",
  });
  if (ctx?.is_hospital_based) badges.push({
    label: "Hospital-Based",
    tooltip: "This nursing home operates within a hospital.",
    variant: "neutral",
  });
  if (ctx?.is_continuing_care_retirement_community) badges.push({
    label: "CCRC",
    tooltip: "Continuing Care Retirement Community — offers multiple levels of care (independent living, assisted living, skilled nursing) on one campus.",
    variant: "neutral",
  });

  const hasTimelineData = events.length > 0 || pens.length > 0 || (ctx?.staffing_trend && ctx.staffing_trend.length >= 2);

  // ── Narrative summary — deterministic template from CMS data ──
  // Order: inspection findings first (strongest signal), then status flags,
  // then star rating, penalties, staffing. Leads with the most decision-relevant info.
  const narrativeSentences: string[] = [];

  // ── Inspection analysis — temporally aware, handles follow-ups ──
  // Group inspections by survey_date
  const inspByDate = new Map<string, typeof events>();
  for (const e of events) {
    if (!e.survey_date) continue;
    if (!inspByDate.has(e.survey_date)) inspByDate.set(e.survey_date, []);
    inspByDate.get(e.survey_date)!.push(e);
  }
  const inspDates = [...inspByDate.keys()].sort().reverse();

  // Classify each inspection date
  interface InspSnap {
    date: string;
    citations: typeof events;
    ijCount: number;
    isComplaintDriven: boolean; // all citations are complaint-flagged
    daysSincePrior: number | null;
  }
  const inspSnaps: InspSnap[] = inspDates.map((date, i) => {
    const cits = inspByDate.get(date)!;
    const priorDateStr = inspDates[i + 1] ?? null;
    let daysSincePrior: number | null = null;
    if (priorDateStr) {
      daysSincePrior = Math.round(
        (new Date(date).getTime() - new Date(priorDateStr).getTime()) / (24 * 3600 * 1000)
      );
    }
    return {
      date,
      citations: cits,
      ijCount: cits.filter((e) => e.is_immediate_jeopardy).length,
      isComplaintDriven: cits.every((e) => e.is_complaint_deficiency),
      daysSincePrior,
    };
  });

  if (inspSnaps.length > 0) {
    const latest = inspSnaps[0];
    const prior = inspSnaps.length > 1 ? inspSnaps[1] : null;
    const fmtDate = (d: string) =>
      new Date(d).toLocaleDateString("en-US", { month: "long", year: "numeric" });
    const articleFor = (d: string) => {
      const month = new Date(d).toLocaleDateString("en-US", { month: "long" });
      return "AEIOU".includes(month[0]) ? "An" : "A";
    };

    // Detect if the latest inspection is a follow-up to a nearby prior with serious findings
    const isFollowUp = prior &&
      latest.daysSincePrior !== null &&
      latest.daysSincePrior <= 120 && // within ~4 months
      prior.ijCount > 0;

    if (isFollowUp) {
      // Lead with the serious inspection, frame the follow-up as a re-check
      narrativeSentences.push(
        `${articleFor(prior.date)} ${fmtDate(prior.date)} inspection resulted in ${prior.citations.length} citations, including ${prior.ijCount} at the immediate jeopardy level — CMS's most serious finding.`
      );
      if (latest.ijCount === 0) {
        narrativeSentences.push(
          `A follow-up ${latest.isComplaintDriven ? "complaint " : ""}inspection in ${fmtDate(latest.date)} found ${latest.citations.length} citation${latest.citations.length !== 1 ? "s" : ""}, none at the immediate jeopardy level.`
        );
      } else {
        narrativeSentences.push(
          `A follow-up inspection in ${fmtDate(latest.date)} found ${latest.citations.length} citation${latest.citations.length !== 1 ? "s" : ""}, including ${latest.ijCount} still at the immediate jeopardy level.`
        );
      }
    } else {
      // Standard narrative: describe most recent inspection
      if (latest.ijCount > 0) {
        narrativeSentences.push(
          `The most recent inspection (${fmtDate(latest.date)}) resulted in ${latest.citations.length} citations, including ${latest.ijCount} at the immediate jeopardy level — CMS's most serious finding, indicating a direct threat to resident safety.`
        );
      } else if (latest.citations.length > 0) {
        narrativeSentences.push(
          `The most recent inspection (${fmtDate(latest.date)}) resulted in ${latest.citations.length} citation${latest.citations.length > 1 ? "s" : ""}, none at the immediate jeopardy level.`
        );
      } else {
        narrativeSentences.push(
          `The most recent inspection (${fmtDate(latest.date)}) resulted in no deficiency citations.`
        );
      }

      // Trajectory vs prior (only for non-follow-up comparisons)
      if (prior) {
        if (latest.ijCount > 0 && prior.ijCount === 0) {
          narrativeSentences.push(
            "The prior inspection had no immediate jeopardy findings."
          );
        } else if (latest.ijCount === 0 && prior.ijCount > 0) {
          narrativeSentences.push(
            `The prior inspection (${fmtDate(prior.date)}) included ${prior.ijCount} immediate jeopardy citation${prior.ijCount > 1 ? "s" : ""}; the most recent did not.`
          );
        } else if (latest.citations.length < prior.citations.length * 0.6 && prior.citations.length >= 3) {
          narrativeSentences.push(
            `Citation count decreased from ${prior.citations.length} to ${latest.citations.length} between the two most recent inspections.`
          );
        } else if (latest.citations.length > prior.citations.length * 1.5 && latest.citations.length >= 3) {
          narrativeSentences.push(
            `Citation count increased from ${prior.citations.length} to ${latest.citations.length} between the two most recent inspections.`
          );
        }
      }
    }
  }

  // Current status flags (SFF, abuse)
  if (isSFF) {
    narrativeSentences.push(
      "CMS currently designates this facility for intensive oversight due to persistent serious findings."
    );
  } else if (isSFFCandidate) {
    narrativeSentences.push(
      "CMS currently identifies this facility as a candidate for its Special Focus oversight program."
    );
  }
  if (isAbuseIcon) {
    narrativeSentences.push(
      "CMS records include a substantiated finding of abuse, neglect, or exploitation."
    );
  }

  // Five-Star overall rating — rendered as a badge above the narrative, not inline
  const overallStar = measures.find(
    (m) => m.measure_id === "NH_STAR_OVERALL" && !m.stratification && m.numeric_value !== null
  );

  // Penalties — time-scoped
  if (pens.length > 0) {
    const penDates = pens.map((p) => p.penalty_date).filter(Boolean).sort();
    const oldestPen = penDates[0];
    const newestPen = penDates[penDates.length - 1];
    const denials = pens.filter((p) => p.penalty_type === "Payment Denial");
    const totalDenialDays = denials.reduce((s, p) => s + (p.payment_denial_length_days ?? 0), 0);

    // Format the time range
    const rangeStart = oldestPen ? new Date(oldestPen).getFullYear() : null;
    const rangeEnd = newestPen ? new Date(newestPen).getFullYear() : null;
    const rangeStr = rangeStart && rangeEnd
      ? rangeStart === rangeEnd ? `in ${rangeStart}` : `between ${rangeStart} and ${rangeEnd}`
      : "";

    const parts: string[] = [];
    if (totalFines > 0) parts.push(`$${totalFines.toLocaleString("en-US")} in fines`);
    if (denials.length > 0) {
      const daysStr = totalDenialDays > 0 ? ` totaling ${totalDenialDays} days` : "";
      parts.push(
        `${denials.length} period${denials.length > 1 ? "s" : ""} where CMS stopped paying for new admissions${daysStr}`
      );
    }
    narrativeSentences.push(
      rangeStr
        ? `${rangeStr.charAt(0).toUpperCase() + rangeStr.slice(1)}, CMS imposed ${parts.join(", and ")}.`
        : `CMS imposed ${parts.join(", and ")}.`
    );
  }

  // Staffing — single sentence using trend data (same source as chart)
  // Avoids repeating numbers the chart already shows; focuses on the comparison
  if (ctx?.staffing_trend && ctx.staffing_trend.length >= 2) {
    const trend = ctx.staffing_trend;
    const lastPoint = [...trend].reverse().find((t) => t.reported_total_hprd !== null);
    if (lastPoint?.reported_total_hprd != null) {
      const hprd = lastPoint.reported_total_hprd;
      const avg = NATIONAL_AVG_TOTAL_NURSE_HPRD;
      const rel = hprd < avg - 0.2 ? "below" : hprd > avg + 0.2 ? "above" : "near";
      narrativeSentences.push(
        `Nurse staffing is ${rel} the national average (${hprd.toFixed(1)} vs. ${avg.toFixed(1)} hours per resident per day) — see the staffing trend below.`
      );
    }
  } else if (ctx?.reported_total_hprd != null) {
    const hprd = ctx.reported_total_hprd;
    const avg = NATIONAL_AVG_TOTAL_NURSE_HPRD;
    const rel = hprd < avg - 0.2 ? "below" : hprd > avg + 0.2 ? "above" : "near";
    narrativeSentences.push(
      `Nurse staffing is ${rel} the national average (${hprd.toFixed(1)} vs. ${avg.toFixed(1)} hours per resident per day).`
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-5 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold text-gray-900">
        {providerName} <span className="font-normal text-gray-400">— At a Glance</span>
      </h2>

      {/* Badges: star rating + gate conditions */}
      {(badges.length > 0 || overallStar?.numeric_value != null) && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {/* Overall star rating badge */}
          {overallStar?.numeric_value != null && (
            <span className="group relative inline-flex cursor-help items-center gap-1.5 rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-medium text-gray-700">
              <span className="inline-flex gap-px">
                {[1, 2, 3, 4, 5].map((i) => (
                  <svg key={i} className={`h-3 w-3 ${i <= overallStar.numeric_value! ? "text-gray-600" : "text-gray-200"}`} fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </span>
              {overallStar.numeric_value}/5 Overall
              <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-52 -translate-x-1/2 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-normal leading-relaxed text-gray-600 opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                CMS Overall Five-Star Rating. National average: 3.0. This is a composite of health inspection, quality measure, and staffing ratings.
              </span>
            </span>
          )}
          {badges.map((b) => (
            <span
              key={b.label}
              className={`group relative inline-flex cursor-help items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${
                b.variant === "orange"
                  ? "border border-orange-200 bg-orange-50 text-orange-700"
                  : "border border-gray-200 bg-gray-50 text-gray-600"
              }`}
            >
              {b.variant === "orange" && (
                <svg className="h-3 w-3 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
              )}
              {b.label}
              {/* Hover tooltip */}
              <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-normal leading-relaxed text-gray-600 opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
                {b.tooltip}
              </span>
            </span>
          ))}
        </div>
      )}

      {/* Narrative summary — bridges badges and data */}
      {narrativeSentences.length > 0 && (() => {
        // Split into lead (bold) + rest. Lead = first sentence only when
        // it contains a strong signal (IJ, SFF, abuse, clean record).
        const first = narrativeSentences[0];
        const rest = narrativeSentences.slice(1);
        const hasStrongSignal = /immediate jeopardy|Special Focus|abuse|no deficiency citations/.test(first);

        return (
          <div className="mb-4">
            {hasStrongSignal ? (
              <>
                <p className="text-sm font-medium leading-relaxed text-gray-800">{first}</p>
                {rest.length > 0 && (
                  <p className="mt-1 text-sm leading-relaxed text-gray-600">{rest.join(" ")}</p>
                )}
              </>
            ) : (
              <p className="text-sm leading-relaxed text-gray-700">{narrativeSentences.join(" ")}</p>
            )}
            <p className="mt-1.5 text-[10px] text-gray-400">
              All statements reflect CMS-published data.{" "}
              <a
                href="https://data.cms.gov/provider-data/topics/nursing-homes"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-gray-500"
              >
                View CMS source data
              </a>
            </p>
          </div>
        );
      })()}

      {/* Facility Timeline — the lead visual element */}
      {hasTimelineData && (
        <div className="mb-4">
          <p className="mb-1 text-sm font-semibold text-gray-700">Facility History</p>
          <p className="mb-2 text-xs text-gray-400">
            Inspections, penalties, and staffing levels over time. Hover for details.
          </p>
          <FacilityTimeline
            inspectionEvents={events}
            penalties={pens}
            staffingTrend={ctx?.staffing_trend ?? null}
            standardSurveyDates={ctx?.standard_survey_dates ?? null}
            nationalAvgHprd={NATIONAL_AVG_TOTAL_NURSE_HPRD}
          />
        </div>
      )}

      {/* Five-Star ratings — prominent but with sub-ratings (NH-4) */}
      <div className="mb-4 border-t border-gray-100 pt-4">
        <p className="mb-2 text-base font-semibold text-gray-800">CMS Five-Star Ratings</p>
        <p className="mb-3 text-sm text-gray-500">
          CMS assigns ratings from 1 to 5 stars based on health inspections, staffing,
          and quality measures. These ratings are composites — see the underlying data below.
        </p>
        <FiveStarDisplay measures={measures} />
      </div>

      {/* PBJ Staffing Trend */}
      {ctx && <StaffingStats ctx={ctx} measures={measures} />}

      {/* Most Recent Inspection — concrete deficiency counts + severity mix */}
      {ctx && events.length > 0 && (
        <InspectionSummary
          inspectionEvents={events}
          ctx={ctx}
          providerLastUpdated={new Date().toISOString()}
          state={providerState ?? null}
        />
      )}

      {/* Ownership structure + parent group stats — visually anchors the page */}
      {ownership && ownership.length > 0 && (
        <div className="mt-6 border-t border-gray-100 pt-4">
          <p className="mb-1 text-sm font-semibold text-gray-700">Ownership Structure</p>
          <p className="mb-3 text-xs text-gray-400">
            Corporate ownership and management entities for this facility, with aggregate
            metrics across all facilities in the same parent group.
          </p>
          <OwnershipStructureViz
            ownership={ownership}
            facilityName={providerName}
            nursingHomeContext={ctx}
          />
          {parentGroupStats && (
            <div className="mt-4">
              <OwnershipGroupStats stats={parentGroupStats} />
            </div>
          )}
        </div>
      )}

      {/* Facility context — compact inline */}
      {ctx && (ctx.certified_beds != null || ctx.average_daily_census != null) && (
        <p className="mt-4 text-xs text-gray-400">
          {[
            ctx.certified_beds != null ? `${ctx.certified_beds} certified beds` : null,
            ctx.average_daily_census != null ? `${Math.round(ctx.average_daily_census)} avg daily census` : null,
          ].filter(Boolean).join(" · ")}
        </p>
      )}

      {/* IJ/fines/denials and urban covered by narrative + context line above */}
    </div>
  );
}
