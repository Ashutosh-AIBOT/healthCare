"use client";

import * as React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { EmptyState, ErrorState } from "@/components/ui/card";
import { apiClient } from "@/lib/auth-client";
import { Bell, Send, CheckCircle2, Circle, SkipForward } from "lucide-react";

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
  productive: { label: "Productive", color: "text-primary", bg: "bg-primary-soft" },
  backup: { label: "Backup", color: "text-amber-700", bg: "bg-amber-50" },
  holiday: { label: "Holiday", color: "text-emerald-700", bg: "bg-emerald-50" },
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
  const [telegramChatId, setTelegramChatId] = useState<string>("");
  const [telegramStatus, setTelegramStatus] = useState<string>("");

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

  const handleConnectTelegram = async () => {
    setTelegramStatus("connect_requested");
    await apiClient("/api/v1/integrations/telegram/connect", {
      method: "POST",
      body: JSON.stringify({ chat_id: telegramChatId }),
    });
    setTelegramStatus("connected");
  };

  const handleSendDailyReport = async () => {
    await apiClient("/api/v1/integrations/telegram/daily-report", {
      method: "POST",
      body: JSON.stringify({ date: selectedDate }),
    });
    setTelegramStatus("report_sent");
    setTimeout(() => setTelegramStatus(""), 3000);
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
        <div className="h-10 w-48 animate-pulse rounded-xl bg-mist" />
        <div className="h-40 animate-pulse rounded-[1.75rem] border border-line/30 bg-surface" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-[1.75rem] border border-line/30 bg-surface" />
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
      {/* Hero card */}
      <div className="rounded-[1.75rem] border border-line bg-gradient-to-br from-surface via-surface to-mist/30 p-6 shadow-card">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Time Management</p>
            <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight text-ink">
              {isToday ? `Good ${new Date().getHours() < 12 ? "morning" : "evening"}!` : `Schedule for ${selectedDate}`}
            </h1>
            <p className="mt-1 text-sm text-muted">
              Today&apos;s mode: <span className={`font-semibold ${km.color}`}>{km.label}</span> · {timetables.reduce((a, t) => a + t.blocks.length, 0)} blocks across 3 timetables
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex rounded-full border border-line bg-surface p-1">
              {(["day", "week", "month", "year"] as Period[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`rounded-full px-4 py-1.5 text-xs font-semibold capitalize transition ${period === p ? "bg-primary text-primary-foreground shadow-lift" : "text-muted hover:text-ink"}`}
                >
                  {p}
                </button>
              ))}
            </div>
            <button
              onClick={handleSendDailyReport}
              className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-xs font-semibold text-ink hover:bg-mist"
            >
              <Send className="h-4 w-4" />
              Telegram daily report
            </button>
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
                <p className="text-sm text-muted">No blocks planned for today.</p>
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
              <p className="mt-1 text-xs text-muted">Connect Telegram to get daily reports and check-in reminders.</p>
              <div className="mt-3 flex gap-2">
                <input
                  value={telegramChatId}
                  onChange={(e) => setTelegramChatId(e.target.value)}
                  placeholder="Telegram chat_id"
                  className="flex-1 rounded-xl border border-line bg-surface px-3 py-2 text-xs"
                />
                <button onClick={handleConnectTelegram} className="rounded-xl bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground">Connect</button>
              </div>
              {telegramStatus && <p className="mt-2 text-xs text-muted">{telegramStatus}</p>}
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
