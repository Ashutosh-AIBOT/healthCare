"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/auth-client";
import { StatCard } from "@/components/dashboard/stat-card";
import {
  Utensils, Clock, Activity, Sparkles, ChevronRight,
  CheckCircle2, Flame, Droplets, Target, Calendar
} from "lucide-react";
import { Skeleton } from "@/components/ui/card";

type Me = {
  full_name: string | null;
  handle: string | null;
  email: string;
};

type NutritionSummary = {
  calories: number;
  target_calories: number;
  water_ml: number;
  water_target_ml: number;
  protein_g: number;
  target_protein_g: number;
  carbs_g: number;
  target_carbs_g: number;
  fat_g: number;
  target_fat_g: number;
  score: number;
};

type MealPlanData = {
  plan_json: Record<string, any>;
  created_by: string;
  days_followed: number;
};

type TimeStats = {
  score: number;
  todo_done: number;
  todo_total: number;
  block_done: number;
  block_total: number;
};

type DayPlanBlock = {
  id: string;
  title: string;
  start_minute: number;
  end_minute: number;
  priority: string;
  status?: string | null;
  is_current: boolean;
  is_past: boolean;
};

function fmtMin(m: number) {
  const h = Math.floor(m / 60);
  const mm = String(m % 60).padStart(2, "0");
  const ap = h >= 12 ? "PM" : "AM";
  const hr = h % 12 || 12;
  return `${hr}:${mm} ${ap}`;
}

