import Link from "next/link";
import type { Metadata } from "next";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Reveal } from "@/components/ui/reveal";
import { Disclaimer } from "@/components/brand";
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
        {/* Hero: brand-first, one composition, full-bleed atmosphere */}
        <section className="relative isolate min-h-dvh overflow-hidden">
          <div aria-hidden className="absolute inset-0 -z-20 bg-foam" />
          <div
            aria-hidden
            className="absolute inset-0 -z-10 bg-[radial-gradient(90%_70%_at_12%_18%,color-mix(in_srgb,var(--color-primary)_26%,transparent),transparent_58%),radial-gradient(70%_55%_at_88%_72%,color-mix(in_srgb,var(--color-healthy)_18%,transparent),transparent_60%),linear-gradient(165deg,var(--color-foam)_0%,var(--color-mist)_48%,color-mix(in_srgb,var(--color-primary-soft)_55%,var(--color-foam))_100%)]"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 -z-10 bg-grain opacity-[0.035] mix-blend-multiply"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -left-[18%] top-[8%] -z-10 h-[58vmax] w-[58vmax] animate-drift rounded-full bg-[radial-gradient(circle_at_center,color-mix(in_srgb,var(--color-primary)_22%,transparent),transparent_70%)] blur-3xl"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -right-[12%] bottom-[-8%] -z-10 h-[46vmax] w-[46vmax] animate-drift rounded-full bg-[radial-gradient(circle_at_center,color-mix(in_srgb,var(--color-healthy)_16%,transparent),transparent_72%)] blur-3xl [animation-delay:-7s]"
          />

          <div className="mx-auto flex min-h-dvh max-w-6xl flex-col justify-end px-5 pb-16 pt-32 md:justify-center md:px-8 md:pb-28 md:pt-24">
            <p className="animate-fade-up font-display text-[clamp(4rem,16vw,10rem)] font-semibold leading-[0.86] tracking-[-0.045em] text-ink">
              Aarogya
            </p>
            <h1 className="mt-7 max-w-[18ch] animate-fade-up text-balance text-[clamp(1.65rem,3.8vw,2.65rem)] font-medium leading-[1.15] tracking-tight text-ink [animation-delay:110ms]">
              Your family&apos;s health records, understood.
            </h1>
            <p className="mt-5 max-w-lg animate-fade-up text-pretty text-base leading-relaxed text-muted md:text-lg [animation-delay:200ms]">
              A lab report becomes structured values, plain-language explanation with citations, and the
              next right checkup — never a diagnosis.
            </p>
            <div className="mt-11 flex flex-wrap items-center gap-3 animate-fade-up [animation-delay:290ms]">
              <Link href="/register">
                <Button size="lg" className="group shadow-lift">
                  Start with your family
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-foam/15 transition-transform duration-500 ease-soft group-hover:translate-x-0.5">
                    →
                  </span>
                </Button>
              </Link>
              <Link href="#how">
                <Button size="lg" variant="secondary">
                  See the loop
                </Button>
              </Link>
            </div>
            <Disclaimer className="mt-9 max-w-md animate-fade-up [animation-delay:380ms]" />
          </div>
        </section>

        <section id="how" className="relative border-t border-line/40 bg-mist/60 py-24 md:py-36">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent"
          />
          <div className="mx-auto max-w-6xl px-5 md:px-8">
            <Reveal>
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.24em] text-primary">
                The compounding loop
              </p>
              <h2 className="mt-4 max-w-2xl font-display text-[clamp(2.1rem,4.6vw,3.4rem)] font-semibold leading-[1.04] tracking-tight">
                Report in. Clarity out. Better next test.
              </h2>
              <p className="mt-5 max-w-xl text-pretty text-muted">
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
                <Reveal key={item.step} delayMs={i * 90}>
                  <li className="group h-full rounded-[1.85rem] bg-ink/[0.035] p-[3px] ring-1 ring-ink/[0.04] transition-transform duration-700 ease-soft hover:-translate-y-0.5">
                    <div className="flex h-full flex-col rounded-[calc(1.85rem-3px)] bg-surface/95 p-7 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.75)] md:p-8">
                      <span className="font-mono text-[0.7rem] tracking-[0.2em] text-primary">{item.step}</span>
                      <h3 className="mt-7 text-xl font-semibold tracking-tight">{item.title}</h3>
                      <p className="mt-3 text-sm leading-relaxed text-muted">{item.body}</p>
                    </div>
                  </li>
                </Reveal>
              ))}
            </ol>
          </div>
        </section>

        <section id="trust" className="relative overflow-hidden border-t border-ink bg-ink py-24 text-foam md:py-36">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-1/4 top-0 h-[40vmax] w-[40vmax] rounded-full bg-[radial-gradient(circle,color-mix(in_srgb,var(--color-healthy)_28%,transparent),transparent_70%)] blur-3xl"
          />
          <div className="relative mx-auto max-w-6xl px-5 md:px-8">
            <Reveal>
              <p className="text-[0.7rem] font-semibold uppercase tracking-[0.24em] text-healthy">
                Built for trust
              </p>
              <h2 className="mt-4 max-w-2xl font-display text-[clamp(2.1rem,4.6vw,3.4rem)] font-semibold leading-[1.04]">
                Consent first. Citations always. No silent diagnosis.
              </h2>
            </Reveal>
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
              ].map((item, i) => (
                <Reveal key={item.title} delayMs={i * 80}>
                  <li className="border-t border-foam/15 pt-6">
                    <h3 className="text-base font-semibold tracking-tight">{item.title}</h3>
                    <p className="mt-3 text-sm leading-relaxed text-foam/65">{item.body}</p>
                  </li>
                </Reveal>
              ))}
            </ul>
            <Reveal delayMs={100}>
              <div className="mt-16 border-t border-foam/12 pt-10">
                <Link href="/register">
                  <Button size="lg" className="bg-foam text-ink shadow-lift hover:bg-foam/90">
                    Create your family space →
                  </Button>
                </Link>
              </div>
            </Reveal>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
