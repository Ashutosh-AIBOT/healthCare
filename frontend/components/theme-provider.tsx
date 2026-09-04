"use client";

import * as React from "react";

type Theme = "light" | "dark" | "system";

type Ctx = {
  theme: Theme;
  resolved: "light" | "dark";
  setTheme: (t: Theme) => void;
};

const ThemeCtx = React.createContext<Ctx | null>(null);

function getSystem(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>("system");
  const [resolved, setResolved] = React.useState<"light" | "dark">("light");

  React.useEffect(() => {
    const stored = (localStorage.getItem("aarogya-theme") as Theme | null) ?? "system";
    setThemeState(stored);
    const r = stored === "system" ? getSystem() : stored;
    setResolved(r);
    document.documentElement.classList.toggle("dark", r === "dark");
    document.documentElement.setAttribute("data-theme", r);
  }, []);

  const setTheme = React.useCallback((t: Theme) => {
    localStorage.setItem("aarogya-theme", t);
    const r = t === "system" ? getSystem() : (t as "light" | "dark");
    setResolved(r);
    document.documentElement.classList.toggle("dark", r === "dark");
    document.documentElement.setAttribute("data-theme", r);
    // update theme-color meta
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", r === "dark" ? "#0e1b20" : "#fdfcfa");
  }, []);

  React.useEffect(() => {
    if (theme !== "system") return;
    const m = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const r = getSystem();
      setResolved(r);
      document.documentElement.classList.toggle("dark", r === "dark");
      document.documentElement.setAttribute("data-theme", r);
    };
    m.addEventListener("change", onChange);
    return () => m.removeEventListener("change", onChange);
  }, [theme]);

  return <ThemeCtx.Provider value={{ theme, resolved, setTheme }}>{children}</ThemeCtx.Provider>;
}

export function useTheme() {
  const v = React.useContext(ThemeCtx);
  if (!v) throw new Error("useTheme must be inside ThemeProvider");
  return v;
}
