// InspectionSummary — recent inspection events with citation count + severity mix.
//
// Groups events by time proximity: surveys within ~120 days of each other are
// treated as one inspection event (e.g., a standard survey + a follow-up
// revisit). Each group shows aggregate counts for that event window, with
// sub-rows per distinct survey date so users can see the standard vs. follow-up
// breakdown.
//
// This matters because CMS's Five-Star Health Inspection score weights all
// findings within a rating cycle (standard + revisit + complaint) together —
// a follow-up survey that finds 1 lingering citation is part of the same
// regulatory event as the original 8-citation finding.
//
// Display rules:
// - Severity colored only at J-L (DEC-030 + display-philosophy.md NH-8)
// - Per-event aggregates AND per-survey detail visible
// - Per-measure CMS attribution (Template 3b)

import type { InspectionEvent, NursingHomeContext } from "@/types/provider";
import {
  useStateInspectionAverages,
  getStateAverages,
  type InspectionAverages,
} from "@/lib/state-inspection-averages";

interface Props {
  inspectionEvents: InspectionEvent[];
  ctx: NursingHomeContext;
  providerLastUpdated: string;
  /** 2-char state code for this facility — drives the state-average row.
   *  Pass from provider.address.state. Optional: if null, only the national
   *  average is shown. */
  state?: string | null;
}

// Fallback national averages (used until state_inspection_averages.json loads
// or if it fails). Computed from CMS Health Deficiencies, same 120-day
// clustering. The fetched payload supersedes these when available.
//
// Why averages instead of percentages: "0.24 immediate jeopardy citations
// per inspection on average" is concrete and comparable to a specific
// facility's count. "2.4% of all national citations" obscures both the
// rarity of severe events and the scale of the comparison.
const NAT_AVG_FALLBACK: Pick<InspectionAverages, "ac" | "df" | "ghi" | "jkl" | "total"> = {
  ac: 0.17,
  df: 7.44,
  ghi: 0.31,
  jkl: 0.24,
  total: 8.15,
};

// Cluster events within this many days into the same inspection event
const CLUSTER_WINDOW_DAYS = 120;

interface SurveyDate {
  date: string;
  surveyType: string | null;
  isComplaint: boolean;
  citations: number;
  ac: number;
  df: number;
  ghi: number;
  jkl: number;
}

