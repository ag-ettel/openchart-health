import type { MetadataRoute } from "next";
import { getSiteUrl } from "@/lib/seo";

// Required by Next.js output: "export" for non-page route handlers.
export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  const base = getSiteUrl();
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
      },
    ],
    sitemap: `${base}/sitemap.xml`,
    host: base,
  };
}
