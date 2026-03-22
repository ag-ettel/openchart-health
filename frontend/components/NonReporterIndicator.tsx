// Same visual footprint as SuppressionIndicator. Never de-emphasized.
// Non-reporting is a distinct state from suppression (Rule 9).
// Provider-agnostic language for hospital and nursing home reuse.

import type { TrendPeriod } from "@/types/provider";

interface NonReporterIndicatorProps {
  not_reported_reason: string | null;
  trend: TrendPeriod[] | null; // nullable — Measure.trend is TrendPeriod[] | null
}

// Counts the trailing run of not_reported: true periods.
// Assumes trend is ordered oldest-first (pipeline guarantee).
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
  const consecutive = countConsecutiveNonReporting(trend ?? []);

  return (
    <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
      <p className="text-sm text-gray-700">
        This facility has not submitted data for this measure.
      </p>
      {not_reported_reason && (
        <p className="mt-1 text-sm text-gray-700">{not_reported_reason}</p>
      )}
      {consecutive > 1 && (
        <p className="mt-1 text-sm text-gray-700">
          Data has not been reported for {consecutive} consecutive periods.
        </p>
      )}
    </div>
  );
}
