import { cn } from "@/lib/utils";
import { HTMLAttributes, type ReactNode } from "react";

export function Card({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-xl border border-border bg-surface shadow-card", className)} {...props}>{children}</div>;
}

export function CardHeader({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("mb-4 p-5 pb-0 md:p-6 md:pb-0", className)} {...props}>
      {children}
    </div>
  );
}

export function CardContent({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("p-5 md:p-6", className)} {...props}>
      {children}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-3xl border border-dashed border-line bg-mist/40 px-6 py-10">
      <h3 className="text-lg font-semibold text-ink">{title}</h3>
      <p className="max-w-md text-sm text-muted">{description}</p>
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
}: {
  title?: string;
  description: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-3xl border border-critical/30 bg-critical/5 px-6 py-8" role="alert">
      <h3 className="font-semibold text-critical">{title}</h3>
      <p className="mt-2 text-sm text-muted">{description}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 text-sm font-semibold text-primary underline-offset-4 hover:underline"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-2xl bg-mist", className)} aria-hidden />;
}
