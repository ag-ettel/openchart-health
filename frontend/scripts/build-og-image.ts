/**
 * Generates the default Open Graph image at public/og-default.png.
 *
 * The image is a neutral 1200x630 card with the site name and tagline.
 * No data, no claims — it's the social-share fallback for routes that
 * do not yet have a per-provider preview. See lib/seo.ts for where it
 * is referenced via DEFAULT_OG_IMAGE_PATH.
 *
 * Run: npm run build:og-image
 *
 * Sharp is installed as a Next.js transitive dep (used for image
 * optimization). We pull it in here directly to render the SVG.
 */

import path from "path";
import sharp from "sharp";
import {
  DEFAULT_OG_IMAGE_HEIGHT,
  DEFAULT_OG_IMAGE_WIDTH,
  SITE_NAME,
  SITE_TAGLINE,
} from "../lib/constants";

const OUTPUT_PATH = path.join(__dirname, "..", "public", "og-default.png");

const WIDTH = DEFAULT_OG_IMAGE_WIDTH;
const HEIGHT = DEFAULT_OG_IMAGE_HEIGHT;

// Neutral palette. Matches the site: white-ish background, dark gray text,
// no directional color signaling. The thin top accent uses a non-evaluative
// neutral blue (Tailwind blue-600) consistent with chart data lines.
const BG = "#ffffff";
const TEXT = "#111827"; // gray-900
const SUB_TEXT = "#4b5563"; // gray-600
const ACCENT = "#2563eb"; // blue-600 (data-line color, non-directional)
const RULE = "#e5e7eb"; // gray-200

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

// Split the tagline at a sensible word boundary for two-line wrapping.
// We don't need to be precise — we just want to avoid clipping. Looking
// for a connector word and breaking after it keeps both lines balanced.
function splitTagline(tagline: string): [string, string] {
  // Prefer to break after the first comma; otherwise fall back to roughly
  // the midpoint at a space.
  const commaIdx = tagline.indexOf(",");
  if (commaIdx !== -1 && commaIdx > 20 && commaIdx < tagline.length - 10) {
    return [tagline.slice(0, commaIdx + 1).trim(), tagline.slice(commaIdx + 1).trim()];
  }
  const mid = Math.floor(tagline.length / 2);
  let breakAt = tagline.indexOf(" ", mid);
  if (breakAt === -1) breakAt = tagline.lastIndexOf(" ", mid);
  if (breakAt === -1) return [tagline, ""];
  return [tagline.slice(0, breakAt).trim(), tagline.slice(breakAt + 1).trim()];
}

function buildSvg(): string {
  const padding = 88;
  const accentHeight = 8;
  const titleY = 280;
  const taglineY1 = 360;
  const taglineY2 = 410;
  const footerY = HEIGHT - padding;
  const [taglineLine1, taglineLine2] = splitTagline(SITE_TAGLINE);

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}">
  <rect width="${WIDTH}" height="${HEIGHT}" fill="${BG}"/>
  <rect x="0" y="0" width="${WIDTH}" height="${accentHeight}" fill="${ACCENT}"/>
  <line x1="${padding}" y1="${footerY - 60}" x2="${WIDTH - padding}" y2="${footerY - 60}" stroke="${RULE}" stroke-width="1"/>
  <text x="${padding}" y="${titleY}" fill="${TEXT}"
        font-family="Inter, Arial, sans-serif" font-size="84" font-weight="700"
        letter-spacing="-1.5">${escapeXml(SITE_NAME)}</text>
  <text x="${padding}" y="${taglineY1}" fill="${SUB_TEXT}"
        font-family="Inter, Arial, sans-serif" font-size="34" font-weight="400">${escapeXml(taglineLine1)}</text>
  <text x="${padding}" y="${taglineY2}" fill="${SUB_TEXT}"
        font-family="Inter, Arial, sans-serif" font-size="34" font-weight="400">${escapeXml(taglineLine2)}</text>
  <text x="${padding}" y="${footerY}" fill="${SUB_TEXT}"
        font-family="Inter, Arial, sans-serif" font-size="22" font-weight="500"
        letter-spacing="0.5">SOURCE: CENTERS FOR MEDICARE &amp; MEDICAID SERVICES</text>
</svg>`;
}

async function main(): Promise<void> {
  const svg = buildSvg();
  await sharp(Buffer.from(svg, "utf-8"))
    .png()
    .toFile(OUTPUT_PATH);
  // eslint-disable-next-line no-console
  console.log(`OG image written: ${OUTPUT_PATH} (${WIDTH}x${HEIGHT})`);
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});
