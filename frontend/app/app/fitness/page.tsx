import { StatCard } from "@/components/dashboard/stat-card";
import { EmptyState } from "@/components/ui/card";

const week = [
  { day: "Mon", minutes: 30 },
  { day: "Tue", minutes: 0 },
  { day: "Wed", minutes: 45 },
  { day: "Thu", minutes: 20 },
  { day: "Fri", minutes: 60 },
  { day: "Sat", minutes: 15 },
  { day: "Sun", minutes: 0 },
];

const maxMinutes = Math.max(...week.map((d) => d.minutes), 1);

export default function FitnessPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">Fitness</h1>
        <p className="text-sm text-muted">Activity, workouts, and recovery at a glance.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Active days" value="4 / 7" trend="This week" color="lime" />
        <StatCard label="Active minutes" value="170" trend="+25 vs last week" color="primary" />
        <StatCard label="Workouts" value="6" trend="2 strength · 4 cardio" color="blush" />
        <StatCard label="Rest days" value="3" trend="Recovery on track" color="charcoal" />
      </div>

      <div className="rounded-[1.75rem] bg-surface p-6 shadow-card">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-ink">This week</h2>
          <p className="text-xs text-muted">Minutes per day</p>
        </div>
        <div
          className="mt-6 flex h-40 items-end gap-2 sm:gap-3"
          role="img"
          aria-label="Bar chart of active minutes per day this week"
        >
          {week.map((d) => (
            <div key={d.day} className="flex h-full flex-1 flex-col items-center justify-end gap-2">
              <div
                className={`w-full rounded-xl ${d.minutes > 0 ? "bg-primary" : "bg-line/60"}`}
                style={{ height: `${Math.max((d.minutes / maxMinutes) * 100, 4)}%` }}
              />
              <span className="text-[11px] font-medium text-muted">{d.day}</span>
            </div>
          ))}
        </div>
      </div>

      <EmptyState
        title="Workout logging connects next"
        description="Log runs, strength sessions, and water intake here. The tracking API lands with the fitness backend slice — your week view above will fill in automatically."
      />
    </div>
  );
}
