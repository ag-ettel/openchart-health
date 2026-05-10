import fs from "fs";
import path from "path";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import type { Provider } from "@/types/provider";
import { extractCcnFromSlug, providerSlug, titleCase, formatPhone } from "@/lib/utils";
import { buildNursingHomeMetadata } from "@/lib/seo";
import { buildNursingHomeBreadcrumbsJsonLd, buildNursingHomeJsonLd, jsonLdString } from "@/lib/structured-data";
import { MultipleComparisonDisclosure } from "@/components/MultipleComparisonDisclosure";
import { PaymentAdjustmentHistory } from "@/components/PaymentAdjustmentHistory";
import { NursingHomeSummaryDashboard } from "@/components/NursingHomeSummaryDashboard";
import { InspectionTimeline } from "@/components/InspectionTimeline";
import { PenaltyTimeline } from "@/components/PenaltyTimeline";
import { OwnershipPanel } from "@/components/OwnershipPanel";
import { SetCompareTarget } from "@/components/CompareContext";
import { NHGuideLink } from "@/components/NHGuideLink";
import { NHMeasuresSection } from "./NHMeasuresSection";

// The `[ccn]` folder name is historical; the dynamic segment now carries the
// full provider slug ({name}-{city}-{state}-{ccn}). The trailing 6-digit CCN
// is the canonical key — extractCcnFromSlug pulls it out for data lookup.

const DATA_DIR = path.join(process.cwd(), "..", "build", "data");

function loadProvider(ccn: string): Provider {
  const filePath = path.join(DATA_DIR, `${ccn}.json`);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as Provider;
}

interface SearchIndexEntry {
  provider_id: string;
  provider_type: string;
  name: string;
  city: string | null;
  state: string | null;
}

export function generateStaticParams(): { ccn: string }[] {
  // Required by Next.js `output: "export"`: every URL slug we want to render
  // must be listed here. Read the search index and emit slugs for nursing homes.
  const indexPath = path.join(DATA_DIR, "search_index.json");
  if (fs.existsSync(indexPath)) {
    const raw = fs.readFileSync(indexPath, "utf-8");
    const entries = JSON.parse(raw) as SearchIndexEntry[];
    return entries
      .filter((e) => e.provider_type === "NURSING_HOME")
      .map((e) => ({
        ccn: providerSlug(e.name, e.city, e.state, e.provider_id),
      }));
  }
  return fs
    .readdirSync(DATA_DIR)
    .filter((f) => f.endsWith(".json") && f !== "search_index.json")
    .map((f) => f.replace(/\.json$/, ""))
    .map((ccn) => ({ ccn }));
}

interface NursingHomePageProps {
  params: Promise<{ ccn: string }>;
}

export async function generateMetadata({ params }: NursingHomePageProps): Promise<Metadata> {
  const { ccn: slug } = await params;
  const ccn = extractCcnFromSlug(slug);
  if (!ccn) return {};
  const provider = loadProvider(ccn);
  return buildNursingHomeMetadata(provider);
}

export default async function NursingHomePage({ params }: NursingHomePageProps): Promise<React.JSX.Element> {
  const { ccn: slug } = await params;
  const ccn = extractCcnFromSlug(slug);
  if (!ccn) notFound();
  const provider = loadProvider(ccn);
  const ld = jsonLdString(buildNursingHomeJsonLd(provider));
  const breadcrumbs = jsonLdString(buildNursingHomeBreadcrumbsJsonLd(provider));

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
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: ld }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: breadcrumbs }}
      />
      <SetCompareTarget
        ccn={provider.provider_id}
        name={provider.name}
        providerType={provider.provider_type}
      />
      {/* Provider header */}
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{titleCase(provider.name)}</h1>
        <div className="mt-2 space-y-1">
          {addressLine && (
            <p className="flex items-center gap-2 text-sm text-gray-600">
              <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" /></svg>
              {addressLine}
            </p>
          )}
          {provider.phone && (
            <p className="flex items-center gap-2 text-sm text-gray-600">
              <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z" /></svg>
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

      {/* Summary dashboard — Five-Star, SFF, abuse icon, beds, chain */}
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

      {/* Grounder + filter hint */}
      <p className="mb-1 text-sm text-gray-500">
        All data sourced from CMS. Use the filters to explore by quality domain or category.
      </p>

      {/* Main measures area — sidebar + measures */}
      <NHMeasuresSection
        measures={provider.measures}
        paymentAdjustments={provider.payment_adjustments}
        providerLastUpdated={provider.last_updated}
        providerName={titleCase(provider.name)}
      />

      {/* Inspection detail — accordion, below measures */}
      {inspectionEvents.length > 0 && (
        <section className="mt-10 mb-8">
          <InspectionTimeline
            inspectionEvents={inspectionEvents}
            providerLastUpdated={provider.last_updated}
          />
        </section>
      )}

      {/* Penalty + payment program history */}
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

      {/* Ownership entity detail list — full per-role breakdown.
          The ownership viz + parent-group stats render in the dashboard above. */}
      {hasOwnership && (
        <section className="mt-10 mb-8">
          <OwnershipPanel
            ownership={ownership}
            providerLastUpdated={provider.last_updated}
            nursingHomeContext={provider.nursing_home_context}
          />
        </section>
      )}

      {/* Footer */}
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
