// Annotation for methodology change boundaries (footnote 29, Rule 11).
// Rendered by TrendChart at period boundaries where methodology_change_flag is true.
// Neutral gray — methodology changes are not tail risk thresholds (DEC-030).

import { METHODOLOGY_CHANGE_FOOTNOTE_TEXT } from "@/lib/constants";

interface MethodologyChangeFlagProps {
  periodLabel: string; // the period where the methodology changed
}

export function MethodologyChangeFlag({
  periodLabel,
}: MethodologyChangeFlagProps): JSX.Element {
  return (
    <div className="rounded border border-gray-300 bg-gray-50 px-3 py-2 text-xs text-gray-700">
      <span className="font-medium">{periodLabel}:</span>{" "}
      {METHODOLOGY_CHANGE_FOOTNOTE_TEXT}
    </div>
  );
}
