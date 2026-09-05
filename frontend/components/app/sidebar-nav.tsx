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
};

const mainNav = [
  { href: "/app", label: "Dashboard", icon: icons.dashboard },
  { href: "/app/time", label: "Time Management", icon: icons.time },
  { href: "/app/food", label: "Food", icon: icons.food },
  { href: "/app/doctors", label: "Doctors", icon: icons.doctors },
  { href: "/app/agency", label: "Agency", icon: icons.agency },
  { href: "/app/messaging", label: "Messaging", icon: icons.messaging },
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
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 -translate-x-full border-r border-line bg-surface transition-transform duration-300 ease-soft lg:translate-x-0",
          open && "translate-x-0",
        )}
        aria-label="Sidebar"
      >
        <div className="flex h-full flex-col">
          <div className="flex h-16 items-center gap-2 px-6">
            <span className="font-display text-xl font-semibold text-ink">Aarogya</span>
            <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
              Xomni
            </span>
          </div>
          <div className="px-3 pb-2">
            <Link
              href={xomniAction.href}
              className={cn(
                "flex items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2.5 text-sm font-semibold text-ink shadow-card transition-colors duration-300 ease-soft hover:bg-mist",
                activeItem(xomniAction.href) && "border-primary text-primary",
              )}
            >
              <span className="flex items-center justify-center rounded-lg bg-mist p-1.5 text-muted">
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
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-300 ease-soft",
                      active
                        ? "bg-primary-soft text-primary"
                        : "text-muted hover:bg-mist hover:text-ink",
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    <span
                      className={cn(
                        "flex items-center justify-center rounded-lg p-1.5",
                        active ? "bg-primary text-primary-foreground" : "bg-mist/60 text-muted",
                      )}
                    >
                      {item.icon}
                    </span>
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </nav>
          <div className="mt-auto border-t border-line px-3 py-4">
            <div className="space-y-1">
              {bottomNav.map((item) => {
                const active = activeItem(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-300 ease-soft",
                      active
                        ? "bg-primary-soft text-primary"
                        : "text-muted hover:bg-mist hover:text-ink",
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    <span
                      className={cn(
                        "flex items-center justify-center rounded-lg p-1.5",
                        active ? "bg-primary text-primary-foreground" : "bg-mist/60 text-muted",
                      )}
                    >
                      {item.icon}
                    </span>
                    {item.label}
                  </Link>
                );
              })}
            </div>
            <div className="mt-4 space-y-2">
              <p className="text-xs text-muted">
                Powered by <span className="font-semibold text-primary">Xomni</span>
              </p>
              {onLogout ? (
                <button
                  type="button"
                  onClick={onLogout}
                  className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm font-medium text-muted transition-colors duration-300 ease-soft hover:bg-mist hover:text-ink"
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
