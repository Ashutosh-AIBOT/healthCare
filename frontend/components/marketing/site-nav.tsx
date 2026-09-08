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
  const [overLight, setOverLight] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const trust = document.getElementById("trust");
    if (!trust) return;
    const observer = new IntersectionObserver(
      ([entry]) => setOverLight(entry.boundingClientRect.top < 96),
      { threshold: 0 },
    );
    observer.observe(trust);
    return () => observer.disconnect();
  }, []);

  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-40 flex justify-center px-4 pt-5 md:px-6">
      <nav
        className={cn(
          "pointer-events-auto flex w-full max-w-5xl items-center justify-between gap-4 rounded-full border px-4 py-2.5 backdrop-blur-xl transition-[background-color,border-color] duration-250 ease-soft md:px-5",
          !scrolled && "border-transparent bg-transparent",
          scrolled && !overLight && "border-home-border/80 bg-home-dark/60",
          scrolled && overLight && "border-home-light-border/80 bg-white/70",
        )}
        aria-label="Primary"
      >
        <Logo className={overLight ? "text-home-primary-light" : "text-home-primary-dark"} />
        <ul className="hidden items-center gap-7 md:flex">
          {links.map((l) => (
            <li key={l.href}>
              <Link
                href={l.href}
                className={cn(
                  "text-sm font-medium transition-colors",
                  overLight
                    ? "text-home-secondary-light hover:text-home-primary-light"
                    : "text-home-secondary-dark hover:text-home-primary-dark",
                )}
              >
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className={cn(
              "hidden text-sm font-medium transition-colors sm:inline",
              overLight
                ? "text-home-secondary-light hover:text-home-primary-light"
                : "text-home-secondary-dark hover:text-home-primary-dark",
            )}
          >
            Sign in
          </Link>
          <Link href="/register">
            <Button size="sm" className="group bg-home-gold text-home-dark hover:bg-home-gold/90">
              Get started
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-home-dark/15 text-xs transition-transform group-hover:translate-x-0.5">
                →
              </span>
            </Button>
          </Link>
          <button
            type="button"
            className={cn(
              "relative flex h-10 w-10 items-center justify-center rounded-full border md:hidden",
              overLight ? "border-home-light-border/70" : "border-home-border/70",
            )}
            aria-expanded={open}
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((v) => !v)}
          >
            <span className={cn("absolute h-0.5 w-4 transition-transform duration-500 ease-soft", overLight ? "bg-home-primary-light" : "bg-home-primary-dark", open ? "rotate-45" : "-translate-y-1")} />
            <span className={cn("absolute h-0.5 w-4 transition-transform duration-500 ease-soft", overLight ? "bg-home-primary-light" : "bg-home-primary-dark", open ? "-rotate-45" : "translate-y-1")} />
          </button>
        </div>
      </nav>
      {open ? (
        <div className={cn(
          "pointer-events-auto absolute inset-x-4 top-[4.5rem] rounded-3xl border p-6 shadow-lift backdrop-blur-xl md:hidden",
          overLight ? "border-home-light-border/70 bg-white/95" : "border-home-border/70 bg-home-dark/95",
        )}>
          <ul className="flex flex-col gap-4">
            {links.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className={cn("block text-lg font-medium", overLight ? "text-home-primary-light" : "text-home-primary-dark")}
                  onClick={() => setOpen(false)}
                >
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
