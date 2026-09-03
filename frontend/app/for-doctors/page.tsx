import type { Metadata } from "next";
import Link from "next/link";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Reveal } from "@/components/ui/reveal";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "For doctors",
  description:
    "Approve AI care plans, review shared reports with consent, and keep patients in a continuous loop.",
  alternates: { canonical: "/for-doctors" },
};

export default function ForDoctorsPage() {
  return (
    <>
      <SiteNav />
      <main className="pt-28">
        <section className="mx-auto max-w-6xl px-5 pb-24 md:px-8">
          <Reveal>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Clinicians</p>
            <h1 className="mt-4 max-w-2xl font-display text-[clamp(2.25rem,5vw,3.5rem)] font-semibold leading-[1.05]">
              Stay in the loop when AI drafts a plan.
            </h1>
            <p className="mt-5 max-w-xl text-muted">
              Members with conditions get AI-suggested plans only after your approval. Shared reports
              arrive with field-level consent — never a dump of the whole vault.
            </p>
            <div className="mt-10">
              <Link href="/register">
                <Button size="lg">Request clinician access →</Button>
              </Link>
            </div>
          </Reveal>
          <ul className="mt-16 grid gap-8 md:grid-cols-3">
            {[
              { t: "Plan approval queue", d: "Review AI drafts, edit, approve or reject with a clinical note." },
              { t: "Consented shares", d: "See only fields the patient granted for this encounter." },
              { t: "Booking continuity", d: "Follow-ups and labs booked through Aarogya land back in the timeline." },
            ].map((item, i) => (
              <Reveal key={item.t} delayMs={i * 70}>
                <li>
                  <h2 className="text-lg font-semibold">{item.t}</h2>
                  <p className="mt-3 text-sm text-muted">{item.d}</p>
                </li>
              </Reveal>
            ))}
          </ul>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
