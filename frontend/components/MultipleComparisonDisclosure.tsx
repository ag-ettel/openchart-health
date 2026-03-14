// Renders once per hospital profile page on any view showing the full measure set.
// Position: after PatientSafetyRecord, before the first MeasureGroup.
// Not suppressible. Not collapsible.
// Obligations: see CLAUDE.md: Frontend Specification: Components: MultipleComparisonDisclosure

import { MULTIPLE_COMPARISON_TEXT } from "@/lib/constants";

export function MultipleComparisonDisclosure(): JSX.Element {
  return (
    <div className="rounded border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-relaxed text-gray-700">
      <p>{MULTIPLE_COMPARISON_TEXT}</p>
    </div>
  );
}
