"use client";

import * as React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { EmptyState, ErrorState } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";
import { Bell, CheckCircle2, Circle, SkipForward, TriangleAlert, Calendar } from "lucide-react";

type TimeBlock = {
  id: string;
  timetable_id: string;
  title: string;
  start_minute: number;
  end_minute: number;
  priority: "normal" | "important" | "less";
  description?: string | null;
};
type Timetable = {
  id: string;
  name: string;
  kind: "productive" | "backup" | "holiday";
  is_default: boolean;
  blocks: TimeBlock[];
};
type Todo = {
  id: string;
  title: string;
  description?: string | null;
  due_date: string;
  status: "pending" | "done";
  priority: "normal" | "important" | "less";
  created_by?: string;
  timetable_block_id?: string | null;
};
type HolidayRule = { id: string; rule_type: "weekly" | "specific"; weekday: number | null; specific_date: string | null };
type DayPlanBlock = { id: string; title: string; start_minute: number; end_minute: number; priority: string; status?: string | null; is_current: boolean; is_past: boolean; needs_checkin: boolean };
type DayPlan = { date: string; kind: string; timetable_name: string; current_minute: number; blocks: DayPlanBlock[] };
type TimeEntry = { id: string; date: string; block_id: string; actual_title: string; matched: boolean; duration_minutes: number };

function fmtMin(m: number) {
  const h = Math.floor(m / 60);
  const mm = String(m % 60).padStart(2, "0");
  const ap = h >= 12 ? "PM" : "AM";
  const hr = h % 12 || 12;
  return `${hr}:${mm} ${ap}`;
}
function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
function toDateISO(d: Date) {
  return d.toISOString().slice(0, 10);
}
function weekdayName(n: number) {
  return ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][n];
}

const priorityTone: Record<string, string> = {
  important: "border-l-[4px] border-l-critical bg-critical/5",
  normal: "border-l-[4px] border-l-line bg-surface",
  less: "border-l-[4px] border-l-line/40 bg-mist/30 opacity-80",
};

const priorityLabel: Record<string, string> = {
  important: "High priority",
  normal: "Medium priority",
  less: "Low priority",
};

const kindMeta: Record<string, { label: string; color: string; bg: string }> = {
  productive: { label: "Productive", color: "text-accent-teal", bg: "bg-accent-teal/15" },
  backup: { label: "Backup", color: "text-accent-gold", bg: "bg-accent-gold/15" },
  holiday: { label: "Holiday", color: "text-accent-water", bg: "bg-accent-water/15" },
};

type Period = "day" | "week" | "month" | "year";

