import type { Metadata } from "next";
import { EmptyState } from "@/components/ui/card";
import { Logo } from "@/components/brand";

export const metadata: Metadata = { title: "Lab · Catalog", robots: { index: false } };

export default function LabCatalogPage() {
  return (
    <div className="min-h-dvh bg-mist/40">
      <header className="border-b border-line/60 bg-foam px-4 py-3">
        <Logo href="/lab" />
      </header>
      <main className="mx-auto max-w-6xl px-4 py-10">
        <EmptyState title="Catalog empty" description="Add panels and city pricing in the provider onboarding flow." />
      </main>
    </div>
  );
}
