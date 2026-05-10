// NHGuideLink — reference banner pointing to CMS's official Medicare.gov
// publication titled "Your Guide to Choosing a Nursing Home". compliance-ok
//
// Legal framing (legal-compliance.md): this is a CMS resource, attributed to
// CMS, not editorialized. Surrounding text uses "CMS publishes" / "Medicare.gov"
// rather than "use this to choose" or "decide which facility is right for you."
// We point to CMS's reference; the consumer does the rest.

import { CMS_NH_GUIDE_URL, CMS_NH_GUIDE_TITLE } from "@/lib/constants";

export function NHGuideLink(): React.JSX.Element {
  return (
    <aside className="flex items-start gap-2 rounded-md border border-blue-100 bg-blue-50/60 px-3 py-2 text-xs text-blue-900">
      <svg
        className="mt-0.5 h-4 w-4 shrink-0 text-blue-600"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.75}
        aria-hidden
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
      </svg>
      <p className="leading-relaxed">
        Reference: CMS publishes{" "}
        <a
          href={CMS_NH_GUIDE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium underline decoration-blue-300 underline-offset-2 hover:decoration-blue-600"
        >
          {CMS_NH_GUIDE_TITLE}
        </a>{" "}
        on Medicare.gov — official guidance on what nursing-home characteristics matter and how CMS publishes the underlying data.
        <span className="ml-1 inline-block align-text-bottom text-blue-500" aria-hidden>
          <svg className="inline h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
          </svg>
        </span>
      </p>
    </aside>
  );
}
