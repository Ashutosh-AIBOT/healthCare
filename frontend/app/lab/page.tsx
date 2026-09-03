import Link from "next/link";
import type { Metadata } from "next";
import { Logo } from "@/components/brand";
import { EmptyState } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Lab portal",
  robots: { index: false, follow: false },
};

export default function LabShellPage() {
  return (
    <div className="min-h-dvh bg-mist/40">
      <header className="border-b border-line/60 bg-foam/90">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Logo href="/lab" className="text-lg" />
          <nav className="flex gap-4 text-sm text-muted">
            <span className="font-medium text-ink">Bookings</span>
            <Link href="/lab/catalog" className="hover:text-ink">
              Catalog
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-10">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Lab shell</h1>
          <p className="mt-2 text-sm text-muted">
            Panel pricing and inbound bookings connect in the provider milestones.
          </p>
        </div>
        <EmptyState
          title="No bookings today"
          description="When families book a panel near your pincode, samples and uploads show up here."
          action={
            <Link href="/for-labs">
              <Button size="sm" variant="secondary">
                Learn about lab onboarding
              </Button>
            </Link>
          }
        />
      </main>
    </div>
  );
}
