import Link from "next/link";
import type { Metadata } from "next";
import { Logo } from "@/components/brand";
import { EmptyState } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Doctor portal",
  robots: { index: false, follow: false },
};

export default function DoctorShellPage() {
  return (
    <div className="min-h-dvh bg-mist/40">
      <header className="border-b border-line/60 bg-foam/90">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Logo href="/doctor" className="text-lg" />
          <nav className="flex gap-4 text-sm text-muted">
            <span className="font-medium text-ink">Queue</span>
            <Link href="/doctor/patients" className="hover:text-ink">
              Patients
            </Link>
            <Link href="/app" className="hover:text-ink">
              Family app
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-10">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Clinician shell</h1>
          <p className="mt-2 text-sm text-muted">
            Plan approval queue and consented shares land here in later milestones.
          </p>
        </div>
        <EmptyState
          title="No plans awaiting approval"
          description="When a member with conditions receives an AI plan, it appears here until you approve or reject it."
          action={
            <Link href="/register">
              <Button size="sm" variant="secondary">
                Request clinician access
              </Button>
            </Link>
          }
        />
      </main>
    </div>
  );
}
