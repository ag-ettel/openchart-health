// Sentry server-side configuration.
//
// This site uses output: "export" (static export) — there is no runtime
// Node server in production. This config exists so that build-time errors
// from generateStaticParams, server components, and the build pipeline are
// captured in Sentry. Like the client config, initialization is conditional
// on NEXT_PUBLIC_SENTRY_DSN being set.

import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
    environment: process.env.NODE_ENV,
  });
}
