import Link from "next/link";
import { Logo, Disclaimer } from "@/components/brand";

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative min-h-dvh overflow-hidden bg-foam">
      <div
        aria-hidden
        className="absolute inset-0 bg-[radial-gradient(80%_60%_at_0%_0%,color-mix(in_srgb,var(--color-primary)_18%,transparent),transparent_55%),radial-gradient(60%_50%_at_100%_100%,color-mix(in_srgb,var(--color-healthy)_12%,transparent),transparent_50%)]"
      />
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-grain opacity-[0.03] mix-blend-multiply" />
      <div className="relative mx-auto grid min-h-dvh max-w-6xl lg:grid-cols-[1.05fr_0.95fr]">
        <aside className="hidden flex-col justify-between px-10 py-12 lg:flex xl:px-14">
          <Logo className="text-2xl" />
          <div className="max-w-md pb-8">
            <p className="font-display text-4xl font-semibold leading-[1.1] tracking-tight text-ink xl:text-5xl">
              Health records your family can actually understand.
            </p>
            <p className="mt-5 text-sm leading-relaxed text-muted">
              Explain reports with citations. Share only the fields you choose. Book the next checkup
              without guessing.
            </p>
            <Disclaimer className="mt-8" />
          </div>
        </aside>
        <div className="flex flex-col justify-center px-5 py-16 sm:px-8 lg:border-l lg:border-line/50 lg:bg-surface/40 lg:px-12 lg:backdrop-blur-sm">
          <Logo className="mb-10 lg:hidden" />
          <h1 className="font-display text-3xl font-semibold tracking-tight text-ink md:text-[2rem]">{title}</h1>
          {subtitle ? <p className="mt-2 text-sm leading-relaxed text-muted">{subtitle}</p> : null}
          <div className="mt-8">{children}</div>
          <Disclaimer className="mt-10 lg:hidden" />
          <p className="mt-6 text-center text-xs text-muted lg:text-left">
            <Link href="/" className="transition-colors hover:text-ink">
              ← Back to home
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
