// Prominent context panel on hospital profile pages. Not behind a tab or expand.
// Reads from provider.hospital_context (HospitalContext type).
//
// Displays the 5 confirmed fields from HospitalContext. Deferred fields
// (staffed_beds, is_teaching_hospital, dsh_status, dsh_percentage,
// dual_eligible_proportion, urban_rural_classification — DEC-004/005/006)
// are acknowledged as "Not yet available" per the guiding ethos: never blank,
// never zero, never a missing section header with no content beneath it.
//
// hospital_overall_rating is ordinal (1-5), not continuous — no CI or error bars
// (display-philosophy Rule 4). Footnote on star rating is surfaced when present.
//
// No field is labeled or presented as a quality measure. These are interpretive
// context only (ses-context.md, display-philosophy.md).
//
// Nursing home equivalent (NursingHomeContextPanel) deferred to NH display build.

import type { HospitalContext } from "@/types/provider";

interface ProviderContextPanelProps {
  context: HospitalContext; // caller must guard non-null
  providerName: string;
}

function ContextRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <div className="flex items-baseline justify-between border-b border-gray-100 py-2 text-sm last:border-b-0">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-700">{children}</span>
    </div>
  );
}

function formatBool(val: boolean | null, trueLabel: string, falseLabel: string): string {
  if (val === null) return "Not yet available";
  return val ? trueLabel : falseLabel;
}

function formatStarRating(rating: number | null): string {
  if (rating === null) return "Not yet available";
  return `${rating} out of 5`;
}

export function ProviderContextPanel({
  context,
  providerName,
}: ProviderContextPanelProps): JSX.Element {
  return (
    <div className="rounded border border-gray-200 bg-white px-4 py-4">
      <h2 className="mb-3 text-sm font-semibold text-gray-900">
        Hospital Context: {providerName}
      </h2>
      <p className="mb-3 text-xs text-gray-500">
        These fields are interpretive context, not quality measures.
      </p>

      {/* Confirmed fields from HospitalContext */}
      <div className="mb-4">
        <ContextRow label="CMS Overall Star Rating">
          {formatStarRating(context.hospital_overall_rating)}
          {context.hospital_overall_rating_footnote && (
            <span className="ml-1 text-xs text-gray-500">
              (footnote: {context.hospital_overall_rating_footnote})
            </span>
          )}
        </ContextRow>
        <ContextRow label="Critical Access Hospital">
          {formatBool(context.is_critical_access, "Yes", "No")}
        </ContextRow>
        <ContextRow label="Emergency Services">
          {formatBool(context.is_emergency_services, "Yes", "No")}
        </ContextRow>
        <ContextRow label="Birthing Friendly Designation">
          {formatBool(context.birthing_friendly_designation, "Yes", "No")}
        </ContextRow>
      </div>

      {/* Deferred fields — acknowledged, not silently omitted (DEC-004/005/006) */}
      <div>
        <p className="mb-2 text-xs font-medium text-gray-500">
          Additional context (not yet available)
        </p>
        <div className="text-xs text-gray-500">
          <p>
            Staffed beds, teaching status, DSH status, dual-eligible proportion,
            and urban/rural classification are not available through the CMS
            Provider Data API used by this tool. These fields may be added in a
            future update if a viable data source is identified.
          </p>
        </div>
      </div>
    </div>
  );
}
