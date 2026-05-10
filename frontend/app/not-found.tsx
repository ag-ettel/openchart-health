import type { Metadata } from "next";
import { SITE_NAME } from "@/lib/constants";

// 404 pages should not be indexed by search engines and intentionally do
// not declare a canonical (a 404 has no canonical equivalent).
export const metadata: Metadata = {
  title: `Page not found | ${SITE_NAME}`,
  description: "The requested page could not be found on OpenChart Health.",
  robots: { index: false, follow: false },
};

export default function NotFound(): React.JSX.Element {
  return (
    <div className="py-16">
      <h1 className="text-2xl font-semibold text-gray-900">Page not found</h1>
      <p className="mt-3 max-w-prose text-sm leading-relaxed text-gray-600">
        We could not find the page you requested. The provider CCN may be
        misspelled, or the page may have been removed.
      </p>
      <p className="mt-4 text-sm">
        <a href="/" className="text-gray-900 underline underline-offset-2 hover:no-underline">
          Return to home
        </a>
        <span className="mx-3 text-gray-300">·</span>
        <a href="/methodology/" className="text-gray-900 underline underline-offset-2 hover:no-underline">
          Methodology
        </a>
      </p>
    </div>
  );
}
