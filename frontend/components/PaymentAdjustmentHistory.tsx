// PaymentAdjustmentHistory — renders all available program years for HRRP,
// HACRP, and VBP. SNF_VBP filtered out for hospital profiles.
//
// penalty_flag has three states:
//   true  — penalty applied
//   false — no penalty (participated, not penalized)
//   null  — excluded from program (e.g., HACRP N/A for CAH)
//
// Color: only HACRP consecutive penalties use orange (tail risk threshold per
// DEC-030). Individual penalty_flag=true rows use neutral gray with a text label.
// Orange is reserved for the consecutive-penalty pattern which is a categorical
// tail risk signal, not a per-year color encoding.

import type { PaymentAdjustment, PaymentProgram } from "@/types/provider";
import { consecutivePenalties } from "@/lib/utils";

interface PaymentAdjustmentHistoryProps {
  adjustments: PaymentAdjustment[];
  providerType: "HOSPITAL" | "NURSING_HOME";
}

const PROGRAM_LABELS: Record<PaymentProgram, string> = {
  HRRP: "Hospital Readmissions Reduction Program",
  HACRP: "Hospital-Acquired Condition Reduction Program",
  VBP: "Hospital Value-Based Purchasing Program",
  SNF_VBP: "SNF Value-Based Purchasing Program",
};

// Programs to display per provider type.
const HOSPITAL_PROGRAMS: PaymentProgram[] = ["HRRP", "HACRP", "VBP"];
const NH_PROGRAMS: PaymentProgram[] = ["SNF_VBP"];

function formatAdjustment(pct: number | null): string {
  if (pct === null) return "—";
  if (pct < 0) return `Payment reduction: ${Math.abs(pct).toFixed(2)}%`;
  if (pct > 0) return `Payment bonus: ${pct.toFixed(2)}%`;
  return "No adjustment";
}

function formatPenaltyFlag(flag: boolean | null): string {
  if (flag === null) return "Not applicable";
  return flag ? "Penalty applied" : "No penalty";
}

export function PaymentAdjustmentHistory({
  adjustments,
  providerType,
}: PaymentAdjustmentHistoryProps): JSX.Element {
  const programs =
    providerType === "HOSPITAL" ? HOSPITAL_PROGRAMS : NH_PROGRAMS;

  return (
    <section aria-label="Payment adjustment history">
      <h2 className="mb-3 text-base font-semibold text-gray-900">
        Payment Adjustment History
      </h2>

      {programs.map((program) => {
        const rows = adjustments
          .filter((a) => a.program === program)
          .sort((a, b) => b.program_year - a.program_year); // newest first

        if (rows.length === 0) return null;

        const consecutive = consecutivePenalties(adjustments, program);
        const isHACRPConsecutive =
          program === "HACRP" && consecutive >= 2;

        return (
          <div key={program} className="mb-4">
            <h3 className="mb-2 text-sm font-semibold text-gray-700">
              {PROGRAM_LABELS[program]}
            </h3>

            {/* Consecutive HACRP penalty — orange threshold signal (DEC-030) */}
            {isHACRPConsecutive && (
              <div className="mb-2 rounded border border-orange-200 bg-orange-50 px-3 py-2 text-xs text-orange-700">
                Penalty received in {consecutive} consecutive years.
              </div>
            )}

            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-200 text-left text-gray-500">
                  <th className="py-1 pr-4 font-medium">Year</th>
                  <th className="py-1 pr-4 font-medium">Status</th>
                  <th className="py-1 pr-4 font-medium">Adjustment</th>
                  {rows.some((r) => r.total_score !== null) && (
                    <th className="py-1 font-medium">Score</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.program_year}
                    className="border-b border-gray-100"
                  >
                    <td className="py-1.5 pr-4 text-gray-700">
                      {row.program_year}
                    </td>
                    <td className="py-1.5 pr-4 text-gray-700">
                      {formatPenaltyFlag(row.penalty_flag)}
                    </td>
                    <td className="py-1.5 pr-4 text-gray-700">
                      {formatAdjustment(row.payment_adjustment_pct)}
                    </td>
                    {rows.some((r) => r.total_score !== null) && (
                      <td className="py-1.5 text-gray-700">
                        {row.total_score !== null
                          ? row.total_score.toFixed(2)
                          : "—"}
                        {row.score_percentile !== null && (
                          <span className="ml-1 text-gray-400">
                            ({row.score_percentile.toFixed(0)}th pctl)
                          </span>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}

      {programs.every(
        (p) => !adjustments.some((a) => a.program === p)
      ) && (
        <p className="text-sm text-gray-500">
          No payment adjustment data available.
        </p>
      )}
    </section>
  );
}
