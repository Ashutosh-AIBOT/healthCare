# Frontend Gap Analysis

## Decisions

The pasted plans mix useful engineering checks with generic agency-site patterns.
Aarogya is an authenticated health product, so the interface should optimize for
calm scanning, trust, legibility, and recovery from errors.

Keep:

- semantic landmarks, keyboard navigation, visible focus, reduced motion;
- page-level metadata, canonical URLs, structured data, and noindex for the app;
- responsive layouts, skeletons, empty/error states, server-side validation;
- privacy-aware telemetry, security headers, and end-to-end tests.

Do not make these defaults:

- gradients, glow, grain, glassmorphism, oversized serif headlines, or animated blobs;
- bento grids and double-bezel cards on data-heavy app pages;
- artificial testimonials, invented health metrics, or hardcoded user records;
- smooth-scroll libraries or animation choreography that delays reading and interaction;
- a bottom navigation that duplicates the existing sidebar without a demonstrated mobile need.

## Current gaps

1. Public marketing pages have metadata and JSON-LD, but need verified production URLs,
   real OG/favicon assets, and a reviewed claims/content process.
2. The app has a shared visual token layer, but some legacy utilities still use names
   such as `primary-soft`, `healthy`, and `apricot`; these should be consolidated before
   adding more screens.
3. Global error boundaries, route-transition focus, and an app-wide toast/status system
   are not yet standardized.
4. Security headers and CSP need deployment-specific review because Telegram, LiveKit,
   API proxying, and any analytics domains must be allowlisted deliberately.
5. Core Web Vitals are not measured in production yet. Add RUM only after privacy and
   consent rules are approved; never send report content or health identifiers.
6. Visual regression and browser E2E coverage are not yet present for auth, report upload,
   Xomni streaming, Learn pagination, and mobile navigation.
7. Learn content now has source provenance and paginated test views, but food imports,
   editorial review, semantic embeddings, and source freshness jobs remain separate work.

## Delivery order

1. Consolidate legacy color utilities and add an accessible status/toast primitive.
2. Add error boundaries, focus-on-navigation, and E2E coverage for high-risk workflows.
3. Add production CSP/security headers after listing actual external integrations.
4. Add privacy-safe Web Vitals monitoring and bundle-budget CI.
5. Add reviewed food imports and vector retrieval; keep source/version/license metadata.

## Visual baseline shipped in this pass

- slate/navy neutrals with one restrained teal accent;
- sans-first typography for product UI;
- single-border cards with modest radius and shadow;
- short, transform-safe interaction transitions;
- no auth-page gradients or grain;
- skip link and stable `main` target;
- existing routes, APIs, authentication, and feature behavior unchanged.
