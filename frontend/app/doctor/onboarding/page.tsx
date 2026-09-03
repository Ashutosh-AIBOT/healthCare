"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, ErrorState, Skeleton } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient, getAccessToken, setAccessToken } from "@/lib/auth-client";

type DoctorProfile = {
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
  doctor_details: {
    registration_number: string | null;
    qualifications: string | null;
    specializations: string | null;
    languages: string | null;
    teleconsult_enabled: boolean;
    home_visit_enabled: boolean;
  } | null;
};

export default function DoctorOnboardingPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<DoctorProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    display_name: "",
    bio: "",
    license_number: "",
    years_experience: "",
    consultation_fee_paise: "",
    registration_number: "",
    qualifications: "",
    specializations: "",
    languages: "",
    teleconsult_enabled: false,
    home_visit_enabled: false,
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient<DoctorProfile>("/api/v1/providers/me");
    if (res.error) {
      if (res.error.status === 404) {
        const token = getAccessToken();
        if (!token) {
          router.replace("/login");
          return;
        }
        const created = await apiClient<DoctorProfile>("/api/v1/providers/profile", {
          method: "POST",
          body: JSON.stringify({ provider_type: "doctor", display_name: "" }),
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
        consultation_fee_paise: res.data.consultation_fee_paise ? String(res.data.consultation_fee_paise) : "",
        registration_number: res.data.doctor_details?.registration_number || "",
        qualifications: res.data.doctor_details?.qualifications || "",
        specializations: res.data.doctor_details?.specializations || "",
        languages: res.data.doctor_details?.languages || "",
        teleconsult_enabled: res.data.doctor_details?.teleconsult_enabled || false,
        home_visit_enabled: res.data.doctor_details?.home_visit_enabled || false,
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
      consultation_fee_paise: form.consultation_fee_paise ? Number(form.consultation_fee_paise) : undefined,
    };
    const profileRes = await apiClient<DoctorProfile>("/api/v1/providers/me", {
      method: "PATCH",
      body: JSON.stringify(body),
    });
    if (profileRes.error) {
      setError(profileRes.error.detail || "Failed to save profile.");
      setSaving(false);
      return;
    }

    const detailsRes = await apiClient("/api/v1/providers/me/doctor-details", {
      method: "PATCH",
      body: JSON.stringify({
        registration_number: form.registration_number || undefined,
        qualifications: form.qualifications || undefined,
        specializations: form.specializations || undefined,
        languages: form.languages || undefined,
        teleconsult_enabled: form.teleconsult_enabled,
        home_visit_enabled: form.home_visit_enabled,
      }),
    });
    if (detailsRes.error) {
      setError(detailsRes.error.detail || "Failed to save doctor details.");
      setSaving(false);
      return;
    }

    setSaving(false);
    router.replace("/doctor");
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
          <h1 className="font-display text-3xl font-semibold tracking-tight">Doctor onboarding</h1>
          <p className="mt-2 text-sm text-muted">Complete your profile to start receiving appointments.</p>
        </div>

        {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

        <Card>
          <div className="space-y-4">
            <Input
              label="Display name"
              value={form.display_name}
              onChange={(e) => setForm((prev) => ({ ...prev, display_name: e.target.value }))}
            />
            <Input
              label="Bio"
              value={form.bio}
              onChange={(e) => setForm((prev) => ({ ...prev, bio: e.target.value }))}
              hint="Short professional bio visible to patients."
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
            <Input
              label="Consultation fee (INR)"
              type="number"
              value={form.consultation_fee_paise}
              onChange={(e) => setForm((prev) => ({ ...prev, consultation_fee_paise: e.target.value }))}
              hint="Enter amount in rupees."
            />
          </div>
        </Card>

        <Card>
          <div className="space-y-4">
            <Input
              label="Registration number"
              value={form.registration_number}
              onChange={(e) => setForm((prev) => ({ ...prev, registration_number: e.target.value }))}
            />
            <Input
              label="Qualifications"
              value={form.qualifications}
              onChange={(e) => setForm((prev) => ({ ...prev, qualifications: e.target.value }))}
            />
            <Input
              label="Specializations"
              value={form.specializations}
              onChange={(e) => setForm((prev) => ({ ...prev, specializations: e.target.value }))}
            />
            <Input
              label="Languages"
              value={form.languages}
              onChange={(e) => setForm((prev) => ({ ...prev, languages: e.target.value }))}
              hint="Comma separated"
            />
            <div className="flex items-center gap-3">
              <input
                id="teleconsult"
                type="checkbox"
                checked={form.teleconsult_enabled}
                onChange={(e) => setForm((prev) => ({ ...prev, teleconsult_enabled: e.target.checked }))}
                className="h-4 w-4 rounded border-line text-primary focus:ring-primary"
              />
              <label htmlFor="teleconsult" className="text-sm font-medium text-ink">
                Enable teleconsult
              </label>
            </div>
            <div className="flex items-center gap-3">
              <input
                id="home_visit"
                type="checkbox"
                checked={form.home_visit_enabled}
                onChange={(e) => setForm((prev) => ({ ...prev, home_visit_enabled: e.target.checked }))}
                className="h-4 w-4 rounded border-line text-primary focus:ring-primary"
              />
              <label htmlFor="home_visit" className="text-sm font-medium text-ink">
                Enable home visits
              </label>
            </div>
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
