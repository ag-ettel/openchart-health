"use client";

// Nursing home profile, client-rendered from R2. See HospitalProfileClient
// for rationale — same SPA fallback pattern.

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import type { Provider } from "@/types/provider";
import { extractCcnFromSlug, titleCase, formatPhone } from "@/lib/utils";
import { MultipleComparisonDisclosure } from "@/components/MultipleComparisonDisclosure";
import { PaymentAdjustmentHistory } from "@/components/PaymentAdjustmentHistory";
import { NursingHomeSummaryDashboard } from "@/components/NursingHomeSummaryDashboard";
import { InspectionTimeline } from "@/components/InspectionTimeline";
import { PenaltyTimeline } from "@/components/PenaltyTimeline";
import { OwnershipPanel } from "@/components/OwnershipPanel";
import { SetCompareTarget } from "@/components/CompareContext";
import { NHGuideLink } from "@/components/NHGuideLink";
import { NHMeasuresSection } from "./NHMeasuresSection";

const CDN_BASE = process.env.NEXT_PUBLIC_CDN_BASE ?? "/data";

async function fetchProvider(ccn: string): Promise<Provider> {
  const resp = await fetch(`${CDN_BASE}/${ccn}.json`);
  if (!resp.ok) throw new Error(`Failed to load provider ${ccn}: ${resp.status}`);
  return resp.json() as Promise<Provider>;
}

function ccnFromPathname(pathname: string | null): string | null {
  if (!pathname) return null;
  const match = pathname.match(/^\/nursing-home\/([^/]+)\/?$/);
  if (!match) return null;
  const slug = match[1];
  if (slug === "_unavailable") return null;
  return extractCcnFromSlug(slug);
}

export function NHProfileClient(): React.JSX.Element {
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
        <h1 className="mb-4 text-2xl font-bold text-gray-900">Nursing home not found</h1>
        <p className="text-sm text-gray-600">
          The URL doesn&apos;t match a known nursing home. Try the{" "}
          <a href="/" className="text-blue-700 underline">home page</a> to search,
          or <a href="/filter-explore/nursing-home/" className="text-blue-700 underline">explore by measure</a>.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="py-12 text-center" role="status" aria-live="polite">
        <p className="text-sm text-gray-500">Loading nursing home data...</p>
      </div>
    );
  }

  if (error || !provider) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <h1 className="mb-4 text-2xl font-bold text-gray-900">Could not load nursing home</h1>
        <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" role="alert" aria-live="assertive">
          {error ?? "Provider data is not available right now."}
        </div>
      </div>
    );
  }

  const addr = provider.address;
  const addressParts = [addr.street, addr.city, addr.state, addr.zip].filter(Boolean);
  const addressLine = addressParts.join(", ");
  const inspectionEvents = provider.inspection_events ?? [];
  const penalties = provider.penalties ?? [];
  const ownership = provider.ownership ?? [];
  const hasOwnership = ownership.length > 0;
  const hasPenalties = penalties.length > 0;

  return (
    <article>
      <SetCompareTarget
        ccn={provider.provider_id}
        name={provider.name}
        providerType={provider.provider_type}
      />
      <header className="mb-6">
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

      {/* CMS reference — Medicare.gov NH publication compliance-ok */}
      <div className="mb-4">
        <NHGuideLink />
      </div>

      <section className="mb-6">
        <NursingHomeSummaryDashboard
          measures={provider.measures}
          nursingHomeContext={provider.nursing_home_context}
          inspectionEvents={provider.inspection_events}
          penalties={provider.penalties}
          paymentAdjustments={provider.payment_adjustments}
          providerName={titleCase(provider.name)}
          providerState={provider.address.state}
          ownership={provider.ownership}
          parentGroupStats={provider.parent_group_stats}
        />
      </section>

      <p className="mb-1 text-sm text-gray-500">
        All data sourced from CMS. Use the filters to explore by quality domain or category.
      </p>

      <NHMeasuresSection
        measures={provider.measures}
        paymentAdjustments={provider.payment_adjustments}
        providerLastUpdated={provider.last_updated}
        providerName={titleCase(provider.name)}
      />

      {inspectionEvents.length > 0 && (
        <section className="mt-10 mb-8">
          <InspectionTimeline
            inspectionEvents={inspectionEvents}
            providerLastUpdated={provider.last_updated}
          />
        </section>
      )}

      {(hasPenalties || provider.payment_adjustments.length > 0) && (
        <section className="mt-10 mb-8">
          {hasPenalties && (
            <PenaltyTimeline
              penalties={penalties}
              providerLastUpdated={provider.last_updated}
            />
          )}
          {provider.payment_adjustments.length > 0 && (
            <div className={hasPenalties ? "mt-6 border-t border-gray-100 pt-6" : ""}>
              <PaymentAdjustmentHistory
                adjustments={provider.payment_adjustments}
                providerType="NURSING_HOME"
              />
            </div>
          )}
        </section>
      )}

      {hasOwnership && (
        <section className="mt-10 mb-8">
          <OwnershipPanel
            ownership={ownership}
            providerLastUpdated={provider.last_updated}
            nursingHomeContext={provider.nursing_home_context}
          />
        </section>
      )}

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
