"use client";

// Client-side provider search.
// Reads from /search_index.json (built by scripts/build-search-index.ts).

import { useState, useMemo, useEffect } from "react";
import { providerSlug } from "@/lib/utils";

interface SearchEntry {
  provider_id: string;
  name: string;
  city: string | null;
  state: string | null;
  provider_type: string;
}

export function HomeSearch(): React.JSX.Element {
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
    <>
      <div className="mb-6">
        <label htmlFor="search" className="sr-only">
          Search hospitals and nursing homes by name, city, or CCN
        </label>
        <input
          id="search"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search hospitals and nursing homes by name, city, or CCN…"
          className="w-full rounded border border-gray-300 px-4 py-2 text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 focus:border-blue-500"
        />
      </div>

      {query.trim().length >= 2 && (
        <div className="space-y-1">
          {results.length === 0 ? (
            <p className="text-sm text-gray-500">No results found.</p>
          ) : (
            results.map((entry) => {
              const slug = providerSlug(
                entry.name,
                entry.city,
                entry.state,
                entry.provider_id
              );
              const route =
                entry.provider_type === "HOSPITAL"
                  ? `/hospital/${slug}/`
                  : `/nursing-home/${slug}/`;
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
    </>
  );
}
