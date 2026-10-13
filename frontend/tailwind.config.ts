import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        /* New Semantic Tokens */
        bg: "var(--color-bg)",
        surface: "var(--color-surface)",
        "surface-hover": "var(--color-surface-hover)",
        border: "var(--color-border)",
        "text-primary": "var(--color-text-primary)",
        "text-secondary": "var(--color-text-secondary)",
        "accent-gold": "var(--color-accent-gold)",
        "accent-teal": "var(--color-accent-teal)",
        "accent-water": "var(--color-accent-water)",
        success: "var(--color-success)",
        danger: "var(--color-danger)",

        /* Legacy Fallbacks (to prevent breaking the app during migration) */
        paper: "var(--color-bg)",
        ink: "var(--color-text-primary)",
        mist: "var(--color-surface-hover)",
        foam: "var(--color-bg)",
        sunken: "var(--color-bg)",
        line: "var(--color-border)",
        primary: {
          DEFAULT: "var(--color-accent-gold)",
          foreground: "var(--color-bg)",
          soft: "var(--color-accent-gold)",
        },
        muted: "var(--color-text-secondary)",
        critical: "var(--color-danger)",
        "primary-soft": "var(--color-primary-soft)",
        healthy: "var(--color-healthy)",
        apricot: "var(--color-apricot)",
        lime: "var(--color-lime)",
        "lime-ink": "var(--color-lime-ink)",
        blush: "var(--color-blush)",
        charcoal: {
          DEFAULT: "var(--color-surface-hover)",
          foreground: "var(--color-text-primary)",
        },

        /* Homepage-only fixed two-tone palette (spec hexes, verbatim).
           Scoped to the marketing homepage — nothing else references home-*. */
        home: {
          dark: "#10181D",
          surface: "#172228",
          border: "#2B3A42",
          light: "#F6F8FA",
          "light-border": "#D9E1E6",
          "primary-dark": "#EDF3F4",
          "secondary-dark": "#A0B0B5",
          "primary-light": "#17232B",
          "secondary-light": "#5F6D76",
          gold: "#65B5AC",
        },
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
        full: "var(--radius-full)",
      },
      boxShadow: {
        ambient: "var(--shadow-ambient)",
        lift: "var(--shadow-lift)",
        hairline: "var(--shadow-hairline)",
        card: "var(--shadow-card)",
        "home-gold-glow": "0 0 0 1px rgba(232, 169, 58, 0.3)",
      },
      transitionTimingFunction: {
        soft: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(1.25rem)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "home-rise": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        drift: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "50%": { transform: "translate(2%, -3%) scale(1.04)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.9s cubic-bezier(0.32, 0.72, 0, 1) both",
        "home-rise": "home-rise 0.5s ease-out both",
        drift: "drift 18s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
