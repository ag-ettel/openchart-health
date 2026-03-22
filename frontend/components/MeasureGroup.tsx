// MeasureGroup — renders a section of measures sharing the same measure_group.
//
// Responsibilities:
//   - Group-level SES disclosure (Template 3c) when any measure is HIGH/MODERATE
//   - Group-level attribution (Template 3b) — one per source dataset in the group
//   - Sort: tail_risk_flag measures first, then alphabetical by plain_language
//   - Groups stratified sub-measures via groupByMeasureId() before rendering

import type { Measure } from "@/types/provider";
import { hasSESSensitivity, groupByMeasureId } from "@/lib/utils";
import { MEASURE_GROUP_DISPLAY_NAMES } from "@/lib/constants";
import { SESDisclosureBlock } from "./SESDisclosureBlock";
import { AttributionLine } from "./AttributionLine";
import { MeasureCard } from "./MeasureCard";

interface MeasureGroupProps {
  groupName: string; // measure_group value; used as section heading
  measures: Measure[]; // all measures for this group, pre-filtered
  providerLastUpdated: string;
}

// Deduplicate attribution lines by source_dataset_name. Different measures in
// the same group may come from different CMS datasets with different periods.
function uniqueAttributions(
  measures: Measure[]
): { datasetName: string; periodLabel: string }[] {
  const seen = new Map<string, string>();
  for (const m of measures) {
    const key = `${m.source_dataset_name}||${m.period_label}`;
    if (!seen.has(key)) {
      seen.set(key, m.period_label);
    }
  }
  return Array.from(seen.entries()).map(([key]) => {
    const [datasetName, periodLabel] = key.split("||");
    return { datasetName, periodLabel };
  });
}

// Sort: tail_risk first, then alphabetical by plain_language.
function sortMeasures(measures: Measure[]): Measure[] {
  return [...measures].sort((a, b) => {
    if (a.tail_risk_flag && !b.tail_risk_flag) return -1;
    if (!a.tail_risk_flag && b.tail_risk_flag) return 1;
    const aName = a.measure_plain_language ?? a.measure_name ?? "";
    const bName = b.measure_plain_language ?? b.measure_name ?? "";
    return aName.localeCompare(bName);
  });
}

export function MeasureGroup({
  groupName,
  measures,
  providerLastUpdated,
}: MeasureGroupProps): JSX.Element {
  const showSES = hasSESSensitivity(measures);
  const grouped = groupByMeasureId(measures);
  const attributions = uniqueAttributions(measures);

  // Flatten grouped measures back to a sorted render list. The primary measure
  // for each group renders as a MeasureCard; stratified sub-measures are handled
  // within MeasureCard via its own groupByMeasureId call.
  // Here we sort at the primary-measure level.
  const primaryMeasures: Measure[] = [];
  for (const [, group] of grouped) {
    if (group.primary) {
      primaryMeasures.push(group.primary);
    } else if (group.stratified.length > 0) {
      // No primary (suppressed at dataset level) — use first stratified as anchor
      primaryMeasures.push(group.stratified[0]);
    }
  }
  const sorted = sortMeasures(primaryMeasures);

  return (
    <section aria-label={`${groupName} measures`}>
      <h2 className="mb-3 text-base font-semibold text-gray-900">
        {MEASURE_GROUP_DISPLAY_NAMES[groupName] ?? groupName}
      </h2>

      {/* SES disclosure — at group header level, not collapsible (Template 3c) */}
      {showSES && (
        <div className="mb-3">
          <SESDisclosureBlock />
        </div>
      )}

      {/* Group-level attribution — one per source dataset (Template 3b) */}
      <div className="mb-3">
        {attributions.map((attr) => (
          <AttributionLine
            key={`${attr.datasetName}-${attr.periodLabel}`}
            sourceDatasetName={attr.datasetName}
            periodLabel={attr.periodLabel}
            providerLastUpdated={providerLastUpdated}
          />
        ))}
      </div>

      {/* Measures — tail_risk first, then alphabetical */}
      <div className="space-y-3">
        {sorted.map((m) => (
          <MeasureCard
            key={`${m.measure_id}-${m.period_label}-${m.stratification ?? ""}`}
            measure={m}
            providerLastUpdated={providerLastUpdated}
          />
        ))}
      </div>
    </section>
  );
}
