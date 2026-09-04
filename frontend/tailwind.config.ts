import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "var(--color-paper)",
        ink: "var(--color-ink)",
        mist: "var(--color-mist)",
        foam: "var(--color-foam)",
        sunken: "var(--color-sunken)",
        line: "var(--color-line)",
        surface: "var(--color-surface)",
        primary: {
          DEFAULT: "var(--color-primary)",
          foreground: "var(--color-primary-foreground)",
          soft: "var(--color-primary-soft)",
        },
        apricot: "var(--color-apricot)",
        healthy: {
          DEFAULT: "var(--color-healthy)",
          excellent: "var(--color-healthy-excellent)",
          good: "var(--color-healthy-good)",
        },
        watch: "var(--color-watch)",
        critical: "var(--color-critical)",
        muted: "var(--color-muted)",
        doctor: "var(--color-doctor)",
        agency: "var(--color-agency)",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        DEFAULT: "var(--radius-md)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        "2xl": "1rem",
        "3xl": "1.5rem",
        "4xl": "2rem",
        full: "var(--radius-full)",
      },
      boxShadow: {
        ambient: "var(--shadow-ambient)",
        lift: "var(--shadow-lift)",
        hairline: "var(--shadow-hairline)",
      },
      transitionTimingFunction: {
        soft: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(1.25rem)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        drift: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "50%": { transform: "translate(2%, -3%) scale(1.04)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.9s cubic-bezier(0.32, 0.72, 0, 1) both",
        drift: "drift 18s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
