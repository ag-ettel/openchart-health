// PenaltyTimeline — displays nursing home penalties chronologically.
//
// Display rules:
// - Fine amounts with "Originally $X" when fine_amount_changed is true
// - Payment denials with duration
// - No editorial language about why amounts changed — just CMS-published facts
// - Ownership-quality disclaimer if penalties appear alongside ownership data
//   (handled at page level, not here)

import type { Penalty } from "@/types/provider";

interface PenaltyTimelineProps {
  penalties: Penalty[];
  providerLastUpdated: string;
}

function formatDate(iso: string | null): string {
  if (!iso) return "Date not available";
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatCurrency(amount: number): string {
  return "$" + amount.toLocaleString("en-US", { minimumFractionDigits: 0 });
}

export function PenaltyTimeline({
  penalties,
  providerLastUpdated,
}: PenaltyTimelineProps): React.JSX.Element {
  if (penalties.length === 0) {
    return (
      <section aria-label="Penalty history">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Penalty History</h2>
        <p className="text-sm text-gray-500">
          No CMS-imposed penalties in the current data for this facility.
        </p>
      </section>
    );
  }

  // Sort newest first
  const sorted = [...penalties].sort((a, b) => {
    const aDate = a.penalty_date ?? "";
    const bDate = b.penalty_date ?? "";
    return bDate.localeCompare(aDate);
  });

  const totalFines = sorted
    .filter((p) => p.penalty_type === "Fine" && p.fine_amount !== null)
    .reduce((sum, p) => sum + (p.fine_amount ?? 0), 0);

  return (
    <section aria-label="Penalty history">
      <h2 className="mb-2 text-lg font-semibold text-gray-900">Penalty History</h2>
      <p className="mb-1 text-xs text-gray-500">
        {sorted.length} penalt{sorted.length !== 1 ? "ies" : "y"} on record.
        {totalFines > 0 && ` Total current fines: ${formatCurrency(totalFines)}.`}
      </p>
      <p className="mb-4 text-xs text-gray-400">
        Source: CMS Nursing Home Penalties dataset. Data reflects CMS reporting as of{" "}
        {formatDate(providerLastUpdated)}.
      </p>

      <div className="space-y-3">
        {sorted.map((pen, i) => (
          <div
            key={`${pen.penalty_date}-${pen.penalty_type}-${i}`}
            className="rounded border border-gray-200 bg-white px-3 py-2.5"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-800">
                    {pen.penalty_type}
                  </span>
                  <span className="text-xs text-gray-400">
                    {formatDate(pen.penalty_date)}
                  </span>
                </div>

                {pen.penalty_type === "Fine" && pen.fine_amount !== null && (
                  <div className="mt-1">
                    <p className="text-sm text-gray-700">
                      Current fine: {formatCurrency(pen.fine_amount)}
                    </p>
                    {pen.fine_amount_changed && pen.originally_published_fine_amount !== null && (
                      <p className="text-xs text-gray-500">
                        Originally published: {formatCurrency(pen.originally_published_fine_amount)}
                      </p>
                    )}
                  </div>
                )}

                {pen.penalty_type === "Payment Denial" && (
                  <div className="mt-1">
                    {pen.payment_denial_start_date && (
                      <p className="text-xs text-gray-600">
                        Start date: {formatDate(pen.payment_denial_start_date)}
                      </p>
                    )}
                    {pen.payment_denial_length_days !== null && (
                      <p className="text-xs text-gray-600">
                        Duration: {pen.payment_denial_length_days} day{pen.payment_denial_length_days !== 1 ? "s" : ""}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
