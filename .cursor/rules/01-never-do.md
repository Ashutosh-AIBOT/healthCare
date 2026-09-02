---
description: Absolute prohibitions - things that must never be introduced into this codebase
alwaysApply: true
---

# Never do this

## Styling

- Never create a `.css`, `.scss`, `.sass`, `.less` or `.module.css` file. The only stylesheet in the repo is `apps/web/app/globals.css`, and it may contain **only** Tailwind directives and CSS custom properties defining design tokens.
- Never use `style={{ ... }}`, `<style>` tags, styled-components, emotion, or any CSS-in-JS.
- Never write a raw hex colour, `rgb()`, or arbitrary spacing value in a component. Use tokens: `bg-primary`, `text-muted-foreground`, `p-4`.
- Never use arbitrary Tailwind values (`w-[437px]`, `text-[13px]`) unless the value is genuinely impossible on the scale, and then add a comment explaining why.

## TypeScript / frontend

- Never `any`, `as unknown as`, `@ts-ignore`, or `!` non-null assertions used to silence the compiler. Fix the type.
- Never fetch data in `useEffect`. Use TanStack Query or a server component.
- Never hand-edit `packages/shared-types/` — it is generated from OpenAPI.
- Never hardcode a user-facing string. Use an i18n key.
- Never store a token in `localStorage`, `sessionStorage`, or a non-httpOnly cookie.

## Python / backend

- Never build SQL with f-strings or `%` interpolation. Use bound parameters or the ORM.
- Never `except:` or `except Exception: pass`. Catch specific exceptions, log with context, raise a domain error.
- Never put business logic or ORM queries in a router.
- Never call an LLM, OCR or embedding model in a request handler.
- Never disable RLS, or use a superuser connection, to make a query work.

## Data and safety

- Never log, trace, or place in an error message, notification payload or analytics event: names, phone numbers, emails, addresses, lab values, diagnoses, or any other PHI.
- Never let AI output a diagnosis, dosage, prognosis or treatment instruction. Never ship AI output without the guardrail check and the approved disclaimer.
- Never store money as a float. Integer paise only.
- Never use real patient data in dev, tests, fixtures or seeds. Synthetic only.
- Never post-filter retrieval results by tenant. Pre-filter, or another member's data has already reached the prompt.

## Git and process

- Never commit `.env`, secrets, keys, `node_modules`, `__pycache__`, build output or large binaries.
- Never `git push --force` to `main`. Never `--no-verify`. Never merge red CI.
- Never bundle unrelated changes into one PR, and never produce a single-commit dump.
- Never add a dependency for something the existing stack already does.
- Never claim a task is done without running lint, typecheck and tests.
- Never leave a dead "Coming Soon" button. Hide unfinished work behind a feature flag.
