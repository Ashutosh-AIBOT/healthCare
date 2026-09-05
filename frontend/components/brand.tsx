import Link from "next/link";
import { cn } from "@/lib/utils";

export function Logo({ className, href = "/" }: { className?: string; href?: string }) {
  return (
    <Link
      href={href}
      className={cn(
        "font-display text-xl font-semibold tracking-tight text-ink transition-opacity duration-500 ease-soft hover:opacity-80",
        className,
      )}
    >
      Aarogya
    </Link>
  );
}

export function Disclaimer({ className }: { className?: string }) {
  return (
    <p className={cn("text-xs leading-relaxed text-muted", className)}>
      Not a medical device. Aarogya explains and coordinates care — it does not diagnose, prescribe, or
      replace a clinician.
    </p>
  );
}

export function XomniBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary",
        className,
      )}
    >
      Xomni
    </span>
  );
}
