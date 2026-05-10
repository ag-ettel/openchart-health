// CompareInspectionSummary — most-recent inspection event severity comparison
// for two nursing homes against the national average.
//
// Same 120-day clustering as InspectionSummary: inspections within 120 days
// of each other are treated as one event (a standard survey + any follow-up
// revisits and complaint investigations).
//
// Display rules:
// - J–L Immediate jeopardy is the load-bearing comparison row
// - Color encoding only at J-L when present (DEC-030 + NH-8)
// - All four severity tiers visible (NH-8 visual hierarchy)
// - Three bars per row (A | B | national) on a shared scale per row

import type { InspectionEvent } from "@/types/provider";
import {
  useStateInspectionAverages,
  getStateAverages,
  type InspectionAverages,
} from "@/lib/state-inspection-averages";

interface CompareInspectionSummaryProps {
  eventsA: InspectionEvent[];
  eventsB: InspectionEvent[];
  nameA: string;
  nameB: string;
  /** 2-char state codes (provider.address.state) — drive state-average rows. */
  stateA?: string | null;
  stateB?: string | null;
}

// Fallback national averages used until state_inspection_averages.json loads
// or if it fails. The fetched payload supersedes these.
const NAT_AVG_FALLBACK: Pick<InspectionAverages, "ac" | "df" | "ghi" | "jkl" | "total"> = {
  ac: 0.17,
  df: 7.44,
  ghi: 0.31,
  jkl: 0.24,
  total: 8.15,
};

const CLUSTER_WINDOW_DAYS = 120;

interface SurveyDate {
  date: string;
  isComplaint: boolean;
  citations: number;
  ac: number;
  df: number;
  ghi: number;
  jkl: number;
}

interface MostRecentEvent {
  earliestDate: string;
  latestDate: string;
  surveys: SurveyDate[];
  totalCitations: number;
  ac: number;
  df: number;
  ghi: number;
  jkl: number;
}

function severityBucket(code: string | null): "ac" | "df" | "ghi" | "jkl" | null {
  if (!code) return null;
  if ("ABC".includes(code)) return "ac";
  if ("DEF".includes(code)) return "df";
  if ("GHI".includes(code)) return "ghi";
  if ("JKL".includes(code)) return "jkl";
  return null;
}

function daysBetween(a: string, b: string): number {
  const ad = new Date(a).getTime();
  const bd = new Date(b).getTime();
  return Math.abs(ad - bd) / (1000 * 60 * 60 * 24);
}

function shortDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Compute the most recent inspection event using 120-day clustering. */
function mostRecentEvent(events: InspectionEvent[]): MostRecentEvent | null {
  const byDate = new Map<string, SurveyDate>();
  for (const e of events) {
    if (!e.survey_date) continue;
    const key = e.survey_date.slice(0, 10);
    let s = byDate.get(key);
    if (!s) {
      s = {
        date: key,
        isComplaint: e.is_complaint_deficiency,
        citations: 0,
        ac: 0, df: 0, ghi: 0, jkl: 0,
      };
      byDate.set(key, s);
    }
    s.citations++;
    const b = severityBucket(e.scope_severity_code);
    if (b) s[b]++;
    if (!e.is_complaint_deficiency) s.isComplaint = false;
  }

  const surveys = Array.from(byDate.values()).sort((a, b) => b.date.localeCompare(a.date));
  if (surveys.length === 0) return null;

  // Cluster surveys into one event by time proximity. The window is anchored at
  // the most recent date (cluster.latestDate, set on cluster creation and never
  // updated since surveys arrive newest-first). This matches
  // scripts/export_parent_group_stats.py so per-facility counts are comparable
  // with the parent-group / national aggregate baselines.
  let cluster: MostRecentEvent | null = null;
  for (const s of surveys) {
    if (!cluster) {
      cluster = {
        earliestDate: s.date,
        latestDate: s.date,
        surveys: [s],
        totalCitations: s.citations,
        ac: s.ac, df: s.df, ghi: s.ghi, jkl: s.jkl,
      };
    } else if (daysBetween(cluster.latestDate, s.date) <= CLUSTER_WINDOW_DAYS) {
      cluster.surveys.push(s);
      cluster.totalCitations += s.citations;
      cluster.ac += s.ac;
      cluster.df += s.df;
      cluster.ghi += s.ghi;
      cluster.jkl += s.jkl;
      if (s.date < cluster.earliestDate) cluster.earliestDate = s.date;
    } else {
      break;
    }
  }
  return cluster;
}

