"use client";

// Category filter sidebar with grouped sections and expandable measure previews.
// Desktop: sticky left sidebar. Mobile: horizontal scrollable filter bar.

import { useState } from "react";
import { MEASURE_TAGS } from "@/lib/measure-tags";
import type { MeasureTag } from "@/lib/measure-tags";

interface CategoryNavProps {
  activeTag: string | null;
  onTagChange: (tag: string | null) => void;
  tagCounts: Record<string, number>;
  /** Map of tag id → measure names in that tag, for the preview list */
  tagMeasureNames?: Record<string, string[]>;
}

function TagButton({
  tag,
  active,
  count,
  measureNames,
  onClick,
}: {
  tag: MeasureTag;
  active: boolean;
  count: number;
  measureNames?: string[];
  onClick: () => void;
}): React.JSX.Element | null {
  const [expanded, setExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);
  if (count === 0) return null;

  return (
    <div>
      <button
        type="button"
        onClick={onClick}
        className={`flex w-full items-center justify-between rounded px-3 py-1.5 text-left text-xs transition-colors ${
          active
            ? "bg-blue-50 font-semibold text-blue-700"
            : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
        }`}
      >
        <span>{tag.label}</span>
        <span className="ml-2 flex items-center gap-1">
          <span className={`text-xs ${active ? "text-blue-400" : "text-gray-300"}`}>
            {count}
          </span>
          {measureNames && measureNames.length > 0 && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setExpanded((prev) => !prev); }}
              className="text-gray-300 hover:text-gray-500"
              aria-label="Show measures in this category"
            >
              <svg className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
            </button>
          )}
        </span>
      </button>
      {expanded && measureNames && measureNames.length > 0 && (
        <ul className="ml-3 border-l border-gray-100 pl-3 py-1">
          {(showAll ? measureNames : measureNames.slice(0, 10)).map((name) => (
            <li key={name} className="py-0.5 text-xs text-gray-400 leading-tight">
              {name}
            </li>
          ))}
          {!showAll && measureNames.length > 10 && (
            <li className="py-0.5">
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setShowAll(true); }}
                className="text-xs text-blue-500 hover:text-blue-700"
              >
                +{measureNames.length - 10} more
              </button>
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

function TagSection({
  label,
  tags,
  activeTag,
  tagCounts,
  tagMeasureNames,
  onTagChange,
}: {
  label: string;
  tags: MeasureTag[];
  activeTag: string | null;
  tagCounts: Record<string, number>;
  tagMeasureNames?: Record<string, string[]>;
  onTagChange: (tag: string | null) => void;
}): React.JSX.Element | null {
  const withCounts = tags.filter((t) => (tagCounts[t.id] ?? 0) > 0);
  if (withCounts.length === 0) return null;

  return (
    <>
      <p className="mb-1 mt-3 px-3 text-xs font-semibold uppercase tracking-wide text-gray-400">
        {label}
      </p>
      {withCounts.map((t) => (
        <TagButton
          key={t.id}
          tag={t}
          active={activeTag === t.id}
          count={tagCounts[t.id] ?? 0}
          measureNames={tagMeasureNames?.[t.id]}
          onClick={() => onTagChange(activeTag === t.id ? null : t.id)}
        />
      ))}
    </>
  );
}

// Sidebar sections ordered to match the page layout:
// 1. Patient Experience (matches the first content section)
// 2. By Condition (matches the condition-based quality sections)
// 3. Safety & Outcomes (filters for cross-cutting safety views)
// 4. Utilization & Cost
// 5. Status
const PAGE_ORDER_SECTIONS: { label: string; tagIds: string[] }[] = [
  {
    label: "Patient Experience",
    tagIds: ["patient_experience"],
  },
  {
    label: "By Condition",
    tagIds: ["heart", "lung", "stroke", "orthopedic", "colonoscopy", "cataract",
             "cancer", "sepsis", "vte", "opioid"],
  },
  {
    label: "Safety & Outcomes",
    tagIds: ["mortality", "infections", "complications", "readmissions"],
  },
  {
    label: "Process & Timely Care",
    tagIds: ["timely_emergency", "surgical"],
  },
  {
    label: "Utilization & Cost",
    tagIds: ["imaging", "spending"],
  },
  {
    label: "Status",
    tagIds: ["not_reported"],
  },
];

export function CategoryNav({
  activeTag,
  onTagChange,
  tagCounts,
  tagMeasureNames,
}: CategoryNavProps): React.JSX.Element {
  // Build tag objects from the ordered section definitions
  const tagById = new Map(MEASURE_TAGS.map((t) => [t.id, t]));

  const sectionTags = PAGE_ORDER_SECTIONS.map((s) => ({
    label: s.label,
    tags: s.tagIds
      .map((id) => tagById.get(id))
      .filter((t): t is NonNullable<typeof t> => t !== undefined),
  }));

  // All tags with counts for mobile bar (in page order)
  const allTags = sectionTags
    .flatMap((s) => s.tags)
    .filter((t) => (tagCounts[t.id] ?? 0) > 0);

  return (
    <>
      {/* Desktop: sticky sidebar */}
      <nav
        aria-label="Measure categories"
        className="hidden lg:block lg:w-52 lg:shrink-0"
      >
        <div className="sticky top-16 max-h-[calc(100vh-5rem)] overflow-y-auto space-y-0.5 pb-8">
          {/* All button */}
          <button
            type="button"
            onClick={() => onTagChange(null)}
            className={`flex w-full items-center justify-between rounded px-3 py-1.5 text-left text-xs transition-colors ${
              activeTag === null
                ? "bg-blue-50 font-semibold text-blue-700"
                : "text-gray-500 hover:bg-gray-50 hover:text-gray-700"
            }`}
          >
            <span>All Measures</span>
          </button>

          {sectionTags.map((s) => (
            <TagSection key={s.label} label={s.label} tags={s.tags} activeTag={activeTag} tagCounts={tagCounts} tagMeasureNames={tagMeasureNames} onTagChange={onTagChange} />
          ))}
        </div>
      </nav>

      {/* Mobile: horizontal scrollable filter bar */}
      <div className="sticky top-12 z-20 -mx-6 mb-6 flex gap-1.5 overflow-x-auto border-b border-gray-200 bg-white px-6 py-2 lg:hidden">
        <button
          type="button"
          onClick={() => onTagChange(null)}
          className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            activeTag === null
              ? "bg-blue-100 text-blue-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          All
        </button>
        {allTags.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onTagChange(activeTag === t.id ? null : t.id)}
            className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeTag === t.id
                ? "bg-blue-100 text-blue-700"
                : "bg-gray-100 text-gray-500"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </>
  );
}
