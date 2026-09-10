"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sparkles, CheckCircle2, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ConfirmResult {
  action?: string;
  affected?: Array<{ type: string; id?: string }>;
  version?: number;
  dashboard_url?: string;
  confirmed?: boolean;
}

interface ProposalCardProps {
  action: any;
  onAccept: (edited: Record<string, unknown> | null) => Promise<ConfirmResult>;
  onReject: () => Promise<void>;
}

type MealRow = {
  meal: string;
  name: string;
  calories: number;
  protein: number;
  carbs: number;
  fats: number;
};

const MEAL_TYPES = ["breakfast", "lunch", "snacks", "dinner"] as const;

const KIND_META: Record<string, { title: string; dashboard: string }> = {
  propose_meal_plan: { title: "Meal Plan Update", dashboard: "/app/food" },
  propose_todo: { title: "Schedule Update", dashboard: "/app/time" },
  propose_fitness_activity: { title: "Workout Log", dashboard: "/app/fitness" },
  propose_personal_context: { title: "Personal Context", dashboard: "/app/profile" },
};

function bucketOf(raw: any): string {
  const label = `${raw?.meal ?? ""} ${raw?.name ?? ""}`.toLowerCase();
  const hit = MEAL_TYPES.find((m) => label.includes(m));
  return hit ?? "lunch";
}

function initialMealRows(action: any): MealRow[] {
  const rows: MealRow[] = [];
  if (Array.isArray(action?.proposal)) {
    const rawMeal = String(action?.meal_type ?? "lunch").toLowerCase();
    const meal = (MEAL_TYPES as readonly string[]).includes(rawMeal) ? rawMeal : "lunch";
    for (const r of action.proposal) {
      if (!r || typeof r !== "object") continue;
      rows.push({
        meal,
        name: String(r.name ?? r.description ?? r.title ?? ""),
        calories: Number(r.calories ?? r.kcal ?? 0) || 0,
        protein: Number(r.protein ?? r.protein_g ?? 0) || 0,
        carbs: Number(r.carbs ?? r.carbs_g ?? 0) || 0,
        fats: Number(r.fats ?? r.fat ?? r.fat_g ?? 0) || 0,
      });
    }
  } else if (Array.isArray(action?.meals)) {
    for (const r of action.meals) {
      if (!r || typeof r !== "object") continue;
      rows.push({
        meal: bucketOf(r),
        name: String(r.name ?? r.description ?? ""),
        calories: Number(r.calories ?? 0) || 0,
        protein: Number(r.protein ?? r.protein_g ?? 0) || 0,
        carbs: Number(r.carbs ?? r.carbs_g ?? 0) || 0,
        fats: Number(r.fats ?? r.fat ?? r.fat_g ?? 0) || 0,
      });
    }
  }
  return rows;
}

function initialContextLists(action: any): Record<string, string> {
  const out: Record<string, string> = {};
  const updates = action?.updates;
  if (updates && typeof updates === "object") {
    for (const [k, v] of Object.entries(updates)) {
      out[k] = Array.isArray(v) ? (v as unknown[]).map(String).join("\n") : String(v ?? "");
    }
  }
  return out;
}

const num = (v: string) => {
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? n : 0;
};

