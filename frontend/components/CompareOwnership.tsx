"use client";

// CompareOwnership — paired ownership structure for two nursing homes.
//
// Three render modes:
//   1. Same parent_group_id resolved on both sides — single banner + one
//      OwnershipGroupStats panel + compact paired ownership lists below
//   2. Same chain_name (no resolved parent_group) — banner noting shared chain
//      + paired compact ownership lists, plus any per-side parent_group_stats
//   3. Different parent groups — paired panels side by side, each with its own
//      parent_group_stats when present
//
// Compact ownership list per side (default), expandable to OwnershipStructureViz.
//
// Legal compliance (legal-compliance.md § Ownership Data, NH-6):
// - No causal language between ownership and quality
// - Per-panel CMS attribution
// - Required ownership-quality disclaimer (Template 3g) when quality data
//   appears in same view (it does — this sits inside the compare page).

import { useState } from "react";
import type { Provider, OwnershipEntry, ParentGroupStats } from "@/types/provider";
import { titleCase } from "@/lib/utils";
import { OWNERSHIP_QUALITY_DISCLAIMER } from "@/lib/constants";
import { OwnershipStructureViz } from "./OwnershipStructureViz";
import { OwnershipGroupStats } from "./OwnershipGroupStats";

interface CompareOwnershipProps {
  providerA: Provider;
  providerB: Provider;
}

function resolvedParentGroup(ownership: OwnershipEntry[]): { id: string; name: string } | null {
  for (const o of ownership) {
    if (o.parent_group_id && o.parent_group_name) {
      return { id: o.parent_group_id, name: o.parent_group_name };
    }
  }
  return null;
}

function topRoles(ownership: OwnershipEntry[]): OwnershipEntry[] {
  // Prioritize ownership/operational roles, drop officers/directors below
  // the fold of the compact list.
  const PRIORITY: { match: (r: string) => boolean; rank: number }[] = [
    { match: (r) => r.includes("DIRECT OWNERSHIP"), rank: 0 },
    { match: (r) => r.includes("INDIRECT OWNERSHIP"), rank: 1 },
    { match: (r) => r.includes("OPERATIONAL") || r.includes("MANAGING"), rank: 2 },
    { match: (r) => r.includes("PARTNERSHIP"), rank: 3 },
    { match: (r) => r.includes("MORTGAGE") || r.includes("SECURITY"), rank: 4 },
  ];
  function rank(role: string): number {
    for (const p of PRIORITY) if (p.match(role)) return p.rank;
    return 99;
  }
  return [...ownership].sort((a, b) => {
    const ra = rank(a.role);
    const rb = rank(b.role);
    if (ra !== rb) return ra - rb;
    return a.owner_name.localeCompare(b.owner_name);
  });
}

function shortRole(role: string): string {
  if (role.includes("DIRECT OWNERSHIP")) return "Direct Owner";
  if (role.includes("INDIRECT OWNERSHIP")) return "Indirect Owner";
  if (role.includes("OPERATIONAL") || role.includes("MANAGING")) return "Operator";
  if (role.includes("PARTNERSHIP")) return "Partnership";
  if (role.includes("MORTGAGE") || role.includes("SECURITY")) return "Financial";
  if (role.includes("OFFICER")) return "Officer";
  if (role.includes("DIRECTOR")) return "Director";
  return role;
}

/** Map first, list collapsed below — the bubble viz is the comparable visual;
 *  the long list is opt-in detail. */
