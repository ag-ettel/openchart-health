// Sentry client-side configuration.
//
// Initialization is conditional on NEXT_PUBLIC_SENTRY_DSN being set. When the
// env var is absent (local dev, preview deploys without monitoring), Sentry
// is a no-op — no network calls, no warnings.
//
// PII discipline: this site has no user accounts, no patient data, and no
// query strings that identify individual users. CCNs are public CMS
// identifiers and may appear in URLs. We do NOT send IP addresses,
// cookies, or any user-identifying data. See
// .claude/rules/legal-compliance.md for analytics PII constraints.

import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    // Lower trace sampling for a public, high-traffic data site. Errors are
    // sampled at 100%; performance traces at 10% to keep quota in check.
    tracesSampleRate: 0.1,
    // No session replay — replay can capture form input and rendered text,
    // which is not appropriate for a site that may surface CMS data adjacent
    // to user-driven inputs.
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
    // Strip IP addresses and User-Agent before send. Public site, no auth —
    // we do not need user identifiers to debug crashes.
    sendDefaultPii: false,
    // Match the build environment so dashboards can filter by deploy.
    environment: process.env.NODE_ENV,
  });
}
