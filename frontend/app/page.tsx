import type { Metadata } from "next";
import { HomeSearch } from "./HomeSearch";
import { HOME_INTRO_TEXT, HOME_TITLE_BASE } from "@/lib/constants";
import { buildHomeMetadata } from "@/lib/seo";

export const metadata: Metadata = buildHomeMetadata();

export default function HomePage(): React.JSX.Element {
  return (
    <div>
      <h1 className="mb-2 text-xl font-semibold text-gray-900">
        {HOME_TITLE_BASE}
      </h1>
      <p className="mb-6 text-sm leading-relaxed text-gray-600">
        {HOME_INTRO_TEXT}
      </p>

      <HomeSearch />
    </div>
  );
}
