import type { MetadataRoute } from "next";

const site = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export default function sitemap(): MetadataRoute.Sitemap {
  const paths = ["", "/features", "/pricing", "/for-doctors", "/for-labs", "/legal/medical-disclaimer", "/legal/privacy", "/legal/terms", "/doctors", "/labs"];
  const now = new Date();
  return paths.map((path) => ({
    url: `${site}${path || "/"}`,
    lastModified: now,
    changeFrequency: path === "" ? "weekly" : "monthly",
    priority: path === "" ? 1 : 0.7,
  }));
}
