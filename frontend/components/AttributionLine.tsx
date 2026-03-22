// Per-measure CMS data attribution (Template 3b / legal-compliance.md).
// Required at the bottom of every MeasureCard and at the group level in MeasureGroup.
// Attribution is a legal compliance element — must be visible, not de-emphasized.
// gray-500 meets ~4.5:1 contrast on white; gray-400 does not.

import { formatAttribution } from "@/lib/utils";

interface AttributionLineProps {
  sourceDatasetName: string; // measure.source_dataset_name
  periodLabel: string; // measure.period_label
  providerLastUpdated: string; // provider.last_updated
}

export function AttributionLine({
  sourceDatasetName,
  periodLabel,
  providerLastUpdated,
}: AttributionLineProps): JSX.Element {
  return (
    <p className="mt-3 text-xs text-gray-500">
      {formatAttribution(sourceDatasetName, periodLabel, providerLastUpdated)}
    </p>
  );
}
