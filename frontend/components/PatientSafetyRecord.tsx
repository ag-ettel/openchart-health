// Phase 1: implement.
// Renders first on the hospital profile page, before MultipleComparisonDisclosure
// and all MeasureGroup instances.
// Obligations: see CLAUDE.md: Frontend Specification: Components: PatientSafetyRecord

import type { Measure } from "@/types/provider";

interface PatientSafetyRecordProps {
  measures:            Measure[]; // full provider.measures array; component filters internally
  providerLastUpdated: string;
}

export function PatientSafetyRecord(_props: PatientSafetyRecordProps): JSX.Element {
  // TODO Phase 1: implement
  //
  // Filter: measures.filter(m => m.tail_risk_flag)
  //
  // Sort: by Math.abs((numeric_value ?? national_avg) - (national_avg ?? 0)) descending.
  //   Measures where national_avg is null sort after those with a value.
  //   Suppressed and not_reported tail_risk measures render with full visual presence.
  //   They are never omitted because no value exists.
  //
  // Prohibited strings (do not use anywhere in this component):
  //   "adverse_event_summary", "what could go wrong", "your risk"
  //   No predictive framing of any kind.
  return <div data-component="PatientSafetyRecord" />;
}
