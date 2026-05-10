// /filter-explore/nursing-home — sort and filter CMS measures across all
// nursing homes. Reuses the FilterExploreClient component with the
// nursing-home provider type. See sibling /filter-explore/page.tsx for the
// hospital variant.

import type { Metadata } from "next";
import { buildFilterExploreNursingHomeMetadata } from "@/lib/seo";
import { FilterExploreClient } from "../FilterExploreClient";

export const metadata: Metadata = buildFilterExploreNursingHomeMetadata();

export default function FilterExploreNursingHomePage(): React.JSX.Element {
  return <FilterExploreClient providerType="NURSING_HOME" />;
}
