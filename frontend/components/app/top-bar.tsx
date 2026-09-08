"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { apiClient, getAccessToken, setAccessToken } from "@/lib/auth-client";

type Me = {
  full_name: string | null;
  handle: string | null;
  email: string;
  role: string;
};

export function TopBar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      // Prefer explicit token, fall back to cookie-forwarded auth via BFF
      const token = getAccessToken();
      const headers: Record<string, string> = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      const { data } = await apiClient<Me>("/api/v1/auth/me", { headers });
      if (!cancelled) {
        if (data?.email) setMe(data);
        setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  const initial = (me?.full_name?.trim()?.[0] || me?.handle?.[0] || me?.email?.[0] || "A").toUpperCase();
  const displayName = me?.full_name || me?.handle || me?.email || "Account";

  const handleLogout = async () => {
    setOpen(false);
    await apiClient("/api/v1/auth/logout", { method: "POST", body: "{}" });
    setAccessToken(null);
    // Clear any stale token in memory and force middleware to re-evaluate
    router.replace("/login");
    router.refresh();
  };

  return (
    <header className="sticky top-0 z-30 border-b border-line/50 bg-surface/85 backdrop-blur-xl">
      <div className="flex h-16 items-center justify-between gap-4 px-4 md:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onToggleSidebar}
            aria-label="Toggle sidebar"
            className="rounded-xl p-2 text-muted hover:bg-mist hover:text-ink lg:hidden"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle className="rounded-xl p-2 text-muted hover:bg-mist hover:text-ink" />
          <button
            type="button"
            className="relative rounded-xl p-2 text-muted hover:bg-mist hover:text-ink"
            aria-label="Notifications"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
            <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-critical" />
          </button>
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-soft text-sm font-semibold text-primary ring-1 ring-line/30 transition hover:bg-primary-soft/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
              aria-label="Profile menu"
              aria-haspopup="menu"
              aria-expanded={open}
            >
              {loading ? "…" : initial}
            </button>
            {open ? (
              <div
                role="menu"
                className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-2xl border border-line bg-surface p-2 shadow-lift"
              >
                <div className="rounded-xl bg-mist/50 px-3 py-3">
                  <p className="truncate text-sm font-semibold text-ink" title={displayName}>
                    {displayName}
                  </p>
                  {me?.email ? <p className="truncate text-xs text-muted">{me.email}</p> : null}
                  {me?.role ? <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-primary">{me.role.replaceAll("_", " ")}</p> : null}
                </div>
                <div className="mt-2 grid gap-1">
                  <Link
                    href="/app/profile"
                    onClick={() => setOpen(false)}
                    role="menuitem"
                    className="rounded-xl px-3 py-2 text-sm font-medium text-ink hover:bg-mist"
                  >
                    View profile
                  </Link>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={handleLogout}
                    className="rounded-xl px-3 py-2 text-left text-sm font-semibold text-critical hover:bg-critical/10"
                  >
                    Logout
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
