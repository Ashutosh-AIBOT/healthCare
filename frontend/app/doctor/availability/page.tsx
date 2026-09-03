"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/auth-client";

type Slot = {
  id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
  is_active: boolean;
};

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function DoctorAvailabilityPage() {
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    day_of_week: 1,
    start_time: "09:00",
    end_time: "13:00",
    slot_duration_minutes: 30,
    is_active: true,
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await apiClient<Slot[]>("/api/v1/providers/me/availability");
    if (res.error) {
      setError(res.error.detail || "Failed to load availability.");
      setSlots([]);
      setLoading(false);
      return;
    }
    setSlots(res.data || []);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const addSlot = async () => {
    setSaving(true);
    setError(null);
    const res = await apiClient<Slot>("/api/v1/providers/me/availability", {
      method: "POST",
      body: JSON.stringify(form),
    });
    if (res.error) {
      setError(res.error.detail || "Failed to add slot.");
      setSaving(false);
      return;
    }
    setSlots((prev) => [...(prev || []), res.data!]);
    setSaving(false);
  };

  const updateSlot = async (slotId: string, payload: Partial<Slot>) => {
    const res = await apiClient<Slot>(`/api/v1/providers/me/availability/${slotId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    if (res.error) {
      setError(res.error.detail || "Failed to update slot.");
      return;
    }
    setSlots((prev) => prev?.map((s) => (s.id === slotId ? res.data! : s)) || []);
  };

  const removeSlot = async (slotId: string) => {
    const res = await apiClient(`/api/v1/providers/me/availability/${slotId}`, {
      method: "DELETE",
    });
    if (res.error) {
      setError(res.error.detail || "Failed to remove slot.");
      return;
    }
    setSlots((prev) => prev?.filter((s) => s.id !== slotId) || []);
  };

  if (loading) {
    return (
      <div className="min-h-dvh bg-[linear-gradient(180deg,var(--color-mist)_0%,var(--color-foam)_28%,var(--color-foam)_100%)]">
        <main className="mx-auto max-w-3xl px-4 py-10 md:px-6 md:py-12">
          <Skeleton className="h-8 w-48" />
          <div className="mt-8 space-y-4">
            <Skeleton className="h-40 w-full" />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-[linear-gradient(180deg,var(--color-mist)_0%,var(--color-foam)_28%,var(--color-foam)_100%)]">
      <main className="mx-auto max-w-3xl space-y-6 px-4 py-10 md:px-6 md:py-12">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Availability</h1>
          <p className="mt-2 text-sm text-muted">Set weekly hours so patients can book slots.</p>
        </div>

        {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

        <Card>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium text-ink">Day</label>
              <select
                value={form.day_of_week}
                onChange={(e) => setForm((prev) => ({ ...prev, day_of_week: Number(e.target.value) }))}
                className="mt-1.5 w-full rounded-2xl border border-line bg-surface px-3 py-2 text-sm"
              >
                {DAYS.map((d, i) => (
                  <option key={i} value={i}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-ink">Slot duration (min)</label>
              <input
                type="number"
                value={form.slot_duration_minutes}
                onChange={(e) => setForm((prev) => ({ ...prev, slot_duration_minutes: Number(e.target.value) }))}
                className="mt-1.5 w-full rounded-2xl border border-line bg-surface px-3 py-2 text-sm"
              />
            </div>
            <Input
              label="Start time"
              type="time"
              value={form.start_time}
              onChange={(e) => setForm((prev) => ({ ...prev, start_time: e.target.value }))}
            />
            <Input
              label="End time"
              type="time"
              value={form.end_time}
              onChange={(e) => setForm((prev) => ({ ...prev, end_time: e.target.value }))}
            />
          </div>
          <div className="mt-4 flex justify-end">
            <Button onClick={() => void addSlot()} loading={saving}>
              Add slot
            </Button>
          </div>
        </Card>

        {!slots?.length ? (
          <EmptyState
            title="No slots set"
            description="Add weekly availability so patients know when you can see them."
          />
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {slots.map((slot) => (
              <li key={slot.id}>
                <Card className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-semibold text-ink">
                      {DAYS[slot.day_of_week]} · {slot.start_time} – {slot.end_time}
                    </p>
                    <p className="text-sm text-muted">{slot.slot_duration_minutes} min slots</p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        updateSlot(slot.id, { is_active: !slot.is_active })
                      }
                    >
                      {slot.is_active ? "Disable" : "Enable"}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => void removeSlot(slot.id)}>
                      Remove
                    </Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
