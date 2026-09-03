import type { Metadata } from "next";
import Link from "next/link";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Reveal } from "@/components/ui/reveal";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Features",
  description:
    "Lab report vault, cited AI explanations, checkup advisor, family field-level privacy, and care marketplace.",
  alternates: { canonical: "/features" },
};

const features = [
  {
    title: "Report vault",
    body: "Upload PDFs and scans. Values extracted, units normalized, and stored against each family member.",
  },
  {
    title: "Cited explanations",
    body: "Ask what a marker means. Answers cite your report pages and clinical guidelines — never silent diagnosis.",
  },
  {
    title: "Checkup advisor",
    body: "Screening suggestions map to age, sex, history, and prior labs — with clinician approval when conditions exist.",
  },
  {
    title: "Family privacy",
    body: "Grant access per field. Ungranted data is omitted from responses, not shown as locked placeholders.",
  },
  {
    title: "Book labs & doctors",
    body: "Verified providers near your pincode with transparent prices. Bookings feed the vault automatically.",
  },
  {
    title: "Emergency short-circuit",
    body: "Red-flag language skips the model and surfaces helplines — in-app and on Telegram when linked.",
  },
];

export default function FeaturesPage() {
  return (
    <>
      <SiteNav />
      <main className="pt-28">
        <section className="mx-auto max-w-6xl px-5 pb-20 md:px-8 md:pb-28">
          <Reveal>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Features</p>
            <h1 className="mt-4 max-w-2xl font-display text-[clamp(2.25rem,5vw,3.5rem)] font-semibold leading-[1.05] tracking-tight">
              Everything between a confusing report and the next right step.
            </h1>
            <p className="mt-5 max-w-xl text-muted">
              Aarogya is a family health OS — explain, track, advise, and book — without pretending to be
              your doctor.
            </p>
          </Reveal>
          <ul className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f, i) => (
              <Reveal key={f.title} delayMs={i * 60}>
                <li className="h-full rounded-[1.75rem] bg-black/[0.03] p-1.5 ring-1 ring-black/[0.04]">
                  <div className="h-full rounded-[calc(1.75rem-0.375rem)] bg-surface p-7 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.7)]">
                    <h2 className="text-lg font-semibold tracking-tight">{f.title}</h2>
                    <p className="mt-3 text-sm leading-relaxed text-muted">{f.body}</p>
                  </div>
                </li>
              </Reveal>
            ))}
          </ul>
          <Reveal>
            <div className="mt-16">
              <Link href="/register">
                <Button size="lg">Start with your family →</Button>
              </Link>
            </div>
          </Reveal>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
