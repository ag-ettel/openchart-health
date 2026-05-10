// MeasurePicker — left-rail measure selector for /filter-explore.
//
// Groups measures by measure_group in the canonical render order. Mobile
// degrades to a native <select>. The picker is the single entry point —
// nothing else on the page renders measure data until a measure is selected.
//
// HCAHPS handling: the patient experience dataset ships each topic as 3-5
// response variants (Always/Usually/Sometimes-Never, Definitely Yes/Probably
// Yes/Probably-Definitely No, Yes/No, 9-10/7-8/0-6) plus a star rating and a
// linear mean score. Showing all of them in the picker is noise — selecting
// the primary "top response" is what 99% of users want, and the others are
// reachable via direct URL linking. The picker collapses HCAHPS to one entry
// per topic, labeled with the consumer-facing topic name, and points at the
// primary response variant.

"use client";

import { useMemo, useState } from "react";
import {
  FILTER_EXPLORE_PICKER_HEADING,
  FILTER_EXPLORE_PICKER_SEARCH_PLACEHOLDER,
  FILTER_EXPLORE_PRESETS_HEADING,
  FILTER_EXPLORE_SINGLE_MEASURE_HEADING,
  MEASURE_GROUP_DISPLAY_NAMES,
  MEASURE_GROUP_RENDER_ORDER,
  NH_MEASURE_GROUP_RENDER_ORDER,
  type FilterExplorePreset,
} from "@/lib/constants";
import { HCAHPS_GROUPS, hcahpsBase } from "@/lib/measure-tags";
import type { MeasureManifestEntry } from "@/lib/measure-index";

interface MeasurePickerProps {
  measures: MeasureManifestEntry[];
  presets: readonly FilterExplorePreset[];
  selectedMeasureId: string | null;
  selectedPresetId: string | null;
  onSelectMeasure: (measureId: string) => void;
  onSelectPreset: (presetId: string) => void;
}

// HCAHPS response polarity — for each topic, CMS publishes a positive end
// (Always, Definitely Yes, Yes, 9-10) and a negative end (Sometimes/Never,
// Probably/Definitely No, No, 0-6) plus a middle band. We surface the two
// ends in the picker because they're the most informative — the middle
// band is recoverable as 1 - (top + bottom). Tail-risk philosophy
// (CLAUDE.md): adverse responses are primary content, not secondary tabs.
const HCAHPS_TOP_RESPONSE = /_(A_P|DY|Y_P|9_10)$/;       // most favorable
const HCAHPS_BOTTOM_RESPONSE = /_(SN_P|DN|N_P|0_6)$/;    // least favorable

function isHCAHPSId(id: string): boolean {
  return id.startsWith("H_") && id !== "H_STAR_RATING";
}

type HCAHPSPolarity = "top" | "bottom" | "middle" | null;
function hcahpsPolarity(id: string): HCAHPSPolarity {
  if (HCAHPS_TOP_RESPONSE.test(id)) return "top";
  if (HCAHPS_BOTTOM_RESPONSE.test(id)) return "bottom";
  if (isHCAHPSId(id)) return "middle";
  return null;
}

const HCAHPS_TOP_LABEL_SUFFIX = " — top response %";
const HCAHPS_BOTTOM_LABEL_SUFFIX = " — adverse response %";

/** Display name with HCAHPS topic re-labeling. */
function displayName(entry: MeasureManifestEntry): string {
  const polarity = hcahpsPolarity(entry.measure_id);
  if (polarity === "top" || polarity === "bottom") {
    const base = hcahpsBase(entry.measure_id);
    if (base && HCAHPS_GROUPS[base]) {
      const suffix = polarity === "top" ? HCAHPS_TOP_LABEL_SUFFIX : HCAHPS_BOTTOM_LABEL_SUFFIX;
      return HCAHPS_GROUPS[base] + suffix;
    }
  }
  return entry.measure_name ?? entry.measure_id;
}

function groupLabel(group: string): string {
  return MEASURE_GROUP_DISPLAY_NAMES[group] ?? group;
}

/**
 * Reduce noise in the picker:
 *   - Drop measures nobody is reporting (reported_count === 0). These are
 *     measures where all values are suppressed or missing — selecting one
 *     just shows a table of "Suppressed" rows. Reachable via URL if needed.
 *   - For HCAHPS: keep two entries per topic — the top-response variant
 *     and the adverse-response variant. The middle band, linear-mean
 *     scores, and star ratings are dropped. The kept entries are re-labeled
 *     with the topic name and an explicit polarity suffix so users can pick
 *     whichever end of the distribution they want to sort by.
 */
function reducePickerEntries(measures: MeasureManifestEntry[]): MeasureManifestEntry[] {
  const out: MeasureManifestEntry[] = [];
  for (const m of measures) {
    if (m.reported_count === 0) continue;
    if (isHCAHPSId(m.measure_id)) {
      // Star ratings and linear scores → drop (no rendered numeric value)
      if (m.measure_id.endsWith("_STAR_RATING") || m.measure_id.endsWith("_LINEAR_SCORE")) {
        continue;
      }
      // Only keep the top-response and adverse-response polarities; drop the
      // middle band (Usually / Probably Yes / 7-8) — recoverable from the ends.
      const polarity = hcahpsPolarity(m.measure_id);
      if (polarity !== "top" && polarity !== "bottom") continue;
    }
    out.push(m);
  }
  return out;
}

