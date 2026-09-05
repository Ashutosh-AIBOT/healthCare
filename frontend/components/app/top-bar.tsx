"use client";

import { ThemeToggle } from "@/components/theme-toggle";

export function TopBar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
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
          <div className="relative hidden sm:block">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="search"
              placeholder="Search..."
              className="h-9 w-64 rounded-xl border border-line bg-surface pl-9 pr-4 text-sm text-ink outline-none transition-colors duration-300 ease-soft placeholder:text-muted/70 focus:border-primary focus:ring-2 focus:ring-primary/15"
              aria-label="Search"
            />
          </div>
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
          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-soft text-sm font-semibold text-primary"
            aria-label="Profile"
          >
            A
          </button>
        </div>
      </div>
    </header>
  );
}
