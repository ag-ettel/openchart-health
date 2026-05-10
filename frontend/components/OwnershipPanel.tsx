"use client";

// OwnershipPanel — displays nursing home ownership structure.
//
// Legal compliance (legal-compliance.md § Ownership Data: No Implied Causation):
// - NO causal language connecting ownership to quality
// - NO editorial characterization terms (see legal-compliance.md for full list) compliance-ok
// - Per-panel CMS dataset attribution
// - Processing date visible
//
// Display rules (display-philosophy.md NH-5, NH-6):
// - Structural information, not accusatory
// - Missing percentages stated plainly — the gap is the information
// - Chain affiliation as header context
//
// Future: parent_group_id/parent_group_name from entity resolution will
// link to cross-facility ownership group pages in /filter-explore.

import { useState } from "react";
import type { OwnershipEntry, NursingHomeContext } from "@/types/provider";
import { OWNERSHIP_QUALITY_DISCLAIMER } from "@/lib/constants";

interface OwnershipPanelProps {
  ownership: OwnershipEntry[];
  providerLastUpdated: string;
  nursingHomeContext: NursingHomeContext | null;
}

function formatDate(iso: string | null): string {
  if (!iso) return "Not available";
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function groupByRole(entries: OwnershipEntry[]): Map<string, OwnershipEntry[]> {
  const groups = new Map<string, OwnershipEntry[]>();
  const sorted = [...entries].sort((a, b) => {
    const roleCmp = a.role.localeCompare(b.role);
    if (roleCmp !== 0) return roleCmp;
    return a.owner_name.localeCompare(b.owner_name);
  });
  for (const e of sorted) {
    if (!groups.has(e.role)) groups.set(e.role, []);
    groups.get(e.role)!.push(e);
  }
  return groups;
}

// Friendly role labels
const ROLE_LABELS: Record<string, string> = {
  "5% OR GREATER DIRECT OWNERSHIP INTEREST": "Direct Owners (5%+)",
  "5% OR GREATER INDIRECT OWNERSHIP INTEREST": "Indirect Owners (5%+)",
  "MANAGING EMPLOYEE": "Managing Employees",
  "OPERATIONAL/MANAGERIAL CONTROL": "Operational Control",
  "OFFICER/DIRECTOR": "Officers and Directors",
  "MORTGAGE/SECURITY INTEREST": "Mortgage/Security Interest",
  "GENERAL PARTNERSHIP INTEREST": "General Partners",
  "LIMITED PARTNERSHIP INTEREST": "Limited Partners",
};

export function OwnershipPanel({
  ownership,
  providerLastUpdated,
  nursingHomeContext,
}: OwnershipPanelProps): React.JSX.Element {
  const [showAll, setShowAll] = useState(false);
  const ctx = nursingHomeContext;

  if (ownership.length === 0) {
    return (
      <section aria-label="Ownership information">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Ownership</h2>
        <p className="text-sm text-gray-500">
          No ownership data available in the current CMS dataset for this facility.
        </p>
      </section>
    );
  }

  const groups = groupByRole(ownership);
  const orgEntries = ownership.filter((o) => o.owner_type === "Organization");
  const individualEntries = ownership.filter((o) => o.owner_type === "Individual");

  // Direct owner (usually the most important entity)
  const directOwners = ownership.filter(
    (o) => o.role.includes("DIRECT") && o.owner_type === "Organization"
  );

  // Count entities with missing percentages
  const missingPctCount = ownership.filter(
    (o) => o.ownership_percentage_not_provided || (o.ownership_percentage === null && o.owner_type === "Organization")
  ).length;

  // Default: show direct owners + managing + operational. Expand for full list.
  const PRIMARY_ROLES = new Set([
    "5% OR GREATER DIRECT OWNERSHIP INTEREST",
    "MANAGING EMPLOYEE",
    "OPERATIONAL/MANAGERIAL CONTROL",
  ]);
  const primaryGroups = new Map<string, OwnershipEntry[]>();
  const secondaryGroups = new Map<string, OwnershipEntry[]>();
  for (const [role, entries] of groups) {
    if (PRIMARY_ROLES.has(role)) primaryGroups.set(role, entries);
    else secondaryGroups.set(role, entries);
  }

  const visibleGroups = showAll
    ? groups
    : primaryGroups;
  const hiddenCount = showAll
    ? 0
    : [...secondaryGroups.values()].reduce((s, g) => s + g.length, 0);

  return (
    <section aria-label="Ownership information">
      <h2 className="mb-2 text-lg font-semibold text-gray-900">Ownership</h2>

      {/* Chain affiliation — prominent header context */}
      {ctx?.chain_name && (
        <div className="mb-3 flex items-center gap-2">
          <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-medium text-gray-700">
            Chain: {ctx.chain_name}
          </span>
          {ctx.chain_id && (
            <span className="text-[10px] text-gray-400">CMS Chain ID: {ctx.chain_id}</span>
          )}
        </div>
      )}

      <p className="mb-1 text-xs text-gray-500">
        {orgEntries.length} organization{orgEntries.length !== 1 ? "s" : ""} and{" "}
        {individualEntries.length} individual{individualEntries.length !== 1 ? "s" : ""} on record.
        {missingPctCount > 0 && (
          <span className="text-gray-400">
            {" "}{missingPctCount} with ownership percentage not provided.
          </span>
        )}
      </p>
      <p className="mb-3 text-xs text-gray-400">
        Source: CMS Nursing Home Ownership dataset. Data as of {formatDate(providerLastUpdated)}.
      </p>

      {/* Direct owner highlight */}
      {directOwners.length > 0 && (
        <div className="mb-3 rounded-md border border-blue-100 bg-blue-50 px-3 py-2">
          <p className="text-[10px] font-medium uppercase tracking-wide text-blue-400">Direct Owner</p>
          {directOwners.map((o, i) => (
            <div key={`direct-${i}`} className="mt-1">
              <p className="text-sm font-semibold text-gray-800">{o.owner_name}</p>
              <p className="text-xs text-gray-500">
                {o.ownership_percentage != null
                  ? `${o.ownership_percentage}% ownership`
                  : o.ownership_percentage_not_provided
                    ? "Percentage not provided"
                    : ""}
                {o.association_date && ` · Associated since ${formatDate(o.association_date)}`}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Ownership entities by role */}
      <div className="space-y-3">
        {Array.from(visibleGroups.entries()).map(([role, entries]) => {
          // Skip direct owners in the main list (already highlighted above)
          if (role.includes("DIRECT") && directOwners.length > 0) return null;
          const friendlyRole = ROLE_LABELS[role] ?? role;
          return (
            <div key={role}>
              <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                {friendlyRole}
                <span className="ml-1 font-normal text-gray-300">({entries.length})</span>
              </h3>
              <div className="space-y-1">
                {entries.map((e, i) => (
                  <div
                    key={`${e.owner_name}-${i}`}
                    className="flex items-center justify-between rounded border border-gray-100 bg-white px-3 py-1.5"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm text-gray-700">{e.owner_name}</p>
                      {e.association_date && (
                        <p className="text-[10px] text-gray-400">Since {formatDate(e.association_date)}</p>
                      )}
                    </div>
                    <div className="shrink-0 text-right">
                      {e.ownership_percentage_not_provided ? (
                        <span className="text-[10px] text-gray-400">No % provided</span>
                      ) : e.ownership_percentage !== null ? (
                        <span className="text-xs font-medium text-gray-600">{e.ownership_percentage}%</span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Expand/collapse for secondary roles */}
      {hiddenCount > 0 && (
        <button
          type="button"
          onClick={() => setShowAll(true)}
          className="mt-3 w-full rounded border border-gray-200 bg-gray-50 py-2 text-xs font-medium text-blue-500 hover:bg-gray-100"
        >
          Show {hiddenCount} more entities (indirect owners, officers, partners)
        </button>
      )}
      {showAll && secondaryGroups.size > 0 && (
        <button
          type="button"
          onClick={() => setShowAll(false)}
          className="mt-2 w-full rounded border border-gray-200 bg-gray-50 py-1.5 text-xs text-gray-400 hover:bg-gray-100"
        >
          Show fewer
        </button>
      )}

      {/* Legal disclaimer */}
      <p className="mt-3 text-[10px] leading-relaxed text-gray-400">
        {OWNERSHIP_QUALITY_DISCLAIMER}
      </p>
    </section>
  );
}
