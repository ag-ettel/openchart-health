"use client";

// OwnershipStructureViz — clustered bubble ownership map.
//
// Collapses entities by parent group (entity resolution) so the consumer
// sees "Genesis Healthcare (19 entities, 324 facilities)" as one bubble,
// not 19 separate LLCs. Ungrouped entities with similar names also collapse.
//
// Legal compliance (legal-compliance.md § Ownership Data: No Implied Causation):
// - Structural information only, no editorial characterization

import { useMemo, useState, useRef, useEffect } from "react";
import type { OwnershipEntry, NursingHomeContext } from "@/types/provider";

interface Props {
  ownership: OwnershipEntry[];
  facilityName: string;
  nursingHomeContext: NursingHomeContext | null;
}

type Layer = "direct" | "indirect" | "operational" | "financial";

function getLayer(role: string): Layer {
  if (role.includes("DIRECT")) return "direct";
  if (role.includes("OPERATIONAL") || role.includes("MANAGING")) return "operational";
  if (role.includes("MORTGAGE") || role.includes("SECURITY")) return "financial";
  return "indirect";
}

const LAYER_STYLE: Record<Layer, { fill: string; stroke: string; label: string }> = {
  direct:      { fill: "#818cf8", stroke: "#6366f1", label: "Direct Owner" },
  indirect:    { fill: "#a78bfa", stroke: "#7c3aed", label: "Indirect Owner" },
  operational: { fill: "#34d399", stroke: "#059669", label: "Operator" },
  financial:   { fill: "#fbbf24", stroke: "#d97706", label: "Financial Interest" },
};

const SHORT_ROLE: Record<string, string> = {
  "5% OR GREATER DIRECT OWNERSHIP INTEREST": "Direct Owner",
  "5% OR GREATER INDIRECT OWNERSHIP INTEREST": "Indirect Owner",
  "OPERATIONAL/MANAGERIAL CONTROL": "Operator",
  "MANAGING EMPLOYEE": "Manager",
  "W-2 MANAGING EMPLOYEE": "Manager (W-2)",
  "CONTRACTED MANAGING EMPLOYEE": "Manager (Contract)",
  "CORPORATE OFFICER": "Officer",
  "CORPORATE DIRECTOR": "Director",
  "OFFICER": "Officer",
  "DIRECTOR": "Director",
  "GENERAL PARTNERSHIP INTEREST": "General Partner",
  "LIMITED PARTNERSHIP INTEREST": "Limited Partner",
  "PARTNERSHIP INTEREST": "Partner",
  "5% OR GREATER MORTGAGE INTEREST": "Mortgage Interest",
  "5% OR GREATER SECURITY INTEREST": "Security Interest",
};

interface CollapsedEntity {
  id: string;
  displayName: string;
  entityCount: number;
  entityNames: string[];
  roles: string[];
  layer: Layer;
  facilityCount: number;
  percentage: number | null;
  percentageNotProvided: boolean;
  isParentGroup: boolean;
}

interface BubbleNode extends CollapsedEntity {
  r: number;
  x: number;
  y: number;
}

// Simple name prefix for collapsing ungrouped entities with similar names
function namePrefix(name: string): string {
  return name
    .replace(/[,.]?\s*(LLC|INC|LP|LLP|CORP|CORPORATION|CO)\s*\.?$/i, "")
    .replace(/[,.]$/,"")
    .trim();
}

function packBubbles(nodes: BubbleNode[], cx: number, cy: number): void {
  if (nodes.length === 0) return;
  nodes[0].x = cx;
  nodes[0].y = cy;
  if (nodes.length === 1) return;

  for (let i = 1; i < nodes.length; i++) {
    const node = nodes[i];
    let placed = false;

    for (let angle = 0; angle < Math.PI * 8; angle += 0.12) {
      const dist = nodes[0].r + node.r + 4 + angle * 2.8;
      const tx = cx + Math.cos(angle) * dist;
      const ty = cy + Math.sin(angle) * dist;

      let overlaps = false;
      for (let j = 0; j < i; j++) {
        const dx = tx - nodes[j].x;
        const dy = ty - nodes[j].y;
        const minDist = node.r + nodes[j].r + 3;
        if (dx * dx + dy * dy < minDist * minDist) {
          overlaps = true;
          break;
        }
      }

      if (!overlaps) {
        node.x = tx;
        node.y = ty;
        placed = true;
        break;
      }
    }

    if (!placed) {
      node.x = cx + (Math.random() - 0.5) * 200;
      node.y = cy + (Math.random() - 0.5) * 200;
    }
  }
}

