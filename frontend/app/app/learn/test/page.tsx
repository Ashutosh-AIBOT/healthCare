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

export default function LearnTestPage() {
  const router = useRouter();
  const [parts, setParts] = useState<BodyPart[] | null>(null);
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

  useEffect(() => {
    void load();
  }, [load]);

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

      {parts && parts.length > 0 ? (
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
