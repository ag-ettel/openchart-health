/**
 * Builds a lightweight search index from exported provider JSON files.
 * Output: build/data/search_index.json
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

function main(): void {
  const files = fs.readdirSync(DATA_DIR).filter((f) => {
    return f.endsWith(".json") && f !== "search_index.json";
  });

  const entries: SearchEntry[] = [];

  for (const file of files) {
    const filePath = path.join(DATA_DIR, file);
    const raw = fs.readFileSync(filePath, "utf-8");
    const provider = JSON.parse(raw);

    entries.push({
      provider_id: provider.provider_id,
      name: provider.name,
      city: provider.address?.city ?? null,
      state: provider.address?.state ?? null,
      provider_type: provider.provider_type,
    });
  }

  // Sort by name for stable output
  entries.sort((a, b) => a.name.localeCompare(b.name));

  const outputPath = path.join(DATA_DIR, "search_index.json");
  fs.writeFileSync(outputPath, JSON.stringify(entries), "utf-8");

  console.log(`Search index built: ${entries.length} providers → ${outputPath}`);
}

main();
