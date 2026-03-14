"use client";

// Collapsed by default. Badge always visible when footnotes exist.
// Never hidden entirely when footnote_codes.length > 0.
// Obligations: see CLAUDE.md: Frontend Specification: Components: FootnoteDisclosure

import { useState } from "react";

interface FootnoteDisclosureProps {
  footnote_codes: number[];
  footnote_text:  string[];
}

export function FootnoteDisclosure({
  footnote_codes,
  footnote_text,
}: FootnoteDisclosureProps): JSX.Element | null {
  const [open, setOpen] = useState(false);

  if (footnote_codes.length === 0) return null;

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        className="text-xs text-gray-400 underline hover:no-underline"
      >
        {footnote_codes.length} footnote{footnote_codes.length > 1 ? "s" : ""}
      </button>
      {open && (
        <ul className="mt-2 space-y-1">
          {footnote_codes.map((code, i) => (
            <li key={`${code}-${i}`} className="text-xs text-gray-500">
              <span className="font-medium">{code}</span>
              {footnote_text[i] ? `: ${footnote_text[i]}` : ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
