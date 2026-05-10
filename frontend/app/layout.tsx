import type { Metadata } from "next";
import Script from "next/script";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { CompareProvider } from "@/components/CompareContext";
import { NavBar } from "@/components/NavBar";
import { buildRootMetadata } from "@/lib/seo";
import {
  getPlausibleDomain,
  getPlausibleScriptSrc,
  isAnalyticsEnabled,
} from "@/lib/analytics";
import {
  buildOrganizationJsonLd,
  buildWebsiteJsonLd,
  jsonLdString,
} from "@/lib/structured-data";
import "./globals.css";

export const metadata: Metadata = buildRootMetadata();

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  const plausibleDomain = getPlausibleDomain();
  const orgLd = jsonLdString(buildOrganizationJsonLd());
  const siteLd = jsonLdString(buildWebsiteJsonLd());

  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: orgLd }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: siteLd }}
        />
        {isAnalyticsEnabled() && plausibleDomain && (
          <Script
            defer
            data-domain={plausibleDomain}
            src={getPlausibleScriptSrc()}
            strategy="afterInteractive"
          />
        )}
      </head>
      <body className="min-h-screen bg-white text-gray-900 antialiased" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
        {/* Skip-to-content link for keyboard / screen reader users (WCAG 2.4.1). */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-white focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-blue-300"
        >
          Skip to main content
        </a>
        <CompareProvider>
          <NavBar />

          {/* pb-14 prevents content from hiding behind sticky footer */}
          <main id="main-content" className="mx-auto max-w-6xl px-6 py-8 pb-14">{children}</main>
        </CompareProvider>

        {/* Sticky footer disclaimer */}
        <DisclaimerBanner />
      </body>
    </html>
  );
}
