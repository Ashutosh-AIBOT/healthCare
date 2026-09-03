import type { Metadata } from "next";
import { Suspense } from "react";
import { ProviderSearchClient } from "@/components/search/provider-search-client";

export const metadata: Metadata = {
  title: "Doctors in {city}",
  robots: { index: false, follow: false },
};

export default async function DoctorsCityPage({ params }: { params: Promise<{ city: string }> }) {
  const { city } = await params;
  return (
    <Suspense fallback={<div className="mx-auto max-w-6xl px-4 py-10 md:px-6 md:py-12">Loading…</div>}>
      <ProviderSearchClient providerType="doctor" />
    </Suspense>
  );
}