export default function TimeManagementPage() {
  const [timetables, setTimetables] = useState<Timetable[] | null>(null);
  const [todos, setTodos] = useState<Todo[] | null>(null);
  const [holidayRules, setHolidayRules] = useState<HolidayRule[] | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(todayISO());
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>("day");
  const [dayPlan, setDayPlan] = useState<DayPlan | null>(null);
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [showCheckin, setShowCheckin] = useState(false);
  const [checkinBlock, setCheckinBlock] = useState<DayPlanBlock | null>(null);
  const [checkinTitle, setCheckinTitle] = useState("");
  const [checkinMatched, setCheckinMatched] = useState(true);
  const [newTodoTitle, setNewTodoTitle] = useState("");
  const [newTodoPriority, setNewTodoPriority] = useState<"normal" | "important" | "less">("normal");
  const [addingTodo, setAddingTodo] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    const [tt, td, hr, st, plan, ents] = await Promise.all([
      apiClient<Timetable[]>("/api/v1/time/timetables"),
      apiClient<Todo[]>(`/api/v1/time/todos?due_date=${selectedDate}`),
      apiClient<HolidayRule[]>("/api/v1/time/holiday-rules"),
      apiClient<any>(`/api/v1/time/day/${selectedDate}/stats`),
      apiClient<DayPlan>(`/api/v1/time/day/${selectedDate}/plan`),
      apiClient<TimeEntry[]>(`/api/v1/time/day/${selectedDate}/entries`),
    ]);
    if (tt.error || td.error) {
      setError((tt.error || td.error)?.detail || "Failed to load time data. Please refresh or sign in again.");
      setTimetables(tt.data || []);
      setTodos(td.data || []);
    } else {
      setTimetables(tt.data || []);
      setTodos(td.data || []);
    }
    if (!hr.error) setHolidayRules(hr.data || []);
    if (!st.error) setStats(st.data);
    if (!plan.error) setDayPlan(plan.data || null);
    if (!ents.error) setEntries(ents.data || []);
  }, [selectedDate]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!dayPlan) return;
    const current = dayPlan.blocks.find((b) => b.is_current && b.needs_checkin);
    if (current && !showCheckin) {
      setCheckinBlock(current);
      setShowCheckin(true);
    }
  }, [dayPlan, showCheckin]);

  useEffect(() => {
    const interval = setInterval(() => {
      void load();
    }, 60000);
    return () => clearInterval(interval);
  }, [load]);

  const handleCheckin = async () => {
    if (!checkinBlock) return;
    await apiClient(`/api/v1/time/day/${selectedDate}/checkin`, {
      method: "POST",
      body: JSON.stringify({
        block_id: checkinBlock.id,
        actual_title: checkinTitle || checkinBlock.title,
        matched: checkinMatched,
        duration_minutes: Math.max(1, Math.round((checkinBlock.end_minute - checkinBlock.start_minute) / 2)),
      }),
    });
    setShowCheckin(false);
    setCheckinBlock(null);
    setCheckinTitle("");
    void load();
  };

  const handleToggleTodo = async (todo: Todo) => {
    const nextStatus = todo.status === "done" ? "pending" : "done";
    await apiClient(`/api/v1/time/todos/${todo.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: nextStatus }),
    });
    void load();
  };

  const handleAddTodo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTodoTitle.trim()) return;
    setAddingTodo(true);
    await apiClient("/api/v1/time/todos", {
      method: "POST",
      body: JSON.stringify({
        title: newTodoTitle.trim(),
        due_date: selectedDate,
        priority: newTodoPriority,
        created_by: "USER",
      }),
    });
    setAddingTodo(false);
    setNewTodoTitle("");
    void load();
  };

  const calendar = useMemo(() => {
    const base = new Date(selectedDate + "T12:00:00");
    const y = base.getFullYear();
    const m = base.getMonth();
    const first = new Date(y, m, 1);
    const startDay = first.getDay();
    const daysInMonth = new Date(y, m + 1, 0).getDate();
    const cells: { d: Date; iso: string; inMonth: boolean }[] = [];
    for (let i = 0; i < 42; i++) {
      const d = new Date(y, m, 1 - startDay + i);
      cells.push({ d, iso: toDateISO(d), inMonth: d.getMonth() === m });
    }
    void daysInMonth;
    return { y, m, cells };
  }, [selectedDate]);

  if (!timetables || !todos) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-48 animate-pulse rounded-xl bg-surface-hover" />
        <div className="h-40 animate-pulse rounded-[1.75rem] border border-border bg-surface" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-[1.75rem] border border-border bg-surface" />
          ))}
        </div>
      </div>
    );
  }

  const today = todayISO();
  const isToday = selectedDate === today;
  const kind = dayPlan?.kind || "productive";
  const km = kindMeta[kind] || kindMeta.productive;
  const productiveTT = timetables.find((t) => t.kind === "productive");
  const backupTT = timetables.find((t) => t.kind === "backup");
  const holidayTT = timetables.find((t) => t.kind === "holiday");
  const dayBlocks = dayPlan?.blocks || [];

  return (
    <div className="space-y-6">
      {error && (
        <div className="flex items-center justify-between rounded-xl border border-danger/30 bg-danger/5 p-4">
          <div className="flex items-center gap-3">
            <TriangleAlert className="h-5 w-5 text-danger" />
            <p className="text-[13px] font-medium text-danger">{error}</p>
          </div>
          <button onClick={load} className="rounded-lg px-3 py-1.5 text-[13px] font-medium text-danger hover:bg-danger/10 transition-colors">
            Retry
          </button>
        </div>
      )}

      {/* Hero card */}
      <div className="rounded-[1.75rem] border border-border bg-surface p-6 shadow-card relative overflow-hidden">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between relative z-10">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary">Time Management</p>
            <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight text-text-primary">
              {isToday ? `Good ${new Date().getHours() < 12 ? "morning" : "evening"}!` : `Schedule for ${selectedDate}`}
            </h1>
            <p className="mt-1 text-[13px] text-text-secondary">
              Today&apos;s mode: <span className={`font-semibold ${km.color}`}>{km.label}</span> · {timetables.reduce((a, t) => a + t.blocks.length, 0)} blocks across 3 timetables
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <div className="relative flex rounded-full border border-border bg-surface p-1">
              <div 
                className="absolute top-1 bottom-1 w-[68px] rounded-full bg-accent-gold/15 transition-transform duration-300 ease-soft"
                style={{
                  transform: `translateX(${["day", "week", "month", "year"].indexOf(period) * 100}%)`
                }}
              />
              {(["day", "week", "month", "year"] as Period[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`relative z-10 w-[68px] py-1.5 text-[13px] font-semibold capitalize transition-colors duration-300 ease-soft ${
                    period === p ? "text-accent-gold" : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-line bg-surface/80 p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Daily score</p>
            <p className="mt-2 font-display text-4xl font-semibold text-ink">{stats?.score ?? 0}<span className="text-lg text-muted">/100</span></p>
            <p className="mt-1 text-xs text-muted">Todos {stats?.todo_done ?? 0}/{stats?.todo_total ?? 0} · Blocks {stats?.block_done ?? 0}/{stats?.block_total ?? 0}</p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-mist">
              <div className="h-full rounded-full bg-primary transition-all" style={{ width: `var(--score-w, ${Math.min(100, stats?.score ?? 0)}%)` } as React.CSSProperties} />
            </div>
          </div>
          <div className="rounded-2xl border border-line bg-surface/80 p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Today&apos;s todos</p>
            <p className="mt-2 text-2xl font-semibold text-ink">{todos.filter((t) => t.status === "done").length} / {todos.length}</p>
            <p className="text-xs text-muted">{stats?.todo_pct ?? 0}% done</p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-mist">
              <div className="h-full rounded-full bg-primary transition-all" style={{ width: `var(--todo-w, ${Math.min(100, stats?.todo_pct ?? 0)}%)` } as React.CSSProperties} />
            </div>
            
            {todos.length > 0 && (
              <div className="mt-4 space-y-2 border-t border-line/50 pt-4">
                {todos.map(t => (
                  <div
                    key={t.id}
                    onClick={() => handleToggleTodo(t)}
                    className="flex items-center justify-between gap-2 p-1.5 rounded-lg hover:bg-mist/50 cursor-pointer transition"
                  >
                    <p className={`text-sm ${t.status === 'done' ? 'line-through text-muted' : 'text-ink'}`}>{t.title}</p>
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                          t.created_by === 'XOMNI'
                            ? 'bg-purple-50 text-purple-700 border border-purple-200'
                            : 'bg-blue-50 text-blue-700 border border-blue-200'
                        }`}
                      >
                        {t.created_by === 'XOMNI' ? 'AI Suggested' : 'Manual'}
                      </span>
                      {t.status === 'done' ? <CheckCircle2 className="h-4 w-4 text-primary" /> : <Circle className="h-4 w-4 text-muted" />}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Inline Add Todo Form */}
            <form onSubmit={handleAddTodo} className="mt-4 flex items-center gap-2 border-t border-line/50 pt-3">
              <input
                type="text"
                placeholder="+ Add task for today..."
                value={newTodoTitle}
                onChange={(e) => setNewTodoTitle(e.target.value)}
                className="flex-1 bg-mist/30 rounded-lg px-2.5 py-1.5 text-xs text-ink placeholder:text-muted outline-none border border-line/60 focus:border-primary"
              />
              <select
                value={newTodoPriority}
                onChange={(e) => setNewTodoPriority(e.target.value as any)}
                className="bg-mist/30 text-[11px] rounded-lg px-2 py-1.5 border border-line/60 text-ink outline-none"
              >
                <option value="important">High</option>
                <option value="normal">Normal</option>
                <option value="less">Low</option>
              </select>
              <button
                type="submit"
                disabled={addingTodo || !newTodoTitle.trim()}
                className="bg-primary hover:bg-primary-hover text-primary-foreground text-xs font-semibold px-3 py-1.5 rounded-lg transition disabled:opacity-50"
              >
                {addingTodo ? "..." : "Add"}
              </button>
            </form>
          </div>
          <div className="rounded-2xl border border-line bg-surface/80 p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Timetable adherence</p>
            <p className="mt-2 text-2xl font-semibold text-ink">{stats?.block_pct ?? 0}%</p>
            <p className="text-xs text-muted">{stats?.block_done ?? 0}/{stats?.block_total ?? 0} blocks done</p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-mist">
              <div className="h-full rounded-full bg-primary transition-all" style={{ width: `var(--block-w, ${Math.min(100, stats?.block_pct ?? 0)}%)` } as React.CSSProperties} />
            </div>
          </div>
        </div>
      </div>

      {/* Day plan / Timeline */}
      {period === "day" ? (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-xl font-semibold text-ink">Today&apos;s plan</h2>
              <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${km.bg} ${km.color}`}>{km.label} timetable</span>
            </div>
            <div className="rounded-[1.5rem] border border-line bg-surface p-4 shadow-card">
              {dayBlocks.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-hover text-text-secondary mb-4">
                    <Calendar className="h-6 w-6" />
                  </div>
                  <h3 className="text-[14px] font-semibold text-text-primary">No blocks planned</h3>
                  <p className="text-[13px] text-text-secondary mt-1">Your schedule is clear for today.</p>
                  <button className="mt-4 rounded-xl border border-border bg-surface px-4 py-2 text-[13px] font-medium text-text-primary shadow-sm hover:bg-surface-hover transition-colors">
                    Add a block
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {dayBlocks.map((b) => (
                    <div
                      key={b.id}
                      className={`flex items-center justify-between gap-3 rounded-2xl border px-4 py-3 transition ${
                        b.is_current ? "border-primary/40 bg-primary-soft/40 shadow-lift" : "border-line bg-surface"
                      } ${b.is_past && !b.status ? "opacity-70" : ""}`}
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium text-ink">{b.title}</p>
                        <p className="text-xs text-muted">
                          {fmtMin(b.start_minute)} – {fmtMin(b.end_minute)} · {priorityLabel[b.priority] || b.priority}
                          {b.status ? ` · ${b.status}` : null}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {b.is_current && !b.status && (
                          <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-primary" />
                        )}
                        {b.status === "done" ? (
                          <CheckCircle2 className="h-5 w-5 text-primary" />
                        ) : b.status === "partial" ? (
                          <Circle className="h-5 w-5 text-amber-600" />
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-[1.5rem] border border-line bg-surface p-4 shadow-card">
              <h3 className="text-sm font-semibold text-ink">Quick actions</h3>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button onClick={() => setSelectedDate(todayISO())} className="rounded-xl border border-line px-3 py-2 text-xs font-semibold hover:bg-mist">Today</button>
                <button onClick={() => setSelectedDate(toDateISO(new Date(Date.now() - 86400000)))} className="rounded-xl border border-line px-3 py-2 text-xs font-semibold hover:bg-mist">Yesterday</button>
                <button onClick={() => setSelectedDate(toDateISO(new Date(Date.now() + 86400000)))} className="rounded-xl border border-line px-3 py-2 text-xs font-semibold hover:bg-mist">Tomorrow</button>
                <button onClick={() => setShowCheckin(true)} className="rounded-xl bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground">Check in</button>
              </div>
            </div>
            <div className="rounded-[1.5rem] border border-line bg-surface p-4 shadow-card">
              <h3 className="text-sm font-semibold text-ink">Telegram</h3>
              <p className="mt-1 text-xs text-muted">Connect a bot from Profile. Once linked, Xomni proposals can be confirmed here or in Telegram.</p>
              <Link href="/app/profile" className="mt-3 inline-flex rounded-xl bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground">
                Open Telegram settings
              </Link>
            </div>
          </div>
        </div>
      ) : null}

      {/* 3 timetable cards */}
      <div>
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl font-semibold text-ink">Your timetables</h2>
          <span className="text-xs text-muted">Productive · Backup · Holiday</span>
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {productiveTT && (
            <div className="rounded-[1.5rem] border border-line bg-surface p-5 shadow-card">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Productive</p>
              <p className="mt-1 font-semibold text-ink">{productiveTT.name}</p>
              <p className="text-xs text-muted">{productiveTT.blocks.length} blocks</p>
              <div className="mt-3 space-y-2">
                {productiveTT.blocks.slice(0, 5).map((b) => (
                  <div key={b.id} className={`rounded-xl px-3 py-2 text-xs ${b.priority === "important" ? "bg-critical/10 text-critical" : b.priority === "less" ? "bg-mist text-muted" : "bg-mist/60 text-ink"}`}>
                    {fmtMin(b.start_minute)}–{fmtMin(b.end_minute)} · {b.title}
                  </div>
                ))}
                {productiveTT.blocks.length > 5 ? <p className="text-xs text-muted">+{productiveTT.blocks.length - 5} more</p> : null}
              </div>
            </div>
          )}
          {backupTT && (
            <div className="rounded-[1.5rem] border border-line bg-surface p-5 shadow-card">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Backup</p>
              <p className="mt-1 font-semibold text-ink">{backupTT.name}</p>
              <p className="text-xs text-muted">{backupTT.blocks.length} blocks</p>
              <div className="mt-3 space-y-2">
                {backupTT.blocks.map((b) => (
                  <div key={b.id} className={`rounded-xl px-3 py-2 text-xs ${b.priority === "important" ? "bg-critical/10 text-critical" : b.priority === "less" ? "bg-mist text-muted" : "bg-mist/60 text-ink"}`}>
                    {fmtMin(b.start_minute)}–{fmtMin(b.end_minute)} · {b.title}
                  </div>
                ))}
              </div>
            </div>
          )}
          {holidayTT && (
            <div className="rounded-[1.5rem] border border-line bg-surface p-5 shadow-card">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Holiday</p>
              <p className="mt-1 font-semibold text-ink">{holidayTT.name}</p>
              <p className="text-xs text-muted">{holidayTT.blocks.length} blocks</p>
              <div className="mt-3 space-y-2">
                {holidayTT.blocks.map((b) => (
                  <div key={b.id} className={`rounded-xl px-3 py-2 text-xs ${b.priority === "important" ? "bg-critical/10 text-critical" : b.priority === "less" ? "bg-mist text-muted" : "bg-mist/60 text-ink"}`}>
                    {fmtMin(b.start_minute)}–{fmtMin(b.end_minute)} · {b.title}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Week / Month / Year summaries */}
      {period !== "day" ? (
        <div className="rounded-[1.5rem] border border-line bg-surface p-6 shadow-card">
          <h2 className="font-display text-xl font-semibold text-ink capitalize">{period} overview</h2>
          <p className="mt-1 text-sm text-muted">Coming soon — weekly, monthly, and yearly trend cards will appear here with historical adherence and priority breakdowns.</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
              <div key={d} className="rounded-2xl border border-dashed border-line p-4 text-center">
                <p className="text-xs font-semibold text-muted">{d}</p>
                <p className="mt-1 text-lg font-semibold text-ink">--</p>
                <p className="text-xs text-muted">adherence</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Error */}
      {error ? <ErrorState description={error} onRetry={() => void load()} /> : null}

      {/* Check-in inline panel */}
      {showCheckin && checkinBlock ? (
        <div className="rounded-[1.5rem] border border-line bg-surface p-5 shadow-card">
          <div className="flex items-center gap-3">
            <Bell className="h-5 w-5 text-primary" />
            <div>
              <h3 className="font-display text-lg font-semibold text-ink">What are you working on?</h3>
              <p className="text-xs text-muted">
                Planned: <span className="font-semibold text-ink">{checkinBlock.title}</span> · {fmtMin(checkinBlock.start_minute)} – {fmtMin(checkinBlock.end_minute)}
              </p>
            </div>
          </div>
          <div className="mt-4 space-y-3">
            <input
              value={checkinTitle}
              onChange={(e) => setCheckinTitle(e.target.value)}
              placeholder="What are you actually doing?"
              className="w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm"
            />
            <div className="flex items-center gap-2">
              <input type="checkbox" id="matched" checked={checkinMatched} onChange={(e) => setCheckinMatched(e.target.checked)} className="h-4 w-4 rounded border-line accent-primary" />
              <label htmlFor="matched" className="text-xs text-muted">It matches the planned task</label>
            </div>
            <div className="flex gap-2">
              <button onClick={handleCheckin} className="flex-1 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground">Save check-in</button>
              <button onClick={() => { setShowCheckin(false); setCheckinBlock(null); }} className="rounded-xl border border-line px-4 py-2.5 text-sm font-semibold">Skip</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
