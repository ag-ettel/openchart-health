// PatientSafetyRecord — the primary view on a hospital profile page.
//
// "Tail risk is the primary product, not a secondary tab." (Principle 2)
//
// Renders FIRST on the profile page, before MultipleComparisonDisclosure and all
// MeasureGroup instances. Every measure with tail_risk_flag=true appears here
// regardless of its value, suppression state, or reporting status.
//
// Sort philosophy: suppressed and non-reported tail risk measures sort to the TOP,
// not the bottom. A suppressed mortality rate is a stronger signal of uncertainty
// than a reported rate near the average. Absence is information (Principle 3).
//
// HACRP consecutive penalty integration: display-philosophy requires that
// consecutive HACRP penalties surface prominently in this view, not only in
// PaymentAdjustmentHistory. This component accepts payment adjustments and
// detects the pattern.

import type { Measure, PaymentAdjustment } from "@/types/provider";
import { consecutivePenalties } from "@/lib/utils";
import { MeasureCard } from "./MeasureCard";

interface PatientSafetyRecordProps {
  measures: Measure[]; // full provider.measures array; filters internally
  paymentAdjustments: PaymentAdjustment[];
  providerLastUpdated: string;
}

// Sort tail risk measures: suppressed/not-reported first (absence is the signal),
// then by absolute deviation from national_avg descending, then measures without
// a national_avg last among the valued group.
function sortTailRisk(measures: Measure[]): Measure[] {
  return [...measures].sort((a, b) => {
    const aAbsent = a.suppressed || a.not_reported;
    const bAbsent = b.suppressed || b.not_reported;

    // Absent measures sort first — absence on a tail risk measure is the
    // strongest uncertainty signal.
    if (aAbsent && !bAbsent) return -1;
    if (!aAbsent && bAbsent) return 1;
    if (aAbsent && bAbsent) return 0;

    // Both have values. Sort by absolute deviation from national_avg.
    const aHasDeviation =
      a.numeric_value !== null && a.national_avg !== null;
    const bHasDeviation =
      b.numeric_value !== null && b.national_avg !== null;

    if (aHasDeviation && !bHasDeviation) return -1;
    if (!aHasDeviation && bHasDeviation) return 1;
    if (!aHasDeviation && !bHasDeviation) return 0;

    const aDev = Math.abs(a.numeric_value! - a.national_avg!);
    const bDev = Math.abs(b.numeric_value! - b.national_avg!);
    return bDev - aDev; // larger deviation first
  });
}

export function PatientSafetyRecord({
  measures,
  paymentAdjustments,
  providerLastUpdated,
}: PatientSafetyRecordProps): JSX.Element {
  const tailRisk = sortTailRisk(
    measures.filter((m) => m.tail_risk_flag)
  );
  const hacrpConsecutive = consecutivePenalties(paymentAdjustments, "HACRP");

  return (
    <section aria-label="Patient safety record">
      <h2 className="mb-3 text-base font-semibold text-gray-900">
        Patient Safety Record
      </h2>

      {/* HACRP consecutive penalty — prominent warning per display-philosophy */}
      {hacrpConsecutive >= 2 && (
        <div className="mb-4 rounded border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-700">
          This hospital has received a Hospital-Acquired Condition Reduction
          Program (HACRP) penalty in {hacrpConsecutive} consecutive years.
          HACRP penalties are applied to hospitals in the bottom quartile of
          patient safety scores.
        </div>
      )}

      {tailRisk.length === 0 ? (
        <p className="text-sm text-gray-500">
          No tail risk measures available for this hospital.
        </p>
      ) : (
        <div className="space-y-3">
          {tailRisk.map((m) => (
            <MeasureCard
              key={`${m.measure_id}-${m.period_label}-${m.stratification ?? ""}`}
              measure={m}
              providerLastUpdated={providerLastUpdated}
            />
          ))}
        </div>
      )}
    </section>
  );
}
