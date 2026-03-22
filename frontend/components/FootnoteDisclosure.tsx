// Footnotes are first-class data (Principle 3, display-philosophy Rule 3).
// Always visible — never collapsed by default. A consumer must not click to
// discover that a measure has data quality caveats.
//
// Footnote 29 (methodology change) is special-cased: it triggers Data Integrity
// Rule 11 and must be visually prominent, not buried in a list.
//
// Accepts nullable arrays matching the Measure type. Returns null when no
// footnotes exist.

import {
  METHODOLOGY_CHANGE_FOOTNOTE_TEXT,
} from "@/lib/constants";

interface FootnoteDisclosureProps {
  footnote_codes: number[] | null;
  footnote_text: string[] | null;
}

const METHODOLOGY_CHANGE_CODE = 29;

export function FootnoteDisclosure({
  footnote_codes,
  footnote_text,
}: FootnoteDisclosureProps): React.JSX.Element | null {
  if (!footnote_codes || footnote_codes.length === 0) return null;

  const texts = footnote_text ?? [];
  const hasMethodologyChange = footnote_codes.includes(METHODOLOGY_CHANGE_CODE);

  // Separate footnote 29 from other footnotes for distinct rendering.
  const standardFootnotes = footnote_codes
    .map((code, i) => ({ code, text: texts[i] ?? null }))
    .filter((f) => f.code !== METHODOLOGY_CHANGE_CODE);

  return (
    <div className="mt-2 space-y-2">
      {/* Footnote 29: methodology change — prominent warning (Rule 11) */}
      {hasMethodologyChange && (
        <div className="rounded border border-gray-300 bg-gray-50 px-3 py-2 text-xs text-gray-700">
          <span className="font-semibold">Footnote 29:</span>{" "}
          {METHODOLOGY_CHANGE_FOOTNOTE_TEXT}
        </div>
      )}

      {/* Standard footnotes — always visible, never collapsed */}
      {standardFootnotes.length > 0 && (
        <ul className="space-y-1">
          {standardFootnotes.map((f, i) => (
            <li
              key={`${f.code}-${i}`}
              className="text-xs text-gray-600"
            >
              <span className="font-medium">Footnote {f.code}</span>
              {f.text ? `: ${f.text}` : " (no description available)"}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
