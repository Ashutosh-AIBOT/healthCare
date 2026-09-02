---
description: SEO, GEO and structured data rules for public marketing and directory pages
globs: apps/web/app/(marketing)/**/*.{ts,tsx}
alwaysApply: false
---

# SEO and GEO rules

Public pages are the acquisition engine: landing, pricing, for-doctors, for-labs, blog, and the programmatic doctor, lab, test and city directories.

## Rendering

Public pages are SSR or ISR — never client-only, never `useEffect`-fetched. Prices and provider details must revalidate on demand when a provider, price or post changes, so a cached page never shows a stale price.

## Every indexable page needs

- A unique `title` and `meta description` from the page-type template. Never a duplicate across cities.
- Exactly one `h1`, headings in order, semantic HTML.
- `canonical`, `hreflang` for `en` and `hi`, and `BreadcrumbList`.
- The right JSON-LD: `Physician` and `MedicalClinic` for doctors, `MedicalTest` with `Offer` for tests, `Article` for posts, `FAQPage` where FAQs exist. Never emit `aggregateRating` without real reviews behind it.
- `next/image` with dimensions and meaningful `alt`; an OG image.

## Crawl budget protection

- Faceted, sorted and paginated URLs (`?specialization=&sort=fee&page=7`) are `noindex, nofollow` and canonical to the clean page. Without this, city times specialization times filter combinations explode into tens of thousands of thin URLs.
- Internal search result pages are never indexed.
- Pagination past page 5 is noindexed.

## Content quality gate

A programmatic page is only indexable if it passes the gate: real inventory (at least one verified provider or priced test), real prices, and minimum unique content. Anything failing the gate renders with `noindex` rather than shipping as thin content. Incomplete provider profiles are excluded from search and noindexed until completed.

## E-E-A-T for medical content

Medical content carries an author, a medical reviewer with credentials, and a visible last-reviewed date. Nothing medical publishes without reviewer sign-off in the editorial workflow.

## GEO / AEO (AI answer engines)

- Answer-first structure: a direct 40–60 word answer immediately under each question heading, detail below.
- Stable, citable fact blocks with source and date.
- Keep `/llms.txt` and `/llms-full.txt` current.
- Machine-readable price and test JSON endpoints for retrieval.
- Consistent entity naming across the site and external profiles.

## Performance

Public pages carry the strictest budgets: LCP under 2.0s on mobile. No client-side data fetching, no heavy JS, fonts subset and preloaded. A Lighthouse and SEO regression check runs in CI and fails the build on missing meta, canonical or JSON-LD.
