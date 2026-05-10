"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import type { DirectoryEntry } from "@/types/directory";
import type { DirectoryEntryWithDistance } from "@/lib/geo";
import { sortByDistance } from "@/lib/geo";
import { titleCase } from "@/lib/utils";
import {
  compareNearbyOpened,
  compareNearbyResultClicked,
} from "@/lib/analytics";

const MAX_NEARBY_RESULTS = 20;
const MAX_SEARCH_RESULTS = 30;
const MIN_SEARCH_LENGTH = 2;
const NEARBY_MAX_DISTANCE_MI = 100;
const NEARBY_MIN_RESULTS = 3;

type Slot = "a" | "b";

/** Format distance with appropriate precision. */
function formatDistance(miles: number): string {
  if (miles < 1) return "<1 mi";
  if (miles < 10) return `${miles.toFixed(1)} mi`;
  return `${Math.round(miles)} mi`;
}

interface CompareNearbyDrawerProps {
  currentCcn: string;
  currentName: string;
  providerType: string;
}

/** Provider-type-aware display labels. */
function typeLabels(providerType: string): {
  singular: string;       // "Hospital" or "Nursing Home"
  plural: string;         // "Hospitals" or "Nursing Homes"
  pluralLower: string;    // "hospitals" or "nursing homes"
  upperSingular: string;  // "HOSPITAL" or "NURSING HOME" (slot pill heading)
} {
  switch (providerType) {
    case "NURSING_HOME":
      return { singular: "Nursing Home", plural: "Nursing Homes", pluralLower: "nursing homes", upperSingular: "NURSING HOME" };
    case "HOME_HEALTH":
      return { singular: "Home Health Agency", plural: "Home Health Agencies", pluralLower: "home health agencies", upperSingular: "HOME HEALTH" };
    case "HOSPICE":
      return { singular: "Hospice", plural: "Hospices", pluralLower: "hospices", upperSingular: "HOSPICE" };
    case "HOSPITAL":
    default:
      return { singular: "Hospital", plural: "Hospitals", pluralLower: "hospitals", upperSingular: "HOSPITAL" };
  }
}

