// SEO metadata builders. Subject to legal-compliance.md § Positioning.
// All copy lives in lib/constants.ts — this module only assembles
// Next.js Metadata objects. Components must not inline copy or build
// metadata objects directly; call buildMetadata() from generateMetadata.

import type { Metadata } from "next";
import type { Provider } from "@/types/provider";
import {
  COMPARE_DESCRIPTION,
  COMPARE_TITLE_BASE,
  DEFAULT_OG_IMAGE_ALT,
  DEFAULT_OG_IMAGE_HEIGHT,
  DEFAULT_OG_IMAGE_PATH,
  DEFAULT_OG_IMAGE_WIDTH,
  DEFAULT_SITE_URL,
  FILTER_EXPLORE_DESCRIPTION,
  FILTER_EXPLORE_NH_DESCRIPTION,
  FILTER_EXPLORE_NH_TITLE_BASE,
  FILTER_EXPLORE_TITLE_BASE,
  HOME_DESCRIPTION,
  HOME_OG_DESCRIPTION,
  HOME_TITLE_BASE,
  HOSPITAL_META_DESCRIPTION,
  METHODOLOGY_DESCRIPTION,
  METHODOLOGY_TITLE_BASE,
  NURSING_HOME_META_DESCRIPTION,
  SEO_DESCRIPTION_MAX,
  SEO_TITLE_MAX,
  SITE_DESCRIPTION,
  SITE_NAME,
  SITE_TWITTER_HANDLE,
  TITLE_SUFFIX,
} from "@/lib/constants";
import { providerSlug, titleCase } from "@/lib/utils";

export function getSiteUrl(): string {
  const raw = process.env.NEXT_PUBLIC_SITE_URL ?? DEFAULT_SITE_URL;
  return raw.replace(/\/+$/, "");
}

function joinUrl(base: string, pathname: string): string {
  if (!pathname.startsWith("/")) pathname = "/" + pathname;
  return base + pathname;
}

function clamp(text: string, max: number): string {
  if (text.length <= max) return text;
  const truncated = text.slice(0, max - 1);
  const lastSpace = truncated.lastIndexOf(" ");
  const cutAt = lastSpace > max * 0.6 ? lastSpace : truncated.length;
  return truncated.slice(0, cutAt).trimEnd() + "…";
}

interface BuildMetadataInput {
  title: string;
  description: string;
  /**
   * Optional separate description for OG/Twitter cards. Social-share copy
   * can be slightly more compelling than a Google snippet because it is
   * not a 160-char SERP truncation target. When omitted, the meta
   * description is reused for OG/Twitter.
   */
  ogDescription?: string;
  pathname: string;
  ogImagePath?: string;
}

export function buildMetadata({
  title,
  description,
  ogDescription,
  pathname,
  ogImagePath = DEFAULT_OG_IMAGE_PATH,
}: BuildMetadataInput): Metadata {
  const siteUrl = getSiteUrl();
  const url = joinUrl(siteUrl, pathname);
  const fullTitle = title.endsWith(TITLE_SUFFIX) ? title : `${title}${TITLE_SUFFIX}`;
  const safeTitle = clamp(fullTitle, SEO_TITLE_MAX);
  const safeDescription = clamp(description, SEO_DESCRIPTION_MAX);
  const safeOgDescription = clamp(
    ogDescription ?? description,
    SEO_DESCRIPTION_MAX
  );
  const ogImageUrl = joinUrl(siteUrl, ogImagePath);

  const twitter: NonNullable<Metadata["twitter"]> = {
    card: "summary_large_image",
    title: safeTitle,
    description: safeOgDescription,
    images: [ogImageUrl],
  };
  if (SITE_TWITTER_HANDLE) {
    twitter.site = SITE_TWITTER_HANDLE;
    twitter.creator = SITE_TWITTER_HANDLE;
  }

  return {
    title: safeTitle,
    description: safeDescription,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      url,
      siteName: SITE_NAME,
      title: safeTitle,
      description: safeOgDescription,
      images: [
        {
          url: ogImageUrl,
          width: DEFAULT_OG_IMAGE_WIDTH,
          height: DEFAULT_OG_IMAGE_HEIGHT,
          alt: DEFAULT_OG_IMAGE_ALT,
        },
      ],
    },
    twitter,
  };
}

export function buildHomeMetadata(): Metadata {
  return buildMetadata({
    title: HOME_TITLE_BASE,
    description: HOME_DESCRIPTION,
    ogDescription: HOME_OG_DESCRIPTION,
    pathname: "/",
  });
}

export function buildMethodologyMetadata(): Metadata {
  return buildMetadata({
    title: METHODOLOGY_TITLE_BASE,
    description: METHODOLOGY_DESCRIPTION,
    pathname: "/methodology/",
  });
}

export function buildCompareMetadata(): Metadata {
  return buildMetadata({
    title: COMPARE_TITLE_BASE,
    description: COMPARE_DESCRIPTION,
    pathname: "/compare/",
  });
}

