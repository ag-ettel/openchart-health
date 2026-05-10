// StaffingDetail — collapsible section showing all available staffing metrics.
//
// Shows reported vs CMS-adjusted hours side-by-side with national averages.
// The gap between reported and adjusted IS the case-mix adjustment story.

"use client";

import { useState } from "react";
import type { NursingHomeContext } from "@/types/provider";

interface Props {
  ctx: NursingHomeContext;
}

// National averages (CMS Feb 2026 snapshot)
const NAT_AVG = {
  reported_total: 3.89,
  reported_rn: 0.68,
  reported_aide: 2.29,
  reported_lpn: 0.57,
  adjusted_total: 3.96,
  adjusted_rn: 0.68,
  weekend_rn: 0.49,
  weekend_total: 3.14,
  pt: 0.06,
  turnover_total: 46.4,
  turnover_rn: 43.6,
};

interface MetricRow {
  label: string;
  value: number | null;
  adjustedValue?: number | null;
  nationalAvg: number;
  unit: string;
  note?: string;
}

function StaffingBar({ value, nationalAvg, unit, maxScale }: {
  value: number; nationalAvg: number; unit: string; maxScale: number;
}): React.JSX.Element {
  const pct = Math.min((value / maxScale) * 100, 100);
  const natPct = Math.min((nationalAvg / maxScale) * 100, 100);

  const format = (v: number) =>
    unit === "%" ? `${v.toFixed(1)}%` : v.toFixed(2);

  return (
    <div className="relative h-4 rounded-full bg-gray-100">
      <div
        className="h-4 rounded-full bg-indigo-300/70"
        style={{ width: `${pct}%`, transition: "width 0.4s ease" }}
      />
      <div
        className="absolute top-0 h-4 w-px bg-gray-500"
        style={{ left: `${natPct}%` }}
        title={`National avg: ${format(nationalAvg)}`}
      />
    </div>
  );
}

