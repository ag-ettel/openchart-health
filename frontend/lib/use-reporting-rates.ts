"use client";

// Hook to load and cache national reporting rates per measure.
// reporting_rates.json is loaded once on first access and cached in memory.
// Same fetch/cache pattern as use-distributions.ts.

import { useState, useEffect } from "react";

export interface ReportingRate {
  reported: number;
  suppressed: number;
  not_reported: number;
  /** Hospitals where CMS has a row for this measure (excludes non-participating types). */
  eligible_hospitals: number;
  pct_reported: number;
  period_label: string;
}

let cached: Record<string, ReportingRate> | null = null;
let loading = false;
let listeners: Array<() => void> = [];

function notifyListeners(): void {
  for (const fn of listeners) fn();
}

async function loadReportingRates(): Promise<void> {
  if (cached || loading) return;
  loading = true;
  try {
    const res = await fetch("/reporting_rates.json");
    if (res.ok) {
      cached = await res.json();
    }
  } catch {
    // Reporting rate data not available — cards render without it
  } finally {
    loading = false;
    notifyListeners();
  }
}

/** Look up a single measure's reporting rate. */
export function useReportingRate(measureId: string): ReportingRate | null {
  const [, setTick] = useState(0);

  useEffect(() => {
    const listener = () => setTick((t) => t + 1);
    listeners.push(listener);
    loadReportingRates();
    return () => {
      listeners = listeners.filter((l) => l !== listener);
    };
  }, []);

  if (!cached) return null;
  return cached[measureId] ?? null;
}

/** Return the full reporting rates map (for bulk lookups). */
export function useReportingRates(): Record<string, ReportingRate> | null {
  const [, setTick] = useState(0);

  useEffect(() => {
    const listener = () => setTick((t) => t + 1);
    listeners.push(listener);
    loadReportingRates();
    return () => {
      listeners = listeners.filter((l) => l !== listener);
    };
  }, []);

  return cached;
}
