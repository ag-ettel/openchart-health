// CompareFiveStar — paired CMS Five-Star ratings (Overall + 3 sub-ratings)
// for two nursing homes, with national averages.
//
// Display rules (display-philosophy.md NH-4, Rule 4):
// - Star ratings are ordinal categorical, no error bars
// - No directional color coding (DEC-030)
// - Show suppression states explicitly with footnotes
// - Both facilities visible at the same prominence

import type { Measure } from "@/types/provider";

interface CompareFiveStarProps {
  measuresA: Measure[];
  measuresB: Measure[];
  nameA: string;
  nameB: string;
}

const STAR_MEASURE_MAP: { id: string; label: string; avgLabel: string }[] = [
  { id: "NH_STAR_OVERALL", label: "Overall", avgLabel: "3.0" },
  { id: "NH_STAR_HEALTH_INSP", label: "Inspection", avgLabel: "2.8" },
  { id: "NH_STAR_QM", label: "Quality", avgLabel: "3.6" },
  { id: "NH_STAR_STAFFING", label: "Staffing", avgLabel: "2.9" },
];

function findStar(measures: Measure[], id: string): Measure | null {
  return measures.find((m) => m.measure_id === id && m.stratification === null) ?? null;
}

interface StarCellState {
  value: number | null;
  suppressed: boolean;
  footnotes: string[] | null;
}

function getState(m: Measure | null): StarCellState {
  if (!m) return { value: null, suppressed: false, footnotes: null };
  if (m.suppressed) return { value: null, suppressed: true, footnotes: m.footnote_text };
  if (m.not_reported) return { value: null, suppressed: false, footnotes: m.footnote_text };
  return { value: m.numeric_value, suppressed: false, footnotes: m.footnote_text };
}

function StarRow({ value }: { value: number }): React.JSX.Element {
  return (
    <span className="inline-flex gap-px">
      {Array.from({ length: 5 }, (_, i) => (
        <svg
          key={i}
          className={`h-4 w-4 ${i < value ? "text-gray-700" : "text-gray-200"}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </span>
  );
}

function StarCell({ state }: { state: StarCellState }): React.JSX.Element {
  if (state.value !== null) {
    return (
      <div className="flex items-center gap-2">
        <StarRow value={state.value} />
        <span className="text-sm font-semibold tabular-nums text-gray-800">{state.value}/5</span>
      </div>
    );
  }
  if (state.suppressed) {
    return <p className="text-xs text-gray-400">Suppressed</p>;
  }
  return <p className="text-xs text-gray-400">Not rated</p>;
}

export function CompareFiveStar({ measuresA, measuresB, nameA, nameB }: CompareFiveStarProps): React.JSX.Element | null {
  const rows = STAR_MEASURE_MAP.map(({ id, label, avgLabel }) => {
    const a = findStar(measuresA, id);
    const b = findStar(measuresB, id);
    return {
      label,
      avgLabel,
      stateA: getState(a),
      stateB: getState(b),
    };
  });

  const anyData = rows.some((r) => r.stateA.value !== null || r.stateB.value !== null);
  if (!anyData) return null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-4 shadow-sm">
      <h3 className="text-base font-semibold text-gray-800">CMS Five-Star Ratings</h3>
      <p className="mt-1 text-xs text-gray-500">
        CMS assigns ratings from 1 to 5 stars. These are composites — see the underlying measures below.
      </p>

      {/* Header row with provider name labels (desktop) */}
      <div className="mt-4 hidden grid-cols-[8rem_1fr_1fr_4rem] items-end gap-x-4 gap-y-1 lg:grid">
        <span />
        <span className="flex items-center gap-1.5 text-xs font-bold text-blue-700">
          <span className="inline-block h-2 w-2 rounded-full bg-blue-600" />
          {nameA}
        </span>
        <span className="flex items-center gap-1.5 text-xs font-bold text-gray-800">
          <span className="inline-block h-2 w-2 rounded-full bg-gray-700" />
          {nameB}
        </span>
        <span className="text-right text-xs font-medium text-gray-500">Nat&apos;l avg</span>
      </div>

      <div className="mt-3 space-y-3 lg:mt-1">
        {rows.map((r) => (
          <div
            key={r.label}
            className="grid grid-cols-1 gap-y-1 lg:grid-cols-[8rem_1fr_1fr_4rem] lg:items-center lg:gap-x-4 lg:border-b lg:border-gray-100 lg:py-2 lg:last:border-b-0"
          >
            <p className="text-sm font-medium text-gray-700">{r.label}</p>

            {/* Provider A */}
            <div>
              <p className="lg:hidden text-[10px] font-bold uppercase tracking-wide text-blue-700">{nameA}</p>
              <StarCell state={r.stateA} />
            </div>

            {/* Provider B */}
            <div>
              <p className="lg:hidden text-[10px] font-bold uppercase tracking-wide text-gray-700">{nameB}</p>
              <StarCell state={r.stateB} />
            </div>

            <p className="text-xs text-gray-500 lg:text-right">
              <span className="lg:hidden">Nat&apos;l avg: </span>
              {r.avgLabel}
            </p>
          </div>
        ))}
      </div>

      {/* Footnotes — collected from both sides */}
      {rows.some((r) => (r.stateA.footnotes && r.stateA.footnotes.length > 0) || (r.stateB.footnotes && r.stateB.footnotes.length > 0)) && (
        <div className="mt-3 space-y-0.5">
          {rows.flatMap((r, i) => {
            const items: React.JSX.Element[] = [];
            if (r.stateA.footnotes && r.stateA.footnotes.length > 0) {
              items.push(
                <p key={`a-${i}`} className="text-[10px] text-gray-400">
                  {nameA} – {r.label}: {r.stateA.footnotes.join("; ")}
                </p>
              );
            }
            if (r.stateB.footnotes && r.stateB.footnotes.length > 0) {
              items.push(
                <p key={`b-${i}`} className="text-[10px] text-gray-400">
                  {nameB} – {r.label}: {r.stateB.footnotes.join("; ")}
                </p>
              );
            }
            return items;
          })}
        </div>
      )}

      <p className="mt-3 text-[10px] text-gray-400">
        Source: CMS Nursing Home Provider Information.
      </p>
    </div>
  );
}
