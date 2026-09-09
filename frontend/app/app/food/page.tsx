"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/auth-client";
import { Skeleton } from "@/components/ui/card";
import {
  Utensils, Sparkles, Heart, Plus, ChevronRight, History,
  CheckCircle2, Clock, Flame, ShieldAlert, ArrowRightLeft, Edit3, X
} from "lucide-react";

type MealItem = {
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fats: number;
  created_by?: string;
};

type MealPlanJson = {
  breakfast?: MealItem[];
  lunch?: MealItem[];
  snacks?: MealItem[];
  dinner?: MealItem[];
  [key: string]: any;
};

type MealPlanResponse = {
  id: string | null;
  plan_json: MealPlanJson;
  created_by: string;
  version: number;
  ai_generated: boolean;
  notes?: string | null;
  days_followed: number;
  preferences?: {
    craving: string;
    recommended: string;
  };
};

type NutritionSummary = {
  calories: number;
  target_calories: number;
  water_ml: number;
  protein_g: number;
  target_protein_g: number;
  carbs_g: number;
  target_carbs_g: number;
  fat_g: number;
  target_fat_g: number;
  score: number;
};

type MealPlanHistoryItem = {
  id: string;
  version: number;
  plan_json: MealPlanJson;
  created_by: string;
  valid_from: string | null;
  valid_to: string | null;
};