function CompactOwnershipList({
  ownership,
  facilityName,
  isListExpanded,
  onToggleList,
  context,
}: {
  ownership: OwnershipEntry[];
  facilityName: string;
  isListExpanded: boolean;
  onToggleList: () => void;
  context: Provider["nursing_home_context"];
}): React.JSX.Element {
  const sorted = topRoles(ownership);
  const orgs = sorted.filter((o) => o.owner_type === "Organization");
  const orgCount = orgs.length;
  const indCount = sorted.length - orgCount;

  return (
    <div>
      {/* Topline counts */}
      <p className="text-xs text-gray-500">
        <span className="font-semibold text-gray-700">{ownership.length}</span> ownership entries
        {orgCount > 0 && <span className="text-gray-400"> · {orgCount} organization{orgCount !== 1 ? "s" : ""}</span>}
        {indCount > 0 && <span className="text-gray-400"> · {indCount} individual{indCount !== 1 ? "s" : ""}</span>}
      </p>

      {/* Map: visible by default — primary visual signal */}
      <div className="mt-3">
        <OwnershipStructureViz
          ownership={ownership}
          facilityName={facilityName}
          nursingHomeContext={context ?? null}
        />
      </div>

      {/* Entry list: collapsed by default */}
      <button
        type="button"
        onClick={onToggleList}
        className="mt-3 flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700"
      >
        <svg className={`h-3 w-3 transition-transform ${isListExpanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
        {isListExpanded
          ? `Hide ${sorted.length} ownership entries`
          : `Show all ${sorted.length} ownership entries`}
      </button>

      {isListExpanded && (
        <ul className="mt-2 border-t border-gray-100 pt-2 space-y-1">
          {sorted.map((o, i) => (
            <li key={`${o.owner_name}-${o.role}-${i}`} className="flex items-baseline justify-between gap-2 border-b border-gray-50 py-1 last:border-b-0">
              <span className="min-w-0 flex-1">
                <span className="text-xs font-medium text-gray-700">{titleCase(o.owner_name)}</span>
                <span className="ml-2 text-[10px] text-gray-400">{shortRole(o.role)}</span>
              </span>
              <span className="shrink-0 text-[10px] tabular-nums text-gray-500">
                {o.ownership_percentage_not_provided
                  ? "no %"
                  : o.ownership_percentage !== null
                    ? `${o.ownership_percentage}%`
                    : "—"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SharedParentGroupBanner({
  groupName,
  facilityCount,
}: {
  groupName: string;
  facilityCount: number;
}): React.JSX.Element {
  return (
    <div className="mb-3 rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm">
      <p className="font-semibold text-blue-800">
        Both facilities are associated with {titleCase(groupName)}
      </p>
      <p className="mt-0.5 text-xs text-blue-700">
        {facilityCount.toLocaleString()} CMS-published facilities are linked to this corporate group.
      </p>
    </div>
  );
}

function SharedChainBanner({ chainName }: { chainName: string }): React.JSX.Element {
  return (
    <div className="mb-3 rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm">
      <p className="font-semibold text-blue-800">
        Both facilities report the chain affiliation {titleCase(chainName)}
      </p>
      <p className="mt-0.5 text-xs text-blue-700">
        Chain affiliation comes from CMS Provider Information; corporate ownership entities below may differ.
      </p>
    </div>
  );
}

export function CompareOwnership({
  providerA,
  providerB,
}: CompareOwnershipProps): React.JSX.Element | null {
  const ownA = providerA.ownership ?? [];
  const ownB = providerB.ownership ?? [];
  const pgA = providerA.parent_group_stats;
  const pgB = providerB.parent_group_stats;

  const [listExpandedA, setListExpandedA] = useState(false);
  const [listExpandedB, setListExpandedB] = useState(false);

  if (ownA.length === 0 && ownB.length === 0) return null;

  const groupA = resolvedParentGroup(ownA);
  const groupB = resolvedParentGroup(ownB);
  const chainA = providerA.nursing_home_context?.chain_name?.trim() ?? null;
  const chainB = providerB.nursing_home_context?.chain_name?.trim() ?? null;

  const sameParentGroup = groupA && groupB && groupA.id === groupB.id;
  const sameChain = !sameParentGroup && chainA && chainB && chainA === chainB;

  const nameA = titleCase(providerA.name);
  const nameB = titleCase(providerB.name);

  const sharedGroupStats = sameParentGroup ? (pgA ?? pgB) : null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-4 shadow-sm">
      <h3 className="text-base font-semibold text-gray-800">Ownership Structure</h3>
      <p className="mt-1 text-xs text-gray-500">
        Corporate ownership and management entities for each facility.
      </p>

      {/* Shared-banner cases */}
      {sameParentGroup && groupA && (
        <div className="mt-3">
          <SharedParentGroupBanner
            groupName={groupA.name}
            facilityCount={(pgA ?? pgB)?.facility_count ?? ownA.find((o) => o.parent_group_facility_count != null)?.parent_group_facility_count ?? 0}
          />
        </div>
      )}
      {sameChain && chainA && (
        <div className="mt-3">
          <SharedChainBanner chainName={chainA} />
        </div>
      )}

      {/* Compact paired ownership lists */}
      <div className="mt-2 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-blue-100 bg-blue-50/30 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-bold text-blue-700">
            <span className="inline-block h-2 w-2 rounded-full bg-blue-600" />
            {nameA}
          </p>
          {chainA && !sameChain && !sameParentGroup && (
            <p className="mb-2 text-[10px] text-gray-500">Chain: {titleCase(chainA)}</p>
          )}
          {ownA.length > 0 ? (
            <CompactOwnershipList
              ownership={ownA}
              facilityName={nameA}
              isListExpanded={listExpandedA}
              onToggleList={() => setListExpandedA((v) => !v)}
              context={providerA.nursing_home_context}
            />
          ) : (
            <p className="text-xs text-gray-400">No ownership data available.</p>
          )}
        </div>

        <div className="rounded-md border border-gray-200 bg-gray-50/50 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-bold text-gray-700">
            <span className="inline-block h-2 w-2 rounded-full bg-gray-700" />
            {nameB}
          </p>
          {chainB && !sameChain && !sameParentGroup && (
            <p className="mb-2 text-[10px] text-gray-500">Chain: {titleCase(chainB)}</p>
          )}
          {ownB.length > 0 ? (
            <CompactOwnershipList
              ownership={ownB}
              facilityName={nameB}
              isListExpanded={listExpandedB}
              onToggleList={() => setListExpandedB((v) => !v)}
              context={providerB.nursing_home_context}
            />
          ) : (
            <p className="text-xs text-gray-400">No ownership data available.</p>
          )}
        </div>
      </div>

      {/* Parent group stats panels */}
      {sharedGroupStats && (
        <div className="mt-4">
          <OwnershipGroupStats stats={sharedGroupStats} />
        </div>
      )}
      {!sharedGroupStats && (pgA || pgB) && (
        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
          {pgA ? <OwnershipGroupStats stats={pgA} /> : <PlaceholderGroupPanel name={nameA} />}
          {pgB ? <OwnershipGroupStats stats={pgB} /> : <PlaceholderGroupPanel name={nameB} />}
        </div>
      )}

      {/* Required disclosures (Template 3g) */}
      <p className="mt-3 text-[10px] leading-relaxed text-gray-400">
        Source: CMS Nursing Home Ownership and Provider Information. {OWNERSHIP_QUALITY_DISCLAIMER}
      </p>
    </div>
  );
}

function PlaceholderGroupPanel({ name }: { name: string }): React.JSX.Element {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 text-xs text-gray-500">
      <p className="font-medium text-gray-600">{name}</p>
      <p className="mt-1">Parent group statistics not available.</p>
    </div>
  );
}

// Suppress unused import warning if Provider type only imported for typing.
export type { CompareOwnershipProps };
