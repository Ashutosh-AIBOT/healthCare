"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";

type Meal = {
  id: string;
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fats: number;
  time: string;
};

type NutritionSummary = {
  calories: number;
  water: number;
  meals: number;
  score: number;
};

export default function FoodPage() {
  const [meals, setMeals] = useState<Meal[] | null>(null);
  const [summary, setSummary] = useState<NutritionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const [m, s] = await Promise.all([
      apiClient<Meal[]>("/api/v1/meals"),
      apiClient<NutritionSummary>("/api/v1/nutrition/summary"),
    ]);
    if (m.error) {
      setError(m.error.detail || "Failed to load meals.");
      setMeals([]);
      return;
    }
    if (s.error) {
      setError(s.error.detail || "Failed to load nutrition summary.");
      setSummary({ calories: 0, water: 0, meals: 0, score: 0 });
      return;
    }
    setMeals(m.data || []);
    setSummary(s.data || { calories: 0, water: 0, meals: 0, score: 0 });
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const isLoading = meals === null && summary === null && !error;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-10 w-24" />
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
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Food</h1>
        <p className="text-sm text-muted">Track meals, nutrition insights, and dietary preferences.</p>
      </div>

      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Today&apos;s Calories</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{summary?.calories.toLocaleString() ?? 0}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Water Intake</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{summary?.water ? `${summary.water}L` : "0L"}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Meals Logged</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{summary?.meals ?? 0}</p>
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <p className="text-xs text-muted">Nutrient Score</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{summary?.score ?? 0}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card lg:col-span-2">
          <h2 className="font-semibold text-ink">Nutrition Tracker</h2>
          {!meals?.length ? (
            <EmptyState
              title="No meals logged"
              description="Start logging your meals to see nutrition insights and daily breakdowns."
            />
          ) : (
            <ul className="mt-4 space-y-3">
              {meals.map((meal) => (
                <li key={meal.id} className="flex items-center justify-between gap-4 rounded-2xl bg-mist/60 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-ink">{meal.name}</p>
                    <p className="text-xs text-muted">
                      {meal.time} · P: {meal.protein}g · C: {meal.carbs}g · F: {meal.fats}g
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-ink">{meal.calories} kcal</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
          <h2 className="font-semibold text-ink">Daily Targets</h2>
          <p className="mt-2 text-sm text-muted">
            Track progress against calories, protein, carbs, and fats.
          </p>
          <div className="mt-4 grid gap-2">
            {[
              { label: "Calories", current: summary?.calories ?? 0, target: 2200 },
              { label: "Protein", current: meals?.reduce((s, m) => s + m.protein, 0) ?? 0, target: 150 },
              { label: "Carbs", current: meals?.reduce((s, m) => s + m.carbs, 0) ?? 0, target: 250 },
              { label: "Fats", current: meals?.reduce((s, m) => s + m.fats, 0) ?? 0, target: 65 },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between rounded-2xl bg-mist/60 px-4 py-2">
                <span className="text-sm text-ink">{item.label}</span>
                <span className="text-sm font-semibold text-ink">
                  {item.current} / {item.target}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-3">
          <h2 className="font-semibold text-ink">Recent Meals</h2>
          <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
            {!meals?.length ? (
              <EmptyState
                title="No meal history"
                description="Meal history and nutrition insights will load here."
              />
            ) : (
              <p className="text-sm text-muted">
                Showing {meals.length} meal{meals.length === 1 ? "" : "s"} logged today.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