export function buildFilterExploreMetadata(): Metadata {
  return buildMetadata({
    title: FILTER_EXPLORE_TITLE_BASE,
    description: FILTER_EXPLORE_DESCRIPTION,
    pathname: "/filter-explore/",
  });
}

export function buildFilterExploreNursingHomeMetadata(): Metadata {
  return buildMetadata({
    title: FILTER_EXPLORE_NH_TITLE_BASE,
    description: FILTER_EXPLORE_NH_DESCRIPTION,
    pathname: "/filter-explore/nursing-home/",
  });
}

export function buildRootMetadata(): Metadata {
  // Plain title default. Per-page metadata supplies a fully-qualified title
  // via buildMetadata(), which appends TITLE_SUFFIX exactly once. Avoids
  // Next.js's title.template, which would double-append the suffix.
  return {
    metadataBase: new URL(getSiteUrl()),
    title: `${SITE_NAME} — CMS Quality Data`,
    description: SITE_DESCRIPTION,
    applicationName: SITE_NAME,
    referrer: "strict-origin-when-cross-origin",
    robots: { index: true, follow: true },
    // Icons live in public/ rather than app/. Next.js's app/icon.png convention
    // hits a Windows readlink edge case at build time on some Node versions;
    // explicit metadata works on every platform.
    icons: {
      icon: [
        { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
        { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
        { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
      ],
      apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
    },
    // Search engine ownership verification tags. These render as
    // <meta name="..." content="..."> in the document head.
    verification: {
      google: "VLK0jqgo037_50uRaTEqh9bJUzpe46OojlWONvBPYqo",
      // Bing uses the msvalidate.01 meta name; Next.js emits non-standard
      // verification names via the `other` map.
      other: {
        "msvalidate.01": "D898468D758C55D665D72989A0CCD510",
      },
    },
  };
}

// ─── Per-provider metadata (factual, no advisory or evaluative language) ──

function periodRange(provider: Provider): string | null {
  let earliest: string | null = null;
  let latest: string | null = null;
  for (const m of provider.measures) {
    const start = m.period_start;
    const end = m.period_end;
    if (start && (earliest === null || start < earliest)) earliest = start;
    if (end && (latest === null || end > latest)) latest = end;
  }
  if (!earliest && !latest) return null;
  const fmt = (iso: string): string => iso.slice(0, 7);
  if (earliest && latest) return `${fmt(earliest)} to ${fmt(latest)}`;
  return fmt(earliest ?? latest!);
}

function locationLabel(provider: Provider): string | null {
  const city = provider.address.city;
  const state = provider.address.state;
  if (city && state) return `${titleCase(city)}, ${state}`;
  if (state) return state;
  if (city) return titleCase(city);
  return null;
}

export function buildHospitalMetaTitle(provider: Provider): string {
  const name = titleCase(provider.name);
  const reservedForSuffix = TITLE_SUFFIX.length;
  return clamp(`${name} — Quality Data`, SEO_TITLE_MAX - reservedForSuffix);
}

export function buildHospitalMetaDescription(provider: Provider): string {
  return clamp(
    HOSPITAL_META_DESCRIPTION({
      name: titleCase(provider.name),
      location: locationLabel(provider),
      measureCount: provider.measures.length,
      periodRange: periodRange(provider),
    }),
    SEO_DESCRIPTION_MAX
  );
}

export function buildNursingHomeMetaTitle(provider: Provider): string {
  const name = titleCase(provider.name);
  const reservedForSuffix = TITLE_SUFFIX.length;
  return clamp(`${name} — Quality Data`, SEO_TITLE_MAX - reservedForSuffix);
}

export function buildNursingHomeMetaDescription(provider: Provider): string {
  const ctx = provider.nursing_home_context;
  return clamp(
    NURSING_HOME_META_DESCRIPTION({
      name: titleCase(provider.name),
      location: locationLabel(provider),
      measureCount: provider.measures.length,
      inspectionCount: provider.inspection_events?.length ?? 0,
      periodRange: periodRange(provider),
      isSpecialFocusFacility: ctx?.is_special_focus_facility === true,
      isSpecialFocusFacilityCandidate:
        ctx?.is_special_focus_facility_candidate === true,
      isAbuseIcon: ctx?.is_abuse_icon === true,
    }),
    SEO_DESCRIPTION_MAX
  );
}

function providerProfileSlug(provider: Provider): string {
  return providerSlug(
    provider.name,
    provider.address?.city ?? null,
    provider.address?.state ?? null,
    provider.provider_id
  );
}

export function buildHospitalMetadata(provider: Provider): Metadata {
  return buildMetadata({
    title: buildHospitalMetaTitle(provider),
    description: buildHospitalMetaDescription(provider),
    pathname: `/hospital/${providerProfileSlug(provider)}/`,
  });
}

export function buildNursingHomeMetadata(provider: Provider): Metadata {
  return buildMetadata({
    title: buildNursingHomeMetaTitle(provider),
    description: buildNursingHomeMetaDescription(provider),
    pathname: `/nursing-home/${providerProfileSlug(provider)}/`,
  });
}