export function OwnershipStructureViz({ ownership, facilityName, nursingHomeContext }: Props): React.JSX.Element {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(660);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) setContainerWidth(entry.contentRect.width);
    });
    obs.observe(el);
    setContainerWidth(el.clientWidth);
    return () => obs.disconnect();
  }, []);

  const { bubbles, leadership, individualOwners, parentGroupName } = useMemo(() => {
    // Step 1: Collapse by parent_group_id
    const groupMap = new Map<string, CollapsedEntity>();
    const ungrouped: OwnershipEntry[] = [];

    for (const o of ownership) {
      if (o.owner_type === "Individual") continue;
      if (o.parent_group_id) {
        const existing = groupMap.get(o.parent_group_id);
        const layer = getLayer(o.role);
        if (existing) {
          if (!existing.entityNames.includes(o.owner_name)) {
            existing.entityNames.push(o.owner_name);
            existing.entityCount = existing.entityNames.length;
          }
          if (!existing.roles.includes(o.role)) existing.roles.push(o.role);
          const pri: Record<Layer, number> = { direct: 0, operational: 1, indirect: 2, financial: 3 };
          if (pri[layer] < pri[existing.layer]) existing.layer = layer;
          if (o.ownership_percentage !== null) existing.percentage = o.ownership_percentage;
          // Use parent_group_facility_count (deduplicated) when available
          if (o.parent_group_facility_count != null && o.parent_group_facility_count > existing.facilityCount)
            existing.facilityCount = o.parent_group_facility_count;
          else if (o.entity_facility_count != null && o.entity_facility_count > existing.facilityCount)
            existing.facilityCount = o.entity_facility_count;
        } else {
          groupMap.set(o.parent_group_id, {
            id: o.parent_group_id,
            displayName: o.parent_group_name ?? o.owner_name,
            entityCount: 1,
            entityNames: [o.owner_name],
            roles: [o.role],
            layer,
            facilityCount: o.parent_group_facility_count ?? o.entity_facility_count ?? 1,
            percentage: o.ownership_percentage,
            percentageNotProvided: o.ownership_percentage_not_provided,
            isParentGroup: true,
          });
        }
      } else {
        ungrouped.push(o);
      }
    }

    // Step 2: Collapse ungrouped by name prefix similarity
    const ungroupedMap = new Map<string, CollapsedEntity>();
    for (const o of ungrouped) {
      const prefix = namePrefix(o.owner_name);
      const existing = ungroupedMap.get(prefix);
      const layer = getLayer(o.role);
      if (existing) {
        if (!existing.entityNames.includes(o.owner_name)) {
          existing.entityNames.push(o.owner_name);
          existing.entityCount = existing.entityNames.length;
        }
        if (!existing.roles.includes(o.role)) existing.roles.push(o.role);
        const pri: Record<Layer, number> = { direct: 0, operational: 1, indirect: 2, financial: 3 };
        if (pri[layer] < pri[existing.layer]) existing.layer = layer;
        if (o.ownership_percentage !== null) existing.percentage = o.ownership_percentage;
        if (o.entity_facility_count != null && o.entity_facility_count > existing.facilityCount)
          existing.facilityCount = o.entity_facility_count;
      } else {
        ungroupedMap.set(prefix, {
          id: `ungrouped_${prefix}`,
          displayName: o.owner_name,
          entityCount: 1,
          entityNames: [o.owner_name],
          roles: [o.role],
          layer,
          facilityCount: o.entity_facility_count ?? 1,
          percentage: o.ownership_percentage,
          percentageNotProvided: o.ownership_percentage_not_provided,
          isParentGroup: false,
        });
      }
    }

    // Merge all collapsed entities
    const allEntities = [...groupMap.values(), ...ungroupedMap.values()];
    const maxFac = Math.max(...allEntities.map((e) => e.facilityCount), 1);

    // Build bubble nodes sorted by facility count desc
    const nodes: BubbleNode[] = allEntities
      .sort((a, b) => b.facilityCount - a.facilityCount)
      .map((e) => ({
        ...e,
        r: Math.max(5, 55 * Math.sqrt(e.facilityCount / maxFac)),
        x: 0,
        y: 0,
      }));

    // Pack
    const svgW = containerWidth;
    const svgH = 420;
    packBubbles(nodes, svgW / 2, svgH / 2);

    // Individuals
    const indivMap = new Map<string, { name: string; roles: string[] }>();
    for (const o of ownership) {
      if (o.owner_type !== "Individual") continue;
      const ex = indivMap.get(o.owner_name);
      if (ex) { if (!ex.roles.includes(o.role)) ex.roles.push(o.role); }
      else indivMap.set(o.owner_name, { name: o.owner_name, roles: [o.role] });
    }
    const leaders = Array.from(indivMap.values()).filter(
      (e) => e.roles.some((r) => r.includes("OFFICER") || r.includes("DIRECTOR"))
    );
    const indivOwners = Array.from(indivMap.values()).filter(
      (e) => e.roles.some((r) => r.includes("DIRECT") || r.includes("INDIRECT"))
        && !e.roles.some((r) => r.includes("OFFICER") || r.includes("DIRECTOR"))
    );

    const pg = allEntities.find((e) => e.isParentGroup)?.displayName ?? null;

    return { bubbles: nodes, leadership: leaders, individualOwners: indivOwners, parentGroupName: pg };
  }, [ownership, containerWidth]);

  // Fixed SVG height — no jitter
  const svgH = 420;

  // Auto-fit viewBox
  const viewBox = useMemo(() => {
    if (bubbles.length === 0) return `0 0 ${containerWidth} ${svgH}`;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const b of bubbles) {
      minX = Math.min(minX, b.x - b.r);
      minY = Math.min(minY, b.y - b.r);
      maxX = Math.max(maxX, b.x + b.r);
      maxY = Math.max(maxY, b.y + b.r);
    }
    const pad = 25;
    return `${minX - pad} ${minY - pad} ${maxX - minX + pad * 2} ${maxY - minY + pad * 2}`;
  }, [bubbles, containerWidth, svgH]);

  const activeId = selectedId ?? hoveredId;
  const activeNode = bubbles.find((b) => b.id === activeId);
  const center = bubbles[0];

  return (
    <div className="space-y-3">
      {parentGroupName && (
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 0h.008v.008h-.008V7.5Z" />
            </svg>
            Part of {parentGroupName}
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div ref={containerRef} className="lg:col-span-2 rounded-lg border border-gray-200 bg-gray-950 overflow-hidden">
          <svg viewBox={viewBox} className="w-full" style={{ height: svgH }}>
            {/* Connection lines */}
            {center && bubbles.slice(1).map((b) => (
              <line
                key={`line-${b.id}`}
                x1={center.x} y1={center.y} x2={b.x} y2={b.y}
                stroke="rgba(255,255,255,0.06)"
                strokeWidth={0.5}
                style={{ transition: "stroke 0.3s" }}
              />
            ))}

            {/* Bubbles — largest on top */}
            {[...bubbles].reverse().map((b) => {
              const style = LAYER_STYLE[b.layer];
              const isActive = b.id === activeId;
              const isDimmed = activeId != null && !isActive;

              return (
                <g
                  key={b.id}
                  opacity={isDimmed ? 0.15 : 1}
                  style={{ transition: "opacity 0.4s ease" }}
                  onMouseEnter={() => setHoveredId(b.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  onClick={() => setSelectedId(selectedId === b.id ? null : b.id)}
                  cursor="pointer"
                >
                  {isActive && (
                    <circle
                      cx={b.x} cy={b.y} r={b.r + 3}
                      fill="none" stroke="rgba(255,255,255,0.5)"
                      strokeWidth={1.5}
                    />
                  )}
                  <circle
                    cx={b.x} cy={b.y} r={b.r}
                    fill={style.fill} stroke={style.stroke}
                    strokeWidth={isActive ? 1.5 : 0.5}
                    fillOpacity={0.85}
                  />
                  {/* Facility count */}
                  {b.r >= 14 && (
                    <text
                      x={b.x} y={b.y}
                      textAnchor="middle" dominantBaseline="central"
                      fill="white" fontWeight="700"
                      fontSize={Math.max(8, Math.min(b.r * 0.5, 18))}
                      style={{ pointerEvents: "none" }}
                    >
                      {b.facilityCount}
                    </text>
                  )}
                  {/* Name label — large bubbles only */}
                  {b.r >= 30 && (
                    <text
                      x={b.x} y={b.y + b.r + 10}
                      textAnchor="middle"
                      fill="rgba(255,255,255,0.45)"
                      fontSize={8}
                      style={{ pointerEvents: "none" }}
                    >
                      {b.displayName.length > 26 ? b.displayName.substring(0, 24) + "..." : b.displayName}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* Detail panel */}
        <div className="space-y-3">
          {activeNode ? (
            <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3" style={{ minHeight: 120 }}>
              <p className="text-xs font-semibold text-indigo-700">{activeNode.displayName}</p>
              <div className="mt-1.5 space-y-1 text-xs text-gray-600">
                {activeNode.entityCount > 1 && (
                  <p className="text-[10px] text-gray-400">
                    {activeNode.entityCount} CMS entities consolidated
                  </p>
                )}
                <p>
                  <span className="font-medium text-gray-500">
                    Role{activeNode.roles.length > 1 ? "s" : ""}:
                  </span>{" "}
                  {[...new Set(activeNode.roles.map((r) => SHORT_ROLE[r] ?? r))].join(", ")}
                </p>
                <p>
                  <span className="font-medium text-gray-500">Facilities:</span>{" "}
                  <span className="font-semibold text-gray-800">{activeNode.facilityCount}</span>{" "}
                  across CMS data
                </p>
                {activeNode.percentage !== null && (
                  <p>
                    <span className="font-medium text-gray-500">Ownership:</span>{" "}
                    {activeNode.percentage}%
                    <span className="ml-1 text-[10px] text-gray-400">(direct share of this facility)</span>
                  </p>
                )}
                {activeNode.percentageNotProvided && (
                  <p className="text-gray-400">Ownership percentage not provided by CMS</p>
                )}
                {activeNode.entityCount > 1 && (
                  <details className="mt-2 group/names">
                    <summary className="flex cursor-pointer items-center gap-1.5 text-[11px] text-blue-600 hover:text-blue-700">
                      <span>Show {activeNode.entityCount} entity names</span>
                      <span
                        className="relative inline-flex"
                        tabIndex={0}
                        aria-label="How entity names are grouped"
                      >
                        <span className="inline-block cursor-help rounded-full border border-blue-300 px-1 text-[9px] font-medium text-blue-500 hover:border-blue-500 hover:text-blue-700 peer">
                          ?
                        </span>
                        <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1 hidden w-64 -translate-x-1/2 rounded-md border border-gray-200 bg-white px-3 py-2 text-[11px] font-normal leading-relaxed text-gray-600 shadow-lg peer-hover:block peer-focus:block">
                          CMS publishes each owning entity by its legal name (LLC, INC, LP, trust, etc.). Many corporate families operate through dozens of distinct legal entities. We group these into one parent entity when they share most of the same facilities and corporate leadership, and confirm against CMS-published chain affiliations. Each original CMS entity name is preserved here.
                        </span>
                      </span>
                    </summary>
                    <ul className="mt-1 space-y-0.5 text-[10px] text-gray-500">
                      {activeNode.entityNames.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-center" style={{ minHeight: 120 }}>
              <p className="text-xs text-gray-400">
                Hover or tap a bubble to see details. Larger bubbles appear in more facilities.
              </p>
            </div>
          )}

          {leadership.length > 0 && (
            <div className="rounded-md border border-gray-200 bg-white p-3">
              <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                Officers and Directors
                <span className="ml-1 font-normal text-gray-300">({leadership.length})</span>
              </h4>
              <div className="space-y-1">
                {leadership.slice(0, 6).map((e, i) => (
                  <div key={`lead-${i}`} className="flex items-center justify-between text-xs">
                    <span className="truncate text-gray-700">{e.name}</span>
                    <span className="ml-2 shrink-0 text-[10px] text-gray-400">
                      {e.roles.map((r) => SHORT_ROLE[r] ?? r).join(", ")}
                    </span>
                  </div>
                ))}
                {leadership.length > 6 && (
                  <p className="text-[10px] text-gray-400">and {leadership.length - 6} more</p>
                )}
              </div>
            </div>
          )}

          {individualOwners.length > 0 && (
            <div className="rounded-md border border-gray-200 bg-white p-3">
              <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                Individual Owners
                <span className="ml-1 font-normal text-gray-300">({individualOwners.length})</span>
              </h4>
              <div className="space-y-1">
                {individualOwners.slice(0, 5).map((e, i) => (
                  <div key={`ind-${i}`} className="flex items-center justify-between text-xs">
                    <span className="truncate text-gray-700">{e.name}</span>
                    <span className="ml-2 shrink-0 text-[10px] text-gray-400">
                      {e.roles.map((r) => SHORT_ROLE[r] ?? r).join(", ")}
                    </span>
                  </div>
                ))}
                {individualOwners.length > 5 && (
                  <p className="text-[10px] text-gray-400">and {individualOwners.length - 5} more</p>
                )}
              </div>
            </div>
          )}

          <div className="rounded-md border border-gray-200 bg-white p-3">
            <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400">Legend</h4>
            <div className="space-y-1.5 text-[10px] text-gray-500">
              {(["direct", "indirect", "operational", "financial"] as Layer[]).map((l) => (
                <div key={l} className="flex items-center gap-2">
                  <span
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: LAYER_STYLE[l].fill, border: `1px solid ${LAYER_STYLE[l].stroke}` }}
                  />
                  {LAYER_STYLE[l].label}
                </div>
              ))}
              <p className="mt-1 text-gray-400">
                Number = facilities this entity appears in. Related entities (same corporate group) are consolidated into one bubble.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
