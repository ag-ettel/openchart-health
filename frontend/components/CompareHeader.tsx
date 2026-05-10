"use client";

// CompareHeader — side-by-side provider identity, gate conditions, and basic
// context for the compare page. Provider-type-aware:
//   - HOSPITAL: hospital_context badges (critical access, emergency, birthing-friendly),
//     CMS overall star rating
//   - NURSING_HOME: gate-condition badges (SFF, abuse icon, CCRC, hospital-based),
//     bed count, chain affiliation. SFF and abuse icon are gate conditions per
//     display-philosophy.md NH-9 — full visual prominence.
//
// Stacks vertically on mobile, side-by-side on lg+.

import type { Provider, NursingHomeContext } from "@/types/provider";
import { titleCase, formatPhone } from "@/lib/utils";

interface CompareHeaderProps {
  providerA: Provider;
  providerB: Provider;
}

interface ContextBadge {
  label: string;
  tooltip: string;
  variant: "neutral" | "orange";
}

function hospitalBadges(provider: Provider): ContextBadge[] {
  const ctx = provider.hospital_context;
  if (!ctx) return [];
  const badges: ContextBadge[] = [];
  if (ctx.is_critical_access) {
    badges.push({
      label: "Critical Access",
      tooltip: "CMS-designated Critical Access Hospital — generally rural, ≤25 inpatient beds, with specific Medicare reimbursement structure.",
      variant: "neutral",
    });
  }
  if (ctx.is_emergency_services) {
    badges.push({ label: "Emergency Services", tooltip: "This hospital provides emergency department services.", variant: "neutral" });
  }
  if (ctx.birthing_friendly_designation) {
    badges.push({ label: "Birthing Friendly", tooltip: "CMS Birthing-Friendly designation, indicating reported maternity care quality practices.", variant: "neutral" });
  }
  return badges;
}

function nhBadges(ctx: NursingHomeContext | null): ContextBadge[] {
  if (!ctx) return [];
  const badges: ContextBadge[] = [];
  if (ctx.is_special_focus_facility === true) {
    badges.push({
      label: "Special Focus Facility",
      tooltip: "CMS designates this facility for intensive oversight due to a history of serious inspection findings.",
      variant: "orange",
    });
  } else if (ctx.is_special_focus_facility_candidate === true) {
    badges.push({
      label: "Special Focus Candidate",
      tooltip: "CMS has identified this facility as a candidate for its Special Focus program based on inspection history.",
      variant: "orange",
    });
  }
  if (ctx.is_abuse_icon === true) {
    badges.push({
      label: "Abuse Finding",
      tooltip: "CMS has flagged this facility based on a substantiated finding of abuse, neglect, or exploitation.",
      variant: "orange",
    });
  }
  if (ctx.is_hospital_based === true) {
    badges.push({ label: "Hospital-Based", tooltip: "This nursing home operates within a hospital.", variant: "neutral" });
  }
  if (ctx.is_continuing_care_retirement_community === true) {
    badges.push({
      label: "CCRC",
      tooltip: "Continuing Care Retirement Community — multiple levels of care (independent living, assisted living, skilled nursing) on one campus.",
      variant: "neutral",
    });
  }
  return badges;
}

function WarningIcon(): React.JSX.Element {
  return (
    <svg className="h-3 w-3 shrink-0" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
    </svg>
  );
}

function Badge({ badge }: { badge: ContextBadge }): React.JSX.Element {
  const cls = badge.variant === "orange"
    ? "border border-orange-200 bg-orange-50 text-orange-700"
    : "border border-gray-200 bg-gray-50 text-gray-600";
  return (
    <span
      className={`group relative inline-flex cursor-help items-center gap-1 rounded-full px-3 py-0.5 text-xs font-medium ${cls}`}
    >
      {badge.variant === "orange" && <WarningIcon />}
      {badge.label}
      <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-60 -translate-x-1/2 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-normal leading-relaxed text-gray-600 opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
        {badge.tooltip}
      </span>
    </span>
  );
}

