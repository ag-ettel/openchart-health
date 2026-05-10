"use client";

// Full measures section with sidebar visible from the start.
// Rendering order: Patient Experience (HCAHPS) → condition-based sections
// with critical safety surfaced highest, related metrics grouped.
// Retired measures and payment programs are excluded.

import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import type { Measure, PaymentAdjustment } from "@/types/provider";
import { measureHasData, hasSESSensitivity } from "@/lib/utils";
import { getTagsForMeasure, isHCAHPS, isRetiredHCAHPS, groupHCAHPS, hcahpsBase, HCAHPS_GROUPS } from "@/lib/measure-tags";
import { useReportingRates } from "@/lib/use-reporting-rates";
import { CategoryNav } from "./CategoryNav";
import { MeasureCard } from "@/components/MeasureCard";
import { NotReportedCard } from "@/components/NotReportedCard";
import { HCAHPSGroupCard } from "@/components/HCAHPSGroupCard";
import { SESDisclosureBlock } from "@/components/SESDisclosureBlock";
import { PatientSafetyRecord } from "@/components/PatientSafetyRecord";
import { MultipleComparisonDisclosure } from "@/components/MultipleComparisonDisclosure";

interface MeasuresSectionProps {
  measures: Measure[];
  paymentAdjustments: PaymentAdjustment[];
  providerLastUpdated: string;
  providerName: string;
}

// --- Section-based measure ordering ---

// Sections render in this order. Condition sections group related measures
// across domains (e.g., heart mortality + heart readmissions together).
// Domain sections catch remaining measures without a condition tag.
const SECTION_RENDER_ORDER: { id: string; label: string }[] = [
  // Condition sections — related measures across domains
  { id: "heart", label: "Heart & Cardiac" },
  { id: "lung", label: "Lung & Respiratory" },
  { id: "stroke", label: "Stroke" },
  { id: "sepsis", label: "Sepsis" },
  { id: "vte", label: "Blood Clots (VTE)" },
  { id: "orthopedic", label: "Hip & Knee" },
  // Infections — cohesive group kept together
  { id: "infections", label: "Healthcare-Associated Infections" },
  // Remaining condition sections
  { id: "opioid", label: "Opioid Safety" },
  { id: "cancer", label: "Cancer & Chemotherapy" },
  { id: "colonoscopy", label: "Colonoscopy & Colon" },
  { id: "cataract", label: "Cataract Surgery" },
  // Domain fallback sections — measures without a condition tag
  { id: "mortality", label: "Mortality" },
  { id: "complications", label: "Complications & Safety" },
  { id: "readmissions", label: "Unplanned Hospital Visits" },
  { id: "timely_emergency", label: "Timely & Emergency Care" },
  { id: "surgical", label: "Surgical & Procedural" },
  { id: "imaging", label: "Imaging Efficiency" },
  { id: "spending", label: "Medicare Spending" },
  { id: "other", label: "Other Measures" },
];

const CONDITION_TAGS = new Set([
  "heart", "lung", "stroke", "sepsis", "vte", "orthopedic",
  "opioid", "colonoscopy", "cataract", "cancer",
]);

/** Assign a measure to its primary display section. */
function assignSection(tags: string[]): string {
  // Infections stay together as a cohesive group
  if (tags.includes("infections")) return "infections";
  // Condition tags take priority — groups related measures across domains
  for (const t of tags) {
    if (CONDITION_TAGS.has(t)) return t;
  }
  // Domain fallback
  const domains = [
    "mortality", "complications", "readmissions",
    "timely_emergency", "surgical", "imaging", "spending",
  ];
  for (const d of domains) {
    if (tags.includes(d)) return d;
  }
  return "other";
}

/** Sort within a section: tail_risk first, then alphabetical. */
function sortWithinSection(measures: Measure[]): Measure[] {
  return [...measures].sort((a, b) => {
    if (a.tail_risk_flag && !b.tail_risk_flag) return -1;
    if (!a.tail_risk_flag && b.tail_risk_flag) return 1;
    const aName = a.measure_plain_language ?? a.measure_name ?? "";
    const bName = b.measure_plain_language ?? b.measure_name ?? "";
    return aName.localeCompare(bName);
  });
}

