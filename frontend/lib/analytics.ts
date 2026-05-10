// Analytics scaffolding. Defaults to Plausible (privacy-friendly, no cookie
// banner needed). Domain is configured via NEXT_PUBLIC_PLAUSIBLE_DOMAIN; if
// unset, the script is not loaded and helpers no-op. Swap providers by
// replacing the Script tag in app/layout.tsx and updating trackEvent() —
// the call sites stay the same.
//
// PII discipline (legal-compliance.md): this site has no user accounts and
// no patient data. CCN is a public CMS identifier and is safe to log. Do NOT
// log provider names, addresses, or anything that could identify a user
// query that's not already public CMS data. Use snake_case for property
// names per Plausible convention.

declare global {
  interface Window {
    plausible?: (
      event: string,
      options?: { props?: Record<string, string | number | boolean | null> },
    ) => void;
  }
}

export function getPlausibleDomain(): string | null {
  const domain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN;
  if (!domain || domain.trim() === "") return null;
  return domain.trim();
}

export function getPlausibleScriptSrc(): string {
  const host = process.env.NEXT_PUBLIC_PLAUSIBLE_HOST ?? "https://plausible.io";
  return `${host.replace(/\/+$/, "")}/js/script.js`;
}

export function isAnalyticsEnabled(): boolean {
  return getPlausibleDomain() !== null;
}

type EventProps = Record<string, string | number | boolean | null>;

function trackEvent(name: string, props?: EventProps): void {
  if (typeof window === "undefined") return;
  if (!window.plausible) return;
  window.plausible(name, props ? { props } : undefined);
}

// ─── Typed event helpers ──────────────────────────────────────────────
//
// Each helper documents the call-site intent. Property names are stable
// analytics keys (snake_case per Plausible convention) — do not rename
// without updating the dashboards that consume them.

export type ProviderTypeForAnalytics = "HOSPITAL" | "NURSING_HOME";

export function trackCompareClick(ccnA: string, ccnB: string): void {
  trackEvent("Compare Click", { ccn_a: ccnA, ccn_b: ccnB });
}

export function trackMeasureExpand(
  measureId: string,
  providerType: ProviderTypeForAnalytics,
): void {
  trackEvent("Measure Expand", {
    measure_id: measureId,
    provider_type: providerType,
  });
}

export function trackProviderView(
  providerId: string,
  providerType: ProviderTypeForAnalytics,
): void {
  trackEvent("Provider View", {
    provider_id: providerId,
    provider_type: providerType,
  });
}

export function trackSearchSubmit(query: string, resultCount: number): void {
  trackEvent("Search Submit", {
    query_length: query.length,
    result_count: resultCount,
  });
}

export function trackOutboundClick(href: string, label: string): void {
  trackEvent("Outbound Click", { href, label });
}

// ─── Compare-page conversion events ───────────────────────────────────

/** Fires when /compare loads both providers successfully. */
export function compareStarted(args: {
  ccnA: string;
  ccnB: string;
  providerType: ProviderTypeForAnalytics;
}): void {
  trackEvent("Compare Started", {
    ccn_a: args.ccnA,
    ccn_b: args.ccnB,
    provider_type: args.providerType,
  });
}

/** Fires the first time the CompareNearbyDrawer opens in a session. */
export function compareNearbyOpened(args: {
  originCcn: string;
  providerType: string;
}): void {
  trackEvent("Compare Nearby Opened", {
    origin_ccn: args.originCcn,
    provider_type: args.providerType,
  });
}

/** Fires when a result row is clicked in CompareNearbyDrawer. */
export function compareNearbyResultClicked(args: {
  originCcn: string;
  selectedCcn: string;
  distanceMiles: number | null;
}): void {
  trackEvent("Compare Nearby Result Clicked", {
    origin_ccn: args.originCcn,
    selected_ccn: args.selectedCcn,
    distance_miles: args.distanceMiles,
  });
}

// ─── /filter-explore conversion events ────────────────────────────────

/** Fires when a measure is selected in the filter-explore picker. */
export function measureFilterExploreSelected(args: {
  measureId: string;
  measureGroup: string;
}): void {
  trackEvent("Filter Explore Measure Selected", {
    measure_id: args.measureId,
    measure_group: args.measureGroup,
  });
}

/** Fires when the user changes the sort column or direction. */
export function measureFilterExploreSorted(args: {
  measureId: string;
  sortColumn: string;
  sortDirection: "asc" | "desc";
}): void {
  trackEvent("Filter Explore Sorted", {
    measure_id: args.measureId,
    sort_column: args.sortColumn,
    sort_direction: args.sortDirection,
  });
}
