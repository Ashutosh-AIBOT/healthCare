"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { ProviderCard } from "@/components/dashboard/provider-card";
import { apiClient } from "@/lib/auth-client";

type Provider = {
  id: string;
  display_name: string;
  provider_type: string;
  city: string | null;
  specialization: string | null;
  rating: number | null;
  consultation_fee_paise: number | null;
  verification_status: string;
  years_experience: number | null;
  is_active: boolean;
};

type SearchFilters = {
  q: string;
  provider_type: string;
  city: string;
  specialization: string;
  verified_only: boolean;
};

export default function DoctorsPage() {
  const [providers, setProviders] = useState<Provider[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<SearchFilters>({
    q: "",
    provider_type: "",
    city: "",
    specialization: "",
    verified_only: false,
  });

  const load = useCallback(async () => {
    setError(null);
    const params = new URLSearchParams();
    if (filters.q) params.set("q", filters.q);
    if (filters.provider_type) params.set("provider_type", filters.provider_type);
    if (filters.city) params.set("city", filters.city);
    if (filters.specialization) params.set("specialization", filters.specialization);
    if (filters.verified_only) params.set("verified_only", "true");

    const [listRes, searchRes] = await Promise.all([
      apiClient<Provider[]>("/api/v1/providers/"),
      apiClient<Provider[]>("/api/v1/search/providers" + (params.toString() ? `?${params.toString()}` : "")),
    ]);
    if (listRes.error) {
      setError(listRes.error.detail || "Failed to load providers.");
      setProviders([]);
      return;
    }
    if (searchRes.error) {
      setError(searchRes.error.detail || "Failed to search providers.");
      setProviders([]);
      return;
    }
    const combined = [...(listRes.data || []), ...(searchRes.data || [])];
    const unique = Array.from(new Map(combined.map((p) => [p.id, p])).values());
    setProviders(unique);
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  const isLoading = providers === null && !error;

  const stats = useMemo(() => {
    if (!providers?.length) return { verified: 0, specialties: 0, cities: 0, avgRating: 0 };
    const cities = new Set(providers.map((p) => p.city).filter(Boolean));
    const specialties = new Set(providers.map((p) => p.specialization).filter(Boolean));
    const ratings = providers.filter((p) => p.rating != null).map((p) => p.rating as number);
    const avg = ratings.length ? ratings.reduce((s, r) => s + r, 0) / ratings.length : 0;
    return {
      verified: providers.filter((p) => p.verification_status === "verified").length,
      specialties: specialties.size,
      cities: cities.size,
      avgRating: Math.round(avg * 10) / 10,
    };
  }, [providers]);

  const topSpecialties = useMemo(() => {
    if (!providers?.length) return [];
    const counts: Record<string, number> = {};
    providers.forEach((p) => {
      if (p.specialization) counts[p.specialization] = (counts[p.specialization] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, count]) => ({ name, count }));
  }, [providers]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-10 w-24" />
          <Skeleton className="mt-2 h-5 w-72" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-[1.75rem]" />
          ))}
        </div>
        <Skeleton className="h-64 w-full rounded-[1.75rem]" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Doctors</h1>
        <p className="text-sm text-muted">Browse providers, view profiles, and book consultations.</p>
      </div>

      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Verified</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{stats.verified}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Specialties</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{stats.specialties}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Cities</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{stats.cities}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Avg Rating</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{stats.avgRating || "—"}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card lg:col-span-2">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="font-semibold text-ink">Doctor Directory</h2>
              <p className="mt-1 text-xs text-muted">
                Search by name, city, or specialty.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <input
                type="search"
                placeholder="Search providers..."
                value={filters.q}
                onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
                className="w-full rounded-2xl border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-muted md:w-64"
              />
              <select
                value={filters.verified_only ? "true" : ""}
                onChange={(e) => setFilters((f) => ({ ...f, verified_only: e.target.value === "true" }))}
                className="rounded-2xl border border-line bg-surface px-4 py-2 text-sm text-ink"
              >
                <option value="">All statuses</option>
                <option value="true">Verified only</option>
              </select>
            </div>
          </div>
          {!providers?.length ? (
            <EmptyState
              title="No providers found"
              description="Try adjusting your search or filters."
            />
          ) : (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {providers.slice(0, 8).map((p) => (
                <ProviderCard
                  key={p.id}
                  name={p.display_name}
                  specialty={p.specialization || p.provider_type}
                  available={p.verification_status === "verified"}
                />
              ))}
            </div>
          )}
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <h2 className="font-semibold text-ink">Top Specialties</h2>
          {!topSpecialties.length ? (
            <p className="mt-2 text-sm text-muted">No specialty data yet.</p>
          ) : (
            <ul className="mt-4 space-y-2">
              {topSpecialties.map((s) => (
                <li key={s.name} className="flex items-center justify-between rounded-2xl bg-mist/60 px-4 py-2">
                  <span className="text-sm text-ink">{s.name}</span>
                  <span className="text-xs font-semibold text-muted">{s.count}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          <h2 className="font-semibold text-ink">Featured Providers</h2>
          <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
            {!providers?.length ? (
              <EmptyState
                title="No featured providers"
                description="Provider profiles and availability will load here."
              />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {providers
                  .filter((p) => p.verification_status === "verified")
                  .slice(0, 4)
                  .map((p) => (
                    <ProviderCard
                      key={p.id}
                      name={p.display_name}
                      specialty={p.specialization || p.provider_type}
                      available
                    />
                  ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
