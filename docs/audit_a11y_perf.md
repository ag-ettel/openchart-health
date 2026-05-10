# Accessibility and Performance Audit — OpenChart Health

**Audit date:** 2026-05-09
**Audit type:** Source code review (the `frontend/out/` static export was not present;
no production build was available at audit time, so no Lighthouse or axe-core run
could be executed against rendered HTML)
**Scope:** `frontend/app/`, `frontend/components/`, `frontend/public/`
**Tools available:** none of axe-core, pa11y, or lighthouse were installed in
`node_modules/`; `next build` had not been run (no `out/` and no `.next/static/chunks/`
production artifacts exist — only dev caches under `.next/cache/`)

---

## Critical issues (must-fix before launch)

### C1. DisclaimerBanner fails the 4.5:1 contrast requirement
- **File:** `frontend/components/DisclaimerBanner.tsx:13`
- **Problem:** The banner text is `text-gray-500` (#6b7280) on `bg-gray-50/95`
  (#f9fafb at ~95% opacity over white). Tailwind `gray-500` on `gray-50` is roughly
  4.34:1 — under WCAG AA at the body-text size used (`text-xs`, ~12px), and below
  the explicit `4.5:1` floor stated in `frontend-spec.md` line 35 and the legal-
  compliance disclosure rule for Template 3a. This is a **legal compliance failure**,
  not just an a11y nit, because the disclaimer is the primary legal shield.
- **Fix:** Use `text-gray-700` (#374151) on `bg-gray-50` — that pair is ~10.4:1.
  Increasing from `text-xs` to `text-sm` would also help readability.

### C2. No skip-to-content link in the layout
- **File:** `frontend/app/layout.tsx` (no skip link present)
- **Problem:** The `<NavBar>` (`frontend/components/NavBar.tsx`) renders 3-4 nav
  buttons before `<main>`. Keyboard and screen-reader users must Tab past every
  nav item on every page load. WCAG 2.4.1 Bypass Blocks (Level A) requires a
  bypass mechanism. The only `sr-only` class in the entire frontend is on the home
  search label (`HomeSearch.tsx:46`). No skip link was found anywhere.
- **Fix:** Add as the very first child of `<body>` in `layout.tsx`:
  ```tsx
  <a href="#main-content"
     className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4
                focus:z-[100] focus:rounded focus:bg-blue-600 focus:px-4 focus:py-2
                focus:text-white">
    Skip to main content
  </a>
  ```
  Then add `id="main-content"` to the existing `<main>` element on layout.tsx:59.

### C3. CompareIntervalPlot SVG has no accessible name
- **File:** `frontend/components/CompareIntervalPlot.tsx:92-109`
- **Problem:** The CI whisker `<svg>` lacks `role="img"`, `aria-label`, and a
  `<title>` element. Screen readers announce only "image" or skip it. The grep
  audit found exactly one `role="img"`/`<title>` use in the entire components
  tree (`FacilityTimeline.tsx:597`). All other SVG charts (Recharts ResponsiveContainer
  output, sparklines in `HospitalSummaryDashboard.tsx:60`, `NavBar.tsx` icons,
  `BenchmarkBar`, `DistributionHistogram`, `CompareIntervalPlot`) are unlabeled.
- **Fix:** For meaningful charts add `role="img"` + `aria-label="..."` describing
  the value comparison; for purely decorative icons (NavBar SVG glyphs that sit
  next to a text label), add `aria-hidden="true"` so AT doesn't double-announce.

### C4. Distribution / Benchmark / Sparkline charts have no text alternative
- **Files:**
  - `frontend/components/DistributionHistogram.tsx:97-138` (the histogram bar
    container has no role/label; tooltip content only shown on hover, never via AT)
  - `frontend/components/BenchmarkBar.tsx:57-95` (only individual `aria-label`s
    on absolute-positioned line/dot div elements — `<div aria-label>` without a
    role is announced inconsistently across screen readers)
  - `frontend/components/HospitalSummaryDashboard.tsx:60-69` (Sparkline `<svg>`
    with no labeling at all)
- **Problem:** These visualisations encode primary content. A non-sighted user
  cannot access the comparison.
- **Fix:** Wrap each chart in a `<figure>` with a `<figcaption>` (or `role="img"`
  + `aria-label`) summarising the value vs. national average in plain language.
  Reuse the existing punchline strings — the data is already there.

### C5. Filter-explore filter dropdowns lack label association on `<option>` placeholders
- **File:** `frontend/components/FilterExploreFilters.tsx:65-99`
- **Problem:** The labels themselves are properly wired (`htmlFor="filter-state"`
  → `id="filter-state"`). However, the placeholder `<option value="">{ALL}</option>`
  is selectable on focus and has no distinguishing semantics — combined with the
  fact that the "Clear filters" button on line 121 only renders conditionally,
  keyboard users can lose track of state. **More importantly:** the focus ring
  on the selects (`focus:border-gray-500`, line 73, 91) provides no visible
  outline — Tailwind's `focus:outline-none` removes the native outline and the
  border-only treatment fails WCAG 2.4.7 Focus Visible (Level AA) under most
  contrast conditions.
- **Fix:** Replace `focus:outline-none` with `focus:outline focus:outline-2
  focus:outline-blue-500 focus:outline-offset-1` (or remove the `focus:outline-none`
  and let the browser's native outline render).

### C6. Pervasive `focus:outline-none` removes focus indicator across interactive surfaces
- **Files:**
  - `frontend/components/CompareNearbyDrawer.tsx:383` (drawer search input)
  - `frontend/components/FilterExploreFilters.tsx:73, 91, 112` (filter selects/input)
  - `frontend/app/HomeSearch.tsx:55` (homepage search input)
  - `frontend/app/compare/ComparePageClient.tsx:739` (compare-picker search input)
- **Problem:** All four critical user-input surfaces strip the native focus
  outline and replace it with a 1px border-color change (`focus:border-blue-300`
  / `focus:border-gray-500`). A 1px tonal change does not meet WCAG 2.4.7 (Focus
  Visible) or 1.4.11 (Non-text Contrast 3:1 for UI components).
- **Fix:** Either restore `focus-visible:outline focus-visible:outline-2
  focus-visible:outline-blue-500` or use `focus:ring-2 focus:ring-blue-500`
  consistently. The HomeSearch input *does* set `focus:ring-1 focus:ring-gray-500`
  — that 1px ring at gray-500 is still too thin/low-contrast; use `ring-2` minimum.

### C7. `<details>`/`<summary>` collapsible patterns lack accessible-name pairing
- **Files (counts via grep):** 8 files use `<details>` (40 occurrences). Examples:
  - `frontend/components/HCAHPSGroupCard.tsx` (multiple expandable rows)
  - `frontend/components/MeasureCard.tsx` (10 details blocks)
  - `frontend/app/compare/ComparePageClient.tsx:300, 540, 561` (collapsible sections,
    trend chart toggle, source toggle)
- **Problem:** The native `<details>`/`<summary>` element is broadly accessible
  by default, but the **sticky bottom collapse bar** pattern in
  `ComparePageClient.tsx:316-333` and the equivalent in `MeasuresSection.tsx`
  duplicates the disclosure state in a separate floating button. When the user
  closes the section via the floating button, `el.open = false` is set
  imperatively (line 322); however, screen readers tied to the original
  `<summary>` will not be notified. There's no `aria-expanded` synchronization
  between the floating control and the originating `<summary>`.
- **Fix:** Either replace the floating collapse bar with `<summary>`-anchored
  toggling, or have the floating button programmatically focus the `<summary>`
  after toggling so AT users land back at a known location.

### C8. Heading hierarchy skips levels on hospital and NH profile pages
- **Files:**
  - `frontend/app/hospital/[ccn]/page.tsx:97` (h1)
  - `frontend/app/hospital/[ccn]/MeasuresSection.tsx:382, 431, 436` (h2)
  - `frontend/components/HCAHPSGroupCard.tsx:132` (h3 — fine)
  - `frontend/components/PatientSafetyRecord.tsx:57` (h2 — fine)
  - `frontend/components/HospitalSummaryDashboard.tsx` — has no heading at all
    despite being a major section on the page
- **Problem:** `HospitalSummaryDashboard` is rendered between the h1 and the h2
  sections in `MeasuresSection`. It contains badge groups, sparklines, and stat
  blocks but no h2 — the section is anonymous to AT users navigating by heading.
  Same gap exists on `NursingHomeSummaryDashboard.tsx`. Within HCAHPSGroupCard,
  the card uses h3 (line 132) without an enclosing h2 in some compare layouts —
  in `ComparePageClient.tsx:1237` an h2 "Patient Experience" wraps it correctly,
  but the per-card h3 inside `CompareHCAHPSGroup` (`ComparePageClient.tsx:471`)
  is fine only because it's nested under that h2.
- **Fix:** Add an h2 (visually hidden if needed via `sr-only`) inside
  `HospitalSummaryDashboard` and `NursingHomeSummaryDashboard` — e.g.,
  `<h2 className="sr-only">At a glance</h2>`.

### C9. Recharts charts (TrendChart, CompareTrendChart) are not keyboard-navigable
- **Files:**
  - `frontend/components/TrendChart.tsx:241-484`
  - `frontend/components/CompareTrendChart.tsx:200-294`
- **Problem:** Recharts `<ResponsiveContainer>`/`<ComposedChart>` produce SVG
  with no `role="img"` wrapper and no `aria-label`. Tooltips fire only on
  pointer/touch events (no keyboard equivalent). For a data-aggregation tool
  whose primary value is the trend display, the chart data is inaccessible to
  keyboard-only and screen-reader users.
- **Fix:** Two-part: (1) wrap each `<ResponsiveContainer>` in a `<figure>` with
  a `<figcaption>` summarising the trend trajectory in words (the data is
  available — current value, period count, direction); (2) consider rendering
  a visually-hidden `<table>` of the same data points adjacent to each chart
  for AT users. Recharts' built-in `accessibilityLayer` prop (recharts 2.10+
  available — package.json declares ^2.12.0) should be enabled on every
  `<ComposedChart>`.

### C10. Compare-page CCN inputs trigger immediate navigation with no confirmation
- **File:** `frontend/app/compare/ComparePageClient.tsx:632-636`
- **Problem:** When both slots fill, `useEffect` triggers
  `window.location.href = ...` synchronously inside an effect. Keyboard users
  who simply Tab away after typing risk an unintended navigation. There is no
  intermediate "Compare" button confirming the intent. The effect also ignores
  the prior URL — back-button history can become confusing.
- **Fix:** Replace the side-effect navigation with an explicit
  `<button type="button">Compare these providers</button>` that the user
  activates intentionally. The `CompareNearbyDrawer` already has this pattern
  on line 357 — apply consistently.

---

## Recommended improvements (nice-to-have)

### R1. Switch from `<link>` Google Fonts to `next/font/google`
- **File:** `frontend/app/layout.tsx:33-36`
- **Issue:** Inter is loaded via `<link href="fonts.googleapis.com/...">`. This
  blocks rendering and contributes to CLS until the font swaps. `next/font/google`
  self-hosts and inlines critical CSS, and works with `output: "export"`.
- **Action:** Replace with:
  ```tsx
  import { Inter } from "next/font/google";
  const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
  // ... <html className={inter.variable}>
  ```
  Then remove the inline `style={{ fontFamily: ... }}` on `<body>` (line 54)
  and use `font-sans` with the Tailwind fontFamily extension. Caller asked
  to note rather than change — this is a recommendation only.

### R2. Sparse `aria-live` / status announcements for async loading states
- **Files:**
  - `frontend/components/CompareNearbyDrawer.tsx:391-400` (loading/error)
  - `frontend/app/compare/ComparePageClient.tsx:830-845` (loading/error/CCN mismatch)
- **Issue:** "Loading providers...", "Failed to load...", and "Please select two
  different providers..." render as static text. AT users won't be notified.
- **Action:** Wrap status messages in an element with `role="status"
  aria-live="polite"` (or `role="alert"` for error states).

### R3. Many client components should be server components
- **Files:** 35 components/pages declare `"use client"` per grep. Many are
  pure-render with no state/effects (e.g., `OwnershipPanel.tsx`,
  `OwnershipStructureViz.tsx`, `FacilityTimeline.tsx` portions, `PresetTable.tsx`,
  `FilterExploreTable.tsx`). Rough estimate: 8-10 of the 35 do not actually
  need client-side React.
- **Action:** Audit each `"use client"` directive. Components without `useState`,
  `useEffect`, `useMemo`, event handlers, or browser APIs can drop the directive
  and ship 0 bytes of JS. Net savings likely 30-80KB gzipped.

### R4. Recharts is the largest single dependency — code-split TrendChart/CompareTrendChart
- **Issue:** Recharts ^2.12 typically lands ~90-120KB gzipped per page that imports
  it. Both `TrendChart` and `CompareTrendChart` use ResponsiveContainer +
  ComposedChart. Profile pages with no expanded trend will still ship the
  bundle today because the import chain is eager (`MeasureCard` → `TrendChart`
  at module top).
- **Action:** Use `next/dynamic(() => import("./TrendChart"), { ssr: false })`
  — or restructure so `TrendChart` is only imported when the user expands the
  trend `<details>`.

### R5. distributions.json and search_index.json are large public assets
- **Files:**
  - `frontend/public/distributions.json` — **2,086,830 bytes (2.0 MB)**
  - `frontend/public/search_index.json` — **2,793,585 bytes (2.7 MB)**
- **Issue:** Both are fetched at first interactive use:
  - `distributions.json` — by `useDistribution` hooks on profile and compare pages
  - `search_index.json` — by `HomeSearch.tsx:22` and `ComparePageClient.tsx:603`
  At 2-3 MB uncompressed each, these meaningfully impact first-search latency and
  mobile data plans. Both are highly compressible (gzip should be ~10-15% of raw).
- **Action:** Confirm the production CDN serves these with `Content-Encoding: gzip`
  or `br`. Consider sharding `distributions.json` by measure_id (one file per
  measure, fetched lazily by `useDistribution`) — most page loads need only 1-5
  measures, not the entire 2MB blob. `search_index.json` could be trimmed to
  one record per provider with a smaller schema (drop fields not used for
  matching).

### R6. Public icon and OG image weights are reasonable but verify on launch
- **Inventory:**
  - `og-default.png` — **40,877 bytes** (under the 300KB target)
  - `icon-192.png` — 4,336 bytes
  - `icon-512.png` — 15,960 bytes
  - `apple-touch-icon.png` — 4,031 bytes
  - `favicon-32.png` — 685 bytes
  All under the 50KB-per-icon target stated in the audit brief.
- **Action:** None required. Verify the 1200×630 dimensions on `og-default.png`
  match Twitter Card and Open Graph minimums.

### R7. Stacked-bar HCAHPS slices use color-only differentiation
- **Files:** `frontend/components/HCAHPSGroupCard.tsx:43-65`,
  `frontend/app/compare/ComparePageClient.tsx:352-369`
- **Issue:** The blue/light-blue/gray triplet (`#2563eb`, `#93c5fd`, `#e5e7eb`)
  encodes "Always" / "Usually" / "Sometimes/Never" by hue + lightness. Users
  with deuteranopia will see the two blues as similar; gray vs. light blue is
  marginal. The `title` attribute on each slice (line 172, 410) is the only
  alternative — `title` is not announced consistently by AT.
- **Action:** Add either (a) a visible micro-legend below each stacked bar
  (`HCAHPSGroupCard` already does this on line 178+ for the full card; the
  compact compare variant on `ComparePageClient.tsx:413` is acceptable), or
  (b) hatch/stripe patterns via SVG patterns instead of pure color, or
  (c) inline percentage labels on the slices when slice width permits.

### R8. `text-gray-400` body text appears in many places
- **Files:** 30 files use `text-gray-400` (303 occurrences total per grep
  including `text-gray-300/400/500`). Many are decorative/secondary
  (e.g., footer microcopy, period labels in card meta), but several are
  load-bearing data:
  - `frontend/components/DistributionHistogram.tsx:142, 145` (axis tick labels)
  - `frontend/components/BenchmarkBar.tsx:98` (axis labels)
  - `frontend/components/CompareIntervalPlot.tsx:237` (CI whisker legend)
  - `frontend/components/MeasureCard.tsx` (period meta)
- **Issue:** `text-gray-400` (#9ca3af) on white is ~3.05:1 — fails WCAG AA for
  body text (4.5:1 required). Acceptable only as decoration or for large text
  (≥18pt). Most uses are 10-12px, well under the large-text threshold.
- **Action:** Promote to `text-gray-500` (#6b7280, ~4.6:1 — passing) or
  `text-gray-600` for data-bearing labels. Decorative microcopy may stay at
  gray-400 if it conveys no information.

### R9. Title-attribute tooltips are not keyboard-reachable
- **Files:** 12+ files use `title="..."` on buttons/elements (e.g.,
  `CompareNearbyDrawer.tsx:265, 345`). Tooltip content displayed via `title`
  appears on mouse hover only.
- **Action:** For interactive elements where the title is purely supplementary
  to a visible label (e.g., the close X buttons), keep title. Where the title
  conveys unique information, switch to a Radix `Tooltip` primitive (already
  a project-approved dependency per `frontend-spec.md`) — it provides keyboard
  focus reveal.

### R10. Filter-explore measure picker (MeasurePicker) — flat list at scale
- **File:** `frontend/components/MeasurePicker.tsx`
- **Issue:** With 207 measures across hospital + NH groups, the picker can grow
  long. Without proper grouping landmarks (h2 per group? `<fieldset>` with
  `<legend>`?), AT users navigate a flat list.
- **Action:** Wrap each measure_group in a `<fieldset>`/`<legend>` or use
  proper heading semantics with `aria-labelledby`.

### R11. Loading spinners use plain text — no spinner with `role="status"`
- **Files:** Multiple ("Loading providers...", "Loading...", "Loading provider data...")
- **Action:** Wrap in `role="status"` for AT announcements. Adds zero visual
  change but makes "loading" intelligible to screen readers.

### R12. The orange tail-risk badges are correctly color-coded but lack textual
       reinforcement in some contexts
- **Files:**
  - `NursingHomeSummaryDashboard.tsx:347-362` (SFF, SFF Candidate, Abuse Finding
    badges) — these have `tooltip` text and the visible label is a plain-language
    string, so they pass the "not color-only" requirement
  - `InspectionSummary.tsx` and citations (J/K/L) — verify each citation row
    pairs the orange visual treatment with a textual "Immediate Jeopardy" or
    severity letter so colorblind users get the signal from text
- **Status:** Per code reading, the badges meet the rule (color reinforces, does
  not solely encode). Worth a manual visual QA pass at launch to confirm no
  citation row leans on color alone.

---

## Bundle / asset analysis

No production build (`out/` or `.next/static/chunks/`) was available, so chunk
sizes could not be measured directly. Inferred chunk concerns based on imports:

| Concern | Source | Likely chunk impact |
|---|---|---|
| Recharts on every profile + compare page | `MeasureCard.tsx:28` (TrendChart), `ComparePageClient.tsx:48` (CompareTrendChart) | ~90-120KB gzipped — would exceed 200KB threshold once shared with React + Radix Dialog |
| Radix Dialog on global nav | `NavBar.tsx` → `CompareNearbyDrawer.tsx:5` | ~15-25KB gzipped, loaded on every page |
| `distributions.json` (2.0 MB raw) | Fetched by `useDistribution` hook on profile and compare | Compressed: ~200-300KB; mobile users feel this |
| `search_index.json` (2.7 MB raw) | Fetched on home + compare picker | Compressed: ~250-400KB |
| Inter via Google Fonts `<link>` | `layout.tsx:33` | Render-blocking, ~30-50KB depending on subset |

**Run `next build && next export` then re-audit chunks.** The largest single
optimization win is dynamic-importing TrendChart so it only loads when a user
expands a trend `<details>`.

---

## Source files reviewed

- `e:\openchart-health\CLAUDE.md`
- `e:\openchart-health\.claude\rules\frontend-spec.md`
- `e:\openchart-health\.claude\rules\legal-compliance.md`
- `e:\openchart-health\frontend\app\layout.tsx`
- `e:\openchart-health\frontend\app\page.tsx`
- `e:\openchart-health\frontend\app\HomeSearch.tsx`
- `e:\openchart-health\frontend\app\compare\ComparePageClient.tsx`
- `e:\openchart-health\frontend\app\filter-explore\page.tsx`
- `e:\openchart-health\frontend\app\filter-explore\FilterExploreClient.tsx`
- `e:\openchart-health\frontend\app\hospital\[ccn]\page.tsx`
- `e:\openchart-health\frontend\app\hospital\[ccn]\CategoryNav.tsx`
- `e:\openchart-health\frontend\app\hospital\[ccn]\MeasuresSection.tsx`
- `e:\openchart-health\frontend\app\nursing-home\[ccn]\page.tsx`
- `e:\openchart-health\frontend\app\methodology\page.tsx`
- `e:\openchart-health\frontend\components\DisclaimerBanner.tsx`
- `e:\openchart-health\frontend\components\NavBar.tsx`
- `e:\openchart-health\frontend\components\CompareNearbyDrawer.tsx`
- `e:\openchart-health\frontend\components\CompareIntervalPlot.tsx`
- `e:\openchart-health\frontend\components\CompareTrendChart.tsx`
- `e:\openchart-health\frontend\components\TrendChart.tsx`
- `e:\openchart-health\frontend\components\DistributionHistogram.tsx`
- `e:\openchart-health\frontend\components\BenchmarkBar.tsx`
- `e:\openchart-health\frontend\components\MeasureCard.tsx`
- `e:\openchart-health\frontend\components\MeasureGroup.tsx`
- `e:\openchart-health\frontend\components\HCAHPSGroupCard.tsx`
- `e:\openchart-health\frontend\components\HospitalSummaryDashboard.tsx`
- `e:\openchart-health\frontend\components\NursingHomeSummaryDashboard.tsx` (partial)
- `e:\openchart-health\frontend\components\PatientSafetyRecord.tsx`
- `e:\openchart-health\frontend\components\NotReportedCard.tsx`
- `e:\openchart-health\frontend\components\AttributionLine.tsx`
- `e:\openchart-health\frontend\components\SuppressionIndicator.tsx`
- `e:\openchart-health\frontend\components\NonReporterIndicator.tsx`
- `e:\openchart-health\frontend\components\InspectionSummary.tsx` (partial)
- `e:\openchart-health\frontend\components\FilterExploreFilters.tsx`
- `e:\openchart-health\frontend\components\MeasurePicker.tsx` (partial)
- `e:\openchart-health\frontend\components\PaymentAdjustmentHistory.tsx` (partial)
- `e:\openchart-health\frontend\components\OwnershipStructureViz.tsx` (partial)
- `e:\openchart-health\frontend\components\FacilityTimeline.tsx` (SVG portion only)
- `e:\openchart-health\frontend\package.json`
- `e:\openchart-health\frontend\public\` (icon and OG asset weights)

---

## Summary

| Bucket | Count |
|---|---|
| Critical issues (must fix before launch) | **10** |
| Recommended improvements | **12** |
| Bundle analysis status | Source-level only — no production build was available |

The two highest-priority items are **C1** (DisclaimerBanner contrast — direct
legal-compliance failure) and **C2** (no skip-to-content link — WCAG 2.4.1 Level A
failure). Both are one-line fixes. The chart accessibility cluster (**C3**, **C4**,
**C9**) is the largest body of work and should be tracked together — adopting
Recharts' `accessibilityLayer` prop and a `<figure>`/`<figcaption>` pattern
across the four chart components would resolve most of it.
