---
description: Required UI states, accessibility and performance budgets for every screen
globs: frontend/**/*.tsx
alwaysApply: false
---

# UI states, accessibility, performance

## Every screen ships four states

No component that loads data is complete until all four exist. This is a merge blocker.

1. **Loading** — a skeleton shaped like the real content. Never a full-page spinner. Never a layout shift when data arrives.
2. **Empty** — an explanation plus a primary CTA. "No reports yet. Upload your first lab report to see explained results and trends." Never a blank area.
3. **Error** — a human sentence and a retry button, mapped from the error code via i18n. Never a raw exception, status code or JSON dump.
4. **Populated** — the real thing.

Partial and permission states also matter: a report still processing shows its stage; a record the actor lacks consent for shows a request-access state, not a 403 screen.

```tsx
if (isPending) return <ReportListSkeleton />;
if (error) return <ErrorState code={error.code} onRetry={refetch} />;
if (!data.length) return <EmptyState title={t("reports.empty.title")} action={<UploadButton />} />;
```

## Accessibility (WCAG 2.1 AA, non-negotiable)

- Every flow completable by keyboard alone; visible focus rings (never `outline-none` without a replacement).
- Every input has a real `<label>`; placeholders are not labels. Errors linked via `aria-describedby`.
- Semantic elements: `<button>` for actions, `<a>` for navigation, one `<h1>` per page, headings in order.
- Icon-only buttons carry `aria-label`. Decorative icons get `aria-hidden`.
- Streaming AI output lives in `aria-live="polite"`; critical alerts use `role="alert"`.
- Contrast checked against tokens; never rely on colour alone to convey a lab flag — pair it with text or an icon.
- Respect `prefers-reduced-motion`; animation is decoration, never the only feedback.
- Modals trap focus and restore it on close.

## Performance budgets (enforced in CI)

LCP under 2.0s, INP under 200ms, CLS under 0.05, route JS under 180KB gzipped.

- `next/image` with explicit dimensions for everything; never a bare `<img>`.
- `next/font` with subsetting; Devanagari loads only for the Hindi locale.
- Dynamically import charts, voice recorder, video room, PDF viewer.
- Virtualize lists beyond 100 rows.
- Memoize only after measuring; premature `useMemo` is noise.

## Copy

All user-facing text comes from i18n keys, never inline strings. Tone and the approved medical disclaimer strings are in `docs/copy-guide.md` — disclaimers are used verbatim, never paraphrased.
