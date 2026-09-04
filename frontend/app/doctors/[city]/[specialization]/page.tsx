import type { Metadata } from "next";
import { Suspense } from "react";
import { ProviderSearchClient } from "@/components/search/provider-search-client";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ city: string; specialization: string }>;
}): Promise<Metadata> {
  const { city, specialization } = await params;
  return {
    title: `${specialization} doctors in ${city}`,
    description: `Find verified ${specialization.toLowerCase()} doctors in ${city}. Compare fees, experience, and book appointments.`,
    robots: { index: true, follow: true },
    alternates: { canonical: `/doctors/${city}/${specialization}` },
  };
}

export default async function DoctorCitySpecializationPage({
  params,
}: {
  params: Promise<{ city: string; specialization: string }>;
}) {
  const { city, specialization } = await params;
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-6xl px-4 py-10 md:px-6 md:py-12">Loading…</div>
      }
    >
      <ProviderSearchClient
        providerType="doctor"
        initialCity={city}
        initialSpecialization={specialization}
        qualityGate
      />
    </Suspense>
  );
}
