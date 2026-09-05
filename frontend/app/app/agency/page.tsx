"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type Agency = {
  id: string;
  name: string;
  city: string;
  coordinator: string;
  status: string;
};

type Agreement = {
  id: string;
  agency_name: string;
  type: string;
  start_date: string;
  end_date: string | null;
  status: string;
};

type Coordinator = {
  id: string;
  name: string;
  email: string;
  assigned_agencies: string[];
};

export default function AgencyPage() {
  const [agencies, setAgencies] = useState<Agency[] | null>(null);
  const [agreements, setAgreements] = useState<Agreement[] | null>(null);
  const [coordinators, setCoordinators] = useState<Coordinator[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const [a, ag, c] = await Promise.all([
      apiClient<Agency[]>("/api/v1/agencies"),
      apiClient<Agreement[]>("/api/v1/agreements"),
      apiClient<Coordinator[]>("/api/v1/coordinators"),
    ]);
    if (a.error) {
      setError(a.error.detail || "Failed to load agencies.");
      setAgencies([]);
      return;
    }
    if (ag.error) {
      setError(ag.error.detail || "Failed to load agreements.");
      setAgreements([]);
      return;
    }
    if (c.error) {
      setError(c.error.detail || "Failed to load coordinators.");
      setCoordinators([]);
      return;
    }
    setAgencies(a.data || []);
    setAgreements(ag.data || []);
    setCoordinators(c.data || []);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const isLoading = agencies === null && agreements === null && coordinators === null && !error;

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
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Agency</h1>
        <p className="text-sm text-muted">Manage care agencies, coordinators, and service agreements.</p>
      </div>

      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Active Agencies</p>
          <p className="mt-2 text-2xl font-semibold text-ink">
            {agencies?.filter((a) => a.status === "active").length ?? 0}
          </p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Coordinators</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{coordinators?.length ?? 0}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Agreements</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{agreements?.length ?? 0}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Pending</p>
          <p className="mt-2 text-2xl font-semibold text-ink">
            {agencies?.filter((a) => a.status === "pending").length ?? 0}
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card lg:col-span-2">
          <h2 className="font-semibold text-ink">Agency Management</h2>
          {!agencies?.length ? (
            <EmptyState
              title="No agencies yet"
              description="Agency onboarding and coordination tools will appear here."
            />
          ) : (
            <ul className="mt-4 space-y-3">
              {agencies.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-4 rounded-2xl bg-mist/60 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-ink">{a.name}</p>
                    <p className="text-xs text-muted">
                      {a.city} · Coordinator: {a.coordinator}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-semibold capitalize ${
                      a.status === "active"
                        ? "bg-healthy-excellent/10 text-healthy-excellent"
                        : "bg-mist text-muted"
                    }`}
                  >
                    {a.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <h2 className="font-semibold text-ink">Service Agreements</h2>
          {!agreements?.length ? (
            <p className="mt-2 text-sm text-muted">
              View and manage contracts with care agencies.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {agreements.map((ag) => (
                <li key={ag.id} className="rounded-2xl bg-mist/60 px-4 py-3">
                  <p className="text-sm font-semibold text-ink">{ag.agency_name}</p>
                  <p className="text-xs text-muted">
                    {ag.type} · {new Date(ag.start_date).toLocaleDateString()}
                    {ag.end_date ? ` → ${new Date(ag.end_date).toLocaleDateString()}` : ""}
                  </p>
                  <span className="mt-2 inline-block rounded-full bg-mist px-2.5 py-1 text-[11px] font-semibold capitalize text-muted">
                    {ag.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          <h2 className="font-semibold text-ink">Coordinator Directory</h2>
          <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
            {!coordinators?.length ? (
              <EmptyState
                title="No coordinators yet"
                description="Agency coordinators and assignments will load here."
              />
            ) : (
              <ul className="grid gap-3 md:grid-cols-2">
                {coordinators.map((c) => (
                  <li key={c.id} className="rounded-2xl bg-mist/60 px-4 py-3">
                    <p className="text-sm font-semibold text-ink">{c.name}</p>
                    <p className="text-xs text-muted">{c.email}</p>
                    <p className="mt-1 text-xs text-muted">
                      Agencies: {c.assigned_agencies.length > 0 ? c.assigned_agencies.join(", ") : "None"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
