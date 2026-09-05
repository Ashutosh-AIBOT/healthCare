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

function readInitialTheme(): { theme: Theme; resolved: "light" | "dark" } {
  if (typeof window === "undefined") {
    return { theme: "light", resolved: "light" };
  }
  const stored = (localStorage.getItem("aarogya-theme") as Theme | null) ?? "light";
  const resolved = stored === "system" ? getSystem() : stored;
  return { theme: stored, resolved };
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState(readInitialTheme);

  React.useEffect(() => {
    const { theme, resolved } = state;
    document.documentElement.classList.toggle("dark", resolved === "dark");
    document.documentElement.setAttribute("data-theme", resolved);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", resolved === "dark" ? "#0e1b20" : "#fdfcfa");
  }, [state.resolved]);

  const setTheme = React.useCallback((t: Theme) => {
    localStorage.setItem("aarogya-theme", t);
    const resolved = t === "system" ? getSystem() : t;
    setState({ theme: t, resolved });
  }, []);

  React.useEffect(() => {
    if (state.theme !== "system") return;
    const m = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      const resolved = getSystem();
      setState((prev) => ({ ...prev, resolved }));
      document.documentElement.classList.toggle("dark", resolved === "dark");
      document.documentElement.setAttribute("data-theme", resolved);
    };
    m.addEventListener("change", onChange);
    return () => m.removeEventListener("change", onChange);
  }, [state.theme]);

  return (
    <ThemeCtx.Provider value={{ theme: state.theme, resolved: state.resolved, setTheme }}>
      {children}
    </ThemeCtx.Provider>
  );
}

export function useTheme() {
  const v = React.useContext(ThemeCtx);
  if (!v) throw new Error("useTheme must be inside ThemeProvider");
  return v;
}