interface InspectionEventGroup {
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

function formatDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function shortDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function daysBetween(a: string, b: string): number {
  const ad = new Date(a).getTime();
  const bd = new Date(b).getTime();
  return Math.abs(ad - bd) / (1000 * 60 * 60 * 24);
}

function surveyKindLabel(s: SurveyDate): string {
  if (s.isComplaint) return "Complaint investigation";
  if (s.citations === 0) return "Standard survey (no deficiencies)";
  return "Standard survey";
}

function fmtVariationNumber(n: number): string {
  return n < 10 ? n.toFixed(1) : n.toFixed(0);
}

function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

export function InspectionSummary({
  inspectionEvents,
  ctx,
  providerLastUpdated,
  state,
}: Props): React.JSX.Element | null {
  const averagesPayload = useStateInspectionAverages();
  const stateAvg = getStateAverages(averagesPayload, state ?? null);
  const nationalAvg = averagesPayload?.national ?? null;
  // Step 1: group events by survey_date into per-survey rows
  const byDate = new Map<string, SurveyDate>();
  for (const e of inspectionEvents) {
    if (!e.survey_date) continue;
    const key = e.survey_date.slice(0, 10);
    let s = byDate.get(key);
    if (!s) {
      s = {
        date: key,
        surveyType: e.survey_type,
        isComplaint: e.is_complaint_deficiency,
        citations: 0,
        ac: 0, df: 0, ghi: 0, jkl: 0,
      };
      byDate.set(key, s);
    }
    s.citations++;
    const b = severityBucket(e.scope_severity_code);
    if (b) s[b]++;
    // If any event on this date is non-complaint, classify the survey as standard
    if (!e.is_complaint_deficiency) s.isComplaint = false;
  }

  const surveys = Array.from(byDate.values()).sort((a, b) => b.date.localeCompare(a.date));
  if (surveys.length === 0 && ctx.cycle_1_total_health_deficiencies == null) return null;

  // Step 2: cluster surveys into inspection events by time proximity.
  //
  // Window is anchored at the cluster's MOST RECENT date — the cluster includes
  // the most recent survey plus any survey within CLUSTER_WINDOW_DAYS BEFORE it.
  // Anchoring at the rolling earliest date would let an arbitrary chain of
  // surveys (each within 120 days of the next) merge across many months, which
  // would diverge from export_parent_group_stats.py and inflate the per-facility
  // event counts vs. the national/group baseline.
  const groups: InspectionEventGroup[] = [];
  for (const s of surveys) {
    const last = groups[groups.length - 1];
    const within = last && daysBetween(last.latestDate, s.date) <= CLUSTER_WINDOW_DAYS;
    if (within) {
      last.surveys.push(s);
      last.totalCitations += s.citations;
      last.ac += s.ac; last.df += s.df; last.ghi += s.ghi; last.jkl += s.jkl;
      // Surveys arrive newest-first, so `s.date` is older than `last.latestDate`;
      // update earliestDate downward.
      if (s.date < last.earliestDate) last.earliestDate = s.date;
    } else {
      groups.push({
        earliestDate: s.date,
        latestDate: s.date,
        surveys: [s],
        totalCitations: s.citations,
        ac: s.ac, df: s.df, ghi: s.ghi, jkl: s.jkl,
      });
    }
  }

  // Cap at the 3 most recent inspection events
  const recentGroups = groups.slice(0, 3);
  const mostRecent = recentGroups[0] ?? null;

  // Header: date range + survey breakdown for the most recent event
  let header: React.JSX.Element | null = null;
  if (mostRecent) {
    const dateRange = mostRecent.earliestDate === mostRecent.latestDate
      ? formatDate(mostRecent.latestDate)
      : `${shortDate(mostRecent.earliestDate)} – ${shortDate(mostRecent.latestDate)}`;
    const surveyDescription = mostRecent.surveys.length === 1
      ? surveyKindLabel(mostRecent.surveys[0])
      : `${mostRecent.surveys.length} surveys (${mostRecent.surveys.map(surveyKindLabel).join(", ").toLowerCase()})`;
    header = (
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className="text-sm font-semibold text-gray-800">{dateRange}</span>
          <span className="ml-2 text-xs text-gray-500">{surveyDescription}</span>
        </div>
        <div className="text-right text-xs">
          <span className="text-base font-bold tabular-nums text-gray-800">
            {mostRecent.totalCitations}
          </span>
          <span className="ml-1 text-gray-500">
            total citation{mostRecent.totalCitations !== 1 ? "s" : ""}
          </span>
          {mostRecent.jkl > 0 && (
            <span className="ml-2 font-semibold text-orange-700">
              {mostRecent.jkl} immediate jeopardy
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6 border-t border-gray-100 pt-4">
      <p className="mb-1 text-sm font-semibold text-gray-700">Most Recent Inspection Event</p>
      <p className="mb-3 text-xs text-gray-400">
        A standard survey and any follow-up revisits or complaint investigations within {CLUSTER_WINDOW_DAYS} days are treated as one inspection event.
      </p>

      {recentGroups.length === 0 ? (
        <p className="text-xs text-gray-400">
          {ctx.cycle_1_total_health_deficiencies != null
            ? `${ctx.cycle_1_total_health_deficiencies} deficiencies cited in the most recent CMS rating cycle. Detailed inspection events not yet loaded.`
            : "No inspection events available."}
        </p>
      ) : (
        <>
          {header}
          {mostRecent && (
            <SeverityComparison
              group={mostRecent}
              stateCode={state ?? null}
              stateAvg={stateAvg}
              nationalAvg={nationalAvg}
            />
          )}
        </>
      )}

      {mostRecent && mostRecent.jkl > 0 && (
        <p className="mt-3 rounded bg-orange-50 px-3 py-2 text-[11px] leading-relaxed text-orange-700">
          Immediate jeopardy citations (scope and severity J, K, or L) indicate
          findings that placed residents at risk of serious injury, harm, or death —
          the most serious tier of CMS deficiency findings.
        </p>
      )}

      {/* State variation note — surfaces the meta-context that inspection
          regimes differ by state, so cross-state comparisons need care. */}
      {stateAvg && nationalAvg && (
        <p className="mt-3 text-[11px] leading-relaxed text-gray-500">
          State context: {state} averages {fmtVariationNumber(stateAvg.total)} citations per inspection event
          ({fmtPct(stateAvg.pct_facilities_with_recent_ij)} of facilities had at least one immediate jeopardy citation in their most recent event),
          versus {fmtVariationNumber(nationalAvg.total)} nationally ({fmtPct(nationalAvg.pct_facilities_with_recent_ij)}).
          Inspection regimes vary substantially by state — citation counts and severity classifications reflect both facility quality and state inspection practices.
        </p>
      )}

      <p className="mt-3 text-[10px] text-gray-400">
        Source: CMS Nursing Home Health Deficiencies. Data reflects CMS reporting as of {formatDate(providerLastUpdated)}.
      </p>
    </div>
  );
}

// --- Severity comparison sub-component ---

interface SeverityComparisonProps {
  group: InspectionEventGroup;
  stateCode: string | null;
  stateAvg: InspectionAverages | null;
  nationalAvg: InspectionAverages | null;
}

interface ComparisonRow {
  range: string;
  label: string;
  facility: number;
  state: number | null;
  national: number;
  isJKL: boolean;
}

const SEVERITY_DESCRIPTIONS: Record<string, string> = {
  "J–L": "Immediate jeopardy. Findings that placed residents at risk of serious injury, harm, or death — the most serious tier of CMS deficiency findings.",
  "G–I": "Actual harm. Findings of harm to a resident that did not rise to the level of immediate jeopardy.",
  "D–F": "More than minimal potential for harm. The most common CMS citation tier; nearly all nursing homes have some D–F citations in any given inspection.",
  "A–C": "Minimal potential for harm. The least serious tier of CMS findings.",
};

function SeverityComparison({ group, stateCode, stateAvg, nationalAvg }: SeverityComparisonProps): React.JSX.Element {
  // Use fetched national if available, otherwise fall back to bundled constant
  // (handles edge case where the JSON fails to load).
  const nat = nationalAvg ?? NAT_AVG_FALLBACK;

  const rows: ComparisonRow[] = [
    { range: "J–L", label: "Immediate jeopardy", facility: group.jkl, state: stateAvg?.jkl ?? null, national: nat.jkl, isJKL: true },
    { range: "G–I", label: "Actual harm", facility: group.ghi, state: stateAvg?.ghi ?? null, national: nat.ghi, isJKL: false },
    { range: "D–F", label: "Moderate", facility: group.df, state: stateAvg?.df ?? null, national: nat.df, isJKL: false },
    { range: "A–C", label: "Low", facility: group.ac, state: stateAvg?.ac ?? null, national: nat.ac, isJKL: false },
  ];

  // Shared bar scale across all rows so visual length is comparable across severity tiers.
  const max = Math.max(
    ...rows.map((r) => Math.max(r.facility, r.state ?? 0, r.national)),
  ) * 1.15;
  const scale = max > 0 ? max : 1;

  const fmt = (n: number) =>
    n === 0 ? "0" : n < 1 ? n.toFixed(2) : n < 10 ? n.toFixed(1) : n.toFixed(0);

  return (
    <div className="mt-4 rounded-md border border-gray-200 bg-white p-3">
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
        Citations per inspection event — facility{stateCode && stateAvg ? `, ${stateCode} avg,` : ""} vs. national avg
      </p>
      <p className="mb-3 text-xs text-gray-400">
        State and national averages use each facility&apos;s most recent inspection event with the same 120-day clustering as above.
        State inspection regimes vary substantially, so the state row is the more directly comparable baseline.
      </p>

      <div className="space-y-3">
        {rows.map((r) => {
          const facWidth = (r.facility / scale) * 100;
          const stateWidth = r.state !== null ? (r.state / scale) * 100 : null;
          const natWidth = (r.national / scale) * 100;
          const showOrange = r.isJKL && r.facility > 0;
          const facilityColor = showOrange ? "bg-orange-500" : "bg-gray-700";
          // Ratio is relative to STATE when available (more meaningful given
          // state-to-state variation), else national.
          const benchVal = r.state ?? r.national;
          const benchLabel = r.state !== null ? `${stateCode} avg` : "nat'l";
          const ratio = benchVal > 0.05 ? r.facility / benchVal : null;
          const showRatio = ratio !== null && (ratio >= 2 || ratio <= 0.5);
          const description = SEVERITY_DESCRIPTIONS[r.range];

          return (
            <div key={r.range} className="group relative">
              <div className="mb-1 flex items-baseline justify-between text-sm">
                <span className={showOrange ? "font-semibold text-orange-700" : "text-gray-700"}>
                  {r.label}{" "}
                  <span className="text-xs text-gray-400">({r.range})</span>
                  <span
                    className="ml-1 inline-block cursor-help rounded-full border border-gray-200 px-1 text-[9px] font-medium text-gray-400 hover:border-gray-400 hover:text-gray-600"
                    aria-label={`About ${r.label} (${r.range})`}
                  >
                    ?
                  </span>
                </span>
                <span className="tabular-nums">
                  <span
                    className={`font-semibold ${showOrange ? "text-orange-700" : "text-gray-800"}`}
                    title={`This facility: ${fmt(r.facility)} ${r.label.toLowerCase()} citation${r.facility === 1 ? "" : "s"} in the most recent inspection event`}
                  >
                    {fmt(r.facility)}
                  </span>
                  {r.state !== null && (
                    <span
                      className="ml-2 text-gray-500"
                      title={`${stateCode} state average: ${fmt(r.state)} ${r.label.toLowerCase()} citation${r.state === 1 ? "" : "s"} per inspection event`}
                    >
                      {stateCode} {fmt(r.state)}
                    </span>
                  )}
                  <span
                    className="ml-2 text-gray-500"
                    title={`National average: ${fmt(r.national)} ${r.label.toLowerCase()} citation${r.national === 1 ? "" : "s"} per inspection event`}
                  >
                    nat&apos;l {fmt(r.national)}
                  </span>
                  {showRatio && ratio !== null && (
                    <span className={`ml-2 text-xs ${showOrange ? "text-orange-700" : "text-gray-500"}`}>
                      {ratio >= 2 ? `${ratio.toFixed(1)}× ${benchLabel}` : `${ratio.toFixed(2)}× ${benchLabel}`}
                    </span>
                  )}
                </span>
              </div>

              {/* Three-row mini bar chart: facility, state (if known), national */}
              <div className="space-y-1">
                {/* Facility bar */}
                <div className="flex items-center gap-2">
                  <span className="w-14 shrink-0 text-[11px] text-gray-500">facility</span>
                  <div
                    className="relative h-4 flex-1 rounded bg-gray-50"
                    title={`This facility's most recent inspection event: ${fmt(r.facility)} citation${r.facility === 1 ? "" : "s"} in the ${r.range} severity range.`}
                  >
                    <div
                      className={`h-4 rounded ${facilityColor}`}
                      style={{ width: `${Math.min(facWidth, 100)}%`, transition: "width 0.4s ease" }}
                    />
                  </div>
                </div>
                {/* State avg bar — only when known */}
                {stateWidth !== null && (
                  <div className="flex items-center gap-2">
                    <span className="w-14 shrink-0 text-[11px] text-gray-500">{stateCode} avg</span>
                    <div
                      className="relative h-4 flex-1 rounded bg-gray-50"
                      title={`${stateCode} state average: ${fmt(r.state!)} ${r.label.toLowerCase()} citation${r.state === 1 ? "" : "s"} per inspection event.`}
                    >
                      <div
                        className="h-4 rounded bg-gray-500"
                        style={{ width: `${Math.min(stateWidth, 100)}%`, transition: "width 0.4s ease" }}
                      />
                    </div>
                  </div>
                )}
                {/* National avg bar */}
                <div className="flex items-center gap-2">
                  <span className="w-14 shrink-0 text-[11px] text-gray-500">nat&apos;l avg</span>
                  <div
                    className="relative h-4 flex-1 rounded bg-gray-50"
                    title={`Across all CMS-inspected nursing homes, an average of ${fmt(r.national)} ${r.label.toLowerCase()} citation${r.national === 1 ? "" : "s"} per inspection event in the ${r.range} severity range.`}
                  >
                    <div
                      className="h-4 rounded bg-gray-300"
                      style={{ width: `${Math.min(natWidth, 100)}%`, transition: "width 0.4s ease" }}
                    />
                  </div>
                </div>
              </div>

              {/* Hover description tooltip */}
              {description && (
                <div className="pointer-events-none absolute left-0 top-full z-10 mt-1 hidden w-full max-w-md rounded-md border border-gray-200 bg-white px-3 py-2 text-xs leading-relaxed text-gray-600 shadow-lg group-hover:block">
                  {description}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
