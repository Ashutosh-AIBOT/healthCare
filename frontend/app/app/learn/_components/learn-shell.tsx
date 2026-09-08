"use client";

import * as React from "react";
import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Search, BookOpen, Utensils, FlaskConical, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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

type NavItem = { label: string; href: string; icon: React.ReactNode; active: boolean };

export function LearnShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCategories = useCallback(async () => {
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
    void loadCategories();
  }, [loadCategories]);

  const foodCategories = categories?.filter((c) => c.kind === "food") || [];
  const testCategories = categories?.filter((c) => c.kind === "test_info") || [];

  const isFood = pathname?.startsWith("/app/learn/food");
  const isTest = pathname?.startsWith("/app/learn/test");

  const mainNav: NavItem[] = [
    { label: "Overview", href: "/app/learn", icon: <BookOpen className="h-4 w-4" />, active: pathname === "/app/learn" },
    { label: "Eat Food", href: "/app/learn/food", icon: <Utensils className="h-4 w-4" />, active: isFood },
    { label: "Test Checkup", href: "/app/learn/test", icon: <FlaskConical className="h-4 w-4" />, active: isTest },
  ];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = search.trim();
    if (!q) return;
    router.push(`/app/learn/search?q=${encodeURIComponent(q)}`);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-12">
      <div className="lg:col-span-3 space-y-4">
        <Card>
          <CardContent className="p-4">
            <h2 className="text-sm font-semibold text-ink">Learn</h2>
            <p className="mt-1 text-xs text-muted">Food & health test info</p>
            <form onSubmit={handleSearch} className="mt-3">
              <div className="flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2">
                <Search className="h-4 w-4 text-muted" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search..."
                  className="flex-1 bg-transparent text-sm outline-none"
                />
              </div>
            </form>
            <nav className="mt-4 space-y-1">
              {mainNav.map((item) => (
                <button
                  key={item.href}
                  onClick={() => router.push(item.href)}
                  className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
                    item.active ? "bg-primary-soft text-primary" : "text-muted hover:bg-mist hover:text-ink"
                  }`}
                >
                  <span className={item.active ? "text-primary" : "text-muted"}>{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </nav>
          </CardContent>
        </Card>

        {isFood && foodCategories.length > 0 && !loading && !error ? (
          <Card>
            <CardContent className="p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Food categories</h3>
              <div className="mt-2 space-y-1">
                {foodCategories.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => router.push(`/app/learn/food/${cat.slug}`)}
                    className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm transition-colors ${
                      pathname === `/app/learn/food/${cat.slug}` ? "bg-primary-soft text-primary" : "text-muted hover:bg-mist hover:text-ink"
                    }`}
                  >
                    <span>{cat.title}</span>
                    <ChevronRight className="h-4 w-4" />
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : null}

        {isTest && testCategories.length > 0 && !loading && !error ? (
          <Card>
            <CardContent className="p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Body parts</h3>
              <div className="mt-2 space-y-1">
                {testCategories.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => router.push(`/app/learn/test/${cat.slug}`)}
                    className={`flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm transition-colors ${
                      pathname === `/app/learn/test/${cat.slug}` ? "bg-primary-soft text-primary" : "text-muted hover:bg-mist hover:text-ink"
                    }`}
                  >
                    <span>{cat.title}</span>
                    <ChevronRight className="h-4 w-4" />
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : null}
      </div>

      <div className="lg:col-span-9">
        {error ? (
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-critical">{error}</p>
              <button onClick={loadCategories} className="mt-2 text-sm font-semibold text-primary">Retry</button>
            </CardContent>
          </Card>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
