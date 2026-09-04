# Aarogya Design System — MASTER

> Generated via blueprint §2–§4 + 12-skill synthesis (taste v2, frontend-design, web-design-guidelines, etc.)
> Dials: VARIANCE 5 / MOTION 4 / DENSITY 3 — Calm Clear Credible (hospital chart + family album + productivity tool)

## Tokens (frontend/app/globals.css only — AGENTS #1)

- Colors oklch: paper 0.985 0.006 95, ink 0.22 0.02 200, primary teal 0.48 0.09 190, primary-soft 0.93 0.03 190, apricot 0.72 0.14 55, muted 0.52 0.02 200, line 0.9 0.02 200, health excellent 0.62 0.13 165 / good 0.72 0.12 130 / watch 0.78 0.13 80 / critical 0.62 0.16 35, doctor indigo 0.50 0.11 250, agency plum 0.55 0.10 300. Dark: paper 0.19 0.015 210, surface 0.235 0.018 210, primary lift 0.72 0.10 190.
- Radii 14/999/10/20, shadows ambient/lift + hairline, grain 2% via datauri.
- Typography: display Bricolage Grotesque 500/600/700, sans Public Sans, mono IBM Plex Mono tabular-nums, scale 1.25 12→49px, 18px 1.7 68ch knowledge.
- Motion 120 hover/press 1px, 200 dropdown, 320 sheet/modal 8px rise+fade, 700 MetricRing cubic 0.32 0.72 0 1 once; prefers-reduced-motion → opacity only.

## Component Library (20 components, 5 states each)

MetricRing, ScoreCard, PillarBar, FamilyGraph, PermissionMatrix, ConsentDialog, SensitiveField, AccessLogTimeline, VerifiedBadge, AIMessage, PlanCard, LogSheet, FoodItem/ExerciseCard, DoctorCard/PackageCard, BookingStepper, UploadDropzone, EmptyState, Skeleton, Toast, CommandPalette — all shadcn+Radix+CVA, 44px targets, focus 2+2px, keyboard paths.

## Shell & Layout

240→64 rail role-tinted, top bar breadcrumb+⌘K+avatar-stack pill, FAB centre mobile, max 1200 32 gutters, sections 32px.

## Responsive / A11y / Perf

390/768/1024/1440, color alone never status (icon+label), axe WCAG 2.2 AA 4.5:1, LCP <2 CLS 0.05 INP 200, AVIF/WebP, dynamic import thresholds.

## SEO

JSON-LD Organization/WebSite/Physician/MedicalTest/FAQPage, llms.txt, sitemap by type, quality gate, hreflang en/hi.

See per-page overrides: pages/landing.md, dashboard.md, family.md, knowledge.md (to be added).
