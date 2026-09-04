import { Fraunces, Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import type { Metadata } from "next";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const sans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Aarogya — Your family's health records, understood",
    template: "%s · Aarogya",
  },
  description:
    "Upload a lab report. Get cited explanations, cross-lab trends, and the right doctor or test — without a diagnosis from an algorithm.",
  applicationName: "Aarogya",
  openGraph: {
    type: "website",
    locale: "en_IN",
    siteName: "Aarogya",
    title: "Aarogya — Your family's health records, understood",
    description:
      "Family health OS and care marketplace. Explain reports, track trends, book verified labs and doctors.",
    url: siteUrl,
  },
  twitter: {
    card: "summary_large_image",
    title: "Aarogya",
    description: "Your family's health records, understood.",
  },
  robots: { index: true, follow: true },
  alternates: { canonical: "/" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
