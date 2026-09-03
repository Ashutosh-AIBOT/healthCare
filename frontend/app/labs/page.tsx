import type { Metadata } from "next";
import { Suspense } from "react";
import { ProviderSearchClient } from "@/components/search/provider-search-client";

export const metadata: Metadata = {
  title: "Find labs",
  robots: { index: true, follow: true },
};

export default function FindLabsPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-6xl px-4 py-10 md:px-6 md:py-12">Loading…</div>}>
      <ProviderSearchClient providerType="lab" />
    </Suspense>
  );
}
