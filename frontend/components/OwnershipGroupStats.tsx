// OwnershipGroupStats — aggregate citation, fine, and gate-condition metrics
// for the parent ownership group, vs national averages.
//
// Aggregations use the same 120-day inspection clustering as the per-facility
// InspectionSummary view: each facility's most recent inspection event is the
// unit of comparison.
//
// Legal compliance: per legal-compliance.md § Ownership Data, the disclosure
// states that aggregation does not establish a causal relationship between
// ownership and quality outcomes.

import { OWNERSHIP_QUALITY_DISCLAIMER } from "@/lib/constants";
import type { ParentGroupStats } from "@/types/provider";

interface Props {
  stats: ParentGroupStats;
}

const SEVERITY_DESCRIPTIONS: Record<string, string> = {
  "J–L": "Immediate jeopardy. Findings that placed residents at risk of serious injury, harm, or death — the most serious tier of CMS deficiency findings.",
  "G–I": "Actual harm. Findings of harm to a resident that did not rise to the level of immediate jeopardy.",
  "D–F": "More than minimal potential for harm. The most common CMS citation tier; nearly all nursing homes have some D–F citations in any given inspection.",
  "A–C": "Minimal potential for harm. The least serious tier of CMS findings.",
};

interface RowDef {
  range: string;
  label: string;
  group: number | null;
  national: number;
  isJKL: boolean;
}

function fmt(n: number): string {
  if (n === 0) return "0";
  if (n < 1) return n.toFixed(2);
  if (n < 10) return n.toFixed(1);
  return n.toFixed(0);
}

