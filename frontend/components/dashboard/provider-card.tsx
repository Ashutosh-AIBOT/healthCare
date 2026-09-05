import { cn } from "@/lib/utils";

export function ProviderCard({
  name,
  specialty,
  available,
  className,
}: {
  name: string;
  specialty: string;
  available?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-[1.25rem] bg-surface p-4 shadow-card transition-colors duration-300 ease-soft hover:shadow-lift",
        className,
      )}
    >
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-mist text-sm font-semibold text-ink">
          {name
            .split(" ")
            .map((n) => n[0])
            .join("")
            .slice(0, 2)}
        </div>
        <div>
          <p className="text-sm font-semibold text-ink">{name}</p>
          <p className="text-xs text-muted">{specialty}</p>
        </div>
      </div>
      <span
        className={cn(
          "rounded-full px-2.5 py-1 text-[11px] font-semibold",
          available
            ? "bg-healthy-excellent/10 text-healthy-excellent"
            : "bg-mist text-muted",
        )}
      >
        {available ? "Available" : "Busy"}
      </span>
    </div>
  );
}
