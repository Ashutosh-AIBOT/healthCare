import Link from "next/link";
import type { Metadata } from "next";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Reveal } from "@/components/ui/reveal";
import { Button } from "@/components/ui/button";
import { ArrowUpRight, Check, FileText, LockKeyhole, ShieldCheck } from "lucide-react";

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
      <main id="main-content">
        <section className="relative isolate min-h-[92dvh] overflow-hidden bg-home-dark">
          <div className="mx-auto grid min-h-[92dvh] max-w-7xl items-center gap-14 px-5 pb-20 pt-32 md:grid-cols-[0.9fr_1.1fr] md:gap-16 md:px-8 md:pb-24 md:pt-24">
            <div>
              <p className="animate-home-rise text-xs font-semibold uppercase tracking-[0.12em] text-home-gold">
                Family health, made legible
              </p>
              <h1 className="mt-5 max-w-[11ch] animate-home-rise font-display text-[clamp(3.5rem,7vw,6.8rem)] font-semibold leading-[0.92] tracking-[-0.04em] text-home-primary-dark [animation-delay:80ms]">
                Care starts with clarity.
              </h1>
              <p className="mt-7 max-w-[500px] animate-home-rise text-pretty text-lg leading-relaxed text-home-secondary-dark [animation-delay:160ms]">
                Aarogya turns scattered reports into a trusted family health record and a clear next step.
              </p>
              <div className="mt-9 flex flex-wrap items-center gap-3 animate-home-rise [animation-delay:240ms]">
                <Link href="/register">
                  <Button size="lg" className="group bg-home-gold text-home-dark shadow-lift hover:bg-home-gold/90">
                    Start with your family
                    <ArrowUpRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </Button>
                </Link>
                <Link href="#how">
                  <Button size="lg" className="border border-home-border bg-home-surface text-home-primary-dark hover:border-home-gold/50">
                    See the loop
                  </Button>
                </Link>
              </div>
              <p className="mt-8 flex items-center gap-2 text-[13px] text-home-secondary-dark [animation-delay:320ms]">
                <LockKeyhole className="h-3.5 w-3.5 text-home-gold" />
                Consent first. No silent diagnosis.
              </p>
            </div>

            <div className="relative animate-home-rise [animation-delay:180ms]" aria-label="Aarogya report explanation preview">
              <div className="relative overflow-hidden rounded-[1.5rem] border border-home-border bg-home-surface shadow-lift">
                <div className="flex items-center justify-between border-b border-home-border px-5 py-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-home-primary-dark">
                    <FileText className="h-4 w-4 text-home-gold" />
                    May health review
                  </div>
                  <span className="rounded-full border border-home-border px-2.5 py-1 font-mono text-[10px] text-home-secondary-dark">PRIVATE</span>
                </div>
                <div className="grid gap-5 p-5 sm:grid-cols-[0.75fr_1.25fr] sm:p-7">
                  <div className="rounded-xl border border-home-border bg-home-dark p-5">
                    <div className="flex items-center justify-between text-[11px] text-home-secondary-dark">
                      <span>HbA1c</span>
                      <span>Report 02</span>
                    </div>
                    <p className="mt-7 font-display text-5xl font-semibold tracking-tight text-home-primary-dark">5.8</p>
                    <p className="mt-2 text-xs text-home-secondary-dark">% · lab range 4.0–5.6</p>
                    <div className="mt-8 h-1.5 overflow-hidden rounded-full bg-home-border">
                      <div className="h-full w-[62%] rounded-full bg-home-gold" />
                    </div>
                    <p className="mt-3 text-[11px] text-home-gold">Worth watching</p>
                  </div>
                  <div className="flex flex-col justify-between">
                    <div>
                      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-home-gold">
                        <ShieldCheck className="h-4 w-4" /> Explained with context
                      </div>
                      <h2 className="mt-4 font-display text-2xl font-semibold leading-tight text-home-primary-dark">A small signal, not a verdict.</h2>
                      <p className="mt-3 text-sm leading-relaxed text-home-secondary-dark">Your result sits just above this lab&apos;s range. Compare the next report and discuss patterns with a clinician.</p>
                    </div>
                    <div className="mt-7 border-t border-home-border pt-4">
                      <p className="text-[11px] uppercase tracking-[0.1em] text-home-secondary-dark">Next right check</p>
                      <div className="mt-2 flex items-center gap-2 text-sm font-semibold text-home-primary-dark">
                        <Check className="h-4 w-4 text-home-gold" /> Add a follow-up report in 3 months
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between border-t border-home-border bg-home-dark/60 px-5 py-3 text-[11px] text-home-secondary-dark">
                  <span>Source: your uploaded report</span>
                  <span className="flex items-center gap-1 text-home-gold">View details <ArrowUpRight className="h-3 w-3" /></span>
                </div>
              </div>
            </div>
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
              <h2 className="max-w-2xl font-display text-[clamp(2.1rem,4.6vw,2.5rem)] font-semibold leading-[1.04] tracking-tight text-home-primary-light">
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
