// PatientSafetyRecord — condensed primary view of critical safety indicators.
//
// Shows top measures by deviation from national average (most noteworthy first).
// Limited to a preview count to keep the page scannable. The full set is
// available in All Quality Measures filtered by "Critical Safety Indicators".

"use client";

import { useState } from "react";
import type { Measure, PaymentAdjustment } from "@/types/provider";
import { consecutivePenalties, measureHasData } from "@/lib/utils";
import { MeasureCard } from "./MeasureCard";

const PREVIEW_COUNT = 5;

interface PatientSafetyRecordProps {
  measures: Measure[];
  paymentAdjustments: PaymentAdjustment[];
  providerLastUpdated: string;
  providerName?: string;
  providerType?: string;
}

function sortTailRisk(measures: Measure[]): Measure[] {
  return [...measures].sort((a, b) => {
    const aHasDev = a.numeric_value !== null && a.national_avg !== null;
    const bHasDev = b.numeric_value !== null && b.national_avg !== null;
    if (aHasDev && !bHasDev) return -1;
    if (!aHasDev && bHasDev) return 1;
    if (!aHasDev && !bHasDev) return 0;

    const aDev = Math.abs(a.numeric_value! - a.national_avg!);
    const bDev = Math.abs(b.numeric_value! - b.national_avg!);
    return bDev - aDev;
  });
}

export function PatientSafetyRecord({
  measures,
  paymentAdjustments,
  providerLastUpdated,
  providerName = "This hospital",
  providerType,
}: PatientSafetyRecordProps): React.JSX.Element {
  const [showAll, setShowAll] = useState(false);

  const tailRisk = sortTailRisk(
    measures.filter((m) => m.tail_risk_flag && m.stratification === null && measureHasData(m))
  );
  const hacrpConsecutive = consecutivePenalties(paymentAdjustments, "HACRP");

  const visible = showAll ? tailRisk : tailRisk.slice(0, PREVIEW_COUNT);
  const hasMore = tailRisk.length > PREVIEW_COUNT;

  return (
    <section aria-label="Critical safety indicators">
      <h2 className="mb-3 text-lg font-semibold text-gray-900">
        Critical Safety Indicators
      </h2>
      <p className="mb-4 text-xs text-gray-500">
        Measures related to mortality, serious complications, infections, and adverse events.
        {tailRisk.length > PREVIEW_COUNT && !showAll && (
          <> Showing top {PREVIEW_COUNT} of {tailRisk.length} measures.</>
        )}
      </p>

      {hacrpConsecutive >= 2 && (
        <div className="mb-4 rounded border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-700">
          This hospital has received a Hospital-Acquired Condition Reduction
          Program (HACRP) penalty in {hacrpConsecutive} consecutive years.
        </div>
      )}

      {tailRisk.length === 0 ? (
        <p className="text-sm text-gray-500">
          No critical safety measures with data available for this hospital.
        </p>
      ) : (
        <>
          <div className="space-y-4">
            {visible.map((m) => (
              <MeasureCard
                key={`${m.measure_id}-${m.period_label}-${m.stratification ?? ""}`}
                measure={m}
                providerLastUpdated={providerLastUpdated}
                providerName={providerName}
                providerType={providerType}
              />
            ))}
          </div>

          {hasMore && (
            <button
              type="button"
              onClick={() => setShowAll((prev) => !prev)}
              className="mt-4 w-full rounded border border-gray-200 bg-gray-50 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
            >
              {showAll
                ? "Show fewer"
                : `Show all ${tailRisk.length} critical safety measures`}
            </button>
          )}
        </>
      )}
    </section>
  );
}
