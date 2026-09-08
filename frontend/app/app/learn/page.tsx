"use client";

import * as React from "react";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, EmptyState } from "@/components/ui/card";
import { MedicalNote } from "@/components/learn/medical-note";
import { apiClient } from "@/lib/auth-client";

type Category = {
  id: string;
  slug: string;
  title: string;
  kind: "food" | "test_info";
  description: string | null;
  icon: string | null;
  sort_order: number;
};

export default function LearnOverviewPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await apiClient<Category[]>("/api/v1/learn/categories");
      if (!res.error) {
        setCategories(res.data || []);
      } else {
        setError(res.error.detail || "Failed to load categories");
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
      <div className="space-y-6">
        <div className="h-8 w-48 animate-pulse rounded-xl bg-mist" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-40 animate-pulse rounded-[1.75rem] border border-line/30 bg-surface" />
          ))}
        </div>
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
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Learn</h1>
        <p className="mt-1 text-sm text-muted">Explore food and health test information.</p>
      </div>

      {categories && categories.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => router.push(cat.kind === "food" ? `/app/learn/food/${cat.slug}` : `/app/learn/test/${cat.slug}`)}
              className="rounded-[1.5rem] border border-line bg-surface p-5 text-left shadow-card transition hover:shadow-lift"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">{cat.kind === "food" ? "Food" : "Test"}</p>
              <p className="mt-1 font-semibold text-ink">{cat.title}</p>
              {cat.description && <p className="mt-1 text-xs text-muted">{cat.description}</p>}
            </button>
          ))}
        </div>
      ) : (
        <EmptyState title="No categories yet" description="Check back soon for healthy eating and test guides." />
      )}

      <MedicalNote />
    </div>
  );
}
