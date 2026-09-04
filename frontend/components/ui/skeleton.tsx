import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-line/60", className)} {...props} />;
}

export function CardSkeleton() {
  return (
    <div className="rounded-[1.75rem] border border-line bg-surface p-6">
      <Skeleton className="h-6 w-32" />
      <Skeleton className="mt-4 h-24 w-full" />
      <Skeleton className="mt-4 h-4 w-24" />
    </div>
  );
}

export function ListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full rounded-xl" />
      ))}
    </div>
  );
}
