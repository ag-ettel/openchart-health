// Post-build: copy public/_redirects and public/_headers into out/ explicitly.
//
// Next.js's static export does not reliably copy underscore-prefixed files
// from public/ — they get filtered as "internal" alongside _next/. Cloudflare
// Pages reads _redirects from the root of the build output for its SPA
// fallback rewrites; without this step, every /hospital/* and
// /nursing-home/* URL would 404 because no static HTML matches.
//
// Run from package.json "build" after "next build".

const fs = require("fs");
const path = require("path");

const FILES = ["_redirects", "_headers"];
const PUBLIC = path.join(__dirname, "..", "public");
const OUT = path.join(__dirname, "..", "out");

if (!fs.existsSync(OUT)) {
  console.warn(`[copy-redirects] out/ directory missing — skipping (was next build run?)`);
  process.exit(0);
}

for (const name of FILES) {
  const src = path.join(PUBLIC, name);
  const dst = path.join(OUT, name);
  if (!fs.existsSync(src)) continue;
  fs.copyFileSync(src, dst);
  const size = fs.statSync(dst).size;
  console.log(`[copy-redirects] ${name} (${size}B) -> ${path.relative(process.cwd(), dst)}`);
}
