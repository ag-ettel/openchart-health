import fs from "fs";
import path from "path";
import type { Metadata } from "next";
import { providerSlug } from "@/lib/utils";
import { buildHomeMetadata } from "@/lib/seo";
import { NHProfileClient } from "./NHProfileClient";

// Provider pages are CLIENT-RENDERED at runtime — see HospitalProfileClient
// for rationale. The static export emits one shell HTML per
// generateStaticParams entry; public/_redirects rewrites every
// /nursing-home/{slug}/ URL to that shell.

const DATA_DIR = path.join(process.cwd(), "..", "build", "data");

interface SearchIndexEntry {
  provider_id: string;
  provider_type: string;
  name: string;
  city: string | null;
  state: string | null;
}

export function generateStaticParams(): { ccn: string }[] {
  const params: { ccn: string }[] = [{ ccn: "_unavailable" }];
  if (!fs.existsSync(DATA_DIR)) return params;
  const indexPath = path.join(DATA_DIR, "search_index.json");
  if (fs.existsSync(indexPath)) {
    const raw = fs.readFileSync(indexPath, "utf-8");
    const entries = JSON.parse(raw) as SearchIndexEntry[];
    for (const e of entries.filter((x) => x.provider_type === "NURSING_HOME")) {
      params.push({ ccn: providerSlug(e.name, e.city, e.state, e.provider_id) });
    }
    return params;
  }
  for (const f of fs.readdirSync(DATA_DIR)) {
    if (!f.endsWith(".json") || f === "search_index.json") continue;
    params.push({ ccn: f.replace(/\.json$/, "") });
  }
  return params;
}

export async function generateMetadata(): Promise<Metadata> {
  return buildHomeMetadata();
}

export default function NursingHomePage(): React.JSX.Element {
  return <NHProfileClient />;
}
