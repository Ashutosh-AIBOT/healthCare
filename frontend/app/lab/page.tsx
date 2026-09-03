import Link from "next/link";
import type { Metadata } from "next";
import { Logo } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Card, EmptyState } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Lab portal",
  robots: { index: false, follow: false },
};

export default function LabDashboardPage() {
  return (
    <div className="min-h-dvh bg-[linear-gradient(180deg,var(--color-mist)_0%,var(--color-foam)_28%,var(--color-foam)_100%)]">
      <header className="sticky top-0 z-30 border-b border-line/50 bg-foam/85 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 md:px-6">
          <Logo href="/lab" className="text-lg" />
          <nav className="hidden items-center gap-1 md:flex" aria-label="Lab">
            <Link href="/lab/onboarding" className="rounded-full px-3.5 py-1.5 text-sm font-medium text-muted hover:bg-mist hover:text-ink">
              Profile
            </Link>
            <Link href="/lab/catalog" className="rounded-full px-3.5 py-1.5 text-sm font-medium text-muted hover:bg-mist hover:text-ink">
              Catalog
            </Link>
            <Link href="/lab/bookings" className="rounded-full px-3.5 py-1.5 text-sm font-medium text-muted hover:bg-mist hover:text-ink">
              Bookings
            </Link>
            <Link href="/app" className="rounded-full px-3.5 py-1.5 text-sm font-medium text-muted hover:bg-mist hover:text-ink">
              Family app
            </Link>
          </nav>
          <Button variant="ghost" size="sm">
            Sign out
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-8 px-4 py-10 md:px-6 md:py-12">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="font-display text-3xl font-semibold tracking-tight">Lab dashboard</h1>
            <p className="mt-2 text-sm text-muted">Complete onboarding, manage catalog, and process bookings.</p>
          </div>
          <div className="flex gap-3">
            <Link href="/lab/onboarding">
              <Button variant="secondary">Complete profile</Button>
            </Link>
            <Link href="/lab/catalog">
              <Button>Manage catalog</Button>
            </Link>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <p className="text-sm text-muted">Verification status</p>
            <p className="mt-2 text-2xl font-semibold text-ink">Pending</p>
            <p className="mt-1 text-sm text-muted">Submit your lab details for review.</p>
          </Card>
          <Card>
            <p className="text-sm text-muted">Today&apos;s collections</p>
            <p className="mt-2 text-2xl font-semibold text-ink">0</p>
            <p className="mt-1 text-sm text-muted">Collections connect in M9.</p>
          </Card>
          <Card>
            <p className="text-sm text-muted">Pending uploads</p>
            <p className="mt-2 text-2xl font-semibold text-ink">0</p>
            <p className="mt-1 text-sm text-muted">Report uploads connect in M9.</p>
          </Card>
        </div>

        <EmptyState
          title="Complete your onboarding"
          description="Add accreditation, serviceable pincodes, and home-collection details."
          action={
            <Link href="/lab/onboarding">
              <Button size="sm" variant="secondary">
                Start onboarding
              </Button>
            </Link>
          }
        />
      </main>
    </div>
  );
}
