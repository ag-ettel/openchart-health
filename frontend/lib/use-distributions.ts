"use client";

// Hook to load and cache the national distribution data.
// distributions.json is loaded once on first access and cached in memory.

import { useState, useEffect } from "react";

interface DistributionData {
  counts: number[];
  bin_edges: number[];
  total: number;
  mean: number;
  median: number;
}

let cached: Record<string, DistributionData> | null = null;
let loading = false;
let listeners: Array<() => void> = [];

function notifyListeners(): void {
  for (const fn of listeners) fn();
}

async function loadDistributions(): Promise<void> {
  if (cached || loading) return;
  loading = true;
  try {
    // In dev, fetch from the build/data directory via the dev server
    // In production, this would be a static file served from the CDN
    const res = await fetch("/distributions.json");
    if (res.ok) {
      cached = await res.json();
    }
  } catch {
    // Distribution data not available — histograms won't render
  } finally {
    loading = false;
    notifyListeners();
  }
}

export function useDistribution(
  measureId: string,
  periodLabel: string
): DistributionData | null {
  const [, setTick] = useState(0);

  useEffect(() => {
    const listener = () => setTick((t) => t + 1);
    listeners.push(listener);
    loadDistributions();
    return () => {
      listeners = listeners.filter((l) => l !== listener);
    };
  }, []);

  if (!cached) return null;
  // Try exact period match first
  const key = `${measureId}|${periodLabel}`;
  const exact = cached[key];
  // Fall back to LATEST (full national distribution) when period-specific
  // is missing or has too few providers for a meaningful histogram
  if (!exact || exact.total < 100) {
    const latest = cached[`${measureId}|LATEST`];
    if (latest && latest.total >= 100) return latest;
  }
  return exact ?? null;
}
