"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Logo } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { href: "#how", label: "How it works" },
  { href: "/features", label: "Features" },
  { href: "/pricing", label: "Pricing" },
  { href: "/for-doctors", label: "For doctors" },
];

export function SiteNav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-40 flex justify-center px-4 pt-5 md:px-6">
      <nav
        className={cn(
          "pointer-events-auto flex w-full max-w-5xl items-center justify-between gap-4 rounded-full border border-line/60 bg-foam/80 px-4 py-2.5 shadow-ambient backdrop-blur-xl transition-all duration-700 ease-soft md:px-5",
          scrolled && "bg-foam/95",
        )}
        aria-label="Primary"
      >
        <Logo />
        <ul className="hidden items-center gap-7 md:flex">
          {links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="text-sm font-medium text-muted transition-colors hover:text-ink">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-2">
          <Link href="/login" className="hidden text-sm font-medium text-muted hover:text-ink sm:inline">
            Sign in
          </Link>
          <Link href="/register">
            <Button size="sm" className="group">
              Get started
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-foam/15 text-xs transition-transform group-hover:translate-x-0.5">
                →
              </span>
            </Button>
          </Link>
          <button
            type="button"
            className="relative flex h-10 w-10 items-center justify-center rounded-full border border-line/70 md:hidden"
            aria-expanded={open}
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((v) => !v)}
          >
            <span className={cn("absolute h-0.5 w-4 bg-ink transition-transform duration-500 ease-soft", open ? "rotate-45" : "-translate-y-1")} />
            <span className={cn("absolute h-0.5 w-4 bg-ink transition-transform duration-500 ease-soft", open ? "-rotate-45" : "translate-y-1")} />
          </button>
        </div>
      </nav>
      {open ? (
        <div className="pointer-events-auto absolute inset-x-4 top-[4.5rem] rounded-3xl border border-line/70 bg-foam/95 p-6 shadow-lift backdrop-blur-xl md:hidden">
          <ul className="flex flex-col gap-4">
            {links.map((l) => (
              <li key={l.href}>
                <Link href={l.href} className="block text-lg font-medium" onClick={() => setOpen(false)}>
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </header>
  );
}
