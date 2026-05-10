// /filter-explore — sort and filter CMS measures across all hospitals.
//
// This is a research and exploration tool, not a leaderboard. // compliance-ok
// Users select a measure, see all hospitals that report it, and sort/filter
// the list. The user controls sort order — the tool does not editorialize
// which end matters.
//
// See:
//   .claude/rules/legal-compliance.md § Positioning (sort/filter constraints)
//   .claude/rules/frontend-spec.md (filter-explore positioning notes)
//   .claude/rules/data-integrity.md (suppression, footnotes, periods, samples)
//
// The page is a thin server-component shell that renders a client component.
// All filtering, sorting, and data fetching happens client-side because the
// per-measure index files (one per measure_id) are too large to embed.

import type { Metadata } from "next";
import { buildFilterExploreMetadata } from "@/lib/seo";
import { FilterExploreClient } from "./FilterExploreClient";

export const metadata: Metadata = buildFilterExploreMetadata();

export default function FilterExplorePage(): React.JSX.Element {
  return <FilterExploreClient providerType="HOSPITAL" />;
}