function sortMeasures(measures: Measure[]): Measure[] {
  return [...measures].sort((a, b) => {
    const aName = a.measure_plain_language ?? a.measure_name ?? "";
    const bName = b.measure_plain_language ?? b.measure_name ?? "";
    return aName.localeCompare(bName);
  });
}

interface MeasureSection {
  id: string;
  label: string;
  measures: Measure[];
}

/** Collapsible section that scrolls back into view on collapse. */
function CollapsibleSection({
  label,
  count,
  children,
}: {
  label: string;
  count: number;
  children: React.ReactNode;
}): React.JSX.Element {
  const detailsRef = useRef<HTMLDetailsElement>(null);

  const handleToggle = useCallback(() => {
    const el = detailsRef.current;
    if (!el || el.open) return;
    // Section was just collapsed — scroll it into view
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, []);

  return (
    <details ref={detailsRef} className="mb-6 group/section" onToggle={handleToggle}>
      <summary className="sticky top-12 z-10 mb-3 flex cursor-pointer items-center justify-between rounded-md border border-gray-200 bg-gray-50 px-5 py-4 text-base font-semibold text-gray-800 shadow-sm hover:bg-blue-50 hover:text-blue-700">
        <span>
          {label}
          <span className="ml-2 text-sm font-normal text-gray-500">
            ({count} {count === 1 ? "measure" : "measures"})
          </span>
        </span>
        <span className="flex items-center gap-1.5 text-sm font-medium text-gray-600">
          <span className="hidden group-open/section:inline">Collapse</span>
          <span className="inline group-open/section:hidden">Expand</span>
          <svg className="h-5 w-5 shrink-0 transition-transform group-open/section:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </summary>
      <div className="space-y-4 pt-2">
        {children}
      </div>
    </details>
  );
}

export function MeasuresSection({
  measures,
  paymentAdjustments,
  providerLastUpdated,
  providerName,
}: MeasuresSectionProps): React.JSX.Element {
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [showAllPE, setShowAllPE] = useState(false);
  const [peInView, setPeInView] = useState(false);
  const peRef = useRef<HTMLDivElement>(null);

  // Track whether the PE section is visible — hides the fixed collapse bar when not
  useEffect(() => {
    const el = peRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => setPeInView(entry.isIntersecting),
      { threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const primaryMeasures = useMemo(
    () => measures.filter((m) => m.stratification === null),
    [measures]
  );

  const measureTags = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const m of primaryMeasures) {
      map.set(m.measure_id, getTagsForMeasure(m));
    }
    return map;
  }, [primaryMeasures]);

  // Tag counts — exclude retired HCAHPS; count HCAHPS by group (not response)
  const tagCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    const seenHcahpsGroups = new Set<string>();

    for (const m of primaryMeasures) {
      if (isRetiredHCAHPS(m)) continue;
      const tags = measureTags.get(m.measure_id) ?? [];

      if (isHCAHPS(m)) {
        const base = hcahpsBase(m.measure_id);
        if (!base) continue;
        const groupKey = tags.join("|") + "|" + base;
        if (seenHcahpsGroups.has(groupKey)) continue;
        seenHcahpsGroups.add(groupKey);
      }

      for (const t of tags) {
        counts[t] = (counts[t] ?? 0) + 1;
      }
    }
    return counts;
  }, [primaryMeasures, measureTags]);

  // Map of tag id → measure names for sidebar preview.
  // Uses plain language names, skips retired, and collapses HCAHPS responses
  // into their group label so the preview isn't cluttered with response variants.
  const tagMeasureNames = useMemo(() => {
    const names: Record<string, string[]> = {};
    const seenHcahpsGroups = new Set<string>();

    for (const m of primaryMeasures) {
      if (!measureHasData(m)) continue;
      if (isRetiredHCAHPS(m)) continue;

      const tags = measureTags.get(m.measure_id) ?? [];
      let name: string;

      if (isHCAHPS(m)) {
        // Collapse HCAHPS responses into their group label
        const base = hcahpsBase(m.measure_id);
        if (!base) continue;
        const groupKey = tags.join("|") + "|" + base;
        if (seenHcahpsGroups.has(groupKey)) continue;
        seenHcahpsGroups.add(groupKey);
        name = HCAHPS_GROUPS[base] ?? base;
      } else {
        name = m.measure_name ?? m.measure_id;
      }

      for (const t of tags) {
        if (!names[t]) names[t] = [];
        if (!names[t].includes(name)) names[t].push(name);
      }
    }
    return names;
  }, [primaryMeasures, measureTags]);

  const filteredMeasures = useMemo(() => {
    if (activeTag === null) return primaryMeasures;
    return primaryMeasures.filter((m) => {
      const tags = measureTags.get(m.measure_id) ?? [];
      return tags.includes(activeTag);
    });
  }, [primaryMeasures, activeTag, measureTags]);

  // Non-HCAHPS measures with data, excluding retired
  const withData = useMemo(
    () => filteredMeasures.filter(
      (m) => measureHasData(m) && !isHCAHPS(m) && !isRetiredHCAHPS(m)
    ),
    [filteredMeasures]
  );

  // Group non-HCAHPS measures into condition-based sections
  const sections = useMemo((): MeasureSection[] => {
    const sectionMap = new Map<string, Measure[]>();
    for (const m of withData) {
      const tags = measureTags.get(m.measure_id) ?? [];
      const section = assignSection(tags);
      if (!sectionMap.has(section)) sectionMap.set(section, []);
      sectionMap.get(section)!.push(m);
    }
    return SECTION_RENDER_ORDER
      .filter((s) => sectionMap.has(s.id))
      .map((s) => ({
        ...s,
        measures: sortWithinSection(sectionMap.get(s.id)!),
      }));
  }, [withData, measureTags]);

  const notReported = useMemo(
    () => sortMeasures(
      filteredMeasures.filter((m) => !measureHasData(m) && !isRetiredHCAHPS(m))
    ),
    [filteredMeasures]
  );

  const hcahpsGroups = useMemo(
    () => groupHCAHPS(filteredMeasures.filter((m) => measureHasData(m))),
    [filteredMeasures]
  );

  const showSES = hasSESSensitivity(filteredMeasures);

  const overallStarRating = filteredMeasures.find(
    (m) => m.measure_id === "H_STAR_RATING" && measureHasData(m)
  );

  const reportingRates = useReportingRates();

  // Measures not reported here that most hospitals DO report — unusual gaps
  const unusuallyNotReported = useMemo(() => {
    if (!reportingRates) return [];
    return notReported.filter((m) => {
      const rate = reportingRates[m.measure_id];
      return rate !== undefined && rate.pct_reported >= 80;
    });
  }, [notReported, reportingRates]);

  const isNotReportedFilter = activeTag === "not_reported";
  const isFiltered = activeTag !== null;

  return (
    <div className="relative lg:flex lg:gap-8">
      {/* Sidebar — visible from the start */}
      <CategoryNav
        activeTag={activeTag}
        onTagChange={setActiveTag}
        tagCounts={tagCounts}
        tagMeasureNames={tagMeasureNames}
      />

      <div className="min-w-0 flex-1">
        {/* Active filter label */}
        {isFiltered && (
          <div className="mb-4 flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">
              Showing: {activeTag!.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </span>
            <button
              type="button"
              onClick={() => setActiveTag(null)}
              className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-200"
            >
              Clear
            </button>
          </div>
        )}

        {/* Critical Safety Indicators — only when filtered to that tag */}
        {activeTag === "critical_safety" && (
          <section className="mb-8">
            <PatientSafetyRecord
              measures={measures}
              paymentAdjustments={paymentAdjustments}
              providerLastUpdated={providerLastUpdated}
              providerName={providerName}
            />
          </section>
        )}

        {/* Data-bearing measures */}
        {!isNotReportedFilter && (
          <>
            {/* 1. Patient Experience — first card visible, rest behind toggle */}
            {(hcahpsGroups.length > 0 || overallStarRating) && (() => {
              // Build the ordered list: star rating (if present) then HCAHPS groups
              const peCards: React.JSX.Element[] = [];
              if (overallStarRating) {
                peCards.push(
                  <MeasureCard
                    key={overallStarRating.measure_id}
                    measure={overallStarRating}
                    providerLastUpdated={providerLastUpdated}
                    providerName={providerName}
                    onTagClick={setActiveTag}
                  />
                );
              }
              for (let i = 0; i < hcahpsGroups.length; i++) {
                peCards.push(
                  <HCAHPSGroupCard
                    key={hcahpsGroups[i].groupBase}
                    group={hcahpsGroups[i]}
                    providerLastUpdated={providerLastUpdated}
                  />
                );
              }
              const firstCard = peCards[0];
              const restCards = peCards.slice(1);
              const restCount = restCards.length;

              return (
                <div ref={peRef} tabIndex={-1} className="mb-8 focus:outline-none">
                  <h2 className="mb-3 text-lg font-semibold text-gray-900">
                    Patient Experience
                  </h2>
                  <div className="space-y-4">
                    {firstCard}
                  </div>
                  {restCount > 0 && !showAllPE && (
                    <button
                      type="button"
                      onClick={() => setShowAllPE(true)}
                      className="mt-4 w-full rounded border border-gray-200 bg-gray-50 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 hover:text-blue-700"
                    >
                      Show all {restCount + 1} patient experience measures
                    </button>
                  )}
                  {showAllPE && (
                    <>
                      <div className="mt-4 space-y-4">
                        {restCards}
                      </div>
                      <div className="mt-4">
                        <button
                          type="button"
                          onClick={() => setShowAllPE(false)}
                          className="w-full rounded border border-gray-200 bg-gray-50 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100"
                        >
                          Collapse patient experience
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })()}

            {/* Disclosures — after patient experience, before condition sections */}
            <div className="mb-6">
              <MultipleComparisonDisclosure />
            </div>
            {showSES && (
              <div className="mb-4">
                <SESDisclosureBlock />
              </div>
            )}

            {/* 2. Quality measures — grouped by condition, safety-critical first */}
            {sections.length > 0 && (
              <div>
                {!isFiltered && (
                  <h2 className="mb-4 text-lg font-semibold text-gray-900">
                    Quality Measures by Condition
                  </h2>
                )}
                {isFiltered && activeTag !== "critical_safety" && (
                  <h2 className="mb-4 text-lg font-semibold text-gray-900">
                    Quality Measures
                  </h2>
                )}

                {sections.map((section) => (
                  <CollapsibleSection key={section.id} label={section.label} count={section.measures.length}>
                    {section.measures.map((m) => (
                      <MeasureCard
                        key={`${m.measure_id}-${m.period_label}`}
                        measure={m}
                        providerLastUpdated={providerLastUpdated}
                        providerName={providerName}
                        onTagClick={setActiveTag}
                      />
                    ))}
                  </CollapsibleSection>
                ))}
              </div>
            )}
          </>
        )}

        {/* Not reported section — collapsed by default */}
        {notReported.length > 0 && !isNotReportedFilter && (
          <CollapsibleSection label="Not Reported" count={notReported.length}>
            {unusuallyNotReported.length > 0 && (
              <div className="rounded border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800">
                {unusuallyNotReported.length}{" "}
                {unusuallyNotReported.length === 1 ? "measure is" : "measures are"}{" "}
                not reported at this hospital but reported by most eligible hospitals nationally:{" "}
                {unusuallyNotReported.map((m) => m.measure_name ?? m.measure_id).join(", ")}.
              </div>
            )}
            {notReported.map((m) => (
              <NotReportedCard
                key={`${m.measure_id}-${m.period_label}`}
                measure={m}
              />
            ))}
          </CollapsibleSection>
        )}
        {/* Not reported — full view when filtered to that tag */}
        {notReported.length > 0 && isNotReportedFilter && (
          <div className="space-y-1.5">
            {notReported.map((m) => (
              <NotReportedCard
                key={`${m.measure_id}-${m.period_label}`}
                measure={m}
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {withData.length === 0 && hcahpsGroups.length === 0 && !overallStarRating && notReported.length === 0 && (
          <p className="text-sm text-gray-500">
            No measures match the selected filter.
          </p>
        )}
      </div>

      {/* Fixed bottom collapse bar for Patient Experience — only while PE section is in view */}
      {showAllPE && peInView && (
        <div className="fixed inset-x-0 bottom-12 z-30 border-t border-gray-200 bg-white/95 px-4 py-2 backdrop-blur-sm">
          <button
            type="button"
            onClick={() => {
              setShowAllPE(false);
              // Return keyboard focus to the PE section heading so AT users
              // don't lose their place when the floating bar disappears.
              peRef.current?.focus();
              peRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }}
            className="mx-auto block max-w-xl rounded border border-gray-200 bg-gray-50 px-6 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1"
            aria-label="Collapse patient experience section"
          >
            Collapse patient experience
          </button>
        </div>
      )}
    </div>
  );
}