export function ProposalCard({ action, onAccept, onReject }: ProposalCardProps) {
  const kind: string | undefined = action?.action;
  const meta = (kind && KIND_META[kind]) || null;
  const [phase, setPhase] = useState<"editing" | "saving" | "saved" | "rejected">("editing");
  const [cardError, setCardError] = useState<string | null>(null);
  const [result, setResult] = useState<ConfirmResult | null>(null);

  const [mealRows, setMealRows] = useState<MealRow[]>(() => initialMealRows(action));
  const [todoTitle, setTodoTitle] = useState(() => String(action?.title ?? ""));
  const [todoStart, setTodoStart] = useState(() => String(action?.start_hour ?? ""));
  const [todoEnd, setTodoEnd] = useState(() => String(action?.end_hour ?? ""));
  const [todoPriority, setTodoPriority] = useState(() => String(action?.priority ?? "normal"));
  const [fitType, setFitType] = useState(() => String(action?.activity_type ?? ""));
  const [fitDuration, setFitDuration] = useState(() => String(action?.duration_minutes ?? ""));
  const [fitCalories, setFitCalories] = useState(() => String(action?.calories_burned ?? ""));
  const [contextLists, setContextLists] = useState<Record<string, string>>(() => initialContextLists(action));

  if (!meta) return null;

  const totals = mealRows.reduce(
    (t, r) => ({
      calories: t.calories + r.calories,
      protein: t.protein + r.protein,
      carbs: t.carbs + r.carbs,
      fats: t.fats + r.fats,
    }),
    { calories: 0, protein: 0, carbs: 0, fats: 0 }
  );

  const buildEdited = (): Record<string, unknown> | null => {
    if (kind === "propose_meal_plan") {
      const rows = mealRows.filter((r) => r.name.trim());
      if (!rows.length) {
        setCardError("Add at least one meal item before saving.");
        return null;
      }
      return { meals: rows.map((r) => ({ ...r, name: r.name.trim() })) };
    }
    if (kind === "propose_todo") {
      if (!todoTitle.trim()) {
        setCardError("The task needs a title.");
        return null;
      }
      return {
        title: todoTitle.trim(),
        start_hour: todoStart === "" ? null : Number(todoStart),
        end_hour: todoEnd === "" ? null : Number(todoEnd),
        priority: todoPriority,
      };
    }
    if (kind === "propose_fitness_activity") {
      if (!fitType.trim() || !(Number(fitDuration) > 0)) {
        setCardError("Add a workout name and a valid duration in minutes.");
        return null;
      }
      return {
        activity_type: fitType.trim(),
        duration_minutes: Number(fitDuration),
        calories_burned: fitCalories === "" ? null : Number(fitCalories),
      };
    }
    const updates: Record<string, string[]> = {};
    for (const [k, v] of Object.entries(contextLists)) {
      const items = v.split("\n").map((s) => s.trim()).filter(Boolean);
      if (items.length) updates[k] = items;
    }
    if (!Object.keys(updates).length) {
      setCardError("Add at least one context item before saving.");
      return null;
    }
    return { updates };
  };

  const handleAccept = async () => {
    setCardError(null);
    const edited = buildEdited();
    if (!edited) return;
    setPhase("saving");
    try {
      const res = await onAccept(edited);
      setResult(res);
      setPhase("saved");
    } catch (e) {
      setCardError(e instanceof Error ? e.message : "Could not apply proposal.");
      setPhase("editing");
    }
  };

  const handleReject = async () => {
    setCardError(null);
    setPhase("saving");
    try {
      await onReject();
      setPhase("rejected");
    } catch (e) {
      setCardError(e instanceof Error ? e.message : "Could not reject proposal.");
      setPhase("editing");
    }
  };

  if (phase === "saved") {
    const affected = result?.affected ?? [];
    return (
      <div className="mt-4 border border-primary/25 bg-primary-soft/30 rounded-xl p-4 shadow-sm w-full max-w-sm">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <h4 className="text-sm font-semibold text-ink">Saved to dashboard</h4>
        </div>
        <p className="text-[13px] text-ink/80">
          {meta.title} saved
          {typeof result?.version === "number" ? ` · version ${result.version}` : ""}
          {affected.length ? ` · ${affected.length} item${affected.length > 1 ? "s" : ""} updated` : ""}.
        </p>
        {(result?.dashboard_url || meta.dashboard) && (
          <Link
            href={result?.dashboard_url || meta.dashboard}
            className="mt-3 inline-flex items-center justify-center w-full rounded-full bg-ink px-4 py-2 text-[13px] font-medium text-paper hover:bg-ink/90 transition-colors"
          >
            View in dashboard
          </Link>
        )}
      </div>
    );
  }

  if (phase === "rejected") {
    return (
      <div className="mt-4 border border-line/60 bg-surface rounded-xl p-4 w-full max-w-sm">
        <p className="text-[13px] text-muted">Proposal rejected. Nothing was changed.</p>
      </div>
    );
  }

  const busy = phase === "saving";

  return (
    <div className="mt-4 border border-primary/20 bg-primary-soft/30 rounded-xl p-4 shadow-sm w-full max-w-md">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="h-4 w-4 text-primary" />
        <h4 className="text-sm font-semibold text-ink">{meta.title} — review & edit</h4>
      </div>

      {kind === "propose_meal_plan" && (
        <div className="space-y-2 mb-3">
          {mealRows.map((row, i) => (
            <div key={i} className="bg-surface border border-line/50 rounded-lg p-2.5 space-y-2">
              <div className="flex items-center gap-2">
                <select
                  aria-label="Meal"
                  value={row.meal}
                  disabled={busy}
                  onChange={(e) =>
                    setMealRows((prev) => prev.map((r, j) => (j === i ? { ...r, meal: e.target.value } : r)))
                  }
                  className="rounded-lg border border-line bg-paper px-2 py-1.5 text-xs text-ink outline-none"
                >
                  {MEAL_TYPES.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                <Input
                  aria-label="Item name"
                  value={row.name}
                  disabled={busy}
                  onChange={(e) =>
                    setMealRows((prev) => prev.map((r, j) => (j === i ? { ...r, name: e.target.value } : r)))
                  }
                  placeholder="Item name"
                  className="rounded-lg px-3 py-1.5 text-[13px]"
                />
                <button
                  type="button"
                  aria-label="Remove item"
                  disabled={busy}
                  onClick={() => setMealRows((prev) => prev.filter((_, j) => j !== i))}
                  className="p-1.5 rounded-lg text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="grid grid-cols-4 gap-1.5">
                {(
                  [
                    ["calories", "kcal"],
                    ["protein", "prot g"],
                    ["carbs", "carb g"],
                    ["fats", "fat g"],
                  ] as const
                ).map(([field, label]) => (
                  <label key={field} className="block">
                    <span className="block text-[10px] text-muted mb-0.5">{label}</span>
                    <input
                      type="number"
                      min={0}
                      value={row[field]}
                      disabled={busy}
                      onChange={(e) =>
                        setMealRows((prev) =>
                          prev.map((r, j) => (j === i ? { ...r, [field]: num(e.target.value) } : r))
                        )
                      }
                      className="w-full rounded-lg border border-line bg-paper px-2 py-1 text-xs text-ink outline-none focus:border-primary"
                    />
                  </label>
                ))}
              </div>
            </div>
          ))}
          <p className="text-xs text-muted px-1">
            Total: {Math.round(totals.calories)} kcal · {Math.round(totals.protein)}g protein ·{" "}
            {Math.round(totals.carbs)}g carbs · {Math.round(totals.fats)}g fat
          </p>
        </div>
      )}

      {kind === "propose_todo" && (
        <div className="space-y-2 mb-3">
          <Input aria-label="Task title" value={todoTitle} disabled={busy} onChange={(e) => setTodoTitle(e.target.value)} placeholder="Task title" className="rounded-lg px-3 py-2 text-[13px]" />
          <div className="grid grid-cols-3 gap-1.5">
            <label className="block">
              <span className="block text-[10px] text-muted mb-0.5">Start hour</span>
              <input type="number" min={0} max={24} value={todoStart} disabled={busy} onChange={(e) => setTodoStart(e.target.value)} className="w-full rounded-lg border border-line bg-paper px-2 py-1.5 text-xs text-ink outline-none focus:border-primary" />
            </label>
            <label className="block">
              <span className="block text-[10px] text-muted mb-0.5">End hour</span>
              <input type="number" min={0} max={24} value={todoEnd} disabled={busy} onChange={(e) => setTodoEnd(e.target.value)} className="w-full rounded-lg border border-line bg-paper px-2 py-1.5 text-xs text-ink outline-none focus:border-primary" />
            </label>
            <label className="block">
              <span className="block text-[10px] text-muted mb-0.5">Priority</span>
              <select value={todoPriority} disabled={busy} onChange={(e) => setTodoPriority(e.target.value)} className="w-full rounded-lg border border-line bg-paper px-2 py-1.5 text-xs text-ink outline-none">
                <option value="normal">normal</option>
                <option value="important">important</option>
                <option value="less">less</option>
              </select>
            </label>
          </div>
        </div>
      )}

      {kind === "propose_fitness_activity" && (
        <div className="space-y-2 mb-3">
          <Input aria-label="Workout" value={fitType} disabled={busy} onChange={(e) => setFitType(e.target.value)} placeholder="Workout (e.g. walking)" className="rounded-lg px-3 py-2 text-[13px]" />
          <div className="grid grid-cols-2 gap-1.5">
            <label className="block">
              <span className="block text-[10px] text-muted mb-0.5">Minutes</span>
              <input type="number" min={1} value={fitDuration} disabled={busy} onChange={(e) => setFitDuration(e.target.value)} className="w-full rounded-lg border border-line bg-paper px-2 py-1.5 text-xs text-ink outline-none focus:border-primary" />
            </label>
            <label className="block">
              <span className="block text-[10px] text-muted mb-0.5">Calories (optional)</span>
              <input type="number" min={0} value={fitCalories} disabled={busy} onChange={(e) => setFitCalories(e.target.value)} className="w-full rounded-lg border border-line bg-paper px-2 py-1.5 text-xs text-ink outline-none focus:border-primary" />
            </label>
          </div>
        </div>
      )}

      {kind === "propose_personal_context" && (
        <div className="space-y-2 mb-3">
          {Object.entries(contextLists).map(([key, value]) => (
            <label key={key} className="block">
              <span className="block text-[11px] font-medium text-ink mb-1 capitalize">{key.replace(/_/g, " ")}</span>
              <textarea
                value={value}
                disabled={busy}
                rows={2}
                onChange={(e) => setContextLists((prev) => ({ ...prev, [key]: e.target.value }))}
                placeholder="One per line"
                className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-[13px] text-ink outline-none focus:border-primary resize-y"
              />
            </label>
          ))}
        </div>
      )}

      {cardError && (
        <p role="alert" className="text-xs text-danger mb-2">
          {cardError}
        </p>
      )}

      <div className="flex gap-2">
        <Button onClick={handleAccept} disabled={busy} size="sm" className={cn("w-full bg-primary hover:bg-primary/90 text-white shadow-sm")}>
          {busy ? "Saving…" : "Save to dashboard"}
        </Button>
        <Button onClick={handleReject} disabled={busy} size="sm" variant="outline" className="w-full">
          Reject
        </Button>
      </div>
    </div>
  );
}
