"use client";

// CompareFacilityTimeline — two FacilityTimeline panels stacked on a shared
// time axis. The aligned axis lets the user see directly when one facility
// had inspections, penalties, or staffing changes relative to the other.
//
// Approach: compute the union of both providers' event dates + staffing
// quarters, pass it as forcedAxisRange to each FacilityTimeline so the
// dates line up vertically. Legend is rendered once at the bottom rather
// than per-panel.

import type { Provider, StaffingTrendPeriod } from "@/types/provider";
import { titleCase } from "@/lib/utils";
import { NATIONAL_AVG_TOTAL_NURSE_HPRD } from "@/lib/constants";
import { FacilityTimeline } from "./FacilityTimeline";

interface CompareFacilityTimelineProps {
  providerA: Provider;
  providerB: Provider;
}

function parseQuarterMs(label: string): number | null {
  const m = label.match(/^Q(\d)\s+(\d{4})$/);
  if (!m) return null;
  const q = parseInt(m[1], 10);
  const y = parseInt(m[2], 10);
  return new Date(y, (q - 1) * 3, 15).getTime();
}

function collectDateMs(provider: Provider): number[] {
  const out: number[] = [];
  for (const e of provider.inspection_events ?? []) {
    if (!e.survey_date) continue;
    const [y, m, d] = e.survey_date.slice(0, 10).split("-").map(Number);
    out.push(new Date(y, m - 1, d).getTime());
  }
  for (const p of provider.penalties ?? []) {
    const ds = p.penalty_date ?? p.payment_denial_start_date;
    if (!ds) continue;
    const [y, m, d] = ds.slice(0, 10).split("-").map(Number);
    out.push(new Date(y, m - 1, d).getTime());
  }
  const trend: StaffingTrendPeriod[] | null = provider.nursing_home_context?.staffing_trend ?? null;
  if (trend) {
    for (const s of trend) {
      const ms = parseQuarterMs(s.quarter_label);
      if (ms !== null) out.push(ms);
    }
  }
  for (const s of provider.nursing_home_context?.standard_survey_dates ?? []) {
    const [y, m, d] = s.slice(0, 10).split("-").map(Number);
    out.push(new Date(y, m - 1, d).getTime());
  }
  return out;
}

function hasTimelineData(provider: Provider): boolean {
  if ((provider.inspection_events ?? []).length > 0) return true;
  if ((provider.penalties ?? []).length > 0) return true;
  const trend = provider.nursing_home_context?.staffing_trend ?? null;
  if (trend && trend.length >= 2) return true;
  return false;
}

export function CompareFacilityTimeline({
  providerA,
  providerB,
}: CompareFacilityTimelineProps): React.JSX.Element | null {
  const aHas = hasTimelineData(providerA);
  const bHas = hasTimelineData(providerB);
  if (!aHas && !bHas) return null;

  // Union of all dates from both providers — pad by 4% / minimum 60 days
  // (matches FacilityTimeline's internal padding so visual density matches).
  const allMs = [...collectDateMs(providerA), ...collectDateMs(providerB)];
  let forcedAxisRange: { startMs: number; endMs: number } | null = null;
  if (allMs.length > 0) {
    const minMs = Math.min(...allMs);
    const maxMs = Math.max(...allMs);
    const range = maxMs - minMs;
    const padMs = Math.max(range * 0.04, 60 * 24 * 3600 * 1000);
    forcedAxisRange = { startMs: minMs - padMs, endMs: maxMs + padMs };
  }

  const nameA = titleCase(providerA.name);
  const nameB = titleCase(providerB.name);

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-5 shadow-sm">
      <div className="mb-1 flex items-baseline justify-between">
        <h3 className="text-base font-semibold text-gray-800">Facility History</h3>
      </div>
      <p className="mb-4 text-xs text-gray-400">
        Inspections, penalties, and staffing for both facilities on the same time axis. Hover for details.
      </p>

      {/* Provider A panel */}
      <div className="mb-4">
        <p className="mb-1 flex items-center gap-2 text-xs font-bold text-blue-700">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-600" />
          {nameA}
        </p>
        {aHas ? (
          <FacilityTimeline
            inspectionEvents={providerA.inspection_events ?? []}
            penalties={providerA.penalties ?? []}
            staffingTrend={providerA.nursing_home_context?.staffing_trend ?? null}
            standardSurveyDates={providerA.nursing_home_context?.standard_survey_dates ?? null}
            nationalAvgHprd={NATIONAL_AVG_TOTAL_NURSE_HPRD}
            forcedAxisRange={forcedAxisRange}
            hideLegend
          />
        ) : (
          <p className="rounded border border-gray-100 bg-gray-50 px-3 py-2 text-xs text-gray-400">
            No inspection or penalty history available for this facility.
          </p>
        )}
      </div>

      {/* Provider B panel */}
      <div className="border-t border-gray-100 pt-4">
        <p className="mb-1 flex items-center gap-2 text-xs font-bold text-gray-800">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-700" />
          {nameB}
        </p>
        {bHas ? (
          <FacilityTimeline
            inspectionEvents={providerB.inspection_events ?? []}
            penalties={providerB.penalties ?? []}
            staffingTrend={providerB.nursing_home_context?.staffing_trend ?? null}
            standardSurveyDates={providerB.nursing_home_context?.standard_survey_dates ?? null}
            nationalAvgHprd={NATIONAL_AVG_TOTAL_NURSE_HPRD}
            forcedAxisRange={forcedAxisRange}
            hideLegend
          />
        ) : (
          <p className="rounded border border-gray-100 bg-gray-50 px-3 py-2 text-xs text-gray-400">
            No inspection or penalty history available for this facility.
          </p>
        )}
      </div>

      {/* Shared legend */}
      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-gray-100 pt-3 text-[10px] text-gray-500">
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
        <span className="flex items-center gap-1">
          <svg width="16" height="10"><line x1="0" y1="5" x2="16" y2="5" stroke="#2563eb" strokeWidth="2" /></svg>
          Staffing HPRD
        </span>
        <span className="flex items-center gap-1">
          <svg width="16" height="10"><line x1="0" y1="5" x2="16" y2="5" stroke="#ea580c" strokeWidth="1.5" strokeDasharray="4,3" opacity="0.7" /></svg>
          National avg
        </span>
      </div>

      <p className="mt-2 text-[10px] text-gray-400">
        Source: CMS Nursing Home Health Deficiencies, Nursing Home Penalties, and Payroll-Based Journal staffing data.
      </p>
    </div>
  );
}
