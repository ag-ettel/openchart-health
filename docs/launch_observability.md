# Launch Observability

This document describes the observability stack for the OpenChart Health static
site at production launch and the recommended uptime monitoring configuration.
The user provisions accounts; this file specifies what to check, how often, and
when to escalate.

## Components

| Layer | Tool | Status | Notes |
|---|---|---|---|
| Frontend errors | Sentry (`@sentry/nextjs`) | Wired, conditional on DSN | `NEXT_PUBLIC_SENTRY_DSN` env var; absent = no-op. Source maps upload requires `SENTRY_ORG` + `SENTRY_PROJECT` + `SENTRY_AUTH_TOKEN`. |
| Analytics | Plausible | Wired, conditional on domain | `NEXT_PUBLIC_PLAUSIBLE_DOMAIN` env var; absent = no-op. |
| Uptime monitoring | TBD (UptimeRobot, BetterStack, Hetrix, etc.) | Not yet provisioned | This document. |

## Uptime Checks

The site is fully static-exported and served from a CDN. Uptime is therefore
predominantly a CDN / DNS / certificate question, not an app-server question.
The checks below verify that the CDN is serving the canonical surfaces and
that the static export ran successfully.

Replace `https://openchart.health` with the live origin if it differs.

### Tier 1: Critical surfaces (1-minute interval, page on failure)

| Name | URL | Expected | Why |
|---|---|---|---|
| Home page | `https://openchart.health/` | HTTP 200, contains "find and compare" copy | Primary landing surface; if this fails, the site is down for new visitors. |
| Sitemap | `https://openchart.health/sitemap.xml` | HTTP 200, content-type `application/xml`, contains at least 20,000 `<url>` entries | Sitemap is the search-engine entry point; an empty or stale sitemap silently kills indexing. |
| Sample hospital | `https://openchart.health/hospital/cleveland-clinic-foundation-cleveland-oh-360180/` | HTTP 200 | Confirms `generateStaticParams` produced provider pages, not just a stub. Pick a stable, large hospital that will not close. |

If any Tier 1 check fails for two consecutive intervals, page on-call.

### Tier 2: Secondary surfaces (5-minute interval, alert on failure)

| Name | URL | Expected | Why |
|---|---|---|---|
| Methodology | `https://openchart.health/methodology/` | HTTP 200 | Required disclosure page (Template 3h CI methodology). Static, should never 404. |
| Compare picker | `https://openchart.health/compare/` | HTTP 200 | Compare landing page (no CCNs in URL). Confirms client-side fetch infra renders. |
| Filter-explore (hospitals) | `https://openchart.health/filter-explore/` | HTTP 200 | Manifest-driven page; fetch infra check. |
| Filter-explore (nursing homes) | `https://openchart.health/filter-explore/nursing-home/` | HTTP 200 | Same, NH variant. |
| About | `https://openchart.health/about/` | HTTP 200 | Static informational page. |

If any Tier 2 check fails for three consecutive intervals, alert (no page).

### Tier 3: Data freshness probes (hourly interval, alert on staleness)

| Name | URL | Expected | Why |
|---|---|---|---|
| Provider directory | `https://openchart.health/data/provider_directory.json` | HTTP 200, content-type `application/json`, body contains `"openchart_health"` no — body parses as a non-empty JSON array | CompareNearbyDrawer depends on this. A stale or missing directory silently breaks the compare drawer. |
| Sample provider JSON | `https://openchart.health/data/360180.json` | HTTP 200, body parses as JSON, top-level `last_updated` field within last 35 days | Confirms the pipeline ran and published a fresh export. 35-day staleness threshold accommodates monthly CMS refresh cadence. |
| Search index | `https://openchart.health/search_index.json` | HTTP 200, body parses as JSON array, length > 20000 | Drives the home-page search. Empty index = silent failure for search users. |
| Measure manifest | `https://openchart.health/measure-index/_manifest.json` | HTTP 200, body parses as JSON, `measures` array length > 200 | Drives /filter-explore. A truncated manifest silently hides measures. |

If any Tier 3 check fails for three consecutive intervals, alert (no page).
Tier 3 staleness is a pipeline issue, not a CDN issue — the response will be
"the data is old" rather than "the site is down."

### Tier 4: SSL and DNS (daily)

| Name | Check | Expected |
|---|---|---|
| SSL certificate expiry | TLS handshake on port 443 | More than 14 days remaining |
| DNS resolution | A/AAAA record for `openchart.health` | Resolves to expected CDN edge IP range |

Both should be standard checkbox features in any uptime provider.

## Alert Escalation

| Tier | Channel | Acknowledgement window |
|---|---|---|
| Tier 1 (page) | Push notification + SMS | 5 minutes |
| Tier 2 (alert) | Email + push | 30 minutes |
| Tier 3 (alert) | Email | 4 hours |
| Tier 4 (alert) | Email | 24 hours |

Single-engineer operation — there is no rotating on-call. All alerts route to
the maintainer's primary device. Tier escalation is about urgency-of-attention,
not personnel routing.

## Provider Selection Notes

Equivalent feature sets are available from UptimeRobot (free tier covers Tier
1 and Tier 2), BetterStack (better dashboards, paid), Hetrix (cheap), and
Cloudflare Health Checks (bundled if the site is behind Cloudflare).

If the site is fronted by Cloudflare, prefer Cloudflare Health Checks for
Tier 1 — they check from inside the Cloudflare network so a check pass + user
report of "site down" definitively isolates the user's ISP from the origin.

## What These Checks Do Not Cover

- **Pipeline runs** — uptime checks confirm that exported JSON is being
  served, not that the pipeline is running successfully. The `pipeline_runs`
  audit table and the 5% failure threshold abort (data-integrity Rule 6)
  cover the pipeline.
- **Frontend JavaScript errors** — Sentry covers these. An uptime check that
  loads HTML will not catch a runtime crash inside React.
- **Data correctness** — the export validation script in
  `pipeline/export/build_json.py` and the `tests/pipeline/` test suite cover
  schema correctness. Uptime cannot detect "the data is wrong."
- **Search engine indexing** — verify in Google Search Console and Bing
  Webmaster Tools after launch. An uptime probe of `sitemap.xml` is a
  prerequisite, not a substitute.
- **CDN cache invalidation lag** — after a pipeline refresh, the CDN may
  serve stale JSON for up to the cache TTL. The Tier 3 freshness probe
  detects this if the lag exceeds the 35-day staleness threshold.

## Pipeline-side Observability (Cross-reference)

Pipeline-side observability lives separately. See:

- `pipeline_runs` table — every pipeline run logs success/failure/anomaly
  counts (data-integrity Rule 6).
- `docs/pipeline_decisions.md` — DEC entries document material run failures
  and resolutions.
- `make check` — runs compliance lint + linter + tests; should be green
  before every pipeline-affecting commit.

The pipeline writes to `build/data_staging/` and atomically renames to
`build/data/` only after full validation passes. A failed pipeline run never
overwrites a previously successful export, so uptime probes on the static
files cannot regress from a single bad run.
