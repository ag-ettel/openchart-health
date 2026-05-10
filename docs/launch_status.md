# Launch Status

Snapshot of launch-readiness gates from `phase-1.md`. Updated as items resolve.

## Production target

- **Domain**: `openchart.health` (registered, DNS at Cloudflare free tier)
- **Hosting**: Cloudflare Pages — single-vendor DNS + hosting + CDN, free
  tier handles serious traffic, no surprise bills, zero DNS friction
- **Build target**: static export (`output: "export"` in `next.config.mjs`),
  output to `frontend/out/`
- **Build host**: Linux (Cloudflare Pages build environment)

## Cloudflare Pages deploy plan

1. Create a Pages project and connect to the GitHub repo
2. Framework preset: Next.js (Static HTML Export)
3. Build command: `cd frontend && npm install && npm run build`
4. Build output directory: `frontend/out`
5. Node version: 22 (Pages env var) — not 24 (readlink issues)
6. Production environment variables (per `frontend/.env.example`):
   - `NEXT_PUBLIC_SITE_URL=https://openchart.health`
   - `NEXT_PUBLIC_CDN_BASE=/data`
   - `NEXT_PUBLIC_PLAUSIBLE_DOMAIN=openchart.health` (after Plausible setup)
   - `NEXT_PUBLIC_SENTRY_DSN=...` (DSN obtained, ready to paste)
   - Optionally: `SENTRY_ORG=openchart-health`, `SENTRY_PROJECT=openchart-health`,
     `SENTRY_AUTH_TOKEN=...` (mark Encrypted)
7. Bind `openchart.health` and `www.openchart.health`
8. Automatic HTTPS (Cloudflare default)

## Passing

### Code quality
- **Compliance lint**: 0 violations across 100+ files
- **TypeScript strict**: `npx tsc --noEmit` clean
- **SEO check**: pages have title, description, canonical (limited build sample)
- **Pipeline tests**: 515 passing, 67 skipped, no failures

### Frontend display
- Hospital and NH profile pages render from static JSON
- Compare page with side-by-side interval plot, overlaid trend chart, sticky
  collapse with focus restoration, plain language descriptions, all required
  disclosures
- Filter/explore page for hospitals and nursing homes
- CompareNearbyDrawer (proximity-sorted provider selection)
- All 7 conditional disclosures from `legal-compliance.md` checklist render

### Accessibility (audit-driven)
All 10 critical issues from the a11y audit resolved:
- **C1** DisclaimerBanner contrast `text-gray-700` (~10.4:1, meets 4.5:1 legal req)
- **C2** Skip-to-content link in layout (WCAG 2.4.1)
- **C3/C4** Charts wrapped in `<figure>`/`<figcaption>` with plain-language
  `aria-label` summaries: BenchmarkBar, CompareIntervalPlot,
  DistributionHistogram. Sparklines + nav icons marked `aria-hidden`.
- **C5/C6** Focus indicators on all input surfaces use `focus-visible:ring-2
  ring-blue-500 ring-offset-1` (FilterExploreFilters, HomeSearch,
  CompareNearbyDrawer, ComparePageClient)
- **C7** Floating collapse bars return keyboard focus to originating section
  on collapse, with `aria-label` and focus-visible rings
- **C8** Heading hierarchy verified — both summary dashboards have top-level
  h2 ("At a Glance" / NH equivalent)
- **C9** Recharts `accessibilityLayer` prop on TrendChart and CompareTrendChart
- **C10** Compare page CCN selection now uses explicit "Compare these
  providers" button — no more auto-navigation on slot fill

Plus several recommendations addressed:
- **R8** `text-gray-400` axis labels promoted to `text-gray-600`
- **R11** Loading and error states use `role="status"` / `role="alert"` with
  `aria-live` on compare page and CompareNearbyDrawer

### SEO + observability
- Per-page metadata via `generateMetadata` on all routes
- `sitemap.ts`, `robots.ts`, JSON-LD (Hospital, NursingHome, WebSite,
  Organization, BreadcrumbList)
