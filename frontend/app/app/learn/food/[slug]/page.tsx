"use client";

import * as React from "react";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type LearnItem = {
  id: string;
  category_id: string;
  slug: string;
  title: string;
  summary: string | null;
  content: string | null;
  image_url: string | null;
  nutrition: Record<string, any> | null;
  benefits: string[] | null;
  healthy_role: string | null;
  sort_order: number;
};

export default function LearnFoodDetailPage() {
  const params = useParams();
  const slug = params?.slug as string;
  const [item, setItem] = useState<LearnItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!slug) return;
    setError(null);
    setLoading(true);
    try {
      const res = await apiClient<LearnItem>(`/api/v1/learn/items/${slug}`);
      if (!res.error) {
        setItem(res.data || null);
      } else {
        setError(res.error.detail || "Failed to load item");
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

  if (error || !item) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-critical">{error || "Item not found"}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">{item.title}</h1>
        {item.summary && <p className="mt-2 text-sm text-muted">{item.summary}</p>}
      </div>

      {item.image_url && (
        <img src={item.image_url} alt={item.title} className="h-64 w-full rounded-[1.5rem] object-cover" />
      )}

      {item.content && (
        <Card>
          <CardContent className="p-6">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">{item.content}</p>
          </CardContent>
        </Card>
      )}

      {item.nutrition && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-sm font-semibold text-ink">Nutrition</h3>
            <pre className="mt-2 text-xs text-muted">{JSON.stringify(item.nutrition, null, 2)}</pre>
          </CardContent>
        </Card>
      )}

      {item.benefits && item.benefits.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-sm font-semibold text-ink">Benefits</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
              {item.benefits.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {item.healthy_role && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-sm font-semibold text-ink">Healthy Role</h3>
            <p className="mt-2 text-sm text-muted">{item.healthy_role}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
