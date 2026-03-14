// Obligations: see CLAUDE.md: Frontend Specification: Components: NonReporterIndicator
// Same visual footprint as SuppressionIndicator. Never de-emphasized.

import type { TrendPeriod } from "@/types/provider";

interface NonReporterIndicatorProps {
  not_reported_reason: string | null;
  trend:               TrendPeriod[]; // assumed chronologically ordered oldest-first
}

// Counts the trailing run of not_reported: true periods.
// Assumes trend[] is ordered oldest-first, which the pipeline must guarantee.
function countConsecutiveNonReporting(trend: TrendPeriod[]): number {
  let count = 0;
  for (let i = trend.length - 1; i >= 0; i--) {
    if (trend[i].not_reported) {
      count++;
    } else {
      break;
    }
  }
  return count;
}

export function NonReporterIndicator({
  not_reported_reason,
  trend,
}: NonReporterIndicatorProps): JSX.Element {
  const consecutive = countConsecutiveNonReporting(trend);

  return (
    <div className="inline-flex flex-col gap-1 rounded border border-gray-200 bg-gray-50 px-3 py-2">
      <span className="text-sm text-gray-500">
        This hospital has not submitted data for this measure.
      </span>
      {not_reported_reason && (
        <span className="text-sm text-gray-500">{not_reported_reason}</span>
      )}
      {consecutive > 1 && (
        <span className="text-sm text-gray-500">
          This hospital has not reported this measure for {consecutive} consecutive
          periods.
        </span>
      )}
    </div>
  );
}
