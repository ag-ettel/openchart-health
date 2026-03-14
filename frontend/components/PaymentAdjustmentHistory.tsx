// Phase 1: implement.
// Obligations: see CLAUDE.md: Frontend Specification: Components: PaymentAdjustmentHistory

import type { PaymentAdjustment } from "@/types/provider";

interface PaymentAdjustmentHistoryProps {
  adjustments: PaymentAdjustment[];
}

export function PaymentAdjustmentHistory(
  _props: PaymentAdjustmentHistoryProps
): JSX.Element {
  // TODO Phase 1: implement
  //
  // - Render all available program years for HRRP, HACRP, VBP.
  //   SNF_VBP is for nursing homes (deferred). Filter it out for hospital profiles.
  //   Not only the most recent year.
  //
  // - penalty_flag: true -> orange-700 text, orange-50 background.
  //
  // - payment_adjustment_pct with sign and plain-language label:
  //     negative: "Payment reduction: X%"
  //     positive: "Payment bonus: X%"
  //
  // - Consecutive penalty detection:
  //     Sort adjustments by program_year ascending within each program.
  //     When the same program has penalty_flag: true in consecutive years,
  //     render above that program's rows:
  //     "[Program name] penalty received in [N] consecutive years."
  //     Compute from the sorted array. Do not rely on a stored field.
  return <div data-component="PaymentAdjustmentHistory" />;
}
