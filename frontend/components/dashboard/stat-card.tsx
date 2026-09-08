import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

const colorStyles: Record<string, { chipBg: string; chipText: string; barBg: string }> = {
  teal: { chipBg: "bg-accent-teal/15", chipText: "text-accent-teal", barBg: "bg-accent-teal" },
  gold: { chipBg: "bg-accent-gold/15", chipText: "text-accent-gold", barBg: "bg-accent-gold" },
  coral: { chipBg: "bg-danger/15", chipText: "text-danger", barBg: "bg-danger" },
  blue: { chipBg: "bg-accent-water/15", chipText: "text-accent-water", barBg: "bg-accent-water" },
  neutral: { chipBg: "bg-border", chipText: "text-text-primary", barBg: "bg-text-secondary" },
};

export function StatCard({
  label,
  value,
  trend,
  color = "neutral",
  icon,
  progress, // 0 to 100
  className,
}: {
  label: string;
  value: string | number;
  trend?: string;
  color?: "teal" | "gold" | "coral" | "blue" | "neutral";
  icon?: ReactNode;
  progress?: number;
  className?: string;
}) {
  const style = colorStyles[color] || colorStyles.neutral;

  return (
    <div
      className={cn(
        "flex flex-col justify-between rounded-[16px] p-6 bg-surface border border-border",
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-medium text-text-secondary">{label}</span>
        {icon && (
          <span className={cn("flex items-center justify-center h-8 w-8 rounded-full", style.chipBg, style.chipText)}>
            {icon}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-[28px] font-semibold tabular tracking-tight text-text-primary">{value}</p>
        {trend && <p className="mt-1 text-[13px] text-text-secondary">{trend}</p>}
        {typeof progress === "number" && (
          <div className="mt-3 h-1 w-full rounded-full bg-surface-hover overflow-hidden">
            <div 
              className={cn("h-full rounded-full transition-all duration-500 ease-soft", style.barBg)} 
              style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} 
            />
          </div>
        )}
      </div>
    </div>
  );
}