export function CompareNearbyDrawer({
  currentCcn,
  currentName,
  providerType,
}: CompareNearbyDrawerProps) {
  const labels = typeLabels(providerType);
  const [open, setOpen] = useState(false);
  const [directory, setDirectory] = useState<DirectoryEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  // Track whether we've already fired the open analytics event this session
  // — drawer opens repeatedly through a session and we only want the first.
  const hasTrackedOpenRef = useRef(false);

  // Slot state: which providers are selected for A and B
  const [slotA, setSlotA] = useState<DirectoryEntry | null>(null);
  const [slotB, setSlotB] = useState<DirectoryEntry | null>(null);
  const [selectingSlot, setSelectingSlot] = useState<Slot>("b");

  // Determine if A is locked (on a hospital page, A = current hospital)
  const isOnComparePage = typeof window !== "undefined" && window.location.pathname.startsWith("/compare");
  const slotALocked = !isOnComparePage;

  // Fetch directory on first open
  const fetchDirectory = useCallback(async () => {
    if (directory !== null) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/data/provider_directory.json");
      if (!res.ok) throw new Error(`Failed to load provider directory (${res.status})`);
      const data: DirectoryEntry[] = await res.json();
      setDirectory(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load provider directory");
    } finally {
      setLoading(false);
    }
  }, [directory]);

  // Initialize slots from URL params + current provider when directory loads
  useEffect(() => {
    if (!directory) return;

    const currentEntry = directory.find((e) => e.id === currentCcn) ?? null;

    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const aCcn = params.get("a");
      const bCcn = params.get("b");

      if (aCcn) {
        const aEntry = directory.find((e) => e.id === aCcn) ?? null;
        if (aEntry) setSlotA(aEntry);
        else if (currentEntry) setSlotA(currentEntry);
      } else if (currentEntry) {
        setSlotA(currentEntry);
      }

      if (bCcn) {
        const bEntry = directory.find((e) => e.id === bCcn) ?? null;
        if (bEntry) setSlotB(bEntry);
      }
    } else if (currentEntry) {
      setSlotA(currentEntry);
    }
  }, [directory, currentCcn]);

  useEffect(() => {
    if (open) {
      fetchDirectory();
      // User action: clicked the "Compare" trigger to open the drawer.
      // Fires once per page session — guarded by hasTrackedOpenRef so
      // re-opens after dismissal do not double-count.
      if (!hasTrackedOpenRef.current) {
        hasTrackedOpenRef.current = true;
        compareNearbyOpened({
          originCcn: currentCcn,
          providerType,
        });
      }
    }
  }, [open, fetchDirectory, currentCcn, providerType]);

  // Focus search input when drawer opens and data is loaded
  useEffect(() => {
    if (open && !loading && directory !== null) {
      const t = setTimeout(() => inputRef.current?.focus(), 100);
      return () => clearTimeout(t);
    }
  }, [open, loading, directory]);

  // Origin for distance calculation: use whichever slot is NOT being selected
  const referenceEntry = selectingSlot === "b" ? slotA : slotB;
  const originLat = referenceEntry?.lat ?? null;
  const originLon = referenceEntry?.lon ?? null;

  // Filter to same provider type, exclude both selected providers
  const excluded = useMemo(() => {
    const set = new Set<string>();
    if (slotA) set.add(slotA.id);
    if (slotB) set.add(slotB.id);
    return set;
  }, [slotA, slotB]);

  const sameType = useMemo(
    () => directory?.filter((e) => e.t === providerType && !excluded.has(e.id)) ?? [],
    [directory, providerType, excluded],
  );

  // Compute results
  let results: Array<DirectoryEntry & { distanceMiles?: number }> = [];
  const isSearching = query.length >= MIN_SEARCH_LENGTH;

  if (isSearching) {
    const q = query.toLowerCase();
    const matched = sameType.filter(
      (e) =>
        e.n.toLowerCase().includes(q) ||
        (e.c !== null && e.c.toLowerCase().includes(q)) ||
        e.id.startsWith(q),
    );

    if (originLat !== null && originLon !== null) {
      const withDist = sortByDistance(matched, originLat, originLon);
      const withoutCoords = matched
        .filter((e) => e.lat === null || e.lon === null)
        .map((e) => ({ ...e, distanceMiles: undefined }));
      results = [...withDist, ...withoutCoords].slice(0, MAX_SEARCH_RESULTS);
    } else {
      results = matched.slice(0, MAX_SEARCH_RESULTS);
    }
  } else if (originLat !== null && originLon !== null) {
    const sorted = sortByDistance(sameType, originLat, originLon);
    const withinRange = sorted.filter(
      (e, i) => i < NEARBY_MIN_RESULTS || e.distanceMiles <= NEARBY_MAX_DISTANCE_MI,
    );
    results = withinRange.slice(0, MAX_NEARBY_RESULTS);
  } else {
    // No coordinates: show same-state alphabetically
    const state = (slotA ?? slotB)?.s ?? null;
    const sameState = state
      ? sameType.filter((e) => e.s === state)
      : sameType;
    results = [...sameState]
      .sort((a, b) => a.n.localeCompare(b.n))
      .slice(0, MAX_NEARBY_RESULTS);
  }

  const hasCoordinates = originLat !== null && originLon !== null;

  // When user selects a provider from the list
  function handleSelect(entry: DirectoryEntry) {
    // User action: clicked a result row in the nearby drawer to fill a slot.
    // Logs the origin CCN (current page) and the selected CCN — both public
    // CMS identifiers. Distance is derived from zip-code centroids; null
    // when the entry has no coordinates.
    const distanceMiles =
      (entry as DirectoryEntryWithDistance).distanceMiles ?? null;
    compareNearbyResultClicked({
      originCcn: currentCcn,
      selectedCcn: entry.id,
      distanceMiles,
    });

    if (selectingSlot === "a") {
      setSlotA(entry);
      // If B is empty, auto-advance to selecting B
      if (!slotB) setSelectingSlot("b");
    } else {
      setSlotB(entry);
    }
    setQuery("");

    // If both slots are now filled, navigate
    const newA = selectingSlot === "a" ? entry : slotA;
    const newB = selectingSlot === "b" ? entry : slotB;
    if (newA && newB) {
      window.location.href = `/compare?a=${newA.id}&b=${newB.id}`;
    }
  }

  // Slot display component
  function SlotPill({ slot, entry, locked }: { slot: Slot; entry: DirectoryEntry | null; locked: boolean }) {
    const isActive = selectingSlot === slot;
    const label = slot === "a" ? "A" : "B";

    if (!entry) {
      return (
        <button
          type="button"
          onClick={() => !locked && setSelectingSlot(slot)}
          className={`flex-1 min-w-0 rounded-lg border-2 border-dashed px-3 py-2.5 text-left transition-colors ${
            isActive
              ? "border-blue-300 bg-blue-50"
              : "border-gray-200 bg-gray-50 hover:border-gray-300"
          }`}
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">
            {labels.upperSingular} {label}
          </p>
          <p className="mt-0.5 text-xs text-gray-400">
            {isActive ? "Select below..." : "Tap to select"}
          </p>
        </button>
      );
    }

    return (
      <div
        className={`flex-1 min-w-0 rounded-lg border-2 px-3 py-2.5 transition-colors ${
          isActive ? "border-blue-400 bg-blue-50" : "border-gray-200 bg-white"
        }`}
      >
        <div className="flex items-start justify-between gap-1">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">
              {labels.upperSingular} {label}
            </p>
            <p className="mt-0.5 truncate text-sm font-medium text-gray-900">
              {titleCase(entry.n)}
            </p>
            <p className="truncate text-xs text-gray-500">
              {[entry.c ? titleCase(entry.c) : null, entry.s].filter(Boolean).join(", ")}
            </p>
          </div>
          {!locked && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (slot === "a") setSlotA(null);
                else setSlotB(null);
                setSelectingSlot(slot);
              }}
              className="mt-1 shrink-0 rounded p-0.5 text-gray-300 hover:text-gray-500 hover:bg-gray-100"
              aria-label={`Change ${labels.singular.toLowerCase()} ${label}`}
              title="Change"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>
    );
  }

  const listHeading = isSearching
    ? `Results for "${query}"`
    : hasCoordinates
      ? `Nearby — select ${labels.singular} ${selectingSlot.toUpperCase()}`
      : `${labels.plural} in ${(slotA ?? slotB)?.s ?? "your state"}`;

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className="shrink-0 inline-flex items-center gap-1.5 rounded-md border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-600 shadow-sm hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 transition-colors"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
            />
          </svg>
          Compare
        </button>
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30 transition-opacity" />
        <Dialog.Content className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-white shadow-xl flex flex-col transition-transform duration-200 ease-out">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
            <Dialog.Title className="text-base font-semibold text-gray-900">
              Compare {labels.plural}
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                className="rounded-md p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                aria-label="Close"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </Dialog.Close>
          </div>

          {/* Slot picker — always visible */}
          <div className="border-b border-gray-200 bg-gray-50 px-4 py-3">
            <div className="flex gap-2">
              <SlotPill slot="a" entry={slotA} locked={slotALocked} />
              {/* Swap button */}
              {slotA && slotB && (
                <button
                  type="button"
                  onClick={() => {
                    if (slotALocked) return;
                    const tmp = slotA;
                    setSlotA(slotB);
                    setSlotB(tmp);
                  }}
                  disabled={slotALocked}
                  className="self-center shrink-0 rounded-full border border-gray-200 bg-white p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  aria-label={`Swap ${labels.pluralLower}`}
                  title="Swap"
                >
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                  </svg>
                </button>
              )}
              <SlotPill slot="b" entry={slotB} locked={false} />
            </div>
            {/* Go button when both slots filled */}
            {slotA && slotB && (
              <a
                href={`/compare?a=${slotA.id}&b=${slotB.id}`}
                className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              >
                Compare these {labels.pluralLower}
              </a>
            )}
          </div>

          {/* Search input */}
          <div className="px-4 py-3 border-b border-gray-100">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
              </svg>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name, city, or CCN..."
                className="w-full rounded-md border border-gray-200 py-2 pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Results */}
          <div className="flex-1 overflow-y-auto">
            {loading && (
              <div className="px-4 py-8 text-center text-sm text-gray-500" role="status" aria-live="polite">
                Loading providers...
              </div>
            )}

            {error && (
              <div className="px-4 py-8 text-center text-sm text-amber-700" role="alert" aria-live="assertive">
                {error}
              </div>
            )}

            {!loading && !error && directory !== null && (
              <>
                <div className="px-4 pt-3 pb-1">
                  <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500">
                    {listHeading}
                  </h3>
                  {!hasCoordinates && !isSearching && (
                    <p className="mt-1 text-xs text-gray-400">
                      Showing {labels.pluralLower} in {(slotA ?? slotB)?.s ?? "your state"}
                    </p>
                  )}
                </div>

                {results.length === 0 && (
                  <div className="px-4 py-6 text-center text-sm text-gray-500">
                    No matching {labels.pluralLower} found.
                  </div>
                )}

                <ul className="divide-y divide-gray-100">
                  {results.map((entry) => {
                    const dist = (entry as DirectoryEntryWithDistance).distanceMiles;
                    const locationParts: string[] = [];
                    if (entry.c) locationParts.push(titleCase(entry.c));
                    if (entry.s) locationParts.push(entry.s);
                    const locationStr = locationParts.join(", ");

                    return (
                      <li key={entry.id}>
                        <button
                          type="button"
                          onClick={() => handleSelect(entry)}
                          className="block w-full px-4 py-3 text-left hover:bg-blue-50 transition-colors"
                        >
                          <p className="text-sm font-medium text-gray-900">
                            {titleCase(entry.n)}
                          </p>
                          <p className="mt-0.5 text-xs text-gray-500">
                            {locationStr}
                            {dist !== undefined && (
                              <span className="ml-1">
                                &middot; ~{formatDistance(dist)}
                              </span>
                            )}
                          </p>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </>
            )}
          </div>

          {/* Footer note */}
          <div className="border-t border-gray-100 px-4 py-2">
            <p className="text-[11px] text-gray-400">
              Distances are approximate, based on zip code area centroids.
            </p>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
