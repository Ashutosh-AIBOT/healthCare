import { Bricolage_Grotesque, Public_Sans, JetBrains_Mono } from "next/font/google";
import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const display = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700"],
  display: "swap",
});

const sans = Public_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
const ogImage = `${siteUrl}/og-default.png`;

const orgJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Aarogya",
  legalName: "Aarogya Health Technologies",
  url: siteUrl,
  logo: `${siteUrl}/logo.png`,
  description:
    "Family health operating system and care marketplace for India. Explain lab reports with citations, track cross-lab trends, and book verified labs and doctors.",
  sameAs: ["https://twitter.com/aarogya", "https://www.linkedin.com/company/aarogya"],
  contactPoint: [
    {
      "@type": "ContactPoint",
      contactType: "customer support",
      areaServed: "IN",
      availableLanguage: ["en", "hi"],
    },
  ],
};

const websiteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "Aarogya",
  url: siteUrl,
  inLanguage: "en-IN",
  potentialAction: {
    "@type": "SearchAction",
    target: `${siteUrl}/doctors?q={search_term_string}`,
    "query-input": "required name=search_term_string",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fdfcfa" },
    { media: "(prefers-color-scheme: dark)", color: "#0e1b20" },
  ],
  width: "device-width",
  initialScale: 1,
  colorScheme: "light dark",
};

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Aarogya — Your family's health records, understood",
    template: "%s · Aarogya",
  },
  description:
    "Upload a lab report. Get cited explanations, cross-lab trends, and the right doctor or test — without a diagnosis from an algorithm.",
  applicationName: "Aarogya",
  keywords: [
    "lab report explained",
    "medical reports India",
    "find doctors",
    "book lab tests",
    "health records family",
    "Aarogya",
  ],
  authors: [{ name: "Aarogya" }],
  creator: "Aarogya",
  publisher: "Aarogya",
  formatDetection: { email: false, address: false, telephone: false },
  category: "health",
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: siteUrl,
    siteName: "Aarogya",
    title: "Aarogya — Your family's health records, understood",
    description:
      "Family health OS and care marketplace. Explain reports, track trends, book verified labs and doctors.",
    images: [
      {
        url: ogImage,
        width: 1200,
        height: 630,
        alt: "Aarogya — Your family's health records, understood",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Aarogya — Your family's health records, understood",
    description: "Your family's health records, understood.",
    images: [ogImage],
    creator: "@aarogya",
    site: "@aarogya",
  },
  robots: { index: true, follow: true, googleBot: { index: true, follow: true, "max-image-preview": "large" } },
  alternates: { canonical: "/", types: { "application/xml": `${siteUrl}/sitemap.xml` } },
  icons: { icon: "/favicon.ico", apple: "/apple-touch-icon.png" },
  verification: { google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION },
};

const themeInitScript = `(function(){try{var k='aarogya-theme',d=document.documentElement,s=localStorage.getItem(k);var t=s&&s!=='system'?s:'light';if(t==='dark'){d.classList.add('dark');}else{d.classList.remove('dark');}d.setAttribute('data-theme',t);}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-dvh bg-foam text-ink tabular">
        <ThemeProvider>
          <Script
            id="ld-json-organization"
            type="application/ld+json"
            strategy="afterInteractive"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(orgJsonLd) }}
          />
          <Script
            id="ld-json-website"
            type="application/ld+json"
            strategy="afterInteractive"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
          />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
