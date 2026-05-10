# CMS Healthcare Comparison Site — v1 Build Handoff Note

## Context for Claude Code

This note exists to align v1 implementation decisions with a known future state. The consumer-facing product is unchanged — this does not alter the plan to maximize organic growth through honest, comprehensive facility content. However, a professional research subscription tier is a planned future build, and a small number of architectural decisions made now will determine whether that future build is clean or requires partial reconstruction.

Read this before making decisions about analytics instrumentation, data storage, component architecture, and routing structure.

**Precedence note:** This document is a strategic planning artifact. Where it conflicts with established project rules (CLAUDE.md, legal-compliance.md, coding-conventions.md, display-philosophy.md), the project rules govern. The v1 implementation recommendations below have been reviewed against the existing architecture and adjusted where the project's conventions already satisfy or supersede the original suggestion.

---

## What the product is

A hospital and nursing home comparison site built entirely on CMS public data. Every piece of data is free to all users — no gating, no truncation, no information asymmetry between registered and anonymous users. The site earns revenue through display advertising and affiliate links at launch.

**The future professional subscription sells workflow tools, not data access.** This distinction is fundamental and must be preserved in all implementation decisions. When in doubt: if a feature is about *seeing* data, it is free. If a feature is about *doing something faster* with data, it is a future paid feature.

This distinction also reinforces competitive defensibility. Gating public federal data invites competitors who simply don't gate it. A free tier that is the most honest and comprehensive CMS data viewer drives organic and SEO traffic; the paid tier competes on workflow convenience rather than information access. That's a position where improving the free product directly strengthens the paid funnel, rather than creating tension between them.

---

## The four architectural considerations that matter now

### 1. Analytics instrumentation — instrument from day one

The decision of whether and when to build the professional subscription depends entirely on whether professional users are organically finding and using the site. That signal only exists if it is tracked from launch.

**Implement these event tracking calls in v1:**

```javascript
// Multi-facility research session
trackEvent('professional_signal', {
  type: 'multi_facility_session',
  facility_count: n,        // fire when user views 5+ facility profiles in one session
  session_id: sessionId
})

// Return visit to same facility
trackEvent('professional_signal', {
  type: 'return_facility_visit',
  facility_id: facilityId,
  days_since_last_visit: n  // fire when same facility visited within 7 days
})

// Deep data page engagement
trackEvent('professional_signal', {
  type: 'deep_data_engagement',
  page_type: 'inspection_detail' | 'staffing_detail' | 'ownership_detail',
  time_on_page_seconds: n   // fire at 60s+ on data-heavy pages
})

// Direct navigation (returning user)
trackEvent('professional_signal', {
  type: 'direct_navigation',
  // fire when referrer is empty or same domain and it is not first session
})

// Attempted interactions with features that don't exist yet
trackEvent('professional_signal', {
  type: 'feature_probe',
  attempted_action: 'export' | 'save_list' | 'compare_bulk' | 'download'
  // log any UI interactions that imply these workflows even if buttons don't exist
})
```

These events feed a simple analytics dashboard — Google Analytics custom events or PostHog are both fine. The goal is a weekly view of professional signal frequency that informs the build/no-build decision for the pro subscription in 12-18 months.

**Do not skip this.** The observation window is months 1-12. If tracking is not in place at launch, that window is lost.

#### Researcher and journalist signal enrichment

The project's legal-compliance rules identify researchers and journalists as a key audience alongside consumers. These users are the most likely to exhibit the professional signals above — multi-facility sessions, deep data engagement, return visits to the same providers. They are also the most likely early adopters of workflow tools (export, bulk compare, monitoring).

Track referral source alongside professional signals when available:

```javascript
// Referral source context on professional signals
trackEvent('professional_signal', {
  type: 'referral_context',
  referrer_domain: document.referrer ? new URL(document.referrer).hostname : null,
  // .edu, .gov, known newsroom domains are high-signal referrers
  // Do not fingerprint users — domain-level referral only
})
```

This sharpens the build/no-build decision: professional signals from `.edu` domains, `.gov` domains, or known journalism tools suggest a research-oriented user base that would pay for workflow features. Generic consumer traffic with high bounce rates does not. The distinction informs both the decision to build and the pricing model.

