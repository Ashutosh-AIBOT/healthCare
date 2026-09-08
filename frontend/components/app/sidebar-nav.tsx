import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

const icons = {
  dashboard: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  time: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  ),
  food: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M18 8h1a4 4 0 0 1 0 8h-1" />
      <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" />
      <line x1="6" y1="1" x2="6" y2="4" />
      <line x1="10" y1="1" x2="10" y2="4" />
      <line x1="14" y1="1" x2="14" y2="4" />
    </svg>
  ),
  doctors: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0h.5a2.5 2.5 0 0 0 0-5H4Z" />
      <path d="M15.5 11.5a5 5 0 0 0-5-5v-1h5v1Z" />
      <path d="M14.5 11.5a5 5 0 0 1 5-5v1h-5v-1Z" />
      <path d="M20.5 6.5H18v5h5v-2a2.5 2.5 0 0 0-2.5-2.5Z" />
      <path d="M14.5 11.5v5a5 5 0 0 0 5 5h-2a3 3 0 0 1-3-3v-2.5a2.5 2.5 0 0 0-2.5-2.5H8v-1a5 5 0 0 1 5-5h1.5Z" />
      <path d="M6.5 11.5v5a5 5 0 0 0 5 5h.5a2.5 2.5 0 0 0 0-5H6.5Z" />
      <path d="M6.5 11.5a5 5 0 0 1 5-5h.5a2.5 2.5 0 0 1 0 5H11v5a5 5 0 0 1-5 5h-.5a2.5 2.5 0 0 1 0-5H6.5Z" />
    </svg>
  ),
  agency: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  messaging: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  members: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  reports: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  fitness: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M6.5 6.5 17.5 17.5" />
      <path d="m21 21-1-1" />
      <path d="m3 3 1 1" />
      <path d="m18 22 4-4" />
      <path d="m2 6 4-4" />
      <path d="m3 10 7-7" />
      <path d="m14 21 7-7" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  ),
  profile: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  ),
  xomni: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.5 4.5-3 6s-3 3.5-3 5.5" />
      <path d="M12 2a7 7 0 0 0-7 7c0 2.5 1.5 4.5 3 6s3 3.5 3 5.5" />
      <circle cx="12" cy="9" r="2" />
      <path d="M9 21h6" />
    </svg>
  ),
  learn: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v15H6.5A2.5 2.5 0 0 1 4 19.5V4.5A2.5 2.5 0 0 1 6.5 2z" />
      <path d="M8 7h8" />
      <path d="M8 11h8" />
    </svg>
  ),
};

const mainNav = [
  { href: "/app", label: "Dashboard", icon: icons.dashboard },
  { href: "/app/time", label: "Time Management", icon: icons.time },
  { href: "/app/food", label: "Food", icon: icons.food },
  { href: "/app/fitness", label: "Fitness", icon: icons.fitness },
  { href: "/app/learn", label: "Learn", icon: icons.learn },
];

const bottomNav = [
  { href: "/app/settings", label: "Settings", icon: icons.settings },
  { href: "/app/profile", label: "Profile", icon: icons.profile },
];

const xomniAction = { href: "/app/xomni", label: "Xomni", icon: icons.xomni };

