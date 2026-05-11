import fs from "fs";
import path from "path";
import type { Metadata } from "next";
import { providerSlug } from "@/lib/utils";
import { buildHomeMetadata } from "@/lib/seo";
import { HospitalProfileClient } from "./HospitalProfileClient";

// The `[ccn]` folder name is historical; the dynamic segment now carries the
// full provider slug ({name}-{city}-{state}-{ccn}). The trailing 6-digit CCN
// is the canonical key — the client component reads it from the URL.
//
// Provider pages are CLIENT-RENDERED at runtime — the JSON data lives in R2
// and is fetched by HospitalProfileClient. The static export emits one shell
// HTML per generateStaticParams entry; public/_redirects rewrites every
// /hospital/{slug}/ URL to that shell. This trades per-provider SEO for a
// deployment that fits Cloudflare Pages' 20K file limit. See
// docs/launch_status.md for the architectural rationale.

const DATA_DIR = path.join(process.cwd(), "..", "build", "data");

interface SearchIndexEntry {
  provider_id: string;
  provider_type: string;
  name: string;
  city: string | null;
  state: string | null;
}

export function generateStaticParams(): { ccn: string }[] {
  // We always emit a "_unavailable" shell to satisfy Next.js's requirement
  // that output: "export" routes have at least one static param. When
  // build/data/ is present locally (dev / future build-time data path),
  // additionally emit per-provider slugs so links work in dev. In CI/prod
  // only the placeholder ships, and _redirects routes everything else to it.
  const params: { ccn: string }[] = [{ ccn: "_unavailable" }];
  if (!fs.existsSync(DATA_DIR)) return params;
  const indexPath = path.join(DATA_DIR, "search_index.json");
  if (fs.existsSync(indexPath)) {
    const raw = fs.readFileSync(indexPath, "utf-8");
    const entries = JSON.parse(raw) as SearchIndexEntry[];
    for (const e of entries.filter((x) => x.provider_type === "HOSPITAL")) {
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

// Provider-specific metadata isn't available at build time (data is in R2).
// Fall back to the site-level metadata so per-provider URLs still emit valid
// title/description/OG tags. Per-provider SEO is a follow-up.
export async function generateMetadata(): Promise<Metadata> {
  return buildHomeMetadata();
}

export default function HospitalPage(): React.JSX.Element {
  return <HospitalProfileClient />;
}