function ProviderIdentity({ provider }: { provider: Provider }): React.JSX.Element {
  const addr = provider.address;
  const addressLine = [addr.street, addr.city, addr.state, addr.zip].filter(Boolean).join(", ");

  const isHospital = provider.provider_type === "HOSPITAL";
  const isNH = provider.provider_type === "NURSING_HOME";

  const badges = isHospital
    ? hospitalBadges(provider)
    : isNH
      ? nhBadges(provider.nursing_home_context)
      : [];

  // Gate-condition badges (orange) appear first, neutral after, so SFF/abuse
  // are unmistakable per NH-9.
  badges.sort((a, b) => (a.variant === b.variant ? 0 : a.variant === "orange" ? -1 : 1));

  const nhCtx = provider.nursing_home_context;
  const hospCtx = provider.hospital_context;

  return (
    <div className="min-w-0 flex-1">
      <h2 className="text-lg font-bold leading-snug text-gray-900">
        {titleCase(provider.name)}
      </h2>

      {/* Address + phone */}
      <div className="mt-1.5 space-y-1">
        {addressLine && (
          <p className="flex items-center gap-1.5 text-xs text-gray-500">
            <svg className="h-3.5 w-3.5 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" /></svg>
            {addressLine}
          </p>
        )}
        {provider.phone && (
          <p className="flex items-center gap-1.5 text-xs text-gray-500">
            <svg className="h-3.5 w-3.5 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z" /></svg>
            {formatPhone(provider.phone)}
          </p>
        )}
      </div>

      {/* Type / ownership / chain row */}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {provider.provider_subtype && (
          <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-xs text-gray-600">
            <span className="mr-1 font-medium text-gray-500">Type:</span>
            {provider.provider_subtype}
          </span>
        )}
        {provider.ownership_type && (
          <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-xs text-gray-600">
            <span className="mr-1 font-medium text-gray-500">Ownership:</span>
            {provider.ownership_type}
          </span>
        )}
        {isNH && nhCtx?.chain_name && (
          <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-xs text-gray-600">
            <span className="mr-1 font-medium text-gray-500">Chain:</span>
            {titleCase(nhCtx.chain_name)}
          </span>
        )}
        {isNH && nhCtx?.certified_beds != null && (
          <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-0.5 text-xs text-gray-600">
            <span className="mr-1 font-medium text-gray-500">Beds:</span>
            {nhCtx.certified_beds}
          </span>
        )}
      </div>

      {/* Gate-condition / context badges */}
      {badges.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {badges.map((b) => <Badge key={b.label} badge={b} />)}
        </div>
      )}

      {/* Hospital overall rating */}
      {isHospital && hospCtx?.hospital_overall_rating != null && (
        <div className="mt-2 flex items-center gap-1.5">
          <span className="text-xs font-medium text-gray-500">CMS Overall Rating:</span>
          <span className="text-sm font-bold text-gray-800">
            {"★".repeat(hospCtx.hospital_overall_rating)}
            {"☆".repeat(5 - hospCtx.hospital_overall_rating)}
          </span>
          <span className="text-xs text-gray-400">({hospCtx.hospital_overall_rating}/5)</span>
        </div>
      )}

      <p className="mt-2 text-xs text-gray-400">CCN: {provider.provider_id}</p>
    </div>
  );
}

export function CompareHeader({ providerA, providerB }: CompareHeaderProps): React.JSX.Element {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-5 shadow-sm">
      <div className="flex flex-col gap-6 lg:flex-row lg:gap-8">
        <ProviderIdentity provider={providerA} />
        <div className="hidden lg:block lg:w-px lg:bg-gray-200" />
        <div className="border-t border-gray-200 lg:hidden" />
        <ProviderIdentity provider={providerB} />
      </div>
    </div>
  );
}
