// Next.js instrumentation hook — entry point for Sentry initialization on
// the server and edge runtimes. Required for @sentry/nextjs >= 8.
//
// The client config is loaded automatically by next.config.mjs Sentry plugin.
// All three configs are no-ops when NEXT_PUBLIC_SENTRY_DSN is unset.

import * as Sentry from "@sentry/nextjs";

export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}

export const onRequestError = Sentry.captureRequestError;
