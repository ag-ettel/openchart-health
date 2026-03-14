// Required at the bottom of every MeasureCard.
// Obligations: see CLAUDE.md: Frontend Specification: Components: AttributionLine

import { formatAttribution } from "@/lib/utils";

interface AttributionLineProps {
  sourceDatasetName:   string; // measure.source_dataset_name
  periodLabel:         string; // measure.period_label
  providerLastUpdated: string; // provider.last_updated
}

export function AttributionLine({
  sourceDatasetName,
  periodLabel,
  providerLastUpdated,
}: AttributionLineProps): JSX.Element {
  return (
    <p className="mt-3 text-xs text-gray-400">
      {formatAttribution(sourceDatasetName, periodLabel, providerLastUpdated)}
    </p>
  );
}
