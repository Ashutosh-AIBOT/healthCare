import type { Metadata } from "next";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";

export const metadata: Metadata = {
  title: "Privacy policy",
  description: "How Aarogya collects, uses, and protects health and account data.",
  alternates: { canonical: "/legal/privacy" },
};

export default function PrivacyPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-3xl px-5 pb-24 pt-28 md:px-8">
        <h1 className="font-display text-4xl font-semibold tracking-tight">Privacy policy</h1>
        <p className="mt-2 text-sm text-muted">Version 2026-09-01</p>
        <div className="mt-10 space-y-4 text-sm leading-relaxed text-muted">
          <p>
            We process account data (email, handle, name) and health-related data you upload or grant
            access to (reports, values, consents) to provide the service.
          </p>
          <p>
            Family sharing is opt-in and field-level. Ungranted fields are omitted from API responses.
            Clinicians and labs see only what is required for a consented encounter or booking.
          </p>
          <p>
            Contact privacy@aarogya.app for data access or deletion requests. This page will expand
            with DPDP / regional specifics as we launch.
          </p>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
