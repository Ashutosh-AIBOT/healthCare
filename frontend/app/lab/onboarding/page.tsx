"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, ErrorState, Skeleton } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient, getAccessToken } from "@/lib/auth-client";

type LabProfile = {
  id: string;
  provider_type: string;
  display_name: string;
  slug: string;
  bio: string | null;
  photo_url: string | null;
  license_number: string | null;
  years_experience: number | null;
  consultation_fee_paise: number | null;
  verification_status: string;
  lab_details: {
    accreditation: string | null;
    home_collection_enabled: boolean;
    report_turnaround_hours: number | null;
    serviceable_pincodes: string | null;
  } | null;
};

export default function LabOnboardingPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<LabProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    display_name: "",
    bio: "",
    license_number: "",
    years_experience: "",
    accreditation: "",
    home_collection_enabled: false,
    report_turnaround_hours: "",
    serviceable_pincodes: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient<LabProfile>("/api/v1/providers/me");
    if (res.error) {
      if (res.error.status === 404) {
        const token = getAccessToken();
        if (!token) {
          router.replace("/login");
          return;
        }
        const created = await apiClient<LabProfile>("/api/v1/providers/profile", {
          method: "POST",
          body: JSON.stringify({ provider_type: "lab", display_name: "" }),
        });
        if (created.error) {
          setError(created.error.detail || "Failed to create provider profile.");
          setLoading(false);
          return;
        }
        setProfile(created.data || null);
        setForm((prev) => ({ ...prev, display_name: created.data?.display_name || "" }));
      } else {
        setError(res.error.detail || "Failed to load profile.");
      }
      setLoading(false);
      return;
    }
    setProfile(res.data || null);
    if (res.data) {
      setForm({
        display_name: res.data.display_name || "",
        bio: res.data.bio || "",
        license_number: res.data.license_number || "",
        years_experience: res.data.years_experience ? String(res.data.years_experience) : "",
        accreditation: res.data.lab_details?.accreditation || "",
        home_collection_enabled: res.data.lab_details?.home_collection_enabled || false,
        report_turnaround_hours: res.data.lab_details?.report_turnaround_hours ? String(res.data.lab_details.report_turnaround_hours) : "",
        serviceable_pincodes: res.data.lab_details?.serviceable_pincodes || "",
      });
    }
    setLoading(false);
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    setSaving(true);
    setError(null);
    const body: Record<string, unknown> = {
      display_name: form.display_name || undefined,
      bio: form.bio || undefined,
      license_number: form.license_number || undefined,
      years_experience: form.years_experience ? Number(form.years_experience) : undefined,
    };
    const profileRes = await apiClient<LabProfile>("/api/v1/providers/me", {
      method: "PATCH",
      body: JSON.stringify(body),
    });
    if (profileRes.error) {
      setError(profileRes.error.detail || "Failed to save profile.");
      setSaving(false);
      return;
    }

    const detailsRes = await apiClient("/api/v1/providers/me/lab-details", {
      method: "PATCH",
      body: JSON.stringify({
        accreditation: form.accreditation || undefined,
        home_collection_enabled: form.home_collection_enabled,
        report_turnaround_hours: form.report_turnaround_hours ? Number(form.report_turnaround_hours) : undefined,
        serviceable_pincodes: form.serviceable_pincodes || undefined,
      }),
    });
    if (detailsRes.error) {
      setError(detailsRes.error.detail || "Failed to save lab details.");
      setSaving(false);
      return;
    }

    setSaving(false);
    router.replace("/lab");
  };

  if (loading) {
    return (
      <div className="min-h-dvh bg-[linear-gradient(180deg,var(--color-mist)_0%,var(--color-foam)_28%,var(--color-foam)_100%)]">
        <main className="mx-auto max-w-2xl px-4 py-10 md:px-6 md:py-12">
          <Skeleton className="h-8 w-48" />
          <div className="mt-8 space-y-4">
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-[linear-gradient(180deg,var(--color-mist)_0%,var(--color-foam)_28%,var(--color-foam)_100%)]">
      <main className="mx-auto max-w-2xl space-y-6 px-4 py-10 md:px-6 md:py-12">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Lab onboarding</h1>
          <p className="mt-2 text-sm text-muted">Complete your profile to start receiving bookings.</p>
        </div>

        {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

        <Card>
          <div className="space-y-4">
            <Input
              label="Lab name"
              value={form.display_name}
              onChange={(e) => setForm((prev) => ({ ...prev, display_name: e.target.value }))}
            />
            <Input
              label="Bio"
              value={form.bio}
              onChange={(e) => setForm((prev) => ({ ...prev, bio: e.target.value }))}
              hint="Short description visible to patients."
            />
            <Input
              label="License number"
              value={form.license_number}
              onChange={(e) => setForm((prev) => ({ ...prev, license_number: e.target.value }))}
            />
            <Input
              label="Years of experience"
              type="number"
              value={form.years_experience}
              onChange={(e) => setForm((prev) => ({ ...prev, years_experience: e.target.value }))}
            />
          </div>
        </Card>

        <Card>
          <div className="space-y-4">
            <Input
              label="Accreditation"
              value={form.accreditation}
              onChange={(e) => setForm((prev) => ({ ...prev, accreditation: e.target.value }))}
              hint="e.g. NABL Accredited"
            />
            <div className="flex items-center gap-3">
              <input
                id="home_collection"
                type="checkbox"
                checked={form.home_collection_enabled}
                onChange={(e) => setForm((prev) => ({ ...prev, home_collection_enabled: e.target.checked }))}
                className="h-4 w-4 rounded border-line text-primary focus:ring-primary"
              />
              <label htmlFor="home_collection" className="text-sm font-medium text-ink">
                Enable home collection
              </label>
            </div>
            <Input
              label="Report turnaround (hours)"
              type="number"
              value={form.report_turnaround_hours}
              onChange={(e) => setForm((prev) => ({ ...prev, report_turnaround_hours: e.target.value }))}
            />
            <Input
              label="Serviceable pincodes"
              value={form.serviceable_pincodes}
              onChange={(e) => setForm((prev) => ({ ...prev, serviceable_pincodes: e.target.value }))}
              hint="Comma separated"
            />
          </div>
        </Card>

        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => router.back()}>
            Cancel
          </Button>
          <Button onClick={() => void save()} loading={saving}>
            Save profile
          </Button>
        </div>
      </main>
    </div>
  );
}
