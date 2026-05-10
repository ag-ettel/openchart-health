// Next.js config. The Sentry wrapper is conditional on NEXT_PUBLIC_SENTRY_DSN
// being set — when absent (local dev, preview without monitoring), the plain
// nextConfig is exported untouched and Sentry adds zero overhead.

import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  // Trailing slashes ensure each route gets its own directory with index.html
  trailingSlash: true,
};

const sentryDsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

// Sentry build-time options. Source maps upload requires SENTRY_AUTH_TOKEN +
// SENTRY_ORG + SENTRY_PROJECT in the build environment; without them, the
// plugin emits source maps but skips the upload (silent — no build failure).
const sentryBuildOptions = {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  // Suppress source-map upload chatter in CI logs unless verbose is requested.
  silent: !process.env.SENTRY_VERBOSE,
  // Hide source maps from public bundles after upload (production builds).
  // Maps remain in Sentry for stack-trace symbolication.
  hideSourceMaps: true,
  // Tunnel route disabled — this site is fully static, no server route.
  tunnelRoute: undefined,
  webpack: {
    // Strip Sentry's debug logger from production bundles.
    treeshake: { removeDebugLogging: true },
    // Auto Vercel monitors not relevant — this builds for Cloudflare Pages.
    automaticVercelMonitors: false,
  },
};

export default sentryDsn
  ? withSentryConfig(nextConfig, sentryBuildOptions)
  : nextConfig;