function fmtN(n: number): string {
  if (n === 0) return "0";
  if (n < 1) return n.toFixed(2);
  if (n < 10) return n.toFixed(1);
  return n.toFixed(0);
}

function eventDateRangeLabel(ev: MostRecentEvent): string {
  if (ev.earliestDate === ev.latestDate) return shortDate(ev.latestDate);
  return `${shortDate(ev.earliestDate)} – ${shortDate(ev.latestDate)}`;
}

export function CompareInspectionSummary({
  eventsA,
  eventsB,
  nameA,
  nameB,
  stateA,
  stateB,
}: CompareInspectionSummaryProps): React.JSX.Element | null {
  const evA = mostRecentEvent(eventsA);
  const evB = mostRecentEvent(eventsB);
  const averagesPayload = useStateInspectionAverages();
  if (!evA && !evB) return null;

  const stAvgA = getStateAverages(averagesPayload, stateA ?? null);
  const stAvgB = getStateAverages(averagesPayload, stateB ?? null);
  const nat = averagesPayload?.national ?? NAT_AVG_FALLBACK;
  // Full national row (with pct_facilities_with_recent_ij) is only available
  // once the JSON loads; fall back to null for the variation note when not.
  const fullNational = averagesPayload?.national ?? null;
  const sameState = stateA && stateB && stateA === stateB;

  type Row = {
    range: string;
    label: string;
    description: string;
    isJKL: boolean;
    a: number;
    b: number;
    stA: number | null;
    stB: number | null;
    nat: number;
  };
  const rows: Row[] = [
    {
      range: "J–L",
      label: "Immediate jeopardy",
      description: "Findings that placed residents at risk of serious injury, harm, or death — the most serious tier of CMS deficiency findings.",
      isJKL: true,
      a: evA?.jkl ?? 0,
      b: evB?.jkl ?? 0,
      stA: stAvgA?.jkl ?? null,
      stB: stAvgB?.jkl ?? null,
      nat: nat.jkl,
    },
    {
      range: "G–I",
      label: "Actual harm",
      description: "Findings of harm to a resident that did not rise to the level of immediate jeopardy.",
      isJKL: false,
      a: evA?.ghi ?? 0,
      b: evB?.ghi ?? 0,
      stA: stAvgA?.ghi ?? null,
      stB: stAvgB?.ghi ?? null,
      nat: nat.ghi,
    },
    {
      range: "D–F",
      label: "Moderate",
      description: "More than minimal potential for harm. The most common CMS citation tier.",
      isJKL: false,
      a: evA?.df ?? 0,
      b: evB?.df ?? 0,
      stA: stAvgA?.df ?? null,
      stB: stAvgB?.df ?? null,
      nat: nat.df,
    },
    {
      range: "A–C",
      label: "Low",
      description: "Minimal potential for harm. The least serious tier of CMS findings.",
      isJKL: false,
      a: evA?.ac ?? 0,
      b: evB?.ac ?? 0,
      stA: stAvgA?.ac ?? null,
      stB: stAvgB?.ac ?? null,
      nat: nat.ac,
    },
  ];

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-4 shadow-sm">
      <h3 className="text-base font-semibold text-gray-800">Most Recent Inspection Event</h3>
      <p className="mt-1 text-xs text-gray-400">
        A standard survey and any follow-up revisits or complaint investigations within {CLUSTER_WINDOW_DAYS} days are treated as one inspection event. Counts are citations per event.
      </p>

      {/* Per-facility headers — date range + total citations */}
      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div className="rounded-md border border-blue-100 bg-blue-50/50 px-3 py-2">
          <p className="flex items-center gap-1.5 text-xs font-bold text-blue-700">
            <span className="inline-block h-2 w-2 rounded-full bg-blue-600" />
            {nameA}
          </p>
          {evA ? (
            <>
              <p className="mt-0.5 text-xs text-gray-500">{eventDateRangeLabel(evA)}</p>
              <p className="mt-1 text-sm">
                <span className="font-bold text-gray-800">{evA.totalCitations}</span>
                <span className="ml-1 text-gray-500">total citation{evA.totalCitations !== 1 ? "s" : ""}</span>
                {evA.jkl > 0 && (
                  <span className="ml-2 font-semibold text-orange-700">{evA.jkl} immediate jeopardy</span>
                )}
              </p>
            </>
          ) : (
            <p className="mt-1 text-xs text-gray-400">No inspection events available.</p>
          )}
        </div>

        <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
          <p className="flex items-center gap-1.5 text-xs font-bold text-gray-700">
            <span className="inline-block h-2 w-2 rounded-full bg-gray-700" />
            {nameB}
          </p>
          {evB ? (
            <>
              <p className="mt-0.5 text-xs text-gray-500">{eventDateRangeLabel(evB)}</p>
              <p className="mt-1 text-sm">
                <span className="font-bold text-gray-800">{evB.totalCitations}</span>
                <span className="ml-1 text-gray-500">total citation{evB.totalCitations !== 1 ? "s" : ""}</span>
                {evB.jkl > 0 && (
                  <span className="ml-2 font-semibold text-orange-700">{evB.jkl} immediate jeopardy</span>
                )}
              </p>
            </>
          ) : (
            <p className="mt-1 text-xs text-gray-400">No inspection events available.</p>
          )}
        </div>
      </div>

      {/* Severity comparison bars — A | B | state(s) | national, per row */}
      <div className="mt-4 rounded-md border border-gray-100 bg-gray-50/50 p-3">
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
          Citations per inspection event by severity
        </p>
        <p className="mb-3 text-xs text-gray-400">
          Each facility&apos;s most recent inspection event with the same 120-day clustering, alongside state{!sameState && stateA && stateB ? "" : ""} and national averages.
          {!sameState && stateA && stateB && " Inspection regimes vary substantially by state — direct cross-state comparison should be made with care."}
        </p>

        <div className="space-y-4">
          {rows.map((r) => {
            // Scale considers everything that will render so visual lengths
            // stay proportionate across all bars in the row.
            const max = Math.max(r.a, r.b, r.stA ?? 0, r.stB ?? 0, r.nat) * 1.15;
            const scale = max > 0 ? max : 1;
            const w = (v: number | null) => (v === null ? 0 : (v / scale) * 100);
            const showOrangeA = r.isJKL && r.a > 0;
            const showOrangeB = r.isJKL && r.b > 0;

            return (
              <div key={r.range} className="group relative" title={r.description}>
                <div className="mb-1 flex items-baseline justify-between text-sm">
                  <span className={r.isJKL && (r.a > 0 || r.b > 0) ? "font-semibold text-orange-700" : "text-gray-700"}>
                    {r.label}{" "}
                    <span className="text-xs text-gray-400">({r.range})</span>
                  </span>
                </div>

                <div className="space-y-1">
                  {/* A */}
                  <div className="flex items-center gap-2">
                    <span className="w-32 shrink-0 truncate text-[11px] text-blue-700" title={nameA}>
                      <span className="mr-1 inline-block h-2 w-2 rounded-full bg-blue-600 align-middle" />
                      {nameA}
                    </span>
                    <div className="relative h-4 flex-1 rounded bg-gray-50">
                      <div
                        className={`h-4 rounded ${showOrangeA ? "bg-orange-500" : "bg-blue-500"}`}
                        style={{ width: `${Math.min(w(r.a), 100)}%`, transition: "width 0.4s ease" }}
                      />
                    </div>
                    <span className={`w-12 shrink-0 text-right text-sm font-semibold tabular-nums ${showOrangeA ? "text-orange-700" : "text-gray-800"}`}>
                      {fmtN(r.a)}
                    </span>
                  </div>

                  {/* B */}
                  <div className="flex items-center gap-2">
                    <span className="w-32 shrink-0 truncate text-[11px] text-gray-700" title={nameB}>
                      <span className="mr-1 inline-block h-2 w-2 rounded-full bg-gray-700 align-middle" />
                      {nameB}
                    </span>
                    <div className="relative h-4 flex-1 rounded bg-gray-50">
                      <div
                        className={`h-4 rounded ${showOrangeB ? "bg-orange-500" : "bg-gray-600"}`}
                        style={{ width: `${Math.min(w(r.b), 100)}%`, transition: "width 0.4s ease" }}
                      />
                    </div>
                    <span className={`w-12 shrink-0 text-right text-sm font-semibold tabular-nums ${showOrangeB ? "text-orange-700" : "text-gray-800"}`}>
                      {fmtN(r.b)}
                    </span>
                  </div>

                  {/* State avg row(s). Same-state pair: one row labeled with
                      the shared state. Cross-state: two rows, one per state. */}
                  {sameState && r.stA !== null && (
                    <div className="flex items-center gap-2">
                      <span className="w-32 shrink-0 text-[11px] text-gray-500">{stateA} avg</span>
                      <div className="relative h-4 flex-1 rounded bg-gray-50">
                        <div
                          className="h-4 rounded bg-gray-500"
                          style={{ width: `${Math.min(w(r.stA), 100)}%`, transition: "width 0.4s ease" }}
                        />
                      </div>
                      <span className="w-12 shrink-0 text-right text-xs tabular-nums text-gray-500">
                        {fmtN(r.stA)}
                      </span>
                    </div>
                  )}
                  {!sameState && r.stA !== null && (
                    <div className="flex items-center gap-2">
                      <span className="w-32 shrink-0 text-[11px] text-gray-500">{stateA} avg</span>
                      <div className="relative h-4 flex-1 rounded bg-gray-50">
                        <div
                          className="h-4 rounded bg-blue-300"
                          style={{ width: `${Math.min(w(r.stA), 100)}%`, transition: "width 0.4s ease" }}
                        />
                      </div>
                      <span className="w-12 shrink-0 text-right text-xs tabular-nums text-gray-500">
                        {fmtN(r.stA)}
                      </span>
                    </div>
                  )}
                  {!sameState && r.stB !== null && (
                    <div className="flex items-center gap-2">
                      <span className="w-32 shrink-0 text-[11px] text-gray-500">{stateB} avg</span>
                      <div className="relative h-4 flex-1 rounded bg-gray-50">
                        <div
                          className="h-4 rounded bg-gray-400"
                          style={{ width: `${Math.min(w(r.stB), 100)}%`, transition: "width 0.4s ease" }}
                        />
                      </div>
                      <span className="w-12 shrink-0 text-right text-xs tabular-nums text-gray-500">
                        {fmtN(r.stB)}
                      </span>
                    </div>
                  )}

                  {/* National avg */}
                  <div className="flex items-center gap-2">
                    <span className="w-32 shrink-0 text-[11px] text-gray-500">National avg</span>
                    <div className="relative h-4 flex-1 rounded bg-gray-50">
                      <div
                        className="h-4 rounded bg-gray-300"
                        style={{ width: `${Math.min(w(r.nat), 100)}%`, transition: "width 0.4s ease" }}
                      />
                    </div>
                    <span className="w-12 shrink-0 text-right text-xs tabular-nums text-gray-500">
                      {fmtN(r.nat)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {(evA?.jkl ?? 0) > 0 || (evB?.jkl ?? 0) > 0 ? (
          <p className="mt-3 rounded bg-orange-50 px-3 py-2 text-[11px] leading-relaxed text-orange-700">
            Immediate jeopardy citations (scope and severity J, K, or L) indicate findings that placed residents at risk of serious injury, harm, or death — the most serious tier of CMS deficiency findings.
          </p>
        ) : null}
      </div>

      {/* State-variation context */}
      {(stAvgA || stAvgB) && (
        <p className="mt-3 text-[11px] leading-relaxed text-gray-500">
          {sameState && stAvgA && (
            <>
              State context: {stateA} averages {fmtN(stAvgA.total)} citations per inspection event,
              with {(stAvgA.pct_facilities_with_recent_ij * 100).toFixed(1)}% of facilities having at least one immediate jeopardy citation in their most recent event.
              {fullNational && (
                <> National: {fmtN(fullNational.total)} citations, {(fullNational.pct_facilities_with_recent_ij * 100).toFixed(1)}% with recent IJ.</>
              )}
            </>
          )}
          {!sameState && stAvgA && stAvgB && (
            <>
              State context: {stateA} averages {fmtN(stAvgA.total)} citations per event ({(stAvgA.pct_facilities_with_recent_ij * 100).toFixed(1)}% with recent IJ);{" "}
              {stateB} averages {fmtN(stAvgB.total)} citations per event ({(stAvgB.pct_facilities_with_recent_ij * 100).toFixed(1)}% with recent IJ).
              {" "}Inspection regimes vary by state, so cross-state facility comparison reflects both facility quality and state inspection practices.
            </>
          )}
          {!sameState && (stAvgA || stAvgB) && !(stAvgA && stAvgB) && (
            <>
              State context: {stateA && stAvgA ? `${stateA} averages ${fmtN(stAvgA.total)} citations per event` : `${stateB} averages ${fmtN(stAvgB!.total)} citations per event`}.
              National: {fmtN(nat.total)} citations per event.
              Inspection regimes vary by state.
            </>
          )}
        </p>
      )}

      <p className="mt-3 text-[10px] text-gray-400">
        Source: CMS Nursing Home Health Deficiencies.
      </p>
    </div>
  );
}
