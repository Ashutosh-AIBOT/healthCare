import type { Metadata } from "next";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";

export const metadata: Metadata = {
  title: "Terms of service",
  description: "Terms governing use of the Aarogya platform.",
  alternates: { canonical: "/legal/terms" },
};

export default function TermsPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-3xl px-5 pb-24 pt-28 md:px-8">
        <h1 className="font-display text-4xl font-semibold tracking-tight">Terms of service</h1>
        <p className="mt-2 text-sm text-muted">Version 2026-09-01</p>
        <div className="mt-10 space-y-4 text-sm leading-relaxed text-muted">
          <p>
            By creating an account you agree to use Aarogya lawfully, keep credentials secure, and
            acknowledge the Medical Disclaimer. You must be of legal age in your jurisdiction or use
            the service under a parent/guardian account as a family member.
          </p>
          <p>
            We may suspend accounts that abuse the platform, attempt unauthorized access, or upload
            unlawful content. Subscription fees (when billed) are described on the Pricing page.
          </p>
          <p>Full commercial terms will be published before paid launch.</p>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
