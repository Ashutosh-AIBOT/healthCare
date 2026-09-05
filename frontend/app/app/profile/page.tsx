"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type UserProfile = {
  id: string;
  email: string;
  full_name: string | null;
  handle: string | null;
  role: string;
  is_verified: boolean;
  totp_enabled: boolean;
  created_at: string;
};

type ConnectedAccount = {
  id: string;
  provider: string;
  connected_at: string;
};

type Preference = {
  id: string;
  key: string;
  value: string;
  updated_at: string;
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [accounts, setAccounts] = useState<ConnectedAccount[] | null>(null);
  const [preferences, setPreferences] = useState<Preference[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const [me, acc, prefs] = await Promise.all([
      apiClient<UserProfile>("/api/v1/auth/me"),
      apiClient<ConnectedAccount[]>("/api/v1/accounts"),
      apiClient<Preference[]>("/api/v1/preferences"),
    ]);
    if (me.error) {
      setError(me.error.detail || "Failed to load profile.");
      setProfile(null);
      return;
    }
    if (acc.error) {
      setError(acc.error.detail || "Failed to load connected accounts.");
      setAccounts([]);
      return;
    }
    if (prefs.error) {
      setError(prefs.error.detail || "Failed to load preferences.");
      setPreferences([]);
      return;
    }
    setProfile(me.data || null);
    setAccounts(acc.data || []);
    setPreferences(prefs.data || []);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const isLoading = profile === null && accounts === null && preferences === null && !error;

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
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Profile</h1>
        <p className="text-sm text-muted">Manage your personal details, preferences, and connected accounts.</p>
      </div>

      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Member Since</p>
          <p className="mt-2 text-2xl font-semibold text-ink">
            {profile?.created_at ? new Date(profile.created_at).getFullYear() : "—"}
          </p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Connected</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{accounts?.length ?? 0}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Family</p>
          <p className="mt-2 text-2xl font-semibold text-ink">—</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Reports</p>
          <p className="mt-2 text-2xl font-semibold text-ink">—</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card lg:col-span-2">
          <h2 className="font-semibold text-ink">Account Details</h2>
          {!profile ? (
            <p className="mt-2 text-sm text-muted">Profile editing and preference controls will appear here.</p>
          ) : (
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-xs text-muted">Full name</dt>
                <dd className="text-sm font-semibold text-ink">{profile.full_name || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Email</dt>
                <dd className="text-sm font-semibold text-ink">{profile.email}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Handle</dt>
                <dd className="text-sm font-semibold text-ink">{profile.handle || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Role</dt>
                <dd className="text-sm font-semibold text-ink capitalize">{profile.role}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Verified</dt>
                <dd className="text-sm font-semibold text-ink">{profile.is_verified ? "Yes" : "No"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">2FA</dt>
                <dd className="text-sm font-semibold text-ink">{profile.totp_enabled ? "Enabled" : "Disabled"}</dd>
              </div>
            </dl>
          )}
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <h2 className="font-semibold text-ink">Connected Accounts</h2>
          {!accounts?.length ? (
            <p className="mt-2 text-sm text-muted">
              Manage linked providers and authentication methods.
            </p>
          ) : (
            <ul className="mt-4 space-y-2">
              {accounts.map((a) => (
                <li key={a.id} className="flex items-center justify-between rounded-2xl bg-mist/60 px-4 py-2">
                  <span className="text-sm font-semibold text-ink capitalize">{a.provider}</span>
                  <span className="text-xs text-muted">
                    {new Date(a.connected_at).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          <h2 className="font-semibold text-ink">Preferences</h2>
          <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
            {!preferences?.length ? (
              <p className="text-sm text-muted">Theme, notifications, and privacy settings will load here.</p>
            ) : (
              <ul className="space-y-2">
                {preferences.map((p) => (
                  <li key={p.id} className="flex items-center justify-between rounded-2xl bg-mist/60 px-4 py-2">
                    <span className="text-sm text-ink">{p.key}</span>
                    <span className="text-sm font-semibold text-ink">{p.value}</span>
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
