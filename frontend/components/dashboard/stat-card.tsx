import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

const colorStyles: Record<string, string> = {
  primary: "bg-primary text-primary-foreground",
  lime: "bg-primary text-primary-foreground",
  blush: "bg-primary text-primary-foreground",
  charcoal: "bg-primary text-primary-foreground",
  apricot: "bg-primary text-primary-foreground",
};

const icons: Record<string, ReactNode> = {
  primary: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  lime: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  ),
  blush: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  ),
  charcoal: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  apricot: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
      <path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0h.5a2.5 2.5 0 0 0 0-5H4Z" />
      <path d="M15.5 11.5a5 5 0 0 0-5-5v-1h5v1Z" />
      <path d="M14.5 11.5a5 5 0 0 1 5-5v1h-5v-1Z" />
      <path d="M20.5 6.5H18v5h5v-2a2.5 2.5 0 0 0-2.5-2.5Z" />
      <path d="M14.5 11.5v5a5 5 0 0 0 5 5h-2a3 3 0 0 1-3-3v-2.5a2.5 2.5 0 0 0-2.5-2.5H8v-1a5 5 0 0 1 5-5h1.5Z" />
      <path d="M6.5 11.5v5a5 5 0 0 0 5 5h.5a2.5 2.5 0 0 0 0-5H6.5Z" />
      <path d="M6.5 11.5a5 5 0 0 1 5-5h.5a2.5 2.5 0 0 1 0 5H11v5a5 5 0 0 1-5 5h-.5a2.5 2.5 0 0 1 0-5H6.5Z" />
    </svg>
  ),
};

export function StatCard({
  label,
  value,
  trend,
  color = "primary",
  className,
}: {
  label: string;
  value: string | number;
  trend?: string;
  color?: keyof typeof colorStyles;
  className?: string;
}) {
  const bg = colorStyles[color] || colorStyles.primary;

  return (
    <div
      className={cn(
        "flex flex-col justify-between rounded-[1.75rem] p-6 shadow-lift",
        bg,
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium opacity-90">{label}</span>
        <span className="rounded-xl bg-primary-foreground/20 p-2">{icons[color] || icons.primary}</span>
      </div>
      <div>
        <p className="mt-4 text-3xl font-semibold tracking-tight">{value}</p>
        {trend ? <p className="mt-1 text-xs opacity-90">{trend}</p> : null}
      </div>
    </div>
  );
}
