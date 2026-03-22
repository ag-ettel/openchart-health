"use client";

// Home page with provider search.
// Reads from build/data/search_index.json (built by scripts/build-search-index.ts).
// Client-side search — no server calls.

import { useState, useMemo, useEffect } from "react";

interface SearchEntry {
  provider_id: string;
  name: string;
  city: string | null;
  state: string | null;
  provider_type: string;
}

export default function HomePage(): React.JSX.Element {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState<SearchEntry[]>([]);

  useEffect(() => {
    fetch("/search_index.json")
      .then((res) => res.json())
      .then((data: SearchEntry[]) => setIndex(data))
      .catch(() => {
        // Search index not available — page still renders with empty search
      });
  }, []);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    return index
      .filter(
        (entry) =>
          entry.name.toLowerCase().includes(q) ||
          entry.provider_id.includes(q) ||
          (entry.city && entry.city.toLowerCase().includes(q))
      )
      .slice(0, 30);
  }, [query, index]);

  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold text-gray-900">
        Find and Compare CMS Quality Data
      </h1>
      <p className="mb-6 text-sm leading-relaxed text-gray-600">
        CMS publishes this data to help consumers compare healthcare providers.
        This site displays it with uncertainty visible and safety measures
        surfaced prominently.
      </p>

      <div className="mb-6">
        <label htmlFor="search" className="sr-only">
          Search hospitals by name, city, or CCN
        </label>
        <input
          id="search"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search hospitals by name, city, or CCN…"
          className="w-full rounded border border-gray-300 px-4 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
        />
      </div>

      {query.trim().length >= 2 && (
        <div className="space-y-1">
          {results.length === 0 ? (
            <p className="text-sm text-gray-500">No results found.</p>
          ) : (
            results.map((entry) => {
              const route =
                entry.provider_type === "HOSPITAL"
                  ? `/hospital/${entry.provider_id}/`
                  : `/nursing-home/${entry.provider_id}/`;
              return (
                <a
                  key={entry.provider_id}
                  href={route}
                  className="flex items-baseline justify-between rounded px-3 py-2 text-sm hover:bg-gray-50"
                >
                  <span className="font-medium text-gray-900">
                    {entry.name}
                  </span>
                  <span className="ml-4 shrink-0 text-xs text-gray-500">
                    {[entry.city, entry.state].filter(Boolean).join(", ")}
                    {" · "}
                    {entry.provider_id}
                  </span>
                </a>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
