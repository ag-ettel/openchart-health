import type { Metadata } from "next";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenChart Health — CMS Hospital and Nursing Home Quality Data",
  description:
    "Find and compare CMS-published quality data for hospitals and nursing homes, " +
    "with uncertainty visible and safety measures surfaced prominently.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-white text-gray-900 antialiased" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
        {/* Sticky header — stays visible while scrolling */}
        <nav className="sticky top-0 z-30 border-b border-gray-200 bg-white/95 px-6 py-3 backdrop-blur-sm">
          <div className="mx-auto flex max-w-6xl items-center justify-between">
            <a href="/" className="flex items-baseline">
              <span className="text-xl font-bold tracking-tight text-blue-700">
                OpenChart
              </span>
              <span className="ml-1.5 text-xl font-bold tracking-tight text-orange-500">
                Health
              </span>
            </a>
            <div className="flex items-center gap-6 text-sm text-gray-500">
              <a href="/methodology/" className="hover:text-gray-900">
                Methodology
              </a>
            </div>
          </div>
        </nav>

        {/* pb-14 prevents content from hiding behind sticky footer */}
        <main className="mx-auto max-w-6xl px-6 py-8 pb-14">{children}</main>

        {/* Sticky footer disclaimer */}
        <DisclaimerBanner />
      </body>
    </html>
  );
}
