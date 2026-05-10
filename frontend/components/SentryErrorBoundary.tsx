"use client";

// Lightweight error boundary that reports to Sentry when a DSN is configured.
// Used on routes that fetch JSON at runtime (the /compare and /filter-explore
// static-export exceptions) so render failures from malformed CDN data, slow
// connections, or schema drift become visible in production.
//
// Behavior:
//   - With NEXT_PUBLIC_SENTRY_DSN set: errors captured to Sentry, fallback UI shown.
//   - Without DSN (local dev): errors logged to console, fallback UI shown.
//
// Fallback UI is intentionally minimal and informational — no medical-advice
// language, no causal claims about why the data could not load.

import { Component, type ReactNode } from "react";
import * as Sentry from "@sentry/nextjs";

interface SentryErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  /** Tag used in Sentry to group errors by call site. */
  scope?: string;
}

interface SentryErrorBoundaryState {
  hasError: boolean;
}

const DEFAULT_FALLBACK: ReactNode = (
  <div className="mx-auto max-w-2xl rounded border border-amber-200 bg-amber-50 px-4 py-6 text-sm text-amber-800">
    <p className="font-medium">This page could not load.</p>
    <p className="mt-2">
      The data for this view could not be retrieved. Refresh to try again, or return
      to the home page.
    </p>
  </div>
);

export class SentryErrorBoundary extends Component<
  SentryErrorBoundaryProps,
  SentryErrorBoundaryState
> {
  constructor(props: SentryErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(_error: Error): SentryErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    if (dsn) {
      Sentry.withScope((scope) => {
        if (this.props.scope) {
          scope.setTag("boundary", this.props.scope);
        }
        scope.setExtra("componentStack", errorInfo.componentStack);
        Sentry.captureException(error);
      });
    } else {
      // eslint-disable-next-line no-console
      console.error(`[${this.props.scope ?? "boundary"}]`, error, errorInfo);
    }
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.props.fallback ?? DEFAULT_FALLBACK;
    }
    return this.props.children;
  }
}
