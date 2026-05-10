/**
 * Builds a lightweight search index from exported provider JSON files.
 *
 * Outputs:
 *   build/data/search_index.json    — read by sitemap.ts at build time
 *   frontend/public/search_index.json — fetched by HomeSearch / ComparePage clients at /search_index.json
 *
 * Run: npx tsx scripts/build-search-index.ts
 * Or:  npm run build:search-index
 *
 * The search index contains only the fields needed for the home page search:
 * provider_id, name, city, state, provider_type. No measure data.
 */

import fs from "fs";
import path from "path";

interface SearchEntry {
  provider_id: string;
  name: string;
  city: string | null;
  state: string | null;
  provider_type: string;
}

const DATA_DIR = path.join(__dirname, "..", "..", "build", "data");
const PUBLIC_DIR = path.join(__dirname, "..", "public");

function main(): void {
  const files = fs.readdirSync(DATA_DIR).filter((f) => {
    return f.endsWith(".json") && f !== "search_index.json";
  });

  const entries: SearchEntry[] = [];

  let skipped = 0;
  for (const file of files) {
    const filePath = path.join(DATA_DIR, file);
    try {
      const raw = fs.readFileSync(filePath, "utf-8");
      const provider = JSON.parse(raw);
      if (!provider.provider_id) {
        skipped++;
        continue;
      }
      entries.push({
        provider_id: provider.provider_id,
        name: provider.name ?? provider.provider_id,
        city: provider.address?.city ?? null,
        state: provider.address?.state ?? null,
        provider_type: provider.provider_type,
      });
    } catch {
      skipped++;
    }
  }

  // Sort by name for stable output. Defensive: a provider with a null/missing
  // name would crash localeCompare. Push those to the end deterministically.
  entries.sort((a, b) => {
    const an = a.name ?? "";
    const bn = b.name ?? "";
    return an.localeCompare(bn);
  });

  const payload = JSON.stringify(entries);
  const dataPath = path.join(DATA_DIR, "search_index.json");
  const publicPath = path.join(PUBLIC_DIR, "search_index.json");
  fs.writeFileSync(dataPath, payload, "utf-8");
  fs.writeFileSync(publicPath, payload, "utf-8");

  console.log(
    `Search index built: ${entries.length} providers (${skipped} skipped) → ${dataPath} and ${publicPath}`
  );
}

main();
