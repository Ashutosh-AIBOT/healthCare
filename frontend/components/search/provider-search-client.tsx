"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/auth-client";

type Provider = {
  id: string;
  provider_type: string;
  display_name: string;
  slug: string;
  city: string | null;
  state: string | null;
  pincode: string | null;
  consultation_fee_paise: number | null;
  verification_status: string;
  rating: number | null;
  response_rate: number | null;
  completion_rate: number | null;
  years_experience: number | null;
  doctor_details: Record<string, unknown> | null;
  lab_details: Record<string, unknown> | null;
  ranking: {
    text_match: number;
    verification: number;
    experience: number;
    price: number;
    recency: number;
    composite: number;
  };
};

const CITIES = ["Delhi", "Mumbai", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Jaipur"];
const SPECIALIZATIONS = ["General Medicine", "Cardiology", "Dermatology", "Pediatrics", "Orthopedics", "Gynecology"];

export function ProviderSearchClient({ providerType }: { providerType: "doctor" | "lab" }) {
  const searchParams = useSearchParams();
  const [results, setResults] = useState<Provider[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [city, setCity] = useState(searchParams.get("city") || "");
  const [pincode, setPincode] = useState(searchParams.get("pincode") || "");
  const [specialization, setSpecialization] = useState(searchParams.get("specialization") || "");
  const [verifiedOnly, setVerifiedOnly] = useState(searchParams.get("verified") === "1");
  const [minFee, setMinFee] = useState(searchParams.get("min_fee") || "");
  const [maxFee, setMaxFee] = useState(searchParams.get("max_fee") || "");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (city) params.set("city", city);
    if (pincode) params.set("pincode", pincode);
    if (specialization && providerType === "doctor") params.set("specialization", specialization);
    if (verifiedOnly) params.set("verified_only", "true");
    if (minFee) params.set("min_fee_paise", minFee);
    if (maxFee) params.set("max_fee_paise", maxFee);
    params.set("provider_type", providerType);

    const res = await apiClient<Provider[]>(`/api/v1/search/providers?${params.toString()}`);
    if (res.error) {
      setError(res.error.detail || "Search failed.");
      setResults([]);
      setLoading(false);
      return;
    }
    setResults(res.data || []);
    setLoading(false);
  }, [q, city, pincode, specialization, verifiedOnly, minFee, maxFee, providerType]);

  useEffect(() => {
    void load();
  }, [load]);

  const clear = () => {
    setQ("");
    setCity("");
    setPincode("");
    setSpecialization("");
    setVerifiedOnly(false);
    setMinFee("");
    setMaxFee("");
  };

  const providerLabel = providerType === "doctor" ? "Doctor" : "Lab";

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-10 md:px-6 md:py-12">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Find {providerLabel}s
        </h1>
        <p className="mt-2 text-sm text-muted">
          {providerType === "doctor"
            ? "Search by name, specialization, or city. Results are ranked by relevance, verification, and experience."
            : "Search by name, accreditation, or city. Check serviceability before booking."}
        </p>
      </div>

      <Card>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Input
            label="Search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={`Search ${providerLabel.toLowerCase()}...`}
          />
          <div>
            <label className="block text-sm font-medium text-ink">City</label>
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="mt-1.5 w-full rounded-2xl border border-line bg-surface px-3 py-2.5 text-sm"
            >
              <option value="">All cities</option>
              {CITIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          {providerType === "doctor" ? (
            <div>
              <label className="block text-sm font-medium text-ink">Specialization</label>
              <select
                value={specialization}
                onChange={(e) => setSpecialization(e.target.value)}
                className="mt-1.5 w-full rounded-2xl border border-line bg-surface px-3 py-2.5 text-sm"
              >
                <option value="">All</option>
                {SPECIALIZATIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <Input
              label="Pincode"
              value={pincode}
              onChange={(e) => setPincode(e.target.value)}
              placeholder="Home collection pincode"
            />
          )}
          <div className="flex items-end">
            <Button variant="secondary" onClick={clear} className="w-full">
              Clear
            </Button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={verifiedOnly}
              onChange={(e) => setVerifiedOnly(e.target.checked)}
              className="h-4 w-4 rounded border-line text-primary focus:ring-primary"
            />
            Verified only
          </label>
          <Input
            label="Min fee (INR)"
            type="number"
            value={minFee}
            onChange={(e) => setMinFee(e.target.value)}
            className="w-40"
          />
          <Input
            label="Max fee (INR)"
            type="number"
            value={maxFee}
            onChange={(e) => setMaxFee(e.target.value)}
            className="w-40"
          />
          <Button onClick={() => void load()}>Search</Button>
        </div>
      </Card>

      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : results === null ? (
        <Skeleton className="h-40 w-full" />
      ) : !results.length ? (
        <EmptyState
          title="No matches"
          description="Try widening filters or searching another city/specialization."
        />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {results.map((item) => (
            <li key={item.id}>
              <Card>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-semibold text-ink">{item.display_name}</p>
                    <p className="mt-1 text-sm text-muted">
                      {[item.city, item.state].filter(Boolean).join(", ") || "Location not set"}
                    </p>
                    {item.doctor_details && "specializations" in item.doctor_details && (
                      <p className="mt-2 text-xs text-muted">{String(item.doctor_details.specializations)}</p>
                    )}
                    {item.lab_details && "accreditation" in item.lab_details && (
                      <p className="mt-2 text-xs text-muted">{String(item.lab_details.accreditation)}</p>
                    )}
                  </div>
                  <div className="text-right text-xs text-muted">
                    <p className="font-semibold text-ink">{item.verification_status}</p>
                    <p>{item.years_experience ?? "—"} yrs</p>
                    <p>
                      {item.consultation_fee_paise != null
                        ? `₹${(item.consultation_fee_paise / 100).toFixed(2)}`
                        : "Fee on request"}
                    </p>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between gap-3">
                  <p className="text-xs text-muted">
                    Relevance: {(item.ranking.composite * 100).toFixed(0)}% ·{" "}
                    {item.rating != null ? `★ ${item.rating.toFixed(1)}` : "No rating"}
                  </p>
                <a
                  href={`/${providerType}s/${item.slug}`}
                  className="inline-flex items-center justify-center rounded-full border border-line bg-foam/80 px-3 py-1.5 text-xs font-semibold text-ink hover:border-primary/30 hover:bg-primary-soft/40"
                >
                  View profile
                </a>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
