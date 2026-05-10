import type { Metadata } from "next";
import { buildCompareMetadata } from "@/lib/seo";
import { ComparePageClient } from "./ComparePageClient";

export const metadata: Metadata = buildCompareMetadata();

export default function ComparePage(): React.JSX.Element {
  return <ComparePageClient />;
}
