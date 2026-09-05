"use client";

import { useTheme } from "@/components/theme-provider";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, resolved, setTheme } = useTheme();

  const next =
    theme === "light" ? "dark" : theme === "dark" ? "system" : "light";

  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      className={className}
      aria-label={`Switch theme. Current: ${theme} (resolved: ${resolved})`}
    >
      {resolved === "dark" ? "🌙" : "☀️"}
      <span className="sr-only">Toggle theme</span>
    </button>
  );
}