export function StaffingDetail({ ctx }: Props): React.JSX.Element | null {
  const [expanded, setExpanded] = useState(false);

  // Check if we have any staffing data at all
  const hasData = ctx.reported_total_hprd != null || ctx.adjusted_total_hprd != null;
  if (!hasData) return null;

  const metrics: MetricRow[] = [];

  // Hours per resident per day — reported vs adjusted
  if (ctx.reported_total_hprd != null) {
    metrics.push({
      label: "Total Nurse Hours",
      value: ctx.reported_total_hprd,
      adjustedValue: ctx.adjusted_total_hprd,
      nationalAvg: NAT_AVG.reported_total,
      unit: "hprd",
      note: "All nursing staff (RN + LPN + Aide)",
    });
  }
  if (ctx.reported_rn_hprd != null) {
    metrics.push({
      label: "RN Hours",
      value: ctx.reported_rn_hprd,
      adjustedValue: ctx.adjusted_rn_hprd,
      nationalAvg: NAT_AVG.reported_rn,
      unit: "hprd",
    });
  }
  if (ctx.reported_aide_hprd != null) {
    metrics.push({
      label: "Nurse Aide Hours",
      value: ctx.reported_aide_hprd,
      nationalAvg: NAT_AVG.reported_aide,
      unit: "hprd",
    });
  }
  if (ctx.reported_lpn_hprd != null) {
    metrics.push({
      label: "LPN Hours",
      value: ctx.reported_lpn_hprd,
      adjustedValue: ctx.adjusted_lpn_hprd,
      nationalAvg: NAT_AVG.reported_lpn,
      unit: "hprd",
    });
  }
  if (ctx.weekend_rn_hprd != null) {
    metrics.push({
      label: "Weekend RN Hours",
      value: ctx.weekend_rn_hprd,
      nationalAvg: NAT_AVG.weekend_rn,
      unit: "hprd",
      note: "RN staffing on weekends only",
    });
  }
  if (ctx.weekend_total_hprd != null) {
    metrics.push({
      label: "Weekend Total Hours",
      value: ctx.weekend_total_hprd,
      nationalAvg: NAT_AVG.weekend_total,
      unit: "hprd",
    });
  }
  if (ctx.pt_hprd != null && ctx.pt_hprd > 0) {
    metrics.push({
      label: "Physical Therapist Hours",
      value: ctx.pt_hprd,
      nationalAvg: NAT_AVG.pt,
      unit: "hprd",
    });
  }

  // Turnover
  if (ctx.total_turnover != null) {
    metrics.push({
      label: "Total Staff Turnover",
      value: ctx.total_turnover,
      nationalAvg: NAT_AVG.turnover_total,
      unit: "%",
      note: "Percentage of nursing staff who left in the reporting year",
    });
  }
  if (ctx.rn_turnover != null) {
    metrics.push({
      label: "RN Turnover",
      value: ctx.rn_turnover,
      nationalAvg: NAT_AVG.turnover_rn,
      unit: "%",
    });
  }

  if (metrics.length === 0) return null;

  const format = (v: number, unit: string) =>
    unit === "%" ? `${v.toFixed(1)}%` : v.toFixed(2);

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between rounded-md border border-gray-200 bg-gray-50 px-4 py-2 text-left text-sm font-medium text-gray-700 hover:bg-gray-100"
      >
        <span>Staffing Detail — All Metrics</span>
        <span className="text-xs text-gray-400">
          {expanded ? "Collapse" : `${metrics.length} metrics`}
          <svg
            className={`ml-1 inline h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </button>

      {expanded && (
        <div className="mt-2 rounded-md border border-gray-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between text-[10px] text-gray-400">
            <span>Source: CMS Payroll-Based Journal (PBJ). HPRD = hours per resident per day.</span>
            <span>Gray line = national average</span>
          </div>

          <div className="space-y-4">
            {metrics.map((m) => {
              const maxScale = m.unit === "%"
                ? Math.max(m.value ?? 0, m.nationalAvg, 100) * 1.1
                : Math.max(m.value ?? 0, m.adjustedValue ?? 0, m.nationalAvg) * 1.4;

              return (
                <div key={m.label}>
                  <div className="mb-1 flex items-center justify-between">
                    <div>
                      <span className="text-xs font-medium text-gray-700">{m.label}</span>
                      {m.note && (
                        <span className="ml-2 text-[10px] text-gray-400">{m.note}</span>
                      )}
                    </div>
                    <div className="text-right text-xs tabular-nums">
                      <span className="font-semibold text-gray-800">
                        {format(m.value ?? 0, m.unit)}
                      </span>
                      {m.adjustedValue != null && m.adjustedValue !== m.value && (
                        <span className="ml-2 text-gray-400">
                          adj: {format(m.adjustedValue, m.unit)}
                        </span>
                      )}
                      <span className="ml-2 text-gray-400">
                        avg: {format(m.nationalAvg, m.unit)}
                      </span>
                    </div>
                  </div>

                  {/* Reported bar */}
                  <StaffingBar
                    value={m.value ?? 0}
                    nationalAvg={m.nationalAvg}
                    unit={m.unit}
                    maxScale={maxScale}
                  />

                  {/* Adjusted bar (if different from reported) */}
                  {m.adjustedValue != null && m.adjustedValue !== m.value && (
                    <div className="mt-1">
                      <div className="mb-0.5 text-[9px] text-gray-400">Case-mix adjusted</div>
                      <div className="relative h-3 rounded-full bg-gray-100">
                        <div
                          className="h-3 rounded-full bg-indigo-200/60"
                          style={{
                            width: `${Math.min((m.adjustedValue / maxScale) * 100, 100)}%`,
                            transition: "width 0.4s ease",
                          }}
                        />
                        <div
                          className="absolute top-0 h-3 w-px bg-gray-500"
                          style={{ left: `${Math.min((m.nationalAvg / maxScale) * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Case-mix index context */}
          {ctx.nursing_casemix_index != null && (
            <div className="mt-4 rounded border border-gray-100 bg-gray-50 px-3 py-2 text-xs text-gray-600">
              <span className="font-medium">Case-Mix Index:</span>{" "}
              {ctx.nursing_casemix_index.toFixed(2)}
              <span className="ml-2 text-gray-400">
                (1.0 = average acuity; higher = sicker residents requiring more care)
              </span>
            </div>
          )}

          {/* Administrator departures */}
          {ctx.administrator_departures != null && (
            <div className="mt-2 text-xs text-gray-500">
              Administrator departures in reporting period: {ctx.administrator_departures}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
