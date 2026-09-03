import Link from "next/link";
import type { Metadata } from "next";
import { Logo } from "@/components/brand";
import { EmptyState } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Admin",
  robots: { index: false, follow: false },
};

export default function AdminShellPage() {
  return (
    <div className="min-h-dvh bg-mist/40">
      <header className="border-b border-line/60 bg-foam/90">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Logo href="/admin" className="text-lg" />
          <nav className="flex gap-4 text-sm text-muted">
            <span className="font-medium text-ink">Overview</span>
            <Link href="/admin/providers" className="hover:text-ink">
              Providers
            </Link>
            <Link href="/admin/support" className="hover:text-ink">
              Support
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-10">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Platform admin</h1>
          <p className="mt-2 text-sm text-muted">
            Verification queues, AI quality, and support tools arrive in M21.
          </p>
        </div>
        <EmptyState
          title="Ops dashboard placeholder"
          description="Impersonation, tickets, and legal export controls will mount on this shell."
          action={
            <Link href="/app">
              <Button size="sm" variant="secondary">
                Back to family app
              </Button>
            </Link>
          }
        />
      </main>
    </div>
  );
}
