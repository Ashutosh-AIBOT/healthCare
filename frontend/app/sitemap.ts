import type { MetadataRoute } from "next";

const site = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

/**
 * Sitemap baseline — static public routes only (no auth/app).
 * Quality-gated dynamic routes (doctors/labs/tests/posts) will be appended via
 * fetch + revalidateTag webhook after verification (TODO next slice).
 * Keeps lastModified honest; Next generates /sitemap.xml with correct headers.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const staticPaths: Array<{ url: string; priority: number; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"] }> = [
    { url: "/", priority: 1, changeFrequency: "weekly" },
    { url: "/features", priority: 0.8, changeFrequency: "monthly" },
    { url: "/pricing", priority: 0.7, changeFrequency: "monthly" },
    { url: "/for-doctors", priority: 0.7, changeFrequency: "monthly" },
    { url: "/for-labs", priority: 0.7, changeFrequency: "monthly" },
    { url: "/doctors", priority: 0.8, changeFrequency: "daily" },
    { url: "/labs", priority: 0.8, changeFrequency: "daily" },
    { url: "/legal/terms", priority: 0.3, changeFrequency: "monthly" },
    { url: "/legal/privacy", priority: 0.3, changeFrequency: "monthly" },
    { url: "/legal/medical-disclaimer", priority: 0.4, changeFrequency: "monthly" },
  ];

  return staticPaths.map((p) => ({
    url: `${site}${p.url}`,
    lastModified: now,
    changeFrequency: p.changeFrequency,
    priority: p.priority,
  }));
}
