"use client";

import * as React from "react";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, EmptyState } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type Test = {
  id: string;
  body_part_id: string;
  name: string;
  what_it_checks: string | null;
  prep_note: string | null;
  fasting_required: boolean;
  sort_order: number;
};

export default function LearnTestDetailPage() {
  const params = useParams();
  const slug = params?.slug as string;
  const [tests, setTests] = useState<Test[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!slug) return;
    setError(null);
    setLoading(true);
    try {
      const res = await apiClient<Test[]>(`/api/v1/learn/body-parts/${slug}/tests`);
      if (!res.error) {
        setTests(res.data || []);
      } else {
        setError(res.error.detail || "Failed to load tests");
      }
    } catch {
      setError("Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded-xl bg-mist" />
        <div className="h-64 animate-pulse rounded-[1.75rem] border border-line/30 bg-surface" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-critical">{error}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Tests</h1>
        <p className="mt-1 text-sm text-muted">Recommended tests for this body part.</p>
      </div>

      {tests && tests.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tests.map((test) => (
            <Card key={test.id}>
              <CardHeader>
                <p className="text-sm font-semibold text-ink">{test.name}</p>
                {test.fasting_required && (
                  <span className="mt-1 inline-block rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">Fasting required</span>
                )}
              </CardHeader>
              <CardContent>
                {test.what_it_checks && (
                  <div className="mb-2">
                    <p className="text-xs font-semibold text-muted">What it checks</p>
                    <p className="text-sm text-ink">{test.what_it_checks}</p>
                  </div>
                )}
                {test.prep_note && (
                  <div>
                    <p className="text-xs font-semibold text-muted">Preparation</p>
                    <p className="text-sm text-ink">{test.prep_note}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState title="No tests found" description="There are no tests listed for this body part yet." />
      )}
    </div>
  );
}
