"use client";

// Research tool. Deferred to post-hospital-launch build phase.
// See .claude/rules/frontend-spec.md before implementing.
//
// This page is a filter-and-explore tool, not a leaderboard. // compliance-ok
// Do not implement until the hospital build is running in production
// and the pipeline is generating build/data/filterexplore_index.json.
//
// When implementing, the following are non-negotiable:
//   - DisclaimerBanner at the top.
//   - Page title and description must not use "top," "best," "ranked,"
//     or superlative language of any kind.
//   - Sorting on a measure column is permitted. The sorted view must
//     display the measure's ComparisonResult (national average) alongside
//     each value so the sort context is statistically grounded.
//   - Filtering is permitted by: state, urban_rural_classification,
//     is_critical_access, is_teaching_hospital, provider_subtype.
//   - No composite or aggregate score column.
//   - Each hospital name links to /hospital/[ccn], not to an inline expand.
//   - Data source is build/data/filterexplore_index.json (pipeline output).

export default function FilterExplorePage(): JSX.Element {
  return <div data-page="filter-explore-deferred" />;
}
