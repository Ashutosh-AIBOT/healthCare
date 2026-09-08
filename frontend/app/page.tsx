import Link from "next/link";
import type { Metadata } from "next";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Reveal } from "@/components/ui/reveal";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Aarogya — Your family's health records, understood",
  description:
    "A lab report becomes structured values, plain-language explanation with citations, and the next right checkup — never a diagnosis.",
  alternates: { canonical: "/" },
};

const site = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

const orgJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Aarogya",
  url: site,
  description: "Family health operating system and care marketplace for India.",
};

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Does Aarogya diagnose medical conditions?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "No. Aarogya explains lab reports with citations and coordinates care. It does not diagnose, prescribe, or replace a clinician.",
      },
    },
    {
      "@type": "Question",
      name: "Can family members see all my health data?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "No. Access is per field and granted by you. Ungranted fields are omitted from API responses — not shown as locked placeholders.",
      },
    },
  ],
};

export default function HomePage() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(orgJsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }} />
      <SiteNav />
      <main>
        {/* Hero: flat dark, type-scale only — the one load entrance on the page */}
        <section className="relative isolate min-h-dvh overflow-hidden bg-home-dark">
          <div className="mx-auto flex min-h-dvh max-w-6xl flex-col justify-end px-5 pb-16 pt-32 md:justify-center md:px-8 md:pb-28 md:pt-24">
            <p className="animate-home-rise font-display text-[clamp(4rem,14vw,8.75rem)] font-semibold leading-[0.86] tracking-[-0.045em] text-home-primary-dark">
              Aarogya
            </p>
            <h1 className="mt-7 max-w-[18ch] animate-home-rise text-balance text-[clamp(1.65rem,3.8vw,2.5rem)] font-bold leading-[1.15] tracking-tight text-home-primary-dark [animation-delay:80ms]">
              Your family&apos;s health records, understood.
            </h1>
            <p className="mt-5 max-w-[560px] animate-home-rise text-pretty text-lg leading-relaxed text-home-secondary-dark [animation-delay:160ms]">
              A lab report becomes structured values, plain-language explanation with citations, and the
              next right checkup — never a diagnosis.
            </p>
            <div className="mt-11 flex flex-wrap items-center gap-3 animate-home-rise [animation-delay:240ms]">
              <Link href="/register">
                <Button size="lg" className="group bg-home-gold text-home-dark shadow-lift hover:bg-home-gold/90">
                  Start with your family
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-home-dark/15 transition-transform duration-500 ease-soft group-hover:translate-x-0.5">
                    →
                  </span>
                </Button>
              </Link>
              <Link href="#how">
                <Button size="lg" className="border border-home-border bg-home-surface text-home-primary-dark hover:border-home-border">
                  See the loop
                </Button>
              </Link>
            </div>
            <p className="mt-9 max-w-[480px] animate-home-rise text-[13px] leading-relaxed text-home-secondary-dark [animation-delay:320ms]">
              Not a medical device. Aarogya explains and coordinates care — it does not diagnose,
              prescribe, or replace a clinician.
            </p>
          </div>
        </section>

        <section id="how" className="relative bg-home-dark py-24 md:py-36">
          <div className="mx-auto max-w-6xl px-5 md:px-8">
            <Reveal durationMs={400} distancePx={12}>
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-home-gold">
                The compounding loop
              </p>
              <h2 className="mt-4 max-w-2xl font-display text-[clamp(2.1rem,4.6vw,2.5rem)] font-semibold leading-[1.04] tracking-tight text-home-primary-dark">
                Report in. Clarity out. Better next test.
              </h2>
              <p className="mt-5 max-w-xl text-pretty text-home-secondary-dark">
                Each booking feeds the vault. Each vault sharpens the advisor. Your family&apos;s real
                history stays in one place.
              </p>
            </Reveal>
            <ol className="mt-16 grid gap-5 md:grid-cols-3 md:gap-6">
              {[
                {
                  step: "01",
                  title: "Upload a report",
                  body: "PDF or scan. Values extracted, units normalized, flags from the lab’s own ranges.",
                },
                {
                  step: "02",
                  title: "Ask with citations",
                  body: "Plain language grounded in your pages and guidelines — every claim points to a source.",
                },
                {
                  step: "03",
                  title: "Book what follows",
                  body: "Screening suggestions map to verified labs near your pincode with real prices.",
                },
              ].map((item, i) => (
                <Reveal key={item.step} delayMs={i * 100} durationMs={400} distancePx={12}>
                  <li className="group h-full rounded-2xl border border-home-border bg-home-surface p-8 transition-[border-color,transform,box-shadow] duration-150 ease-soft hover:-translate-y-0.5 hover:border-home-gold/30 hover:shadow-home-gold-glow">
                    <span className="text-[13px] font-semibold text-home-gold">{item.step}</span>
                    <h3 className="mt-7 text-xl font-semibold tracking-tight text-home-primary-dark">{item.title}</h3>
                    <p className="mt-3 text-[15px] leading-relaxed text-home-secondary-dark">{item.body}</p>
                  </li>
                </Reveal>
              ))}
            </ol>
          </div>
        </section>

        <section id="trust" className="relative bg-home-light py-24 md:py-36">
          <div className="relative mx-auto max-w-6xl px-5 md:px-8">
            <Reveal durationMs={400} distancePx={12}>
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-home-secondary-light">
                Built for trust
              </p>
              <h2 className="mt-4 max-w-2xl font-display text-[clamp(2.1rem,4.6vw,2.5rem)] font-semibold leading-[1.04] tracking-tight text-home-primary-light">
                Consent first. Citations always. No silent diagnosis.
              </h2>
            </Reveal>
            <Reveal durationMs={400} distancePx={12}>
              <ul className="mt-14 grid gap-10 md:grid-cols-3 md:gap-12">
                {[
                  {
                    title: "Field-level family privacy",
                    body: "Relatives see only what you grant. Ungranted fields are absent — not locked icons.",
                  },
                  {
                    title: "Clinician in the loop",
                    body: "AI plans for members with conditions wait for doctor approval before they go active.",
                  },
                  {
                    title: "Emergency short-circuit",
                    body: "Red-flag language skips the model and surfaces helplines — in-app and on Telegram.",
                  },
                ].map((item) => (
                  <li key={item.title} className="border-t border-home-light-border pt-6">
                    <h3 className="text-base font-semibold tracking-tight text-home-primary-light">{item.title}</h3>
                    <p className="mt-3 text-sm leading-relaxed text-home-secondary-light">{item.body}</p>
                  </li>
                ))}
              </ul>
            </Reveal>
            <div className="mt-16 border-t border-home-light-border pt-10">
              <Link href="/register">
                <Button size="lg" className="bg-home-primary-light text-home-light hover:bg-home-primary-light/90">
                  Create your family space →
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter tone="dark" />
    </>
  );
}
