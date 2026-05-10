"use client";

import { useCompareTarget } from "@/components/CompareContext";
import { CompareNearbyDrawer } from "@/components/CompareNearbyDrawer";
import { FILTER_EXPLORE_NAV_LABEL } from "@/lib/constants";

const navButtonClass =
  "shrink-0 inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-600 shadow-sm hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 transition-colors";

export function NavBar() {
  const { target } = useCompareTarget();

  return (
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
        <div className="flex items-center gap-2">
          {target ? (
            <CompareNearbyDrawer
              currentCcn={target.ccn}
              currentName={target.name}
              providerType={target.providerType}
            />
          ) : (
            <a href="/compare" className={navButtonClass}>
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
                aria-hidden="true"
                focusable="false"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
                />
              </svg>
              Compare
            </a>
          )}
          <a href="/filter-explore/" className={navButtonClass}>
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
              aria-hidden="true"
              focusable="false"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75"
              />
            </svg>
            {FILTER_EXPLORE_NAV_LABEL}
          </a>
          <a href="/methodology/" className={navButtonClass}>
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
              aria-hidden="true"
              focusable="false"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
              />
            </svg>
            Methodology
          </a>
        </div>
      </div>
    </nav>
  );
}
