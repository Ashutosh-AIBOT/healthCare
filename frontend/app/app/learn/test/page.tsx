"use client";

import * as React from "react";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, EmptyState } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type BodyPart = {
  id: string;
  slug: string;
  name: string;
  order_index: number;
  description: string | null;
};

type FastingMode = "all" | "fasting" | "nonfasting";

type FastingTest = {
  id: string;
  body_part_id: string;
  name: string;
  what_it_checks: string | null;
  prep_note: string | null;
  fasting_required: boolean;
  sort_order: number;
};

export default function LearnTestPage() {
  const router = useRouter();
  const [parts, setParts] = useState<BodyPart[] | null>(null);
  const [mode, setMode] = useState<FastingMode>("all");
  const [fastingTests, setFastingTests] = useState<FastingTest[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await apiClient<BodyPart[]>("/api/v1/learn/body-parts");
      if (!res.error) {
        setParts(res.data || []);
      } else {
        setError(res.error.detail || "Failed to load body parts");
      }
    } catch {
      setError("Something went wrong");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFasting = useCallback(async (m: Exclude<FastingMode, "all">) => {
    setError(null);
    setFastingTests(null);
    try {
      const res = await apiClient<FastingTest[]>(
        `/api/v1/learn/tests?fasting=${m === "fasting" ? "true" : "false"}`,
      );
      if (!res.error) {
        setFastingTests(res.data || []);
      } else {
        setError(res.error.detail || "Failed to load tests");
      }
    } catch {
      setError("Something went wrong");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (mode !== "all") void loadFasting(mode);
  }, [mode, loadFasting]);

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-40 animate-pulse rounded-[1.75rem] border border-line/30 bg-surface" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-critical">{error}</p>
          <button onClick={load} className="mt-2 text-sm font-semibold text-primary">Retry</button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Test Checkup</h1>
        <p className="mt-1 text-sm text-muted">Select a body part to view recommended tests.</p>
      </div>

      <div
        role="group"
        aria-label="Fasting filter"
        className="flex flex-wrap gap-2"
      >
        {(
          [
            ["all", "All tests"],
            ["fasting", "Fasting"],
            ["nonfasting", "Non-fasting"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setMode(value)}
            aria-pressed={mode === value}
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition-colors ${
              mode === value
                ? "border-primary bg-primary-soft text-primary"
                : "border-line bg-surface text-muted hover:bg-mist hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {mode !== "all" ? (
        fastingTests === null ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-32 animate-pulse rounded-[1.75rem] border border-line/30 bg-surface" />
            ))}
          </div>
        ) : fastingTests.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {fastingTests.map((t) => (
              <div
                key={t.id}
                className="rounded-[1.5rem] border border-line bg-surface p-5 shadow-card"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold text-ink">{t.name}</p>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${
                      t.fasting_required
                        ? "bg-apricot/20 text-apricot"
                        : "bg-mist text-muted"
                    }`}
                  >
                    {t.fasting_required ? "Fasting" : "Non-fasting"}
                  </span>
                </div>
                {t.what_it_checks ? (
                  <p className="mt-1 line-clamp-2 text-sm text-muted">{t.what_it_checks}</p>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No tests found" description="No tests in this group yet." />
        )
      ) : parts && parts.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {parts.map((part) => (
            <button
              key={part.id}
              onClick={() => router.push(`/app/learn/test/${part.slug}`)}
              className="rounded-[1.5rem] border border-line bg-surface p-5 text-left shadow-card transition hover:shadow-lift"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Body part</p>
              <p className="mt-1 font-semibold text-ink">{part.name}</p>
              {part.description && <p className="mt-1 text-xs text-muted">{part.description}</p>}
            </button>
          ))}
        </div>
      ) : (
        <EmptyState title="No body parts yet" description="Check back soon for health test guides." />
      )}
    </div>
  );
}
