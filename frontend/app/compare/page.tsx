"use client";

// Comparison page. The only route that fetches data at runtime.
// See .claude/rules/frontend-spec.md before implementing.

// TODO Phase 1: implement
//
// Imports needed:
//   import { useSearchParams } from "next/navigation";
//   import { useState, useEffect } from "react";
//   import type { Provider } from "@/types/provider";
//   import {
//     POPULATION_COMPARABILITY_THRESHOLD_PCT
//   } from "@/lib/constants";
//   import {
//     hasSESSensitivity,
//     compareToAverage,
//     compareProviders
//   } from "@/lib/utils";
//   import { ComparisonBadge } from "@/components/ComparisonBadge";
//
// Data fetching:
//   Read CCNs from URL search params (?a=123456&b=789012).
//   Fetch `${process.env.NEXT_PUBLIC_CDN_BASE}/${ccn}.json` for each.
//
// For each shared measure_id, display in the same row:
//   - Both hospital values with formatValue()
//   - Hospital-vs-hospital comparison via:
//       compareProviders(
//         valueA, ciLowerA, ciUpperA,
//         valueB, ciLowerB, ciUpperB,
//         direction
//       )
//     Render result as ComparisonBadge with referenceLabel set to the
//     opposing hospital's name, not a generic label.
//     Example: <ComparisonBadge result={result} referenceLabel={providerB.name} />
//   - National average for the measure with ComparisonBadge for each hospital.
//   - State average when non-null with ComparisonBadge for each hospital.
//
// Population comparability note:
//   Math.abs(
//     (a.hospital_context?.dual_eligible_proportion ?? 0) -
//     (b.hospital_context?.dual_eligible_proportion ?? 0)
//   ) > POPULATION_COMPARABILITY_THRESHOLD_PCT
//
// SESDisclosureBlock: any group with HIGH or MODERATE sensitivity measures.
// ProviderContextPanel: both hospitals, side by side, same visual plane.
// No composite score or aggregate ordering. No personalization language.

export default function ComparePage(): JSX.Element {
  return <div data-page="compare" />;
}
