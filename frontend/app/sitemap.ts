// Sitemap generator. Emitted at build time by Next.js as /sitemap.xml.
// Compatible with output: "export" — runs during the build step.
//
// Static routes are listed explicitly. Provider profile routes are derived
// from search_index.json when present (one read, fast); otherwise we fall
// back to scanning build/data/*.json directly so the sitemap is correct
// even before the pipeline emits the search index.
//
// Note: a single sitemap can hold up to 50,000 URLs per the spec. We're
// under that today (~22K providers); when the catalog grows we should
// switch to a sitemap index via Next's generateSitemaps export.

import fs from "fs";
import path from "path";
import type { MetadataRoute } from "next";
import { getSiteUrl } from "@/lib/seo";
import { providerSlug } from "@/lib/utils";

// Required by Next.js output: "export" for non-page route handlers.
export const dynamic = "force-static";

const DATA_DIR = path.join(process.cwd(), "..", "build", "data");
const SEARCH_INDEX_PATH = path.join(DATA_DIR, "search_index.json");

interface ProviderRow {
  provider_id: string;
  provider_type: string;
  name: string;
  city: string | null;
  state: string | null;
  last_updated: Date;
}

interface SearchEntry {
  provider_id: string;
  provider_type: string;
  name?: string;
  city?: string | null;
  state?: string | null;
  last_updated?: string;
}

function tryLoadSearchIndex(): ProviderRow[] | null {
  try {
    if (!fs.existsSync(SEARCH_INDEX_PATH)) return null;
    const raw = fs.readFileSync(SEARCH_INDEX_PATH, "utf-8");
    const entries = JSON.parse(raw) as SearchEntry[];
    if (!Array.isArray(entries) || entries.length === 0) return null;
    return entries.map((e) => ({
      provider_id: e.provider_id,
      provider_type: e.provider_type,
      name: e.name ?? e.provider_id,
      city: e.city ?? null,
      state: e.state ?? null,
      last_updated: e.last_updated ? new Date(e.last_updated) : new Date(),
    }));
  } catch {
    return null;
  }
}

// Partial read: each provider JSON starts with `{"provider_id": "...",
// "provider_type": "...", ...}`. Reading the first 256 bytes is enough to
// pull both fields via regex and avoids JSON.parse on 22K+ files (which
// pushes the build past Next's 60s static-route timeout). lastmod comes
// from file mtime — close enough for sitemap purposes.

// Need enough bytes to also pull the nested address.{city,state} for slug
// generation in the fallback path. The provider header is small; 512 is plenty.
const HEAD_READ_BYTES = 512;
const PROVIDER_ID_RE = /"provider_id"\s*:\s*"([^"]+)"/;
const PROVIDER_TYPE_RE = /"provider_type"\s*:\s*"([^"]+)"/;
const NAME_RE = /"name"\s*:\s*"([^"]+)"/;
const CITY_RE = /"city"\s*:\s*"([^"]+)"/;
const STATE_RE = /"state"\s*:\s*"([^"]+)"/;

function readHead(filePath: string, bytes: number): string | null {
  let fd: number | null = null;
  try {
    fd = fs.openSync(filePath, "r");
    const buf = Buffer.alloc(bytes);
    const n = fs.readSync(fd, buf, 0, bytes, 0);
    return buf.toString("utf-8", 0, n);
  } catch {
    return null;
  } finally {
    if (fd !== null) {
      try { fs.closeSync(fd); } catch { /* best-effort */ }
    }
  }
}

const SKIPPED_FILENAMES = new Set([
  "search_index.json",
  "ownership_entity_index.json",
  "filterexplore_index.json",
]);

function scanDataDir(): ProviderRow[] {
  if (!fs.existsSync(DATA_DIR)) return [];
  const rows: ProviderRow[] = [];
  for (const entry of fs.readdirSync(DATA_DIR)) {
    if (!entry.endsWith(".json")) continue;
    if (SKIPPED_FILENAMES.has(entry)) continue;
    const full = path.join(DATA_DIR, entry);
    const head = readHead(full, HEAD_READ_BYTES);
    if (!head) continue;
    const idMatch = PROVIDER_ID_RE.exec(head);
    const typeMatch = PROVIDER_TYPE_RE.exec(head);
    if (!idMatch || !typeMatch) continue;
    const nameMatch = NAME_RE.exec(head);
    const cityMatch = CITY_RE.exec(head);
    const stateMatch = STATE_RE.exec(head);
    let mtime: Date;
    try {
      mtime = fs.statSync(full).mtime;
    } catch {
      mtime = new Date();
    }
    rows.push({
      provider_id: idMatch[1],
      provider_type: typeMatch[1],
      name: nameMatch ? nameMatch[1] : idMatch[1],
      city: cityMatch ? cityMatch[1] : null,
      state: stateMatch ? stateMatch[1] : null,
      last_updated: mtime,
    });
  }
  return rows;
}

function loadProviders(): ProviderRow[] {
  return tryLoadSearchIndex() ?? scanDataDir();
}

function dataDirMtime(): Date {
  try {
    return fs.statSync(DATA_DIR).mtime;
  } catch {
    return new Date();
  }
}

export default function sitemap(): MetadataRoute.Sitemap {
  const base = getSiteUrl();
  const lastDataMtime = dataDirMtime();
  const now = new Date();

  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: `${base}/`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${base}/methodology/`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${base}/compare/`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.6,
    },
  ];

  const rows = loadProviders();
  const providerRoutes: MetadataRoute.Sitemap = rows.map((row) => {
    const segment = row.provider_type === "NURSING_HOME" ? "nursing-home" : "hospital";
    const slug = providerSlug(row.name, row.city, row.state, row.provider_id);
    const lastModified = isNaN(row.last_updated.getTime()) ? lastDataMtime : row.last_updated;
    return {
      url: `${base}/${segment}/${slug}/`,
      lastModified,
      changeFrequency: "monthly" as const,
      priority: 0.5,
    };
  });

  return [...staticRoutes, ...providerRoutes];
}
