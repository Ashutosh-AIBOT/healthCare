"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type TestItem = {
  id: string;
  name: string;
  description: string;
  status: "pending" | "completed" | "failed";
  date: string;
};

export default function TestingPage() {
  const [tests, setTests] = useState<TestItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const res = await apiClient<TestItem[]>("/api/v1/testing/tests");
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
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-48 animate-pulse rounded-xl bg-mist" />
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
      <div className="space-y-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Testing</h1>
        <ErrorState description={error} onRetry={() => void load()} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Testing</h1>
          <p className="mt-1 text-sm text-muted">Track and manage your medical tests and lab reports.</p>
        </div>
        <Button onClick={() => {}}>Add Test</Button>
      </div>

      {tests && tests.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tests.map((test) => (
            <Card key={test.id}>
              <CardHeader>
                <p className="text-sm font-semibold text-ink">{test.name}</p>
                <p className="text-xs text-muted">{test.date}</p>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted">{test.description}</p>
                <span className={`mt-3 inline-block rounded-full px-3 py-1 text-xs font-semibold ${
                  test.status === "completed" ? "bg-primary-soft text-primary" :
                  test.status === "failed" ? "bg-critical/10 text-critical" :
                  "bg-mist text-muted"
                }`}>
                  {test.status}
                </span>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No tests yet"
          description="Add your first test to start tracking your health metrics."
          action={<Button onClick={() => {}}>Add Test</Button>}
        />
      )}
    </div>
  );
}
