"use client";

// NH Measures section — condition-based grouping with collapsible sections.
// Follows the hospital MeasuresSection pattern: sections group related measures,
// first section open by default, sticky headers for navigation.

import { useState, useMemo, useCallback, useRef } from "react";
import type { Measure, PaymentAdjustment } from "@/types/provider";
import { measureHasData, hasSESSensitivity, isMeasureRetired } from "@/lib/utils";
import { getTagsForNHMeasure } from "@/lib/measure-tags";
import { NHCategoryNav } from "./NHCategoryNav";
import { MeasureCard } from "@/components/MeasureCard";
import { NotReportedCard } from "@/components/NotReportedCard";
import { SESDisclosureBlock } from "@/components/SESDisclosureBlock";
import { PatientSafetyRecord } from "@/components/PatientSafetyRecord";
import { MultipleComparisonDisclosure } from "@/components/MultipleComparisonDisclosure";

interface NHMeasuresSectionProps {
  measures: Measure[];
  paymentAdjustments: PaymentAdjustment[];
  providerLastUpdated: string;
  providerName: string;
}

// --- Section-based measure ordering ---
// Groups related NH measures by clinical domain. Order reflects user interest:
// resident outcomes first, then process measures, then operational.
const SECTION_RENDER_ORDER: { id: string; label: string; description: string }[] = [
  { id: "long_stay_outcomes", label: "Long-Stay Resident Outcomes", description: "Measures for residents in long-term care: falls, pressure ulcers, UTIs, weight loss, mobility, and more." },
  { id: "short_stay_outcomes", label: "Short-Stay Resident Outcomes", description: "Measures for short-stay rehabilitation residents: rehospitalization, ED visits, and functional outcomes." },
  { id: "claims_quality", label: "Claims-Based Quality", description: "CMS-calculated measures using Medicare claims data, with risk adjustment for patient acuity." },
  { id: "snf_qrp", label: "SNF Quality Reporting", description: "Skilled nursing facility quality measures from the SNF Quality Reporting Program." },
  { id: "spending", label: "Medicare Spending", description: "Per-patient Medicare spending measures." },
  { id: "other", label: "Other Measures", description: "Additional CMS-published measures." },
];

/** Assign a measure to its display section based on group and tags. */
function assignSection(m: Measure): string {
  switch (m.measure_group) {
    case "NH_QUALITY_LONG_STAY": return "long_stay_outcomes";
    case "NH_QUALITY_SHORT_STAY": return "short_stay_outcomes";
    case "NH_QUALITY_CLAIMS": return "claims_quality";
    case "NH_SNF_QRP": return "snf_qrp";
    case "SPENDING": return "spending";
    default: return "other";
  }
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
  description: string;
  measures: Measure[];
}

/** Renders a section's measure list with progressive disclosure: shows the
 * first measure by default, with a button to expand the full list. */
function ExpandableMeasureList({
  measures,
  sectionLabel,
  initialShowAll = false,
  providerLastUpdated,
  providerName,
  onTagClick,
}: {
  measures: Measure[];
  sectionLabel: string;
  initialShowAll?: boolean;
  providerLastUpdated: string;
  providerName: string;
  onTagClick: (tag: string) => void;
}): React.JSX.Element {
  const [showAll, setShowAll] = useState(initialShowAll);
  const visible = showAll ? measures : measures.slice(0, 1);
  const hiddenCount = measures.length - visible.length;

  return (
    <>
      {visible.map((m) => (
        <MeasureCard
          key={`${m.measure_id}-${m.period_label}`}
          measure={m}
          providerLastUpdated={providerLastUpdated}
          providerName={providerName}
          providerType="NURSING_HOME"
          onTagClick={onTagClick}
        />
      ))}
      {measures.length > 1 && (
        <button
          type="button"
          onClick={() => setShowAll((prev) => !prev)}
          className="w-full rounded-md border border-gray-200 bg-gray-50 py-2.5 text-sm font-medium text-blue-600 hover:bg-blue-50 hover:text-blue-700 transition-colors"
        >
          {showAll
            ? `Show fewer ${sectionLabel.toLowerCase()} measures`
            : `Show all ${measures.length} ${sectionLabel.toLowerCase()} measures`}
        </button>
      )}
    </>
  );
}