---

### 2. Data storage — store everything CMS provides, display a subset

The consumer frontend will display a curated view of facility data. The pro subscription will eventually surface additional depth — full historical inspection records, quarterly staffing trends, ownership graph data. The pipeline should collect and store all of this now even if the frontend does not display it.

**Specific fields to collect and store even if not displayed in v1:**

- Full inspection history — all inspections, not just the most recent N
- All quarterly PBJ staffing data — not just the current quarter snapshot
- All deficiency records with full F-tag detail — not just summary counts
- Ownership fields — operating entity, management company, any chain affiliation data CMS provides
- All civil money penalty records with amounts and dates
- All quality measure historical data points

**The principle:** retroactively backfilling historical data from CMS is painful and sometimes impossible if CMS updates its data structure. Storing everything now and choosing what to display is architecturally trivial. Making this decision wrong costs weeks of remediation later.

**Current architecture status:** The existing pipeline schema already satisfies this principle. The database uses upsert-only writes (Data Integrity Rule 5) — rows are never deleted, and all historical reporting periods are retained with `period_start`, `period_end`, and `period_label` per measure value. Inspection events, penalties, staffing data, and ownership fields are all in the Phase 1 schema. The pipeline fetches all rows the CMS API returns for each dataset without truncation. The remaining discipline is ensuring that scheduled pipeline runs accumulate history over time as CMS refreshes quarterly data — data that CMS removes from its API in future quarters will already be preserved locally.

---

### 3. Component architecture — avoid anonymous-only assumptions

The v1 site has no auth and no user accounts. The goal is to avoid structural decisions that make adding auth unnecessarily expensive later — without adding dead code or speculative abstractions now.

**v1 approach (revised):** Do not add `ProFeatureSlot` stubs, `user` props, or auth scaffolding in v1. These add dead code paths that create maintenance burden and contradict the project's convention against designing for hypothetical future requirements.

Instead, the discipline is architectural:
- Keep data fetching isolated from presentation (already the case with static JSON export consumed by Next.js SSG)
- Keep page components focused on rendering data, not managing user state
- When auth lands, add a React context provider (`UserContext`) at the layout level — this injects user state into the component tree without modifying any existing component signatures

The cost of adding a context provider later is trivial (one file, one wrapper in `layout.tsx`). The cost of threading speculative `user` props through every component now is ongoing noise in code review and TypeScript types for a feature that may be 12-18 months away.

**The antifragile framing applies here:** a codebase with no dead code is easier to modify than a codebase with speculative scaffolding that must be understood, maintained, and eventually replaced with the real implementation. Less structure now means more freedom to choose the right structure later.

---

### 4. Routing and data fetching — keep facility data fetching clean

Facility data fetching should be isolated from presentation logic. This matters because the pro sub will need to:
- Serve the same facility data to authenticated users with additional fields unlocked
- Support server-side rendering of facility profiles for SEO while also supporting client-side user state

**The pattern that works:**

```javascript
// lib/facilities.js — single source of truth for facility data fetching
export async function getFacility(facilityId, options = {}) {
  const { includeFullHistory = false, includeOwnershipGraph = false } = options

  // v1: options are ignored, always returns standard CMS data
  // Future: options gate additional data based on subscription state
  
  const data = await cms.getFacility(facilityId)
  return data
}
```

The options are no-ops in v1. They become meaningful when the pro sub adds subscription-aware data serving. The calling code does not change — only the implementation of `getFacility` changes.

---

## What does NOT need to change for v1

To be explicit: none of these considerations change what the product looks like at launch.

- No login or account creation in v1
- No subscription billing in v1
- No gated content in v1 — everything visible to everyone
- No "upgrade" prompts or paywalls in v1
- No change to SEO strategy, content generation, or facility page design
- No change to the data pipeline schedule or CMS source configuration

The consumer product ships exactly as planned. These are invisible structural decisions that exist entirely to make a future build faster and cleaner.

---

## The future pro subscription — for context only, not to build now

