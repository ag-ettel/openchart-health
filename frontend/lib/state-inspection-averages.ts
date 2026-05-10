// Client-side fetch + types for state_inspection_averages.json.
//
// State-level averages exist because nursing home inspection regimes vary
// substantially by state — some states cite at higher overall rates, others
// escalate more readily to immediate jeopardy. Comparing a facility only to
// the national average can mislead in either direction; the state row gives
// the contextual baseline.
//
// Computed offline by scripts/export_state_inspection_averages.py with the
// same 120-day clustering used in InspectionSummary / CompareInspectionSummary
// / OwnershipGroupStats.

import { useEffect, useState } from "react";

export interface InspectionAverages {
  ac: number;
  df: number;
  ghi: number;
  jkl: number;
  total: number;
  facility_count: number;
  pct_facilities_with_recent_ij: number;
}

export interface StateInspectionAveragesPayload {
  states: Record<string, InspectionAverages>;
  national: InspectionAverages;
  computed_at: string;
  method: string;
}

const CDN_BASE = process.env.NEXT_PUBLIC_CDN_BASE ?? "/data";

let cached: StateInspectionAveragesPayload | null = null;
let inflight: Promise<StateInspectionAveragesPayload> | null = null;

async function fetchStateAverages(): Promise<StateInspectionAveragesPayload> {
  if (cached) return cached;
  if (inflight) return inflight;
  inflight = fetch(`${CDN_BASE}/state_inspection_averages.json`)
    .then((r) => {
      if (!r.ok) throw new Error(`Failed to load state inspection averages: ${r.status}`);
      return r.json() as Promise<StateInspectionAveragesPayload>;
    })
    .then((data) => {
      cached = data;
      inflight = null;
      return data;
    })
    .catch((err) => {
      inflight = null;
      throw err;
    });
  return inflight;
}

/** Hook: returns the state averages payload once loaded, null while loading. */
export function useStateInspectionAverages(): StateInspectionAveragesPayload | null {
  const [data, setData] = useState<StateInspectionAveragesPayload | null>(cached);
  useEffect(() => {
    if (cached) {
      setData(cached);
      return;
    }
    let alive = true;
    fetchStateAverages()
      .then((d) => { if (alive) setData(d); })
      .catch(() => { /* fall back to national-only */ });
    return () => { alive = false; };
  }, []);
  return data;
}

/** Resolve a state code (e.g. "AL") to its averages, or null if not present. */
export function getStateAverages(
  payload: StateInspectionAveragesPayload | null,
  state: string | null,
): InspectionAverages | null {
  if (!payload || !state) return null;
  return payload.states[state] ?? null;
}
