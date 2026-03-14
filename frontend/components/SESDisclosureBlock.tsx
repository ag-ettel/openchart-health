// Rendered by MeasureGroup when hasSESSensitivity() is true. Never by MeasureCard.
// Not collapsible. Renders regardless of the specific hospital's DSH percentage.
// Obligations: see CLAUDE.md: Frontend Specification: Components: SESDisclosureBlock

import Link from "next/link";
import { SES_DISCLOSURE_TEXT } from "@/lib/constants";

export function SESDisclosureBlock(): JSX.Element {
  return (
    <div className="rounded border border-blue-200 bg-blue-50 px-4 py-3 text-sm leading-relaxed text-blue-900">
      <p>{SES_DISCLOSURE_TEXT}</p>
      <p className="mt-2">
        <Link href="/methodology" className="underline hover:no-underline">
          Learn more about how these measures are calculated.
        </Link>
      </p>
    </div>
  );
}
