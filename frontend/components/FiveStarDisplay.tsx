// FiveStarDisplay — compact inline CMS Five-Star sub-ratings.
//
// Display rules (display-philosophy.md NH-4):
// - Show overall + 3 domain ratings on one line with star icons
// - Not color-coded by value (DEC-030)
// - Footnotes that suppress ratings must be visible
// - Star ratings are ordinal, not continuous — no CIs (Rule 4)

import type { Measure } from "@/types/provider";

interface FiveStarDisplayProps {
  measures: Measure[];
}

const STAR_MEASURE_MAP: { id: string; label: string; avgLabel: string }[] = [
  { id: "NH_STAR_OVERALL", label: "Overall", avgLabel: "3.0" },
  { id: "NH_STAR_HEALTH_INSP", label: "Inspection", avgLabel: "2.8" },
  { id: "NH_STAR_QM", label: "Quality", avgLabel: "3.6" },
  { id: "NH_STAR_STAFFING", label: "Staffing", avgLabel: "2.9" },
];

function Stars({ value, max = 5 }: { value: number; max?: number }): React.JSX.Element {
  return (
    <span className="inline-flex gap-px">
      {Array.from({ length: max }, (_, i) => (
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

export function FiveStarDisplay({ measures }: FiveStarDisplayProps): React.JSX.Element | null {
  const ratings = STAR_MEASURE_MAP.map(({ id, label, avgLabel }) => {
    const m = measures.find(
      (measure) => measure.measure_id === id && measure.stratification === null
    );
    const value = m && !m.suppressed && !m.not_reported ? m.numeric_value : null;
    const suppressed = m?.suppressed ?? false;
    const footnotes = m?.footnote_text ?? null;
    return { label, value, suppressed, footnotes, avgLabel };
  });

  const hasAny = ratings.some((r) => r.value !== null);
  if (!hasAny) return null;

  return (
    <div>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
        {ratings.map((r) => (
          <div key={r.label} className="text-center">
            {r.value !== null ? (
              <>
                <div className="flex items-center justify-center gap-1">
                  <Stars value={r.value} />
                </div>
                <p className="mt-1 text-sm font-medium text-gray-700">{r.label}</p>
                <p className="text-xs text-gray-500">Nat&apos;l avg: {r.avgLabel}</p>
              </>
            ) : r.suppressed ? (
              <>
                <p className="text-sm text-gray-400">Suppressed</p>
                <p className="mt-1 text-sm font-medium text-gray-500">{r.label}</p>
              </>
            ) : (
              <>
                <p className="text-sm text-gray-300">—</p>
                <p className="mt-1 text-sm font-medium text-gray-500">{r.label}</p>
              </>
            )}
          </div>
        ))}
      </div>
      {ratings.some((r) => r.footnotes && r.footnotes.length > 0) && (
        <div className="mt-2 space-y-0.5">
          {ratings
            .filter((r) => r.footnotes && r.footnotes.length > 0)
            .map((r) => (
              <p key={r.label} className="text-[10px] text-gray-400">
                {r.label}: {r.footnotes!.join("; ")}
              </p>
            ))}
        </div>
      )}
    </div>
  );
}
