// Rendered by MeasureGroup when hasSESSensitivity() is true. Never by MeasureCard.
// Not collapsible. Renders regardless of the specific hospital's data.
// The disclosure is about the measure methodology, not the hospital.
//
// ses-context.md: "Must link to docs/data_dictionary.md."
// In the frontend, data dictionary content is surfaced on the /methodology page.

import Link from "next/link";
import { SES_DISCLOSURE_TEXT } from "@/lib/constants";

export function SESDisclosureBlock(): React.JSX.Element {
  return (
    <div className="rounded border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-relaxed text-gray-700">
      <p>{SES_DISCLOSURE_TEXT}</p>
      <p className="mt-2">
        <Link href="/methodology" className="underline hover:no-underline">
          Learn more about how these measures are calculated.
        </Link>
      </p>
    </div>
  );
}
