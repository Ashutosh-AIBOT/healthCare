"use client";

import React, { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/auth-client";
import { StatCard } from "@/components/dashboard/stat-card";
import { Skeleton } from "@/components/ui/card";
import {
  Activity, Flame, Plus, Sparkles, Trophy, Calendar,
  Dumbbell, Heart, CheckCircle2, ChevronRight, X
} from "lucide-react";
import Link from "next/link";

type FitnessProfile = {
  id: string;
  level: number;
  level_name: string;
  level_subtitle: string;
  level_description: string;
  level_color: string;
  goal_type: string;
  weekly_workout_days: number;
  recommended_workouts: string[];
  intensity: string;
  rest_days: number;
};

type ActivityLogItem = {
  id: string;
  activity_type: string;
  duration_minutes: number;
  calories_burned: number;
  distance_km?: number | null;
  notes?: string | null;
  logged_date: string;
};

type ActivitiesResponse = {
  days: number;
  total_minutes: number;
  total_calories: number;
  workout_count: number;
  daily_chart: Array<{ day: string; minutes: number; date: string }>;
  activities: ActivityLogItem[];
};

type FoodSuggestion = {
  type: string;
  title: string;
  description: string;
  timing: string;
};

export default function FitnessPage() {
  const [profile, setProfile] = useState<FitnessProfile | null>(null);
  const [activitiesData, setActivitiesData] = useState<ActivitiesResponse | null>(null);
  const [suggestions, setSuggestions] = useState<FoodSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);

  // Form state
  const [activityType, setActivityType] = useState("running");
  const [duration, setDuration] = useState(30);
  const [caloriesBurned, setCaloriesBurned] = useState(250);
  const [distanceKm, setDistanceKm] = useState<number | undefined>(undefined);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [profRes, actRes, sugRes] = await Promise.all([
        apiClient<FitnessProfile>("/api/v1/fitness/profile"),
        apiClient<ActivitiesResponse>("/api/v1/fitness/activities?days=7"),
        apiClient<{ suggestions: FoodSuggestion[] }>("/api/v1/fitness/suggestions"),
      ]);

      if (profRes.data) setProfile(profRes.data);
      if (actRes.data) setActivitiesData(actRes.data);
      if (Array.isArray(sugRes.data?.suggestions)) {
        setSuggestions(sugRes.data.suggestions);
      }
    } catch {
      // Graceful fallback
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleUpdateLevel = async (newLevel: number) => {
    await apiClient("/api/v1/fitness/profile", {
      method: "PUT",
      body: JSON.stringify({ level: newLevel }),
    });
    void loadData();
  };

  const handleLogActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    const res = await apiClient("/api/v1/fitness/activity", {
      method: "POST",
      body: JSON.stringify({
        activity_type: activityType,
        duration_minutes: Number(duration),
        calories_burned: caloriesBurned ? Number(caloriesBurned) : undefined,
        distance_km: distanceKm ? Number(distanceKm) : undefined,
        notes: notes || undefined,
      }),
    });
    setSubmitting(false);
    if (!res.error) {
      setIsLogModalOpen(false);
      setNotes("");
      void loadData();
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48 rounded-xl" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-[1.75rem]" />
          ))}
        </div>
        <Skeleton className="h-72 w-full rounded-[1.75rem]" />
      </div>
    );
  }

  const chart = activitiesData?.daily_chart || [
    { day: "Mon", minutes: 0 },
    { day: "Tue", minutes: 0 },
    { day: "Wed", minutes: 0 },
    { day: "Thu", minutes: 0 },
    { day: "Fri", minutes: 0 },
    { day: "Sat", minutes: 0 },
    { day: "Sun", minutes: 0 },
  ];
  const maxMin = Math.max(...chart.map((d) => d.minutes), 60);

  const totalMin = activitiesData?.total_minutes || 0;
  const totalCal = activitiesData?.total_calories || 0;
  const workoutCount = activitiesData?.workout_count || 0;
  const activeDays = chart.filter((d) => d.minutes > 0).length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
            Fitness & Workouts
          </h1>
          <p className="text-sm text-muted">
            Activity tracking, goal levels, and synchronized athletic nutrition.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsLogModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary-hover transition"
          >
            <Plus className="h-3.5 w-3.5" />
            Log Workout
          </button>
          <Link
            href="/app/xomni?mode=fitness"
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-4 py-2 text-xs font-semibold text-ink hover:bg-mist transition"
          >
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            Fitness AI
          </Link>
        </div>
      </div>

      {/* 4 Real-Time Activity StatCards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Active Days This Week"
          value={`${activeDays} / 7`}
          trend={`${profile?.weekly_workout_days || 4} days target`}
          color="lime"
        />
        <StatCard
          label="Active Minutes"
          value={`${totalMin} min`}
          trend="Total logged this week"
          color="primary"
        />
        <StatCard
          label="Calories Burned"
          value={`${totalCal} kcal`}
          trend={`${workoutCount} workouts recorded`}
          color="blush"
        />
        <StatCard
          label="Rest Days"
          value={`${7 - activeDays}`}
          trend={`${profile?.rest_days || 3} recommended`}
          color="charcoal"
        />
      </div>

      {/* Dynamic 7-Day Activity Chart */}
      <div className="rounded-[1.75rem] border border-line bg-surface p-6 shadow-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-ink text-lg">Weekly Activity Timeline</h2>
            <p className="text-xs text-muted">Real active minutes logged per day</p>
          </div>
          <span className="text-xs font-semibold text-primary bg-primary-soft px-3 py-1 rounded-full">
            {totalMin} min total
          </span>
        </div>

        <div
          className="mt-6 flex h-44 items-end gap-3 sm:gap-4 pt-4 border-b border-line/40 pb-2"
          role="img"
          aria-label="Bar chart of active minutes per day this week"
        >
          {chart.map((d) => {
            const heightPct = Math.max(8, Math.round((d.minutes / maxMin) * 100));
            const hasActivity = d.minutes > 0;
            return (
              <div key={d.day} className="flex h-full flex-1 flex-col items-center justify-end gap-2 group">
                <span className="text-[10px] text-muted opacity-0 group-hover:opacity-100 transition">
                  {d.minutes}m
                </span>
                <div
                  className={`w-full rounded-xl transition-all duration-300 ${
                    hasActivity
                      ? "bg-gradient-to-t from-primary to-primary-hover shadow-sm"
                      : "bg-mist/80"
                  }`}
                  style={{ height: `${heightPct}%` }}
                />
                <span className="text-[11px] font-semibold text-muted">{d.day}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3-Level Goal Switcher */}
      <div className="rounded-[1.75rem] border border-line bg-surface p-6 shadow-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-ink text-lg flex items-center gap-2">
              <Trophy className="h-5 w-5 text-amber-500" />
              Fitness Journey Level
            </h2>
            <p className="text-xs text-muted">Select your progression stage to recalibrate your recommendations</p>
          </div>
          <span className="text-xs font-semibold bg-mist px-3 py-1 rounded-full text-ink">
            Current: Level {profile?.level || 2} ({profile?.level_name || "Intermediate"})
          </span>
        </div>

        <div className="grid gap-4 md:grid-cols-3 pt-2">
          {[
            {
              level: 1,
              name: "Level 1: Beginner",
              sub: "Weight Loss & Foundation",
              days: 3,
              desc: "Build sustainable habits, burn excess fat, and establish aerobic base.",
            },
            {
              level: 2,
              name: "Level 2: Intermediate",
              sub: "Muscle Building & Toning",
              days: 4,
              desc: "Progressive overload, hypertrophy training, and body recomposition.",
            },
            {
              level: 3,
              name: "Level 3: Advanced",
              sub: "Athletic Performance",
              days: 5,
              desc: "Peak conditioning, high-intensity intervals, and sport-specific power.",
            },
          ].map((item) => {
            const isSelected = profile?.level === item.level;
            return (
              <button
                key={item.level}
                onClick={() => handleUpdateLevel(item.level)}
                className={`text-left rounded-2xl border p-5 transition-all space-y-2 ${
                  isSelected
                    ? "border-primary bg-primary-soft/30 shadow-lift"
                    : "border-line bg-surface hover:bg-mist/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-ink">{item.name}</span>
                  {isSelected && <CheckCircle2 className="h-4 w-4 text-primary" />}
                </div>
                <p className="text-xs font-medium text-primary">{item.sub}</p>
                <p className="text-[11px] text-muted leading-relaxed">{item.desc}</p>
                <div className="pt-2 text-[10px] font-semibold text-muted">
                  Target: {item.days} workout days / week
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Synchronized Pre/Post Workout Nutrition */}
      {Array.isArray(suggestions) && suggestions.length > 0 && (
        <div className="rounded-[1.75rem] border border-line bg-surface p-6 shadow-card space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-ink text-lg flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              AI Pre & Post Workout Nutrition Sync
            </h2>
            <Link href="/app/food" className="text-xs text-primary font-semibold hover:underline">
              Add to Meal Plan →
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {suggestions.map((sug, i) => (
              <div key={i} className="rounded-xl border border-line/60 bg-mist/20 p-4 space-y-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-primary">
                  {sug.timing || sug.type}
                </span>
                <h4 className="text-xs font-semibold text-ink">{sug.title}</h4>
                <p className="text-[11px] text-muted leading-relaxed">{sug.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Log Workout Modal */}
      {isLogModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-md rounded-[2rem] border border-line bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-line/40 pb-3">
              <h3 className="font-semibold text-ink text-base">Log Workout Activity</h3>
              <button
                onClick={() => setIsLogModalOpen(false)}
                className="flex h-7 w-7 items-center justify-center rounded-full text-muted hover:bg-mist hover:text-ink transition"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleLogActivity} className="space-y-3">
              <div>
                <label className="text-xs font-medium text-muted">Activity Type</label>
                <select
                  value={activityType}
                  onChange={(e) => setActivityType(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                >
                  <option value="running">Running / Jogging</option>
                  <option value="strength">Strength / Weight Training</option>
                  <option value="cycling">Cycling</option>
                  <option value="swimming">Swimming</option>
                  <option value="yoga">Yoga & Mobility</option>
                  <option value="walking">Brisk Walking</option>
                  <option value="hiit">HIIT / Circuit Training</option>
                  <option value="dancing">Sports / Dancing</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-muted">Duration (minutes)</label>
                  <input
                    type="number"
                    min="1"
                    max="600"
                    required
                    value={duration}
                    onChange={(e) => {
                      const dur = Number(e.target.value);
                      setDuration(dur);
                      setCaloriesBurned(dur * 8);
                    }}
                    className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted">Est. Calories Burned</label>
                  <input
                    type="number"
                    min="0"
                    value={caloriesBurned}
                    onChange={(e) => setCaloriesBurned(Number(e.target.value))}
                    className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-muted">Distance (km, optional)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="e.g. 5.2"
                  value={distanceKm ?? ""}
                  onChange={(e) => setDistanceKm(e.target.value ? Number(e.target.value) : undefined)}
                  className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-muted">Notes / How you felt</label>
                <input
                  type="text"
                  placeholder="e.g. Felt energetic, increased bench weight"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-line/40">
                <button
                  type="button"
                  onClick={() => setIsLogModalOpen(false)}
                  className="rounded-xl border border-line px-4 py-2 text-xs font-semibold text-muted hover:bg-mist"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary-hover transition"
                >
                  {submitting ? "Logging..." : "Save Workout"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
