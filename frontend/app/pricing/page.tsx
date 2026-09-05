import type { Metadata } from "next";
import Link from "next/link";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Reveal } from "@/components/ui/reveal";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Simple family plans for Aarogya — vault, explanations, and care marketplace access.",
  alternates: { canonical: "/pricing" },
};

const plans = [
  {
    name: "Family",
    price: "₹499",
    period: "/ month",
    blurb: "Up to 6 members, unlimited report uploads, cited chat, checkup advisor.",
    cta: "Start family plan",
    featured: true,
  },
  {
    name: "Solo",
    price: "₹199",
    period: "/ month",
    blurb: "One member vault, explanations, and booking. Upgrade when you invite family.",
    cta: "Start solo",
    featured: false,
  },
  {
    name: "Clinic",
    price: "Custom",
    period: "",
    blurb: "Doctor and lab portals, panel pricing, and approval workflows. Talk to us.",
    cta: "Contact sales",
    featured: false,
  },
];

export default function PricingPage() {
  return (
    <>
      <SiteNav />
      <main className="pt-28">
        <section className="mx-auto max-w-6xl px-5 pb-20 md:px-8 md:pb-28">
          <Reveal>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Pricing</p>
            <h1 className="mt-4 max-w-xl font-display text-[clamp(2.25rem,5vw,3.5rem)] font-semibold leading-[1.05]">
              Clear plans. No surprise health fees.
            </h1>
            <p className="mt-5 max-w-lg text-muted">
              Lab and doctor booking prices come from providers. Aarogya subscription covers the OS
              layer.
            </p>
          </Reveal>
          <ul className="mt-14 grid gap-6 md:grid-cols-3">
            {plans.map((p, i) => (
              <Reveal key={p.name} delayMs={i * 80}>
                <li
                  className={`flex h-full flex-col rounded-[1.75rem] p-1.5 ring-1 ${
                    p.featured ? "bg-primary ring-primary" : "bg-mist ring-line"
                  }`}
                >
                  <div
                    className={`flex h-full flex-col rounded-[calc(1.75rem-0.375rem)] p-7 ${
                      p.featured ? "bg-primary text-primary-foreground" : "bg-surface shadow-card"
                    }`}
                  >
                    <h2 className="text-lg font-semibold">{p.name}</h2>
                    <p className="mt-4 font-display text-4xl font-semibold tracking-tight">
                      {p.price}
                      <span className={`text-base font-sans font-normal ${p.featured ? "text-primary-foreground/70" : "text-muted"}`}>
                        {p.period}
                      </span>
                    </p>
                    <p className={`mt-4 flex-1 text-sm leading-relaxed ${p.featured ? "text-primary-foreground/80" : "text-muted"}`}>
                      {p.blurb}
                    </p>
                    <Link href={p.name === "Clinic" ? "/for-doctors" : "/register"} className="mt-8">
                      <Button
                        size="lg"
                        className={`w-full ${p.featured ? "bg-surface text-ink hover:bg-surface/90" : ""}`}
                        variant={p.featured ? "secondary" : "secondary"}
                      >
                        {p.cta}
                      </Button>
                    </Link>
                  </div>
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
