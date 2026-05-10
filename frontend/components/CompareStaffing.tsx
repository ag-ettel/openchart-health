"use client";

// CompareStaffing — paired Total Nurse HPRD, RN HPRD, and Staff Turnover for
// two nursing homes with national averages.
//
// Visual approach mirrors OwnershipGroupStats: each metric has two stacked bars
// (Provider A | Provider B) with national average underneath, all on a shared
// scale per metric so visual length is comparable.
//
// Data sources (in order of preference):
// 1. NH measures (NH_STAFF_REPORTED_TOTAL_HPRD, NH_STAFF_REPORTED_RN_HPRD,
//    NH_STAFF_TOTAL_TURNOVER) — provides values + trend
// 2. nursing_home_context fields — fallback when measures absent
//
// No directional color coding (DEC-030).

import type { Measure, NursingHomeContext } from "@/types/provider";

interface CompareStaffingProps {
  measuresA: Measure[];
  measuresB: Measure[];
  ctxA: NursingHomeContext | null;
  ctxB: NursingHomeContext | null;
  nameA: string;
  nameB: string;
}

interface MetricRow {
  key: string;
  label: string;
  unit: "HPRD" | "%";
  natAvg: number;
  natAvgLabel: string;
  valueA: number | null;
  valueB: number | null;
  description: string;
}

function findMeasure(measures: Measure[], id: string): Measure | null {
  const m = measures.find((m) => m.measure_id === id && m.stratification === null);
  if (!m) return null;
  if (m.suppressed || m.not_reported) return null;
  return m;
}

function fmtValue(v: number | null, unit: "HPRD" | "%"): string {
  if (v === null) return "—";
  if (unit === "%") return `${v.toFixed(0)}%`;
  return v.toFixed(unit === "HPRD" ? 2 : 1);
}

export function CompareStaffing({
  measuresA,
  measuresB,
  ctxA,
  ctxB,
  nameA,
  nameB,
}: CompareStaffingProps): React.JSX.Element | null {
  const rnA = findMeasure(measuresA, "NH_STAFF_REPORTED_RN_HPRD")?.numeric_value ?? ctxA?.reported_rn_hprd ?? null;
  const rnB = findMeasure(measuresB, "NH_STAFF_REPORTED_RN_HPRD")?.numeric_value ?? ctxB?.reported_rn_hprd ?? null;
  const totalA = findMeasure(measuresA, "NH_STAFF_REPORTED_TOTAL_HPRD")?.numeric_value ?? ctxA?.reported_total_hprd ?? null;
  const totalB = findMeasure(measuresB, "NH_STAFF_REPORTED_TOTAL_HPRD")?.numeric_value ?? ctxB?.reported_total_hprd ?? null;
  const turnoverA = findMeasure(measuresA, "NH_STAFF_TOTAL_TURNOVER")?.numeric_value ?? ctxA?.total_turnover ?? null;
  const turnoverB = findMeasure(measuresB, "NH_STAFF_TOTAL_TURNOVER")?.numeric_value ?? ctxB?.total_turnover ?? null;

  if (rnA === null && rnB === null && totalA === null && totalB === null && turnoverA === null && turnoverB === null) {
    return null;
  }

  const rows: MetricRow[] = [
    {
      key: "total",
      label: "Total Nurse Hours",
      unit: "HPRD",
      natAvg: 3.9,
      natAvgLabel: "3.9",
      valueA: totalA,
      valueB: totalB,
      description: "Hours of total nursing time per resident per day (PBJ).",
    },
    {
      key: "rn",
      label: "RN Hours",
      unit: "HPRD",
      natAvg: 0.68,
      natAvgLabel: "0.68",
      valueA: rnA,
      valueB: rnB,
      description: "Hours of registered-nurse time per resident per day (PBJ).",
    },
    {
      key: "turnover",
      label: "Staff Turnover",
      unit: "%",
      natAvg: 46,
      natAvgLabel: "46%",
      valueA: turnoverA,
      valueB: turnoverB,
      description: "Percentage of nursing staff who left in the reporting year.",
    },
  ];

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-4 shadow-sm">
      <h3 className="text-base font-semibold text-gray-800">Staffing</h3>
      <p className="mt-1 text-xs text-gray-500">
        From CMS Payroll-Based Journal (PBJ). HPRD = hours per resident per day.
      </p>

      <div className="mt-4 space-y-5">
        {rows.map((row) => {
          const max = Math.max(
            row.valueA ?? 0,
            row.valueB ?? 0,
            row.natAvg,
          ) * 1.15;
          const scale = max > 0 ? max : 1;

          const wA = row.valueA !== null ? (row.valueA / scale) * 100 : 0;
          const wB = row.valueB !== null ? (row.valueB / scale) * 100 : 0;
          const wNat = (row.natAvg / scale) * 100;

          return (
            <div key={row.key}>
              <div className="mb-1 flex items-baseline justify-between">
                <p className="text-sm font-medium text-gray-700">{row.label}</p>
                <p className="text-xs text-gray-400">{row.description}</p>
              </div>

              {/* A bar */}
              <div className="mb-1 flex items-center gap-2">
                <span className="w-32 shrink-0 truncate text-xs text-blue-700" title={nameA}>
                  <span className="mr-1 inline-block h-2 w-2 rounded-full bg-blue-600 align-middle" />
                  {nameA}
                </span>
                <div className="relative h-4 flex-1 rounded bg-gray-50">
                  {row.valueA !== null && (
                    <div
                      className="h-4 rounded bg-blue-500"
                      style={{ width: `${Math.min(wA, 100)}%`, transition: "width 0.4s ease" }}
                    />
                  )}
                </div>
                <span className="w-16 shrink-0 text-right text-sm font-semibold tabular-nums text-gray-800">
                  {fmtValue(row.valueA, row.unit)}
                </span>
              </div>

              {/* B bar */}
              <div className="mb-1 flex items-center gap-2">
                <span className="w-32 shrink-0 truncate text-xs text-gray-700" title={nameB}>
                  <span className="mr-1 inline-block h-2 w-2 rounded-full bg-gray-700 align-middle" />
                  {nameB}
                </span>
                <div className="relative h-4 flex-1 rounded bg-gray-50">
                  {row.valueB !== null && (
                    <div
                      className="h-4 rounded bg-gray-600"
                      style={{ width: `${Math.min(wB, 100)}%`, transition: "width 0.4s ease" }}
                    />
                  )}
                </div>
                <span className="w-16 shrink-0 text-right text-sm font-semibold tabular-nums text-gray-800">
                  {fmtValue(row.valueB, row.unit)}
                </span>
              </div>

              {/* National avg bar */}
              <div className="flex items-center gap-2">
                <span className="w-32 shrink-0 text-xs text-gray-500">National avg</span>
                <div className="relative h-4 flex-1 rounded bg-gray-50">
                  <div
                    className="h-4 rounded bg-gray-300"
                    style={{ width: `${Math.min(wNat, 100)}%`, transition: "width 0.4s ease" }}
                  />
                </div>
                <span className="w-16 shrink-0 text-right text-xs tabular-nums text-gray-500">
                  {row.natAvgLabel}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-4 text-[10px] text-gray-400">
        Source: CMS Nursing Home Provider Information (PBJ-derived staffing).
      </p>
    </div>
  );
}
