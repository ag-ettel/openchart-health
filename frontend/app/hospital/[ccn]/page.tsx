import fs from "fs";
import path from "path";
import type { Provider } from "@/types/provider";
import { titleCase } from "@/lib/utils";
import { MultipleComparisonDisclosure } from "@/components/MultipleComparisonDisclosure";
import { PaymentAdjustmentHistory } from "@/components/PaymentAdjustmentHistory";
import { HospitalSummaryDashboard } from "@/components/HospitalSummaryDashboard";
import { MeasuresSection } from "./MeasuresSection";

const DATA_DIR = path.join(process.cwd(), "..", "build", "data");

function loadProvider(ccn: string): Provider {
  const filePath = path.join(DATA_DIR, `${ccn}.json`);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as Provider;
}

export function generateStaticParams(): { ccn: string }[] {
  return [{ ccn: "010001" }];
}

interface HospitalPageProps {
  params: Promise<{ ccn: string }>;
}

export default async function HospitalPage({ params }: HospitalPageProps): Promise<React.JSX.Element> {
  const { ccn } = await params;
  const provider = loadProvider(ccn);

  const addr = provider.address;
  const addressParts = [addr.street, addr.city, addr.state, addr.zip].filter(Boolean);
  const addressLine = addressParts.join(", ");

  return (
    <article>
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
              {provider.phone}
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

      {/* Summary dashboard — replaces the old context panel */}
      <section className="mb-6">
        <HospitalSummaryDashboard
          measures={provider.measures}
          paymentAdjustments={provider.payment_adjustments}
          hospitalContext={provider.hospital_context}
        />
      </section>

      {/* Grounder + filter hint */}
      <p className="mb-1 text-sm text-gray-500">
        All data sourced from CMS. Use the filters to explore by condition or category.
      </p>

      {/* Main content area — sidebar + measures from the start */}
      <MeasuresSection
        measures={provider.measures}
        paymentAdjustments={provider.payment_adjustments}
        providerLastUpdated={provider.last_updated}
        providerName={titleCase(provider.name)}
      />

      {/* Payment adjustment history */}
      {provider.payment_adjustments.length > 0 && (
        <section className="mt-10 mb-8">
          <h2 className="mb-3 text-lg font-semibold text-gray-900">
            Payment and Value Programs
          </h2>
          <PaymentAdjustmentHistory
            adjustments={provider.payment_adjustments}
            providerType="HOSPITAL"
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
