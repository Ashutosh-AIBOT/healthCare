import type { Metadata } from "next";
import Link from "next/link";
import { SiteNav } from "@/components/marketing/site-nav";
import { SiteFooter } from "@/components/marketing/site-footer";
import { Reveal } from "@/components/ui/reveal";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "For labs",
  description: "List panels, receive bookings by pincode, and push structured results into the family vault.",
  alternates: { canonical: "/for-labs" },
};

export default function ForLabsPage() {
  return (
    <>
      <SiteNav />
      <main className="pt-28">
        <section className="mx-auto max-w-6xl px-5 pb-24 md:px-8">
          <Reveal>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Laboratories</p>
            <h1 className="mt-4 max-w-2xl font-display text-[clamp(2.25rem,5vw,3.5rem)] font-semibold leading-[1.05]">
              Reach families who already know which test they need.
            </h1>
            <p className="mt-5 max-w-xl text-muted">
              Publish panels and prices. Receive bookings near your service area. Deliver results that
              land as structured values — ready for explanation and trends.
            </p>
            <div className="mt-10">
              <Link href="/register">
                <Button size="lg">List your lab →</Button>
              </Link>
            </div>
          </Reveal>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
