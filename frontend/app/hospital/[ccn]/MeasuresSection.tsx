"use client";

// Full measures section with sidebar visible from the start.
// Contains: Critical Safety Indicators, Multiple Comparison Disclosure,
// and all quality measures — all alongside the category filter sidebar.

import { useState, useMemo } from "react";
import type { Measure, PaymentAdjustment } from "@/types/provider";
import { measureHasData, hasSESSensitivity } from "@/lib/utils";
import { getTagsForMeasure, isHCAHPS, isRetiredHCAHPS, groupHCAHPS } from "@/lib/measure-tags";
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

function sortMeasures(measures: Measure[]): Measure[] {
  return [...measures].sort((a, b) => {
    const aName = a.measure_plain_language ?? a.measure_name ?? "";
    const bName = b.measure_plain_language ?? b.measure_name ?? "";
    return aName.localeCompare(bName);
  });
}

export function MeasuresSection({
  measures,
  paymentAdjustments,
  providerLastUpdated,
  providerName,
}: MeasuresSectionProps): React.JSX.Element {
  const [activeTag, setActiveTag] = useState<string | null>(null);

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

  const tagCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const tags of measureTags.values()) {
      for (const t of tags) {
        counts[t] = (counts[t] ?? 0) + 1;
      }
    }
    return counts;
  }, [measureTags]);

  // Map of tag id → measure names for sidebar preview
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
    () => sortMeasures(filteredMeasures.filter((m) => measureHasData(m) && !isHCAHPS(m) && !isRetiredHCAHPS(m))),
    [filteredMeasures]
  );

  const notReported = useMemo(
    () => sortMeasures(filteredMeasures.filter((m) => !measureHasData(m) && !isRetiredHCAHPS(m))),
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

  const tailRiskNotReported = notReported.filter((m) => m.tail_risk_flag);

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

        {/* Critical Safety Indicators — shows when unfiltered or filtered to critical_safety */}
        {(!isFiltered || activeTag === "critical_safety") && (
          <section className="mb-8">
            <PatientSafetyRecord
              measures={measures}
              paymentAdjustments={paymentAdjustments}
              providerLastUpdated={providerLastUpdated}
              providerName={providerName}
            />
          </section>
        )}

        {/* Multiple comparison disclosure */}
        {!isNotReportedFilter && (
          <div className="mb-6">
            <MultipleComparisonDisclosure />
          </div>
        )}

        {/* SES disclosure */}
        {showSES && !isNotReportedFilter && (
          <div className="mb-4">
            <SESDisclosureBlock />
          </div>
        )}

        {/* Section header for filtered views */}
        {isFiltered && !isNotReportedFilter && activeTag !== "critical_safety" && (
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            Quality Measures
          </h2>
        )}

        {/* All measures header when unfiltered */}
        {!isFiltered && (
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            All Quality Measures
          </h2>
        )}

        {/* Data-bearing measure cards */}
        {!isNotReportedFilter && (
          <>
            <div className="space-y-4">
              {withData.map((m) => (
                <MeasureCard
                  key={`${m.measure_id}-${m.period_label}`}
                  measure={m}
                  providerLastUpdated={providerLastUpdated}
                  providerName={providerName}
                  inlineTrend={m.tail_risk_flag}
                  onTagClick={setActiveTag}
                />
              ))}
            </div>

            {/* HCAHPS collapsed groups */}
            {(hcahpsGroups.length > 0 || overallStarRating) && (
              <div className="mt-6">
                {withData.length > 0 && (
                  <h3 className="mb-3 text-sm font-semibold text-gray-900">
                    Patient Survey Results
                  </h3>
                )}
                <div className="space-y-4">
                  {overallStarRating && (
                    <MeasureCard
                      key={overallStarRating.measure_id}
                      measure={overallStarRating}
                      providerLastUpdated={providerLastUpdated}
                      providerName={providerName}
                      onTagClick={setActiveTag}
                    />
                  )}
                  {hcahpsGroups.map((g) => (
                    <HCAHPSGroupCard
                      key={g.groupBase}
                      group={g}
                      providerLastUpdated={providerLastUpdated}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Not reported section */}
        {notReported.length > 0 && (
          <div className={isNotReportedFilter ? "" : "mt-8"}>
            {!isNotReportedFilter && (
              <h3 className="mb-2 text-sm font-semibold text-gray-700">
                Not Reported ({notReported.length} measures)
              </h3>
            )}

            {!isNotReportedFilter && tailRiskNotReported.length > 0 && (
              <div className="mb-3 rounded border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800">
                {tailRiskNotReported.length} safety-related{" "}
                {tailRiskNotReported.length === 1 ? "measure has" : "measures have"}{" "}
                not been reported for the current period:{" "}
                {tailRiskNotReported.map((m) => m.measure_name ?? m.measure_id).join(", ")}.
              </div>
            )}

            <div className="space-y-1.5">
              {notReported.map((m) => (
                <NotReportedCard
                  key={`${m.measure_id}-${m.period_label}`}
                  measure={m}
                />
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {withData.length === 0 && hcahpsGroups.length === 0 && !overallStarRating && notReported.length === 0 && (
          <p className="text-sm text-gray-500">
            No measures match the selected filter.
          </p>
        )}
      </div>
    </div>
  );
}
