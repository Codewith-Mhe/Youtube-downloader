import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const site = process.env.NEXT_PUBLIC_SITE_URL || "https://clipfetch.app";
  const now = new Date();
  const paths = ["", "/privacy", "/terms", "/dmca", "/contact"];
  return paths.map((p) => ({
    url: `${site}${p}`,
    lastModified: now,
    changeFrequency: "monthly" as const,
    priority: p === "" ? 1 : 0.5,
  }));
}
