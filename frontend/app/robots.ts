import type { MetadataRoute } from "next";

const site = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/app/",
          "/api/",
          "/login",
          "/register",
          "/verify",
          "/forgot-password",
          "/reset-password",
          "/admin",
          "/doctor",
          "/lab",
        ],
      },
      // AI crawler explicit allow (GEO) — decide per engine, allow for discoverability
      { userAgent: "GPTBot", allow: ["/", "/doctors", "/labs", "/features", "/legal/"] },
      { userAgent: "PerplexityBot", allow: ["/", "/doctors", "/labs", "/features", "/legal/"] },
      { userAgent: "Google-Extended", allow: "/" },
      // Block faceted/param spam
      { userAgent: "*", disallow: ["/*?*", "/*&*"] },
    ],
    sitemap: `${site}/sitemap.xml`,
    host: site,
  };
}
