import type { Metadata } from "next";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";

export const metadata: Metadata = {
  title: "Medical disclaimer",
  description: "Aarogya is not a medical device and does not diagnose or prescribe.",
  alternates: { canonical: "/legal/medical-disclaimer" },
};

export default function MedicalDisclaimerPage() {
  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-3xl px-5 pb-24 pt-28 md:px-8">
        <h1 className="font-display text-4xl font-semibold tracking-tight">Medical disclaimer</h1>
        <p className="mt-2 text-sm text-muted">Version 2026-09-01</p>
        <div className="prose-legal mt-10 space-y-4 text-sm leading-relaxed text-muted">
          <p>
            Aarogya is a software platform for organizing health records, explaining laboratory reports
            in plain language with citations, suggesting screening checkups, and coordinating bookings
            with labs and clinicians.
          </p>
          <p>
            <strong className="text-ink">Aarogya is not a medical device.</strong> It does not diagnose
            disease, prescribe treatment, or replace consultation with a qualified healthcare
            professional. Always seek the advice of a physician or other qualified provider with any
            questions about a medical condition.
          </p>
          <p>
            Emergency or red-flag situations should use local emergency services. In-app helpline
            prompts are informational and not a substitute for emergency care.
          </p>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
