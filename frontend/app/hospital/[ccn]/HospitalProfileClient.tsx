"use client";

// Hospital profile, client-rendered. Fetches provider JSON from the CDN
// (R2 in production, /data in dev) at runtime.
//
// Why client-rendered and not SSG: the per-provider JSON files don't ship
// with the Pages deployment (22K files would exceed the 20K Pages limit,
// and they're gitignored anyway). The static export emits one shell HTML
// at /hospital/_unavailable/; a public/_redirects rewrite routes every
// /hospital/{slug}/ URL to that shell, and this component reads the URL,
// extracts the CCN, fetches from R2, and renders.
//
// Trade-off: per-provider SEO is lost (search engines see one shell). A
// future iteration could pre-render top-N providers at build time and
// keep SPA fallback for the long tail.

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import type { Provider } from "@/types/provider";
import { extractCcnFromSlug, titleCase, formatPhone } from "@/lib/utils";
import { HospitalSummaryDashboard } from "@/components/HospitalSummaryDashboard";
import { SetCompareTarget } from "@/components/CompareContext";
import { MeasuresSection } from "./MeasuresSection";

const CDN_BASE = process.env.NEXT_PUBLIC_CDN_BASE ?? "/data";

async function fetchProvider(ccn: string): Promise<Provider> {
  const resp = await fetch(`${CDN_BASE}/${ccn}.json`);
  if (!resp.ok) throw new Error(`Failed to load provider ${ccn}: ${resp.status}`);
  return resp.json() as Promise<Provider>;
}

/** Read the CCN slug from the URL path. Returns null when on the placeholder. */
function ccnFromPathname(pathname: string | null): string | null {
  if (!pathname) return null;
  // /hospital/{slug}/ — strip prefix and trailing slash
  const match = pathname.match(/^\/hospital\/([^/]+)\/?$/);
  if (!match) return null;
  const slug = match[1];
  if (slug === "_unavailable") return null;
  return extractCcnFromSlug(slug);
}

export function HospitalProfileClient(): React.JSX.Element {
  const pathname = usePathname();
  const ccn = ccnFromPathname(pathname);
  const [provider, setProvider] = useState<Provider | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ccn) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    fetchProvider(ccn)
      .then((p) => setProvider(p))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [ccn]);

  if (!ccn) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <h1 className="mb-4 text-2xl font-bold text-gray-900">Hospital not found</h1>
        <p className="text-sm text-gray-600">
          The URL doesn&apos;t match a known hospital. Try the{" "}
          <a href="/" className="text-blue-700 underline">home page</a> to search,
          or <a href="/filter-explore/" className="text-blue-700 underline">explore by measure</a>.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="py-12 text-center" role="status" aria-live="polite">
        <p className="text-sm text-gray-500">Loading hospital data...</p>
      </div>
    );
  }

  if (error || !provider) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <h1 className="mb-4 text-2xl font-bold text-gray-900">Could not load hospital</h1>
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" role="alert" aria-live="assertive">
          {error ?? "Provider data is not available right now."}
        </div>
      </div>
    );
  }

  const addr = provider.address;
  const addressParts = [addr.street, addr.city, addr.state, addr.zip].filter(Boolean);
  const addressLine = addressParts.join(", ");

  return (
    <article>
      {/* Provider header */}
      <header className="mb-6">
        <SetCompareTarget
          ccn={provider.provider_id}
          name={provider.name}
          providerType={provider.provider_type}
        />
        <h1 className="text-2xl font-bold text-gray-900">{titleCase(provider.name)}</h1>
        <div className="mt-2 space-y-1">
          {addressLine && (
            <p className="flex items-center gap-2 text-sm text-gray-600">
              <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true" focusable="false"><path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" /></svg>
              {addressLine}
            </p>
          )}
          {provider.phone && (
            <p className="flex items-center gap-2 text-sm text-gray-600">
              <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true" focusable="false"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z" /></svg>
              {formatPhone(provider.phone)}
            </p>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {provider.provider_subtype && (
            <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-3 py-0.5 text-xs text-gray-600">
              <span className="mr-1 font-medium text-gray-500">Type:</span>
              {provider.provider_subtype}
            </span>
          )}
          {provider.ownership_type && (
            <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-3 py-0.5 text-xs text-gray-600">
              <span className="mr-1 font-medium text-gray-500">Ownership:</span>
              {provider.ownership_type}
            </span>
          )}
        </div>
      </header>

      <section className="mb-6">
        <HospitalSummaryDashboard
          measures={provider.measures}
          paymentAdjustments={provider.payment_adjustments}
          hospitalContext={provider.hospital_context}
        />
      </section>

      <p className="mb-1 text-sm text-gray-500">
        All data sourced from CMS. Use the filters to explore by condition or category.
      </p>

      <MeasuresSection
        measures={provider.measures}
        paymentAdjustments={provider.payment_adjustments}
        providerLastUpdated={provider.last_updated}
        providerName={titleCase(provider.name)}
      />

      <footer className="border-t border-gray-200 pt-4 text-xs text-gray-500">
        <p>
          Data reflects CMS reporting as of{" "}
          {new Date(provider.last_updated).toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
          })}.
        </p>
        <p className="mt-1">Provider CCN: {provider.provider_id}</p>
      </footer>
    </article>
  );
}
