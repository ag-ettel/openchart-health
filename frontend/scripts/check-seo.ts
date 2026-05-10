/**
 * SEO QA helper. Sanity check on the static export at out/.
 *
 * Run after `next build` completes (output: "export"):
 *   npx tsx scripts/check-seo.ts
 *   npm run seo-check
 *
 * Verifies that every emitted index.html has:
 *   - <title>
 *   - <meta name="description">
 *   - <link rel="canonical">
 * Flags titles > 60 chars or descriptions > 160 chars (search-engine truncation).
 *
 * Exit code 0 = clean, 1 = issues found. This is a sanity check, not a strict gate.
 */

import fs from "fs";
import path from "path";

const OUT_DIR = path.join(__dirname, "..", "out");
const TITLE_MAX = 60;
const DESCRIPTION_MAX = 160;

interface Issue {
  file: string;
  rule: string;
  detail: string;
}

function walk(dir: string, acc: string[] = []): string[] {
  if (!fs.existsSync(dir)) return acc;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, acc);
    } else if (entry.isFile() && entry.name === "index.html") {
      acc.push(full);
    }
  }
  return acc;
}

function extractTitle(html: string): string | null {
  const m = html.match(/<title[^>]*>([^<]*)<\/title>/i);
  return m ? m[1].trim() : null;
}

function extractMetaDescription(html: string): string | null {
  const m = html.match(
    /<meta[^>]+name=["']description["'][^>]*content=["']([^"']*)["'][^>]*>/i,
  );
  if (m) return m[1].trim();
  const m2 = html.match(
    /<meta[^>]+content=["']([^"']*)["'][^>]+name=["']description["'][^>]*>/i,
  );
  return m2 ? m2[1].trim() : null;
}

function extractCanonical(html: string): string | null {
  const m = html.match(
    /<link[^>]+rel=["']canonical["'][^>]*href=["']([^"']+)["'][^>]*>/i,
  );
  if (m) return m[1].trim();
  const m2 = html.match(
    /<link[^>]+href=["']([^"']+)["'][^>]+rel=["']canonical["'][^>]*>/i,
  );
  return m2 ? m2[1].trim() : null;
}

function main(): void {
  if (!fs.existsSync(OUT_DIR)) {
    console.error(
      `out/ directory not found at ${OUT_DIR}. Run \`next build\` first.`,
    );
    process.exit(1);
  }

  const files = walk(OUT_DIR);
  const issues: Issue[] = [];
  let scanned = 0;

  for (const file of files) {
    const rel = path.relative(OUT_DIR, file);
    // 404 pages don't need canonical and use the site default description.
    if (rel.startsWith("404")) continue;
    scanned += 1;
    const html = fs.readFileSync(file, "utf-8");

    const title = extractTitle(html);
    const description = extractMetaDescription(html);
    const canonical = extractCanonical(html);

    if (!title) {
      issues.push({ file: rel, rule: "missing-title", detail: "no <title>" });
    } else if (title.length > TITLE_MAX) {
      issues.push({
        file: rel,
        rule: "title-too-long",
        detail: `${title.length} chars > ${TITLE_MAX}: ${title}`,
      });
    }

    if (!description) {
      issues.push({
        file: rel,
        rule: "missing-description",
        detail: "no <meta name=description>",
      });
    } else if (description.length > DESCRIPTION_MAX) {
      issues.push({
        file: rel,
        rule: "description-too-long",
        detail: `${description.length} chars > ${DESCRIPTION_MAX}: ${description}`,
      });
    }

    if (!canonical) {
      issues.push({
        file: rel,
        rule: "missing-canonical",
        detail: "no <link rel=canonical>",
      });
    }
  }

  console.log(`Scanned ${scanned} index.html files in out/`);
  if (issues.length === 0) {
    console.log("SEO check passed. All pages have title, description, canonical.");
    process.exit(0);
  }

  // Group by rule for easier reading
  const byRule = new Map<string, Issue[]>();
  for (const issue of issues) {
    const arr = byRule.get(issue.rule) ?? [];
    arr.push(issue);
    byRule.set(issue.rule, arr);
  }
  for (const [rule, arr] of byRule.entries()) {
    console.warn(`\n[${rule}] ${arr.length} occurrence(s):`);
    for (const issue of arr.slice(0, 10)) {
      console.warn(`  ${issue.file}: ${issue.detail}`);
    }
    if (arr.length > 10) {
      console.warn(`  …and ${arr.length - 10} more`);
    }
  }
  console.warn(`\nSEO check found ${issues.length} issue(s).`);
  process.exit(1);
}

main();