- Image assets in `public/`: `og-default.png`, `favicon-32.png`,
  `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`. Wired explicitly
  via `lib/seo.ts` metadata.
- Sentry frontend error monitoring via `@sentry/nextjs` 10.52.0,
  conditional on `NEXT_PUBLIC_SENTRY_DSN` (no-op without env var).
  SentryErrorBoundary on compare and filter-explore pages.
- Plausible analytics scaffolding with 5 typed events wired:
  `compareStarted`, `compareNearbyOpened`, `compareNearbyResultClicked`,
  `measureFilterExploreSelected`, `measureFilterExploreSorted`. No PII.
- Uptime monitoring spec at `docs/launch_observability.md`

### SEO copy (compelling but compliant)
- Home page tagline rewritten: "See what CMS reports on every certified
  hospital and nursing home" framing replaces flat "find and compare"
- Per-NH meta descriptions surface SFF / SFF-Candidate / Abuse-Finding
  CMS designations as factual prefix, e.g. "CMS Special Focus Facility.
  What CMS reports on [Name] in [City], [State]: ..."
- "CMS publishes detailed quality data on every certified hospital and
  nursing home in the country. Most facilities only highlight the best
  of it" framing surfaces the "behind the brochure" angle factually
- All copy verified ≤160 chars meta descriptions, ≤60 chars titles
- All copy passes compliance lint

### Pipeline
- Provider data export: ~22K provider JSONs in `build/data/`
- Methodology page substantively expanded (intervals, no-color rationale,
  tail-risk prominence, three reporting states, compare methodology, sort
  vs ranking, NH specifics, population context, refresh cadence)
- Pipeline refresh scheduler: `scripts/detect_cms_refresh.py`,
  `scripts/scheduled_refresh.py`, `docs/refresh_schedule.md`
- DKAN client added at `pipeline/ingest/client.py` (was missing)

### Audit deliverables
- `docs/audit_a11y_perf.md` — original audit findings
- `docs/launch_observability.md` — uptime monitoring spec
- `docs/refresh_schedule.md` — cron + Windows Task Scheduler entries
- `docs/launch_status.md` — this document

## Open

### Account setup (user action required)

- **Cloudflare Pages project**: deploy plan documented; not yet executed
- **Sentry project**: DSN obtained (`openchart-health` org + project),
  ready to paste into Cloudflare Pages env
- **Plausible account**: not yet created (or self-host alternative)
- **Search Console + Bing Webmaster verification**: needs live deployment

### Remaining a11y polish (non-blocking)

- **R1** `next/font/google` migration (CLS reduction)
- **R3** Server component conversion for non-stateful components
- **R4** Dynamic-import Recharts (~90-120KB gzipped per-page win)
- **R5** Shard `distributions.json` and trim `search_index.json`
- **R7** HCAHPS stacked bar — micro-legend or pattern fill for color-only
  distinction
- **R9** `title` attribute tooltips → Radix Tooltip primitive
- **R10** MeasurePicker fieldset/legend grouping
- **R12** Tail-risk badge text reinforcement audit pass at launch

### Local-only issue (not blocking deploy)

- **`next build` on Windows + Node 24**: fails with EISDIR/readlink errors
  on Next.js internals. Linux build hosts (Cloudflare Pages) won't
  reproduce. For local-build verification: use WSL, downgrade to Node 22
  LTS, or run via a Linux container.

### Deferred

- **Pipeline coverage**: `pipeline/normalize/` 70-95%, `store/` 9%,
  `orchestrate.py` 0%. Most normalizers near phase-1 target;
  store/orchestrate gaps are by design (integration-tested).
- **Per-provider OG images**: generic OG works for launch
- **Automated archive download**: documented in
  `docs/refresh_schedule.md` as a manual step
- **API endpoints in `api/`**: lower priority since static export is
  the primary data path
