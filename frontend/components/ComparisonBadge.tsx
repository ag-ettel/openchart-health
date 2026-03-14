// Renders a ComparisonResult as a labeled, color-coded badge.
// Used by MeasureCard for both national and state average comparisons.
// Color system: blue = better, orange = worse, gray = no significant
// difference or cannot determine. The two gray states carry different
// labels because they mean different things to a consumer.
// Use confidence intervals to determine whether a provider's measure value is
// significantly better or worse than a reference value (national average or another provider).
// Used by compareToAverage() and compareProviders() in lib/utils.ts.

import type { ComparisonResult } from "@/types/provider";

interface ComparisonBadgeProps {
  result:         ComparisonResult;
  referenceLabel: string; // "national average" or "state average"
}

const RESULT_CONFIG: Record<
  ComparisonResult,
  { label: string; className: string }
> = {
  BETTER: {
    label: "Performs better than",
    className: "text-blue-700 bg-blue-50 border-blue-200",
  },
  WORSE: {
    label: "Performs worse than",
    className: "text-orange-700 bg-orange-50 border-orange-200",
  },
  NO_SIGNIFICANT_DIFFERENCE: {
    label: "No significant difference from",
    className: "text-gray-500 bg-gray-50 border-gray-200",
  },
  CANNOT_DETERMINE: {
    label: "Insufficient data to compare with",
    className: "text-gray-500 bg-gray-50 border-gray-200",
  },
};

export function ComparisonBadge({
  result,
  referenceLabel,
}: ComparisonBadgeProps): JSX.Element {
  const { label, className } = RESULT_CONFIG[result];
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-1 text-xs font-medium ${className}`}
    >
      {label} {referenceLabel}
    </span>
  );
}
