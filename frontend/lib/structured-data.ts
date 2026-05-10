// JSON-LD structured data builders.
//
// We expose CMS-published facts (name, address, phone, identifier) and the
// republication chain via creator/sourceOrganization. We do NOT expose any
// editorial assessment — no aggregateRating, no review, no quality score.
// That separation is what keeps this republication, not assertion. See
// legal-compliance.md § Positioning and § Data Attribution.

import type { Provider } from "@/types/provider";
import { providerSlug, titleCase } from "@/lib/utils";
import {
  DEFAULT_OG_IMAGE_PATH,
  SITE_DESCRIPTION,
  SITE_NAME,
} from "@/lib/constants";
import { getSiteUrl } from "@/lib/seo";

export type JsonLd = Record<string, unknown>;

const CMS_PROVIDER_DATA_URL =
  "https://data.cms.gov/provider-data/";

function postalAddress(provider: Provider): JsonLd | null {
  const a = provider.address;
  if (!a.street && !a.city && !a.state && !a.zip) return null;
  const obj: JsonLd = { "@type": "PostalAddress" };
  if (a.street) obj.streetAddress = titleCase(a.street);
  if (a.city) obj.addressLocality = titleCase(a.city);
  if (a.state) obj.addressRegion = a.state;
  if (a.zip) obj.postalCode = a.zip;
  obj.addressCountry = "US";
  return obj;
}

function cmsCreator(): JsonLd {
  return {
    "@type": "GovernmentOrganization",
    name: "Centers for Medicare & Medicaid Services",
    url: CMS_PROVIDER_DATA_URL,
  };
}

function profileSlug(provider: Provider): string {
  return providerSlug(
    provider.name,
    provider.address?.city ?? null,
    provider.address?.state ?? null,
    provider.provider_id
  );
}

function profileUrl(provider: Provider): string {
  const slug = profileSlug(provider);
  const path =
    provider.provider_type === "HOSPITAL"
      ? `/hospital/${slug}/`
      : `/nursing-home/${slug}/`;
  return getSiteUrl() + path;
}

export function buildHospitalJsonLd(provider: Provider): JsonLd {
  const address = postalAddress(provider);
  const ld: JsonLd = {
    "@context": "https://schema.org",
    "@type": "Hospital",
    name: titleCase(provider.name),
    url: profileUrl(provider),
    identifier: {
      "@type": "PropertyValue",
      propertyID: "CMS Certification Number (CCN)",
      value: provider.provider_id,
    },
    sourceOrganization: cmsCreator(),
  };
  if (provider.phone) ld.telephone = provider.phone;
  if (address) ld.address = address;
  return ld;
}

export function buildNursingHomeJsonLd(provider: Provider): JsonLd {
  const address = postalAddress(provider);
  const ld: JsonLd = {
    "@context": "https://schema.org",
    "@type": "MedicalOrganization",
    additionalType: "https://schema.org/NursingHome",
    name: titleCase(provider.name),
    url: profileUrl(provider),
    identifier: {
      "@type": "PropertyValue",
      propertyID: "CMS Certification Number (CCN)",
      value: provider.provider_id,
    },
    sourceOrganization: cmsCreator(),
  };
  if (provider.phone) ld.telephone = provider.phone;
  if (address) ld.address = address;
  return ld;
}

export function buildProviderJsonLd(provider: Provider): JsonLd {
  return provider.provider_type === "NURSING_HOME"
    ? buildNursingHomeJsonLd(provider)
    : buildHospitalJsonLd(provider);
}

export function buildOrganizationJsonLd(): JsonLd {
  const siteUrl = getSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: SITE_NAME,
    url: siteUrl,
    logo: siteUrl + DEFAULT_OG_IMAGE_PATH,
    description: SITE_DESCRIPTION,
  };
}

export function buildWebsiteJsonLd(): JsonLd {
  const siteUrl = getSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: siteUrl,
    description: SITE_DESCRIPTION,
  };
}

// ─── Breadcrumbs ─────────────────────────────────────────────────────
//
// Each crumb has a label and an absolute URL. Search engines render
// breadcrumb rich results when every item has a valid http(s) URL, so
// we always pass through getSiteUrl() rather than emitting bare paths.

export interface BreadcrumbItem {
  name: string;
  pathname: string;
}

export function buildBreadcrumbListJsonLd(items: BreadcrumbItem[]): JsonLd {
  const siteUrl = getSiteUrl();
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: siteUrl + (item.pathname.startsWith("/") ? item.pathname : "/" + item.pathname),
    })),
  };
}

export function buildHospitalBreadcrumbsJsonLd(provider: Provider): JsonLd {
  return buildBreadcrumbListJsonLd([
    { name: "Home", pathname: "/" },
    { name: "Hospitals", pathname: "/filter-explore/" },
    { name: titleCase(provider.name), pathname: `/hospital/${profileSlug(provider)}/` },
  ]);
}

export function buildNursingHomeBreadcrumbsJsonLd(provider: Provider): JsonLd {
  return buildBreadcrumbListJsonLd([
    { name: "Home", pathname: "/" },
    { name: "Nursing Homes", pathname: "/filter-explore/" },
    { name: titleCase(provider.name), pathname: `/nursing-home/${profileSlug(provider)}/` },
  ]);
}

export function jsonLdString(ld: JsonLd | JsonLd[]): string {
  return JSON.stringify(ld).replace(/</g, "\\u003c");
}
