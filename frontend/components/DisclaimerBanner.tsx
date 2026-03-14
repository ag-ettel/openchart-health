// Required on every consumer-facing page. Renders in app/layout.tsx below site nav.
// Obligations: see CLAUDE.md: Frontend Specification: Components: DisclaimerBanner

import { DISCLAIMER_TEXT } from "@/lib/constants";

export function DisclaimerBanner(): JSX.Element {
  return (
    <aside
      role="note"
      aria-label="Site disclaimer"
      className="w-full border-b border-gray-200 bg-gray-50 px-6 py-4"
    >
      <p className="mx-auto max-w-5xl text-base leading-relaxed text-gray-800">
        {DISCLAIMER_TEXT}
      </p>
    </aside>
  );
}
