---
description: Tailwind-only styling rules - no CSS files, no inline styles, tokens only
globs: apps/web/**/*.{ts,tsx,css}
alwaysApply: false
---

# Styling: Tailwind utilities only

**Tailwind is the only styling mechanism in this project.** There is exactly one stylesheet, `apps/web/app/globals.css`, and it contains only Tailwind directives plus CSS custom properties that define design tokens. Nothing else.

## Forbidden

```tsx
// BAD - stylesheet
import styles from "./Card.module.css";

// BAD - inline styles
<div style={{ padding: 16, background: "#4F46E5" }} />

// BAD - CSS-in-JS
const Card = styled.div`padding: 1rem;`

// BAD - raw values instead of tokens
<div className="bg-[#4F46E5] p-[17px] text-[13px]" />
```

## Correct

```tsx
// GOOD - utilities and semantic tokens
<div className="rounded-2xl border border-border bg-card p-4 shadow-sm" />

// GOOD - conditional classes via cn()
<button className={cn("rounded-xl px-4 py-2 font-medium", isActive && "bg-primary text-primary-foreground")} />
```

## Token discipline

Use semantic tokens, never literal colours: `bg-background`, `bg-card`, `bg-primary`, `text-foreground`, `text-muted-foreground`, `border-border`, `bg-destructive`. Health-status tokens: `text-status-normal`, `text-status-watch`, `text-status-critical`. This is what makes dark mode a token swap instead of a rewrite.

Spacing follows the 8pt scale (`p-2`, `p-4`, `p-6`, `p-8`). Radii use `rounded-xl` / `rounded-2xl`. Shadows use `shadow-sm` / `shadow-md`.

## Class ordering and composition

- Order: layout, box model, typography, visual, state, responsive. Prettier's Tailwind plugin enforces this — do not fight it.
- Merge conditionals with `cn()` (clsx + tailwind-merge), never string concatenation.
- Extract a component when the same class string appears three times. Do not extract into a CSS class.
- Component variants use `cva`, not conditional class soup.

## Responsive

Mobile-first. Write the base case for 360px, then layer `sm: md: lg: xl:`. Every screen is verified at 360 / 414 / 768 / 1024 / 1440 / 1920 with no horizontal scroll. Data tables become stacked cards below `md`.
