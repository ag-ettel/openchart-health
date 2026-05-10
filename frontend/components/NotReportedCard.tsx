// NotReportedCard — compact card for measures where data is suppressed or not reported.
// Shows measure name, status, reason, and what % of hospitals report this measure
// nationally so users can judge whether non-reporting is common or unusual.

"use client";

import type { Measure } from "@/types/provider";
import { formatPeriodLabel } from "@/lib/utils";
import { useReportingRate } from "@/lib/use-reporting-rates";

interface NotReportedCardProps {
  measure: Measure;
}

export function NotReportedCard({ measure }: NotReportedCardProps): React.JSX.Element {
  const name = measure.measure_name ?? measure.measure_id;
  const status = measure.suppressed ? "Suppressed" : "Not reported";
  const reason = measure.suppressed
    ? measure.suppression_reason
    : measure.not_reported_reason;

  const rate = useReportingRate(measure.measure_id);

  return (
    <div className="rounded border border-gray-100 bg-gray-50 px-4 py-2.5">
      <div className="flex items-baseline justify-between">
        <div className="min-w-0 flex-1">
          <span className="text-xs font-medium text-gray-600">{name}</span>
          {reason && (
            <span className="ml-2 text-xs text-gray-400">— {reason}</span>
          )}
        </div>
        <div className="ml-4 flex shrink-0 items-center gap-2">
          <span className="text-xs text-gray-400">
            {formatPeriodLabel(measure.period_label)}
          </span>
          <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-500">
            {status}
          </span>
        </div>
      </div>
      {rate !== null && (
        <div className="mt-1 text-xs text-gray-400">
          Reported by {rate.pct_reported}% of eligible hospitals
          {rate.pct_reported >= 80 && (
            <span className="ml-1 font-medium text-amber-600">
              — most hospitals report this
            </span>
          )}
          {rate.pct_reported < 25 && (
            <span className="ml-1 text-gray-400">
              — few hospitals report this
            </span>
          )}
        </div>
      )}
    </div>
  );
}