When analytics show consistent professional usage signals (target: 20+ multi-facility sessions per week, 10+ return visits to same facilities within 7 days), the pro subscription build begins. At that point the product adds:

1. Auth and Stripe subscription billing (Stripe Checkout hosted UI — do not build custom billing)
2. Shortlist and named list tool — save and compare up to 10 facilities
3. Side-by-side comparison table with configurable columns and export
4. Advanced compound filter search — stack geography + staffing threshold + deficiency count + ownership type
5. Monitoring and email alerts — inspection updates, rating changes, ownership changes
6. Chain and portfolio view — all facilities under one owner
7. CSV and PDF export of any facility view, comparison, or filtered search result

**The pro subscription does not gate any data.** All inspection history, staffing trends, ownership data, and deficiency detail remain free to all users. The subscription gates workflow tools only. This is a permanent architectural and ethical commitment — do not design any component that implies data could be gated later.

### Target user profiles for pro tier

The project's legal-compliance positioning identifies three audiences: consumers, researchers, and journalists. The researcher and journalist segments are the strongest candidates for early pro adoption:

- **Health services researchers** — compare facilities by measure, export data for statistical analysis, monitor facilities in a study cohort over time. These users currently scrape CMS data manually or use expensive institutional subscriptions. Workflow tools (export, bulk compare, saved lists) directly replace manual processes.
- **Investigative journalists** — track ownership chains, monitor inspection patterns, compare facilities within a corporate portfolio. Chain/portfolio view and monitoring alerts are high-value for this audience.
- **Healthcare consultants and administrators** — benchmark against peers, track competitor performance, monitor regulatory risk. Compound filters and configurable comparison tables serve this use case.
- **Elder law attorneys** — evaluate nursing homes for Medicaid planning, guardianship proceedings, and neglect litigation. Need inspection history, penalty records, and ownership chains with the ability to export documentation for legal filings. Monitoring alerts track facilities involved in active cases. High willingness to pay for tools that replace manual state survey agency lookups.
- **Geriatric care managers** — place clients across multiple facilities repeatedly. Saved shortlists, side-by-side comparison on staffing and quality measures, and monitoring for rating changes on facilities where they've placed clients. This is daily workflow, not occasional research — high frequency of use drives retention.
- **Hospital discharge planners** — similar to care managers but higher volume and more time-pressured. Need to quickly filter nursing homes by geography, available services, and quality thresholds, then compare a shortlist under time constraints. Compound filters and configurable comparison tables are the exact tools they'd pay for.

All six audiences share a common pattern: they already do this work manually using CMS Care Compare, state survey agency websites, and spreadsheets. The pro tier replaces a fragmented manual workflow, not access to data they can't find elsewhere. This keeps the "workflow not data" line clean and means the free tier never needs to be degraded to justify the paid tier.

These audiences are identifiable through the analytics signals above. Research and journalism users show up via .edu/.gov referral domains and multi-facility sessions. Legal, care management, and discharge planning users show up via nursing-home-heavy session patterns — return visits to nursing home profiles, deep engagement on inspection and penalty pages, multi-facility sessions concentrated in a single state or metro area. The pro tier should be priced and marketed to serve all six without segmenting — the workflow tools are the same, only the use case differs.

---

## Summary of action items for v1 build

| Item | Priority | Effort | Notes |
|------|----------|--------|-------|
| Implement professional signal analytics events | High | 2-4 hours | New dependency (PostHog or GA4). Only v1 item requiring new code. |
| Add referral source context to analytics | High | 1 hour | Bundled with analytics implementation. |
| Store full CMS data in pipeline (all history, all quarters) | Already done | 0 | Existing schema retains all periods via upsert-only writes. |
| Avoid anonymous-only assumptions in page components | Low | Ongoing | Discipline, not code. No stubs or scaffolding in v1. |

Items removed from original plan:
- **ProFeatureSlot stub** — replaced by React context provider strategy at auth time. Adding dead code now is anti-antifragile.
- **getFacility options pattern** — current architecture (static JSON export) already isolates data fetching from presentation. Options pattern is a no-op that adds unused code paths.

Total additional effort: analytics instrumentation only (2-4 hours). The store-everything and component architecture items are already satisfied by the existing design.