export function SidebarNav({
  open,
  onClose,
  onLogout,
  pathname,
}: {
  open: boolean;
  onClose: () => void;
  onLogout?: () => void;
  pathname: string;
}) {
  const activeItem = (href: string) =>
    pathname === href || (href !== "/app" && pathname.startsWith(href));

  React.useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      const onKey = (e: KeyboardEvent) => {
        if (e.key === "Escape") onClose();
      };
      window.addEventListener("keydown", onKey);
      return () => {
        document.body.style.overflow = prev;
        window.removeEventListener("keydown", onKey);
      };
    }
  }, [open, onClose]);

  // focus trap: keep focus inside sidebar when open on mobile
  const asideRef = React.useRef<HTMLElement>(null);
  React.useEffect(() => {
    if (!open || !asideRef.current) return;
    const el = asideRef.current;
    const focusable = el.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
    focusable[0]?.focus();
  }, [open]);

  return (
    <>
      {open ? (
        <button
          type="button"
          onClick={onClose}
          aria-label="Close sidebar"
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm lg:hidden"
        />
      ) : null}
      <aside
        ref={asideRef}
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-[260px] -translate-x-full border-r border-border bg-surface transition-transform duration-300 ease-soft lg:translate-x-0",
          open && "translate-x-0",
        )}
        aria-label="Sidebar"
      >
        <div className="flex h-full flex-col overflow-y-auto overscroll-contain">
          <div className="flex items-center gap-2 p-[20px] pb-4">
            <span className="font-display text-[20px] font-semibold text-text-primary">Aarogya</span>
            <span className="rounded-full border border-accent-gold text-accent-gold px-2 py-0.5 text-[11px] font-semibold leading-none">
              XOMNI
            </span>
          </div>
          
          <div className="px-3 pb-2 pt-2">
            <Link
              href={xomniAction.href}
              className={cn(
                "relative flex items-center gap-[12px] rounded-xl px-[14px] py-[10px] text-[13px] font-medium transition-colors duration-150 ease-soft",
                activeItem(xomniAction.href)
                  ? "bg-surface-hover text-text-primary"
                  : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
              )}
            >
              {activeItem(xomniAction.href) && (
                <span className="absolute left-0 top-0 h-full w-[3px] bg-accent-gold rounded-r-sm" />
              )}
              <span className={cn("flex items-center justify-center [&>svg]:h-[18px] [&>svg]:w-[18px]", activeItem(xomniAction.href) ? "text-accent-gold" : "text-text-secondary")}>
                {xomniAction.icon}
              </span>
              {xomniAction.label}
            </Link>
          </div>

          <nav className="px-3 py-2" aria-label="App">
            <div className="space-y-1">
              {mainNav.map((item) => {
                const active = activeItem(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "relative flex items-center gap-[12px] rounded-xl px-[14px] py-[10px] text-[13px] font-medium transition-colors duration-150 ease-soft",
                      active
                        ? "bg-surface-hover text-text-primary"
                        : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    {active && (
                      <span className="absolute left-0 top-0 h-full w-[3px] bg-accent-gold rounded-r-sm" />
                    )}
                    <span className={cn("flex items-center justify-center [&>svg]:h-[18px] [&>svg]:w-[18px]", active ? "text-accent-gold" : "text-text-secondary")}>
                      {item.icon}
                    </span>
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </nav>

          <div className="mt-auto border-t border-border px-3 py-[14px]">
            <div className="space-y-1">
              {bottomNav.map((item) => {
                const active = activeItem(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "relative flex items-center gap-[12px] rounded-xl px-[14px] py-[10px] text-[13px] font-medium transition-colors duration-150 ease-soft",
                      active
                        ? "bg-surface-hover text-text-primary"
                        : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    {active && (
                      <span className="absolute left-0 top-0 h-full w-[3px] bg-accent-gold rounded-r-sm" />
                    )}
                    <span className={cn("flex items-center justify-center [&>svg]:h-[18px] [&>svg]:w-[18px]", active ? "text-accent-gold" : "text-text-secondary")}>
                      {item.icon}
                    </span>
                    {item.label}
                  </Link>
                );
              })}
            </div>
            <div className="mt-4 space-y-2">
              <p className="text-[11px] text-text-secondary">
                Powered by <span className="font-semibold text-text-primary">Xomni</span>
              </p>
              {onLogout ? (
                <button
                  type="button"
                  onClick={onLogout}
                  className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-[13px] font-medium text-text-secondary transition-colors duration-150 ease-soft hover:bg-surface-hover hover:text-text-primary"
                >
                  Sign out
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
