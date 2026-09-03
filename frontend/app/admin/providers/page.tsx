import type { Metadata } from "next";
import { EmptyState } from "@/components/ui/card";
import { Logo } from "@/components/brand";

export const metadata: Metadata = { title: "Admin · Providers", robots: { index: false } };

export default function AdminProvidersPage() {
  return (
    <div className="min-h-dvh bg-mist/40">
      <header className="border-b border-line/60 bg-foam px-4 py-3">
        <Logo href="/admin" />
      </header>
      <main className="mx-auto max-w-6xl px-4 py-10">
        <EmptyState title="Verification queue empty" description="Provider claims and KYC reviews will list here." />
      </main>
    </div>
  );
}