export default function FoodPage() {
  const [mealPlan, setMealPlan] = useState<MealPlanResponse | null>(null);
  const [summary, setSummary] = useState<NutritionSummary | null>(null);
  const [history, setHistory] = useState<MealPlanHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Manual Add/Edit modal state
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingItemIndex, setEditingItemIndex] = useState<number | null>(null);
  const [editMealType, setEditMealType] = useState<"breakfast" | "lunch" | "snacks" | "dinner">("breakfast");
  const [editItemName, setEditItemName] = useState("");
  const [editCalories, setEditCalories] = useState(250);
  const [editProtein, setEditProtein] = useState(15);
  const [editCarbs, setEditCarbs] = useState(30);
  const [editFats, setEditFats] = useState(7);
  const [saving, setSaving] = useState(false);

  const handleLogWater = async () => {
    const res = await apiClient("/api/v1/nutrition/logs", {
      method: "POST",
      body: JSON.stringify({ entry_type: "water", water_ml: 250 }),
    });
    if (!res.error) void loadData();
  };

  const loadData = useCallback(async () => {
    setError(null);
    try {
      const [planRes, sumRes, histRes] = await Promise.all([
        apiClient<MealPlanResponse>("/api/v1/nutrition/meal-plan/current"),
        apiClient<NutritionSummary>("/api/v1/nutrition/summary"),
        apiClient<MealPlanHistoryItem[]>("/api/v1/nutrition/meal-plan/history"),
      ]);

      if (planRes.error) {
        setError(planRes.error.detail || "Failed to load meal plan.");
      } else if (planRes.data) {
        setMealPlan(planRes.data);
      }

      if (sumRes.data) setSummary(sumRes.data);
      if (histRes.data) setHistory(histRes.data);
    } catch {
      setError("Unable to connect to nutrition services.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Handle manual addition/save
  const handleSaveManualItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mealPlan || !editItemName.trim()) return;

    setSaving(true);
    const updatedPlan = { ...mealPlan.plan_json };
    const currentList = updatedPlan[editMealType] ? [...updatedPlan[editMealType]] : [];
    
    const nextItem = {
      name: editItemName.trim(),
      calories: Number(editCalories),
      protein: Number(editProtein),
      carbs: Number(editCarbs),
      fats: Number(editFats),
      created_by: "USER",
    };
    if (editingItemIndex === null) currentList.push(nextItem);
    else currentList[editingItemIndex] = nextItem;

    updatedPlan[editMealType] = currentList;

    const res = await apiClient<{ status: string; version: number }>("/api/v1/nutrition/meal-plan/save", {
      method: "POST",
      body: JSON.stringify({
        plan_json: updatedPlan,
        created_by: "USER",
        notes: `Added ${editItemName} to ${editMealType} manually`,
      }),
    });

    setSaving(false);
    if (!res.error) {
      setIsEditOpen(false);
      setEditingItemIndex(null);
      setEditItemName("");
      void loadData();
    }
  };

  const editMealItem = (mealType: typeof editMealType, item: MealItem, index: number) => {
    setEditMealType(mealType);
    setEditingItemIndex(index);
    setEditItemName(item.name);
    setEditCalories(item.calories);
    setEditProtein(item.protein);
    setEditCarbs(item.carbs);
    setEditFats(item.fats);
    setIsEditOpen(true);
  };

  const deleteMealItem = async (mealType: typeof editMealType, index: number) => {
    if (!mealPlan) return;
    const updatedPlan = { ...mealPlan.plan_json };
    updatedPlan[mealType] = [...(updatedPlan[mealType] || [])].filter((_, itemIndex) => itemIndex !== index);
    const res = await apiClient("/api/v1/nutrition/meal-plan/save", { method: "POST", body: JSON.stringify({ plan_json: updatedPlan, created_by: "USER", notes: `Removed item from ${mealType}` }) });
    if (!res.error) void loadData();
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

  const targetCal = summary?.target_calories || 0;
  const curCal = summary?.calories || 0;
  const calPct = targetCal > 0 ? Math.min(100, Math.round((curCal / targetCal) * 100)) : 0;

  const targetPro = summary?.target_protein_g || 0;
  const curPro = summary?.protein_g || 0;
  const proPct = targetPro > 0 ? Math.min(100, Math.round((curPro / targetPro) * 100)) : 0;

  const targetCarb = summary?.target_carbs_g || 0;
  const curCarb = summary?.carbs_g || 0;
  const carbPct = targetCarb > 0 ? Math.min(100, Math.round((curCarb / targetCarb) * 100)) : 0;

  const targetFat = summary?.target_fat_g || 0;
  const curFat = summary?.fat_g || 0;
  const fatPct = targetFat > 0 ? Math.min(100, Math.round((curFat / targetFat) * 100)) : 0;

  const meals = mealPlan?.plan_json || {};

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">
            Food & Nutrition Hub
          </h1>
          <p className="text-sm text-muted">
            Personalized meal intelligence, macro calibration, and single-point AI editing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-4 py-2 text-xs font-semibold text-ink hover:bg-mist transition"
          >
            <History className="h-3.5 w-3.5 text-muted" />
            Diet History ({history.length})
          </button>
          <Link
            href="/app/xomni?mode=food"
            className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary-hover transition"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Plan with Xomni AI
          </Link>
        </div>
      </div>

      {/* Dual Reference Intelligence Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Card A: What You Want / Crave */}
        <div className="rounded-[1.75rem] border border-border bg-surface p-6 shadow-card space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-danger/15 text-danger">
                <Heart className="h-4 w-4" />
              </div>
              <h3 className="font-semibold text-text-primary text-base">What You Like & Crave</h3>
            </div>
            <span className="text-[10px] font-semibold uppercase tracking-wider bg-surface-hover text-text-secondary px-2.5 py-0.5 rounded-full">
              Taste Profile
            </span>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            {mealPlan?.preferences?.craving || "Sourdough toast, aromatic Indian spices, paneer, and rich cold brews."}
          </p>
          <div className="pt-2 text-[11px] text-text-secondary italic border-t border-border flex items-center gap-1">
            <span>✨ Xomni incorporates these cravings into satisfying, calibrated healthy recipes.</span>
          </div>
        </div>

        {/* Card B: What Your Health Needs / Should Eat */}
        <div className="rounded-[1.75rem] border border-border bg-surface p-6 shadow-card space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-teal/15 text-accent-teal">
                <Utensils className="h-4 w-4" />
              </div>
              <h3 className="font-semibold text-text-primary text-base">What Your Health Truly Needs</h3>
            </div>
            <span className="text-[10px] font-semibold uppercase tracking-wider bg-surface-hover text-text-secondary px-2.5 py-0.5 rounded-full">
              Clinical Target
            </span>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">
            {mealPlan?.preferences?.recommended || "High-fiber complex carbs, anti-inflammatory herbs, omega-3 fatty acids, and 120g lean daily protein."}
          </p>
          <div className="pt-2 text-[11px] text-text-secondary italic border-t border-border flex items-center gap-1">
            <span>🛡️ Calibrated to keep your insulin sensitivity high and metabolic recovery on track.</span>
          </div>
        </div>
      </div>

      {/* Macro Targets with Progress Bars */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Calories */}
        <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Calories</span>
            <span className="text-xs font-semibold text-accent-water">{calPct}%</span>
          </div>
          <p className="text-2xl font-bold text-text-primary">{curCal} <span className="text-xs font-normal text-text-secondary">/ {targetCal} kcal</span></p>
          <div className="h-2 rounded-full bg-surface-hover overflow-hidden">
            <div className="h-full rounded-full bg-accent-water transition-all duration-300" style={{ width: `${calPct}%` }} />
          </div>
        </div>

        {/* Protein */}
        <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Protein</span>
            <span className="text-xs font-semibold text-accent-teal">{proPct}%</span>
          </div>
          <p className="text-2xl font-bold text-text-primary">{curPro}g <span className="text-xs font-normal text-text-secondary">/ {targetPro}g</span></p>
          <div className="h-2 rounded-full bg-surface-hover overflow-hidden">
            <div className="h-full rounded-full bg-accent-teal transition-all duration-300" style={{ width: `${proPct}%` }} />
          </div>
        </div>

        {/* Carbs */}
        <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Carbs</span>
            <span className="text-xs font-semibold text-accent-gold">{carbPct}%</span>
          </div>
          <p className="text-2xl font-bold text-text-primary">{curCarb}g <span className="text-xs font-normal text-text-secondary">/ {targetCarb}g</span></p>
          <div className="h-2 rounded-full bg-surface-hover overflow-hidden">
            <div className="h-full rounded-full bg-accent-gold transition-all duration-300" style={{ width: `${carbPct}%` }} />
          </div>
        </div>

        {/* Fats */}
        <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Healthy Fats</span>
            <span className="text-xs font-semibold text-danger">{fatPct}%</span>
          </div>
          <p className="text-2xl font-bold text-text-primary">{curFat}g <span className="text-xs font-normal text-text-secondary">/ {targetFat}g</span></p>
          <div className="h-2 rounded-full bg-surface-hover overflow-hidden">
            <div className="h-full rounded-full bg-danger transition-all duration-300" style={{ width: `${fatPct}%` }} />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-accent-water/20 bg-accent-water/5 p-4">
        <div>
          <p className="text-sm font-semibold text-text-primary">Water today: {summary?.water_ml ?? 0} ml</p>
          <p className="text-xs text-text-secondary">Log a 250 ml serving or manage entries from your daily record.</p>
        </div>
        <button onClick={() => void handleLogWater()} className="inline-flex items-center gap-2 rounded-full bg-accent-water px-4 py-2 text-xs font-semibold text-white hover:opacity-90">
          + 250 ml water
        </button>
      </div>

      {/* History Drawer / Panel (if toggled) */}
      {showHistory && (
        <div className="rounded-[1.75rem] border border-primary/20 bg-primary-soft/20 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-ink text-base flex items-center gap-2">
              <History className="h-4 w-4 text-primary" />
              Diet Plan Version History & Tracking
            </h3>
            <button onClick={() => setShowHistory(false)} className="text-xs text-muted hover:text-ink">
              Close
            </button>
          </div>
          <p className="text-xs text-muted">
            Track past meal plan versions, who modified them, and how many days each plan was followed.
          </p>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl border border-line bg-surface p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-primary">Current Plan (v{mealPlan?.version || 1})</span>
                <span className="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-medium">Active</span>
              </div>
              <p className="text-xs text-muted">Followed for: <strong className="text-ink">{mealPlan?.days_followed || 3} days</strong></p>
              <p className="text-xs text-muted">Author: <strong className="text-ink">{mealPlan?.created_by || "XOMNI"}</strong></p>
            </div>

            {history.map((h) => (
              <div key={h.id} className="rounded-xl border border-line bg-surface/80 p-4 space-y-2 opacity-80">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ink">Version {h.version}</span>
                  <span className="text-[10px] bg-mist text-muted px-2 py-0.5 rounded">Archived</span>
                </div>
                <p className="text-xs text-muted">Author: <strong className="text-ink">{h.created_by}</strong></p>
                <p className="text-[11px] text-muted">{h.valid_from ? new Date(h.valid_from).toLocaleDateString() : "Past period"}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Meals Grid (Breakfast, Lunch, Snacks, Dinner) */}
      <div className="grid gap-6 md:grid-cols-2">
        {(["breakfast", "lunch", "snacks", "dinner"] as const).map((mealKey) => {
          const items: MealItem[] = meals[mealKey] || [];
          const mealTitle = mealKey.charAt(0).toUpperCase() + mealKey.slice(1);
          const totalMealCal = items.reduce((acc, i) => acc + (i.calories || 0), 0);
          const totalMealProtein = items.reduce((acc, i) => acc + (i.protein || 0), 0);

          return (
            <div key={mealKey} className="rounded-[1.75rem] border border-line bg-surface p-6 shadow-card space-y-4">
              <div className="flex items-center justify-between border-b border-line/40 pb-3">
                <div>
                  <h3 className="font-semibold text-ink text-lg">{mealTitle}</h3>
                  <p className="text-xs text-muted">{totalMealCal} kcal · {totalMealProtein}g protein</p>
                </div>
                <button
                  onClick={() => {
                    setEditMealType(mealKey);
                    setEditingItemIndex(null);
                    setEditItemName("");
                    setIsEditOpen(true);
                  }}
                  className="inline-flex items-center gap-1 rounded-full border border-line bg-mist/40 px-3 py-1 text-xs font-semibold text-ink hover:bg-mist transition"
                >
                  <Plus className="h-3 w-3" />
                  Add item
                </button>
              </div>

              {items.length === 0 ? (
                <div 
                  className="rounded-xl border border-dashed border-border p-6 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-surface-hover transition-colors duration-200"
                  onClick={() => {
                    setEditMealType(mealKey);
                    setEditingItemIndex(null);
                    setEditItemName("");
                    setIsEditOpen(true);
                  }}
                >
                  <Plus className="h-5 w-5 text-text-secondary mb-2" />
                  <span className="text-[13px] font-medium text-text-primary">Add to {mealTitle}</span>
                  <p className="text-[11px] text-text-secondary mt-1">Click to add manually, or ask Xomni</p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {items.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-xl border border-line/60 bg-mist/20 p-3.5 hover:border-line transition"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-semibold text-ink">{item.name}</p>
                          <span
                            className={`text-[9px] font-semibold px-1.5 py-0.2 rounded uppercase tracking-wider ${
                              item.created_by === "USER"
                                ? "bg-blue-50 text-blue-700 border border-blue-200"
                                : "bg-purple-50 text-purple-700 border border-purple-200"
                            }`}
                          >
                            {item.created_by === "USER" ? "Manual" : "AI Suggested"}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted">
                          {item.calories} kcal · {item.protein}g protein · {item.carbs}g carbs · {item.fats}g fat
                        </p>
                      </div>

                      <div className="flex items-center gap-1"><button onClick={() => editMealItem(mealKey, item, idx)} className="flex h-7 w-7 items-center justify-center rounded-lg text-muted hover:bg-mist hover:text-ink transition" title="Edit meal item"><Edit3 className="h-3.5 w-3.5" /></button><button onClick={() => void deleteMealItem(mealKey, idx)} className="flex h-7 w-7 items-center justify-center rounded-lg text-muted hover:bg-danger/10 hover:text-danger transition" title="Delete meal item"><X className="h-3.5 w-3.5" /></button><Link href={`/app/xomni?mode=food&prompt=Suggest a healthier swap for ${item.name} in my ${mealKey}`} className="flex h-7 w-7 items-center justify-center rounded-lg text-muted hover:bg-mist hover:text-primary transition" title="Swap with Xomni"><ArrowRightLeft className="h-3.5 w-3.5" /></Link></div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Manual Add Item Modal */}
      {isEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-md rounded-[2rem] border border-line bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-line/40 pb-3">
              <h3 className="font-semibold text-ink text-base">
                Add Food to {editMealType.charAt(0).toUpperCase() + editMealType.slice(1)}
              </h3>
              <button
                onClick={() => setIsEditOpen(false)}
                className="flex h-7 w-7 items-center justify-center rounded-full text-muted hover:bg-mist hover:text-ink transition"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveManualItem} className="space-y-3">
              <div>
                <label className="text-xs font-medium text-muted">Food Item Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Grilled Salmon or Sprouted Moong Salad"
                  value={editItemName}
                  onChange={(e) => setEditItemName(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-muted">Calories (kcal)</label>
                  <input
                    type="number"
                    min="0"
                    value={editCalories}
                    onChange={(e) => setEditCalories(Number(e.target.value))}
                    className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted">Protein (g)</label>
                  <input
                    type="number"
                    min="0"
                    value={editProtein}
                    onChange={(e) => setEditProtein(Number(e.target.value))}
                    className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-muted">Carbohydrates (g)</label>
                  <input
                    type="number"
                    min="0"
                    value={editCarbs}
                    onChange={(e) => setEditCarbs(Number(e.target.value))}
                    className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted">Fats (g)</label>
                  <input
                    type="number"
                    min="0"
                    value={editFats}
                    onChange={(e) => setEditFats(Number(e.target.value))}
                    className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs text-ink outline-none focus:border-primary"
                  />
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-line/40">
                <button
                  type="button"
                  onClick={() => setIsEditOpen(false)}
                  className="rounded-xl border border-line px-4 py-2 text-xs font-semibold text-muted hover:bg-mist"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary-hover transition"
                >
                  {saving ? "Saving..." : "Add to Meal Plan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
