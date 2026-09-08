"use client";

import * as React from "react";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, EmptyState } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type Category = { id: string; slug: string; title: string; kind: string; description: string | null };
type LearnItem = { id: string; slug: string; title: string; summary: string | null; category_id: string };
type BodyTest = { id: string; name: string; what_it_checks: string | null; body_part_id: string };

export default function LearnSearchPage() {
  const searchParams = useSearchParams();
  const q = searchParams?.get("q") || "";
  const [results, setResults] = useState<{ categories: Category[]; items: LearnItem[]; tests: BodyTest[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!q) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient<{ categories: Category[]; items: LearnItem[]; tests: BodyTest[] }>(`/api/v1/learn/search?q=${encodeURIComponent(q)}`);
      if (!res.error) {
        setResults(res.data || { categories: [], items: [], tests: [] });
      } else {
        setError(res.error.detail || "Search failed");
      }
    } catch {
      setError("Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [q]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Search</h1>
        <p className="mt-1 text-sm text-muted">Results for &quot;{q}&quot;</p>
      </div>

      {loading && <p className="text-sm text-muted">Searching...</p>}
      {error && <p className="text-sm text-critical">{error}</p>}

      {!loading && results && (
        <div className="space-y-6">
          {results.categories.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-ink">Categories</h2>
              <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {results.categories.map((cat) => (
                  <Card key={cat.id}>
                    <CardContent className="p-4">
                      <p className="text-sm font-semibold text-ink">{cat.title}</p>
                      <p className="text-xs text-muted">{cat.kind}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {results.items.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-ink">Food Items</h2>
              <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {results.items.map((item) => (
                  <Card key={item.id}>
                    <CardContent className="p-4">
                      <p className="text-sm font-semibold text-ink">{item.title}</p>
                      {item.summary && <p className="text-xs text-muted">{item.summary}</p>}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {results.tests.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-ink">Tests</h2>
              <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {results.tests.map((test) => (
                  <Card key={test.id}>
                    <CardContent className="p-4">
                      <p className="text-sm font-semibold text-ink">{test.name}</p>
                      {test.what_it_checks && <p className="text-xs text-muted">{test.what_it_checks}</p>}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {results.categories.length === 0 && results.items.length === 0 && results.tests.length === 0 && (
            <EmptyState title="No results" description="Try a different search term." />
          )}
        </div>
      )}
    </div>
  );
}
