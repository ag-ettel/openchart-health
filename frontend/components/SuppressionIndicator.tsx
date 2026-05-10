// Renders the suppression state for a measure. Same visual footprint as a numeric
// value display — never de-emphasized (display-philosophy Rule 3, Principle 3).
//
// Distinguishes full suppression from count-only suppression (DEC-023):
//   - suppressed=true: the measure value itself is unavailable
//   - count_suppressed=true: value is valid, but sample_size/denominator hidden for privacy
//
// MeasureCard handles the routing: SuppressionIndicator is only rendered when
// suppressed=true (full suppression). Count-suppressed notes render separately
// in MeasureCard because the value IS displayed in that case.
//
// Footnote codes associated with suppression are passed through for display.
// Suppression often carries footnote codes (1, 5, 11) that explain why.

import { FootnoteDisclosure } from "./FootnoteDisclosure";

interface SuppressionIndicatorProps {
  suppression_reason: string | null;
  footnote_codes: number[] | null;
  footnote_text: string[] | null;
}

export function SuppressionIndicator({
  suppression_reason,
  footnote_codes,
  footnote_text,
}: SuppressionIndicatorProps): React.JSX.Element {
  return (
    <div className="rounded border border-gray-200 bg-gray-50 px-3 py-2">
      <p className="text-sm text-gray-700">
        {suppression_reason ??
          "This value was suppressed by CMS due to insufficient data or privacy requirements."}
      </p>
      <FootnoteDisclosure
        footnote_codes={footnote_codes}
        footnote_text={footnote_text}
      />
    </div>
  );
}
