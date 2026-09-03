import type { MetadataRoute } from "next";

const site = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/app/", "/api/", "/login", "/register", "/verify", "/forgot-password", "/reset-password"],
      },
    ],
    sitemap: `${site}/sitemap.xml`,
  };
}