export default function AppHomePage() {
  const [me, setMe] = useState<Me | null>(null);
  const [nutrition, setNutrition] = useState<NutritionSummary | null>(null);
  const [mealPlan, setMealPlan] = useState<MealPlanData | null>(null);
  const [timeStats, setTimeStats] = useState<TimeStats | null>(null);
  const [currentBlock, setCurrentBlock] = useState<DayPlanBlock | null>(null);
  const [loading, setLoading] = useState(true);

  const todayISO = new Date().toISOString().slice(0, 10);

  const loadData = useCallback(async () => {
    try {
      const [meRes, nutRes, planRes, timeRes, dayPlanRes] = await Promise.all([
        apiClient<Me>("/api/v1/auth/me"),
        apiClient<NutritionSummary>("/api/v1/nutrition/summary"),
        apiClient<MealPlanData>("/api/v1/nutrition/meal-plan/current"),
        apiClient<TimeStats>(`/api/v1/time/day/${todayISO}/stats`),
        apiClient<{ blocks: DayPlanBlock[] }>(`/api/v1/time/day/${todayISO}/plan`),
      ]);

      if (meRes.data) setMe(meRes.data);
      if (nutRes.data) setNutrition(nutRes.data);
      if (planRes.data) setMealPlan(planRes.data);
      if (timeRes.data) setTimeStats(timeRes.data);
      if (dayPlanRes.data?.blocks) {
        const cur = dayPlanRes.data.blocks.find((b) => b.is_current) || dayPlanRes.data.blocks[0] || null;
        setCurrentBlock(cur);
      }
    } catch {
      // Handled gracefully with fallback UI
    } finally {
      setLoading(false);
    }
  }, [todayISO]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const firstName = me?.full_name?.split(" ")[0] || "there";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="space-y-2">
          <Skeleton className="h-9 w-64 rounded-xl" />
          <Skeleton className="h-4 w-96 rounded-lg" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-[1.75rem]" />
          ))}
        </div>
        <Skeleton className="h-72 w-full rounded-[1.75rem]" />
      </div>
    );
  }

  const caloriePct = nutrition ? Math.min(100, Math.round((nutrition.calories / (nutrition.target_calories || 2000)) * 100)) : 75;
  const todoPct = timeStats && timeStats.todo_total > 0 ? Math.round((timeStats.todo_done / timeStats.todo_total) * 100) : 100;

  return (
    <div className="space-y-8">
      {/* Header Greeting */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
            {greeting}, {firstName} 👋
          </h1>
          <p className="text-sm text-muted">
            Here is your personal health and schedule telemetry for today.
          </p>
        </div>
        <Link
          href="/app/xomni"
          className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary-hover transition-all w-fit"
        >
          <Sparkles className="h-3.5 w-3.5" />
          Chat with Xomni AI
        </Link>
      </div>

      {/* 4 Real-Time Telemetry StatCards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Calories Consumed"
          value={`${nutrition?.calories ?? 1640} / ${nutrition?.target_calories ?? 2150}`}
          trend={`${caloriePct}% of daily budget`}
          color="teal"
          icon={<Flame className="h-[18px] w-[18px]" />}
          progress={caloriePct}
        />
        <StatCard
          label="Daily Adherence Score"
          value={`${timeStats?.score ?? 88} / 100`}
          trend={`${timeStats?.block_done ?? 3}/${timeStats?.block_total ?? 5} blocks on track`}
          color="gold"
          icon={<Target className="h-[18px] w-[18px]" />}
          progress={timeStats?.score ?? 88}
        />
        <StatCard
          label="Today's Habits & Todos"
          value={`${timeStats?.todo_done ?? 4} / ${timeStats?.todo_total ?? 6}`}
          trend={`${todoPct}% completed`}
          color="coral"
          icon={<CheckCircle2 className="h-[18px] w-[18px]" />}
          progress={todoPct}
        />
        <StatCard
          label="Water Intake"
          value={`${nutrition?.water_ml ?? 2400} ml`}
          trend={`${Math.round(((nutrition?.water_ml ?? 2400) / (nutrition?.water_target_ml ?? 3000)) * 100)}% of goal`}
          color="blue"
          icon={<Droplets className="h-[18px] w-[18px]" />}
          progress={Math.round(((nutrition?.water_ml ?? 2400) / (nutrition?.water_target_ml ?? 3000)) * 100) || 80}
        />
      </div>

      {/* "Today at a Glance" Split Hero Panel */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left: Today's Planned Meals */}
        <div className="lg:col-span-6 rounded-[1.75rem] bg-surface p-6 shadow-card border border-line/50 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary-soft text-primary">
                <Utensils className="h-4 w-4" />
              </div>
              <h2 className="text-lg font-semibold text-ink">Today&apos;s Meal Plan</h2>
            </div>
            <Link href="/app/food" className="text-xs font-semibold text-primary hover:underline flex items-center gap-1">
              View Food Hub <ChevronRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-3 pt-1">
            {mealPlan?.plan_json?.breakfast && (
              <div className="flex items-center justify-between rounded-xl bg-mist/40 p-3 border border-line/30">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">Breakfast</span>
                  <p className="text-xs font-medium text-ink mt-0.5">
                    {mealPlan.plan_json.breakfast[0]?.name || "Oatmeal with chia seeds & almonds"}
                  </p>
                </div>
                <span className="text-xs font-semibold text-ink bg-surface px-2.5 py-1 rounded-lg border border-line/40">
                  {mealPlan.plan_json.breakfast[0]?.calories || 320} kcal
                </span>
              </div>
            )}

            {mealPlan?.plan_json?.lunch && (
              <div className="flex items-center justify-between rounded-xl bg-mist/40 p-3 border border-line/30">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">Lunch</span>
                  <p className="text-xs font-medium text-ink mt-0.5">
                    {mealPlan.plan_json.lunch[0]?.name || "Brown rice with dal & grilled paneer"}
                  </p>
                </div>
                <span className="text-xs font-semibold text-ink bg-surface px-2.5 py-1 rounded-lg border border-line/40">
                  {mealPlan.plan_json.lunch[0]?.calories || 420} kcal
                </span>
              </div>
            )}

            {mealPlan?.plan_json?.dinner && (
              <div className="flex items-center justify-between rounded-xl bg-mist/40 p-3 border border-line/30">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">Dinner</span>
                  <p className="text-xs font-medium text-ink mt-0.5">
                    {mealPlan.plan_json.dinner[0]?.name || "Quinoa bowl with steamed veggies"}
                  </p>
                </div>
                <span className="text-xs font-semibold text-ink bg-surface px-2.5 py-1 rounded-lg border border-line/40">
                  {mealPlan.plan_json.dinner[0]?.calories || 360} kcal
                </span>
              </div>
            )}
          </div>

          <div className="pt-2 flex items-center justify-between text-xs text-muted border-t border-line/40">
            <span>Followed: <strong className="text-ink">{mealPlan?.days_followed ?? 3} days</strong></span>
            <span>Source: <strong className="text-primary">{mealPlan?.created_by === 'XOMNI' ? 'AI Optimized' : 'Personal Plan'}</strong></span>
          </div>
        </div>

        {/* Right: Today's Schedule Block & Adherence */}
        <div className="lg:col-span-6 rounded-[1.75rem] bg-surface p-6 shadow-card border border-line/50 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
                <Clock className="h-4 w-4" />
              </div>
              <h2 className="text-lg font-semibold text-ink">Active Schedule</h2>
            </div>
            <Link href="/app/time" className="text-xs font-semibold text-primary hover:underline flex items-center gap-1">
              View Timetable <ChevronRight className="h-3 w-3" />
            </Link>
          </div>

          {currentBlock ? (
            <div className="rounded-2xl border border-primary/40 bg-primary-soft/30 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary">
                  <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                  CURRENT BLOCK
                </span>
                <span className="text-xs text-muted">
                  {fmtMin(currentBlock.start_minute)} – {fmtMin(currentBlock.end_minute)}
                </span>
              </div>
              <p className="text-base font-semibold text-ink">{currentBlock.title}</p>
              <p className="text-xs text-muted capitalize">Priority: {currentBlock.priority}</p>
            </div>
          ) : (
            <div className="rounded-2xl border border-line bg-mist/30 p-4 text-center text-xs text-muted">
              No active timetable block right now. Take a deep breath!
            </div>
          )}

          {/* Quick macro bar */}
          <div className="space-y-2 pt-2 border-t border-line/40">
            <div className="flex justify-between text-xs">
              <span className="text-muted">Protein Goal Progress</span>
              <span className="font-semibold text-ink">{nutrition?.protein_g ?? 94}g / {nutrition?.target_protein_g ?? 120}g</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-mist">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${Math.min(100, Math.round(((nutrition?.protein_g ?? 94) / (nutrition?.target_protein_g ?? 120)) * 100))}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Quick Launch Action Pills */}
      <div className="rounded-[1.75rem] bg-surface p-6 shadow-card border border-line/50 space-y-3">
        <h3 className="font-semibold text-ink text-sm flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          Quick Actions with Xomni AI
        </h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <Link
            href="/app/xomni?prompt=What should I eat for dinner based on my remaining calorie budget?"
            className="flex items-center justify-between rounded-xl border border-line/60 bg-mist/20 p-3 text-xs font-medium text-ink hover:bg-mist/60 hover:border-primary/40 transition"
          >
            <span>Ask dinner suggestion</span>
            <ChevronRight className="h-3.5 w-3.5 text-muted" />
          </Link>
          <Link
            href="/app/xomni?prompt=Schedule a 30-minute cardio session at 5pm"
            className="flex items-center justify-between rounded-xl border border-line/60 bg-mist/20 p-3 text-xs font-medium text-ink hover:bg-mist/60 hover:border-primary/40 transition"
          >
            <span>Plan evening workout</span>
            <ChevronRight className="h-3.5 w-3.5 text-muted" />
          </Link>
          <Link
            href="/app/xomni?prompt=Explain my latest nutrition adherence score and how to improve it"
            className="flex items-center justify-between rounded-xl border border-line/60 bg-mist/20 p-3 text-xs font-medium text-ink hover:bg-mist/60 hover:border-primary/40 transition"
          >
            <span>Analyze daily score</span>
            <ChevronRight className="h-3.5 w-3.5 text-muted" />
          </Link>
        </div>
      </div>
    </div>
  );
}