/** Collapsible section with sticky header that scrolls back into view on collapse. */
function CollapsibleSection({
  label,
  description,
  count,
  defaultOpen = false,
  children,
}: {
  label: string;
  description: string;
  count: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}): React.JSX.Element {
  const detailsRef = useRef<HTMLDetailsElement>(null);

  const handleToggle = useCallback(() => {
    const el = detailsRef.current;
    if (!el || el.open) return;
    el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, []);

  return (
    <details ref={detailsRef} className="mb-6 group/section" onToggle={handleToggle} open={defaultOpen}>
      <summary className="sticky top-12 z-10 mb-3 flex cursor-pointer items-center justify-between rounded-md border border-gray-300 bg-white px-5 py-4 text-base font-semibold text-gray-800 shadow-md ring-1 ring-gray-200/60 hover:bg-blue-50 hover:text-blue-700">
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
      <p className="mb-3 text-xs text-gray-400">{description}</p>
      <div className="space-y-4 pt-2">
        {children}
      </div>
    </details>
  );
}

export function NHMeasuresSection({
  measures,
  paymentAdjustments,
  providerLastUpdated,
  providerName,
}: NHMeasuresSectionProps): React.JSX.Element {
  const [activeTag, setActiveTag] = useState<string | null>(null);

  // Measures already shown in the summary dashboard topline — hide from detail section to avoid duplication.
  const TOPLINE_MEASURE_IDS = new Set<string>([
    "NH_STAFF_TOTAL_TURNOVER",
    "NH_STAFF_REPORTED_RN_HPRD",
    "NH_STAFF_REPORTED_TOTAL_HPRD",
    "NH_INSP_WEIGHTED_SCORE",
  ]);

  const primaryMeasures = useMemo(
    () => measures.filter((m) =>
      m.stratification === null
      && !isMeasureRetired(m)
      && m.measure_group !== "NH_STAR_RATING"
      && !TOPLINE_MEASURE_IDS.has(m.measure_id)
    ),
    [measures]
  );

  const measureTags = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const m of primaryMeasures) {
      map.set(m.measure_id, getTagsForNHMeasure(m));
    }
    return map;
  }, [primaryMeasures]);

  const tagCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const tags of measureTags.values()) {
      for (const t of tags) {
        counts[t] = (counts[t] ?? 0) + 1;
      }
    }
    return counts;
  }, [measureTags]);

  const tagMeasureNames = useMemo(() => {
    const names: Record<string, string[]> = {};
    for (const m of primaryMeasures) {
      if (!measureHasData(m)) continue;
      const tags = measureTags.get(m.measure_id) ?? [];
      const name = m.measure_name ?? m.measure_id;
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

  const withData = useMemo(
    () => filteredMeasures.filter((m) => measureHasData(m)),
    [filteredMeasures]
  );

  // Group measures into sections
  const sections = useMemo((): MeasureSection[] => {
    const sectionMap = new Map<string, Measure[]>();
    for (const m of withData) {
      const section = assignSection(m);
      if (!sectionMap.has(section)) sectionMap.set(section, []);
      sectionMap.get(section)!.push(m);
    }
    return SECTION_RENDER_ORDER
      .filter((s) => sectionMap.has(s.id))
      .map((s) => ({
        ...s,
        measures: sortWithinSection(sectionMap.get(s.id)!),
      }));
  }, [withData]);

  const notReported = useMemo(
    () => sortMeasures(filteredMeasures.filter((m) => !measureHasData(m))),
    [filteredMeasures]
  );

  const showSES = hasSESSensitivity(filteredMeasures);
  const isNotReportedFilter = activeTag === "not_reported";
  const isFiltered = activeTag !== null;

  return (
    <div className="relative lg:flex lg:gap-8">
      <NHCategoryNav
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
              providerType="NURSING_HOME"
            />
          </section>
        )}

        {/* Disclosures */}
        {!isNotReportedFilter && (
          <>
            <div className="mb-6">
              <MultipleComparisonDisclosure />
            </div>
            {showSES && (
              <div className="mb-4">
                <SESDisclosureBlock />
              </div>
            )}
          </>
        )}

        {/* Section heading */}
        {!isNotReportedFilter && sections.length > 0 && (
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            {isFiltered && activeTag !== "critical_safety" ? "Quality Measures" : "Quality Measures by Domain"}
          </h2>
        )}

        {/* Quality measures — grouped by domain, first section open.
            Within each section, the first measure is shown with a button
            to expand the full list (matches hospital page pattern). */}
        {!isNotReportedFilter && sections.map((section, idx) => (
          <CollapsibleSection
            key={section.id}
            label={section.label}
            description={section.description}
            count={section.measures.length}
            defaultOpen={idx === 0}
          >
            <ExpandableMeasureList
              measures={section.measures}
              sectionLabel={section.label}
              initialShowAll={idx !== 0}
              providerLastUpdated={providerLastUpdated}
              providerName={providerName}
              onTagClick={setActiveTag}
            />
          </CollapsibleSection>
        ))}

        {/* Not reported — collapsed by default */}
        {notReported.length > 0 && !isNotReportedFilter && (
          <CollapsibleSection
            label="Not Reported"
            description="Measures where this facility did not submit data for the current reporting period."
            count={notReported.length}
          >
            {notReported.map((m) => (
              <NotReportedCard
                key={`${m.measure_id}-${m.period_label}`}
                measure={m}
              />
            ))}
          </CollapsibleSection>
        )}
        {/* Not reported — full view when filtered */}
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
        {withData.length === 0 && notReported.length === 0 && (
          <p className="text-sm text-gray-500">
            No measures match the selected filter.
          </p>
        )}
      </div>
    </div>
  );
}
