// Phase 1: implement.
// Obligations: see CLAUDE.md: Frontend Specification: Components: MeasureGroup

import type { Measure } from "@/types/provider";

interface MeasureGroupProps {
  groupName:           string;     // measure_group value; used as section heading
  measures:            Measure[];  // all measures for this group, pre-filtered from provider.measures
  providerLastUpdated: string;
}

export function MeasureGroup(_props: MeasureGroupProps): JSX.Element {
  // TODO Phase 1: implement
  //
  // - hasSESSensitivity(measures) true:
  //     Render SESDisclosureBlock at group header level, above the measure list.
  //     Not collapsible.
  //
  // - Group measures via groupByMeasureId() before rendering MeasureCards.
  //
  // - Render order within the group:
  //     tail_risk_flag: true measures first, then remaining measures.
  //     Within each sub-group: alphabetical by measure_plain_language.
  return <div data-component="MeasureGroup" />;
}
