/**
 * Generates the favicon, Apple touch icon, and web manifest icons.
 *
 * Output (all in public/, referenced explicitly via lib/seo.ts metadata):
 *   public/favicon-32.png       (32x32)   — browser favicon
 *   public/apple-touch-icon.png (180x180) — iOS home-screen icon
 *   public/icon-192.png         (192x192) — web manifest icon
 *   public/icon-512.png         (512x512) — web manifest icon
 *
 * Run: npm run build:icons
 *
 * The icon is a solid blue rounded square with a bold white "O"
 * monogram. Blue (#2563eb) matches the data-line accent color used
 * elsewhere on the site — non-directional per DEC-030.
 *
 * NOTE: icons are NOT placed in app/ (Next.js App Router convention)
 * because that path triggers a Windows readlink edge case during
 * `next build` on Node 24. Explicit metadata in lib/seo.ts covers all
 * platforms.
 */

import path from "path";
import sharp from "sharp";

const PUBLIC_DIR = path.join(__dirname, "..", "public");

const BRAND_BLUE = "#2563eb"; // Tailwind blue-600
const WHITE = "#ffffff";

interface IconSpec {
  size: number;
  outputPath: string;
}

const ICONS: IconSpec[] = [
  { size: 32, outputPath: path.join(PUBLIC_DIR, "favicon-32.png") },
  { size: 180, outputPath: path.join(PUBLIC_DIR, "apple-touch-icon.png") },
  { size: 192, outputPath: path.join(PUBLIC_DIR, "icon-192.png") },
  { size: 512, outputPath: path.join(PUBLIC_DIR, "icon-512.png") },
];

function buildSvg(size: number): string {
  // Rounded-square corner radius scales with size (~18% radius matches
  // iOS / Android adaptive icon expectations).
  const radius = Math.round(size * 0.18);
  // Letter sizing: aim for the cap height to be ~60% of the icon size.
  const fontSize = Math.round(size * 0.66);
  // y baseline: a typical glyph baseline sits ~75% down the box for
  // optical centering. We use dominant-baseline=central and a slight
  // upward nudge for visual centering of the round "O".
  const cy = size / 2;
  const cx = size / 2;

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <rect x="0" y="0" width="${size}" height="${size}" rx="${radius}" ry="${radius}" fill="${BRAND_BLUE}"/>
  <text x="${cx}" y="${cy}" fill="${WHITE}"
        font-family="Arial, Helvetica, sans-serif" font-size="${fontSize}" font-weight="700"
        text-anchor="middle" dominant-baseline="central">O</text>
</svg>`;
}

async function buildIcon(spec: IconSpec): Promise<void> {
  const svg = buildSvg(spec.size);
  await sharp(Buffer.from(svg, "utf-8"))
    .resize(spec.size, spec.size)
    .png()
    .toFile(spec.outputPath);
  // eslint-disable-next-line no-console
  console.log(`Icon written: ${spec.outputPath} (${spec.size}x${spec.size})`);
}

async function main(): Promise<void> {
  for (const spec of ICONS) {
    await buildIcon(spec);
  }
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});
