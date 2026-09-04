"use client";

import { cn } from "@/lib/utils";

type Health = "excellent" | "good" | "watch" | "critical";

const colorMap: Record<Health, string> = {
  excellent: "var(--color-healthy-excellent)",
  good: "var(--color-healthy-good)",
  watch: "var(--color-watch)",
  critical: "var(--color-critical)",
};

export function MetricRing({
  value,
  label,
  health = "excellent",
  size = 96,
  className,
}: {
  value: number;
  label: string;
  health?: Health;
  size?: 96 | 160;
  className?: string;
}) {
  const normalized = Math.max(0, Math.min(100, value));
  const angle = (normalized / 100) * 360;
  const color = colorMap[health];
  return (
    <div
      role="img"
      aria-label={`${label} ${normalized} percent, health ${health}`}
      className={cn("relative inline-flex items-center justify-center rounded-full", className)}
      style={{ width: size, height: size }}
    >
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(${color} ${angle}deg, var(--color-line) ${angle}deg)`,
        }}
      />
      <div className="absolute inset-[8px] flex flex-col items-center justify-center rounded-full bg-surface">
        <span className="font-mono text-lg font-semibold tabular text-ink">{normalized}</span>
        <span className="text-[10px] font-medium uppercase tracking-widest text-muted">{label}</span>
      </div>
    </div>
  );
}
