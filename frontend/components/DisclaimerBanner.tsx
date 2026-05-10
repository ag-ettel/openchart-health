// Required on every consumer-facing page, visible without scrolling
// (legal-compliance.md). Sticky footer ensures constant visibility.

import { DISCLAIMER_TEXT } from "@/lib/constants";

export function DisclaimerBanner(): React.JSX.Element {
  return (
    <aside
      role="note"
      aria-label="Site disclaimer"
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-gray-200 bg-gray-50/95 px-6 py-2 backdrop-blur-sm"
    >
      {/* legal-compliance.md requires 4.5:1 contrast. text-gray-700 on bg-gray-50 = ~10.4:1.
          Do not lower the contrast even for visual harmony; this banner is the primary legal shield. */}
      <p className="mx-auto max-w-5xl text-xs leading-snug text-gray-700">
        {DISCLAIMER_TEXT}
      </p>
    </aside>
  );
}
