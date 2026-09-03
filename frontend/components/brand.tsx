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