function fmtMoney(n: number): string {
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

export function OwnershipGroupStats({ stats }: Props): React.JSX.Element {
  const s = stats;

  const sffPct = s.facility_count > 0 ? s.sff_count / s.facility_count : 0;
  const abusePct = s.facility_count > 0 ? s.abuse_icon_count / s.facility_count : 0;

  // Severity rows in order: most severe first
  const severityRows: RowDef[] = [
    { range: "J–L", label: "Immediate jeopardy", group: s.avg_jkl_per_event, national: s.nat_avg_jkl_per_event, isJKL: true },
    { range: "G–I", label: "Actual harm", group: s.avg_ghi_per_event, national: s.nat_avg_ghi_per_event, isJKL: false },
    { range: "D–F", label: "Moderate", group: s.avg_df_per_event, national: s.nat_avg_df_per_event, isJKL: false },
    { range: "A–C", label: "Low", group: s.avg_ac_per_event, national: s.nat_avg_ac_per_event, isJKL: false },
  ];

  const sevMax = Math.max(
    ...severityRows.map((r) => Math.max(r.group ?? 0, r.national))
  ) * 1.15;
  const sevScale = sevMax > 0 ? sevMax : 1;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-gray-800">
          {s.parent_group_name}
        </h3>
        <span className="text-xs text-gray-500">
          {s.facility_count.toLocaleString()} facilities · group averages vs. national
        </span>
      </div>

      {/* Severity comparison — same visual language as InspectionSummary */}
      <div className="mb-4 rounded-md border border-gray-100 bg-gray-50/50 p-3">
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
          Average citations per inspection event
        </p>
        <p className="mb-3 text-xs text-gray-400">
          Each facility&apos;s most recent inspection event (standard survey + any follow-up revisits within 120 days), averaged across the {s.facility_count.toLocaleString()} facilities in this ownership group.
        </p>

        <div className="space-y-3">
          {severityRows.map((r) => {
            const groupVal = r.group ?? 0;
            const facWidth = (groupVal / sevScale) * 100;
            const natWidth = (r.national / sevScale) * 100;
            const showOrange = r.isJKL && groupVal > r.national * 1.1;
            const groupColor = showOrange ? "bg-orange-500" : "bg-indigo-500";
            const ratio = r.national > 0.05 ? groupVal / r.national : null;
            // Always show ratio when meaningfully different from 1.0.
            // Tighter threshold for J-L since small multipliers matter at high severity.
            const showRatio = ratio !== null && (
              r.isJKL ? (ratio >= 1.1 || ratio <= 0.9) : (ratio >= 1.2 || ratio <= 0.8)
            );
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
                    <span className={`font-semibold ${showOrange ? "text-orange-700" : "text-gray-800"}`}>
                      {fmt(groupVal)}
                    </span>
                    <span className="ml-2 text-gray-500">
                      nat&apos;l {fmt(r.national)}
                    </span>
                    {showRatio && ratio !== null && (
                      <span className={`ml-2 text-xs ${showOrange ? "text-orange-700" : "text-gray-500"}`}>
                        {ratio >= 2 ? `${ratio.toFixed(1)}× avg` : ratio < 1 ? `${ratio.toFixed(2)}× avg` : `${ratio.toFixed(2)}× avg`}
                      </span>
                    )}
                  </span>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="w-14 shrink-0 text-[11px] text-gray-500">group</span>
                    <div
                      className="relative h-4 flex-1 rounded bg-gray-100"
                      title={`Average ${fmt(groupVal)} ${r.label.toLowerCase()} citation${groupVal === 1 ? "" : "s"} per inspection event across ${s.facility_count.toLocaleString()} ${s.parent_group_name} facilities.`}
                    >
                      <div
                        className={`h-4 rounded ${groupColor}`}
                        style={{ width: `${Math.min(facWidth, 100)}%`, transition: "width 0.4s ease" }}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-14 shrink-0 text-[11px] text-gray-500">nat&apos;l avg</span>
                    <div
                      className="relative h-4 flex-1 rounded bg-gray-100"
                      title={`National average: ${fmt(r.national)} ${r.label.toLowerCase()} citation${r.national === 1 ? "" : "s"} per inspection event.`}
                    >
                      <div
                        className="h-4 rounded bg-gray-300"
                        style={{ width: `${Math.min(natWidth, 100)}%`, transition: "width 0.4s ease" }}
                      />
                    </div>
                  </div>
                </div>

                {description && (
                  <div className="pointer-events-none absolute left-0 top-full z-10 mt-1 hidden w-full max-w-md rounded-md border border-gray-200 bg-white px-3 py-2 text-xs leading-relaxed text-gray-600 shadow-lg group-hover:block">
                    {description}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {s.pct_facilities_with_recent_ij != null && s.facilities_with_recent_ij != null && (
          <p className="mt-3 text-xs text-gray-600">
            <span className="font-semibold">{s.facilities_with_recent_ij}</span> of {s.facility_count.toLocaleString()} facilities
            (<span className="font-semibold">{fmtPct(s.pct_facilities_with_recent_ij)}</span>) had at least one immediate jeopardy citation in their most recent inspection event.
            {s.nat_pct_facilities_with_recent_ij != null && (
              <span className="text-gray-400"> Nationally, {fmtPct(s.nat_pct_facilities_with_recent_ij)} of nursing homes had at least one in their most recent event.</span>
            )}
          </p>
        )}
      </div>

      {/* Staffing-threshold rollup — categorical signal (% below CMS minimum
          HPRD), more interpretable than a raw HPRD average since it maps to
          a CMS-defined floor. Only rendered when the group has at least one
          facility with a reported staffing value. */}
      {((s.facilities_with_reported_total_hprd ?? 0) > 0 ||
        (s.facilities_with_reported_rn_hprd ?? 0) > 0) && (
        <div className="mb-4 rounded-md border border-gray-100 bg-gray-50/50 p-3">
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
            Facilities reporting below CMS minimum staffing
          </p>
          <p className="mb-3 text-xs text-gray-400">
            Share of group facilities whose most recent reported staffing falls
            below the CMS minimum hours per resident per day.
            Threshold rule: CMS-3442-F (Minimum Staffing Standards for Long-Term
            Care Facilities, finalized May 2024, phased implementation).
            Facilities without reported staffing are excluded from the denominator.
          </p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {/* Total nurse staffing */}
            {(s.facilities_with_reported_total_hprd ?? 0) > 0 && s.pct_below_total_nurse_threshold != null && (
              <ThresholdRow
                label="Total nurse staffing"
                threshold={s.min_total_nurse_hprd_threshold ?? 3.48}
                pct={s.pct_below_total_nurse_threshold}
                numerator={s.facilities_below_total_nurse_threshold ?? 0}
                denominator={s.facilities_with_reported_total_hprd ?? 0}
                natPct={s.nat_pct_below_total_nurse_threshold ?? null}
              />
            )}
            {/* RN staffing */}
            {(s.facilities_with_reported_rn_hprd ?? 0) > 0 && s.pct_below_rn_threshold != null && (
              <ThresholdRow
                label="RN staffing"
                threshold={s.min_rn_hprd_threshold ?? 0.55}
                pct={s.pct_below_rn_threshold}
                numerator={s.facilities_below_rn_threshold ?? 0}
                denominator={s.facilities_with_reported_rn_hprd ?? 0}
                natPct={s.nat_pct_below_rn_threshold ?? null}
              />
            )}
          </div>
        </div>
      )}

      {/* Penalties + gate-condition tiles */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
          <p className="text-[10px] font-medium uppercase tracking-wide text-gray-400">
            Avg fines
          </p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums text-gray-800">
            {s.avg_fines != null ? fmtMoney(s.avg_fines) : "—"}
          </p>
          {s.nat_avg_fines != null && (
            <p className="text-[10px] text-gray-500">nat&apos;l {fmtMoney(s.nat_avg_fines)}</p>
          )}
        </div>
        <div className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
          <p className="text-[10px] font-medium uppercase tracking-wide text-gray-400">
            Avg penalties
          </p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums text-gray-800">
            {s.avg_penalties != null ? s.avg_penalties.toFixed(1) : "—"}
          </p>
          {s.nat_avg_penalties != null && (
            <p className="text-[10px] text-gray-500">nat&apos;l {s.nat_avg_penalties.toFixed(1)}</p>
          )}
        </div>
        <div className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
          <p className="text-[10px] font-medium uppercase tracking-wide text-gray-400">
            Special Focus
          </p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums text-gray-800">
            {s.sff_count} <span className="text-xs font-normal text-gray-500">({fmtPct(sffPct)})</span>
          </p>
          {s.nat_pct_sff != null && (
            <p className="text-[10px] text-gray-500">nat&apos;l {fmtPct(s.nat_pct_sff)}</p>
          )}
        </div>
        <div className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
          <p className="text-[10px] font-medium uppercase tracking-wide text-gray-400">
            Abuse icon
          </p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums text-gray-800">
            {s.abuse_icon_count} <span className="text-xs font-normal text-gray-500">({fmtPct(abusePct)})</span>
          </p>
          {s.nat_pct_abuse != null && (
            <p className="text-[10px] text-gray-500">nat&apos;l {fmtPct(s.nat_pct_abuse)}</p>
          )}
        </div>
      </div>

      <p className="mt-3 text-[10px] leading-relaxed text-gray-400">
        Averages computed from CMS-published per-facility data across all facilities associated with this ownership group. {OWNERSHIP_QUALITY_DISCLAIMER}
      </p>
    </div>
  );
}

/** One staffing-threshold row: percentage bar + numerator/denominator + nat'l reference. */
function ThresholdRow({
  label,
  threshold,
  pct,
  numerator,
  denominator,
  natPct,
}: {
  label: string;
  threshold: number;
  pct: number;
  numerator: number;
  denominator: number;
  natPct: number | null;
}): React.JSX.Element {
  const widthPct = Math.min(100, pct * 100);
  return (
    <div className="rounded border border-gray-100 bg-white px-3 py-2">
      <p className="text-xs font-medium text-gray-700">
        {label}
        <span className="ml-1 text-[10px] font-normal text-gray-400">
          (CMS minimum {threshold.toFixed(2)} HPRD)
        </span>
      </p>
      <div className="mt-1.5 flex items-center gap-2">
        <div className="relative h-3 flex-1 rounded bg-gray-50">
          <div
            className="h-3 rounded bg-gray-600"
            style={{ width: `${widthPct}%`, transition: "width 0.4s ease" }}
          />
        </div>
        <span className="shrink-0 text-sm font-semibold tabular-nums text-gray-800">
          {(pct * 100).toFixed(1)}%
        </span>
      </div>
      <div className="mt-1 flex items-baseline justify-between text-[10px] text-gray-500">
        <span>
          {numerator.toLocaleString()} of {denominator.toLocaleString()} reporting
        </span>
        {natPct != null && <span>nat&apos;l {(natPct * 100).toFixed(1)}%</span>}
      </div>
    </div>
  );
}
