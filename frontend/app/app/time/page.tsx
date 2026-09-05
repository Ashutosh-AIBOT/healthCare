"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type Appointment = {
  id: string;
  title: string;
  datetime: string;
  provider: string;
  status: string;
};

type Activity = {
  id: string;
  action: string;
  timestamp: string;
};

export default function TimeManagementPage() {
  const [appointments, setAppointments] = useState<Appointment[] | null>(null);
  const [activity, setActivity] = useState<Activity[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<{ upcoming: number; thisWeek: number; reminders: number; hours: number } | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const [appt, act] = await Promise.all([
      apiClient<Appointment[]>("/api/v1/appointments"),
      apiClient<Activity[]>("/api/v1/activity"),
    ]);
    if (appt.error) {
      setError(appt.error.detail || "Failed to load schedule.");
      setAppointments([]);
      return;
    }
    if (act.error) {
      setError(act.error.detail || "Failed to load activity.");
      setActivity([]);
      return;
    }
    const appts = appt.data || [];
    const acts = act.data || [];
    setAppointments(appts);
    setActivity(acts);
    const now = new Date();
    const weekEnd = new Date(now);
    weekEnd.setDate(weekEnd.getDate() + 7);
    setStats({
      upcoming: appts.filter((a) => new Date(a.datetime) >= now).length,
      thisWeek: appts.filter((a) => {
        const d = new Date(a.datetime);
        return d >= now && d <= weekEnd;
      }).length,
      reminders: appts.filter((a) => a.status === "reminder").length,
      hours: appts.reduce((sum, a) => {
        const [h] = a.title.match(/(\d+)h/) || ["0"];
        return sum + Number(h);
      }, 0),
    });
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const isLoading = appointments === null && activity === null && !error;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-10 w-48" />
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
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Time Management</h1>
        <p className="text-sm text-muted">Schedule appointments, set reminders, and track consultation hours.</p>
      </div>

      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Upcoming</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{stats?.upcoming ?? 0}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">This Week</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{stats?.thisWeek ?? 0}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Reminders</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{stats?.reminders ?? 0}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Consultation Hours</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{stats?.hours ?? 0}h</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card lg:col-span-2">
          <h2 className="font-semibold text-ink">Upcoming Schedule</h2>
          {!appointments?.length ? (
            <EmptyState
              title="No appointments"
              description="Your upcoming appointments will appear here once scheduled."
            />
          ) : (
            <ul className="mt-4 space-y-3">
              {appointments.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-4 rounded-2xl bg-mist/60 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-ink">{a.title}</p>
                    <p className="text-xs text-muted">
                      {new Date(a.datetime).toLocaleString()} · {a.provider}
                    </p>
                  </div>
                  <span className="rounded-full bg-mist px-2.5 py-1 text-[11px] font-semibold text-muted capitalize">
                    {a.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <h2 className="font-semibold text-ink">Quick Actions</h2>
          <p className="mt-2 text-sm text-muted">
            Book appointments, set recurring reminders, and manage availability.
          </p>
          <div className="mt-4 space-y-2">
            <button type="button" className="w-full rounded-2xl border border-line bg-surface px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-mist">
              New Appointment
            </button>
            <button type="button" className="w-full rounded-2xl border border-line bg-surface px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-mist">
              Set Reminder
            </button>
            <button type="button" className="w-full rounded-2xl border border-line bg-surface px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-mist">
              Manage Availability
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          <h2 className="font-semibold text-ink">Recent Activity</h2>
          <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
            {!activity?.length ? (
              <EmptyState
                title="No recent activity"
                description="Appointment history and time tracking will appear here."
              />
            ) : (
              <ul className="space-y-3">
                {activity.map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-4 border-b border-line/50 py-2 last:border-b-0">
                    <span className="text-sm text-ink">{a.action}</span>
                    <span className="text-xs text-muted">
                      {new Date(a.timestamp).toLocaleString()}
                    </span>
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