export function MeasurePicker({
  measures,
  presets,
  selectedMeasureId,
  selectedPresetId,
  onSelectMeasure,
  onSelectPreset,
}: MeasurePickerProps): React.JSX.Element {
  const [search, setSearch] = useState("");
  const normalizedSearch = search.trim().toLowerCase();

  // Reduce picker entries first (collapse HCAHPS, drop 0-reporting), then
  // apply search across the reduced set.
  const reduced = useMemo(() => reducePickerEntries(measures), [measures]);

  // Filter by search across name, topic label, plain language, and measure id.
  const filtered = useMemo(() => {
    if (!normalizedSearch) return reduced;
    return reduced.filter((m) => {
      const haystack = [
        displayName(m),
        m.measure_name ?? "",
        m.measure_plain_language ?? "",
        m.measure_id,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedSearch);
    });
  }, [reduced, normalizedSearch]);

  // Group by measure_group, sort by canonical render order with unknown groups at end.
  const grouped = useMemo(() => {
    const map = new Map<string, MeasureManifestEntry[]>();
    for (const m of filtered) {
      const list = map.get(m.measure_group) ?? [];
      list.push(m);
      map.set(m.measure_group, list);
    }
    for (const list of map.values()) {
      list.sort((a, b) => {
        // Tail-risk measures lead each section (display-philosophy.md Rule 2).
        if (a.tail_risk_flag && !b.tail_risk_flag) return -1;
        if (!a.tail_risk_flag && b.tail_risk_flag) return 1;
        // For HCAHPS, sort by topic name so the top/adverse pair stays adjacent,
        // then top before adverse within each pair.
        const aBase = hcahpsBase(a.measure_id);
        const bBase = hcahpsBase(b.measure_id);
        if (aBase && bBase) {
          const aTopic = HCAHPS_GROUPS[aBase] ?? aBase;
          const bTopic = HCAHPS_GROUPS[bBase] ?? bBase;
          const t = aTopic.localeCompare(bTopic);
          if (t !== 0) return t;
          const aPol = hcahpsPolarity(a.measure_id);
          const bPol = hcahpsPolarity(b.measure_id);
          if (aPol === "top" && bPol === "bottom") return -1;
          if (aPol === "bottom" && bPol === "top") return 1;
        }
        return displayName(a).localeCompare(displayName(b));
      });
    }
    // Combine hospital and NH render orders so the picker can render either
    // provider type's groups in canonical order. Hospital groups come first,
    // followed by NH groups; in practice only one set is non-empty per page
    // because the manifest is filtered upstream by provider type.
    const combinedOrder = [...MEASURE_GROUP_RENDER_ORDER, ...NH_MEASURE_GROUP_RENDER_ORDER];
    const orderIndex = new Map(combinedOrder.map((g, i) => [g, i]));
    return Array.from(map.entries()).sort(([a], [b]) => {
      const ai = orderIndex.get(a) ?? 999;
      const bi = orderIndex.get(b) ?? 999;
      if (ai !== bi) return ai - bi;
      return a.localeCompare(b);
    });
  }, [filtered]);

  return (
    <aside className="w-full lg:w-72 lg:shrink-0">
      <div className="lg:sticky lg:top-16 lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto">
        <h2 className="mb-2 text-sm font-semibold text-gray-700">
          {FILTER_EXPLORE_PICKER_HEADING}
        </h2>

        {/* Preset views — multi-measure dashboards. Tail-risk presets first. */}
        <section className="mb-4">
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
            {FILTER_EXPLORE_PRESETS_HEADING}
          </h3>
          <ul className="space-y-0.5">
            {presets.map((p) => {
              const active = p.id === selectedPresetId;
              return (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => onSelectPreset(p.id)}
                    className={`flex w-full flex-col rounded px-2 py-1.5 text-left text-xs transition-colors ${
                      active
                        ? "bg-gray-200 font-semibold text-gray-900"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`}
                    title={p.description}
                  >
                    <span className="leading-snug">{p.label}</span>
                    <span className="mt-0.5 text-[10px] uppercase tracking-wide text-gray-400">
                      {p.measure_ids.length} measures
                      {p.tail_risk ? " · tail risk" : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>

        {/* Single-measure picker — search + grouped list. */}
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
          {FILTER_EXPLORE_SINGLE_MEASURE_HEADING}
        </h3>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={FILTER_EXPLORE_PICKER_SEARCH_PLACEHOLDER}
          className="mb-3 w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-700 placeholder:text-gray-400 focus:border-gray-500 focus:outline-none"
          aria-label={FILTER_EXPLORE_PICKER_SEARCH_PLACEHOLDER}
        />

        {grouped.length === 0 ? (
          <p className="text-xs text-gray-500">No measures match.</p>
        ) : (
          <div className="space-y-3">
            {grouped.map(([group, list]) => (
              <section key={group}>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
                  {groupLabel(group)}
                </h3>
                <ul className="space-y-0.5">
                  {list.map((m) => {
                    const active = m.measure_id === selectedMeasureId;
                    return (
                      <li key={m.measure_id}>
                        <button
                          type="button"
                          onClick={() => onSelectMeasure(m.measure_id)}
                          className={`flex w-full flex-col rounded px-2 py-1.5 text-left text-xs transition-colors ${
                            active
                              ? "bg-gray-200 font-semibold text-gray-900"
                              : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                          }`}
                        >
                          <span className="leading-snug">{displayName(m)}</span>
                          <span className="mt-0.5 text-[10px] uppercase tracking-wide text-gray-400">
                            {m.reported_count.toLocaleString("en-US")} reporting
                            {m.tail_risk_flag ? " · tail risk" : ""}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
