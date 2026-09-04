# AGENTS.md — Read this before writing any code

You are working on **Aarogya**, a multi-tenant AI health SaaS marketplace handling real medical data (PHI). Mistakes here are not cosmetic: they leak another family's medical records, give someone a diagnosis we are not licensed to give, or silently corrupt a lab trend chart a person makes decisions from.

**Read first:** [PLAN.md](PLAN.md) and [CONTRIBUTING.md](CONTRIBUTING.md). Cursor rule files live locally under `.cursor/rules/` and are not published to GitHub. Legacy local folders `.agents/`, `.21st/`, `.claude/`, `.codex/` are gitignored and deprecated — do not read or write them; consolidate guidance here.

---

## The 12 hard rules

1. **Tailwind utilities only.** No `.css`/`.scss` files, no `style={{}}`, no CSS-in-JS, no `<style>` tags. The single exception is `frontend/app/globals.css`, which may contain only Tailwind directives and CSS custom properties that define design tokens.
2. **Business logic lives in `services/`.** Routers parse, authorize, delegate, and return. If a router has an `if` about domain behaviour, it is in the wrong place.
3. **No LLM, OCR or embedding call in an HTTP request path.** Enqueue a job, return `202` with a `job_id`, stream progress over SSE.
4. **Every tenant query is scoped.** RLS is on, and tenant context is set with `SET LOCAL` inside the transaction. Never disable RLS to "make a query work".
5. **Cross-tenant reads require a consent grant.** An appointment alone is not authorization. No grant means `403`.
6. **Never let AI diagnose.** No diagnosis, dosage, prognosis or treatment instruction. Output passes the guardrail and carries the approved disclaimer verbatim from [docs/copy-guide.md](docs/copy-guide.md).
7. **No PHI in logs, traces, error messages, notification payloads or analytics events.** Redact before it leaves the process.
8. **Money is integer paise.** Never a float. Format only at the display layer.
9. **Types are generated, not hand-written.** Frontend types and zod schemas come from OpenAPI. Never hand-edit `packages/shared-types/`.
10. **Every async surface needs loading, empty and error states** before the PR is opened. A screen that can be blank must have an empty state with a CTA.
11. **One feature per branch, one PR, conventional commits.** See [CONTRIBUTING.md](CONTRIBUTING.md).
12. **Never commit secrets, and never use real patient data.** Fixtures and seeds are synthetic only.

---

## Never do this

The ones that get caught in review most often:

- Writing a `.css` file or an inline `style` prop
- `any` in TypeScript, or a bare `except:` in Python
- Building SQL by string interpolation or f-string
- `useEffect` for data fetching instead of TanStack Query
- Hardcoded user-facing strings instead of i18n keys
- A hex colour or arbitrary pixel value instead of a design token
- `console.log` / `print` left in code instead of the structured logger
- Adding a dependency to solve something the existing stack already does
- `git push --force` to `main`, or `--no-verify` to skip hooks
- Marking work complete without running lint, typecheck and tests

---

## Before you start a task

1. Find the milestone in [PLAN.md § 20](PLAN.md). Work inside its scope; do not drift into a later milestone.
2. Check [docs/screens.md](docs/screens.md) for the UI spec if the task touches the frontend.
3. Check [docs/data-dictionary.md](docs/data-dictionary.md) for naming, enums, IDs, units before adding a column.
4. Check [docs/error-codes.md](docs/error-codes.md) before inventing an error.
5. Create the branch: `feat/<slice>`, `fix/<slice>`, `chore/<slice>` or `docs/<slice>`.

## Before you say you are done

Definition of Done (all of it, every time — [PLAN.md § 16](PLAN.md)):

- [ ] API with validation and typed errors
- [ ] RLS and consent enforced, with a **negative test** proving another tenant gets `403`
- [ ] Loading, empty and error states implemented
- [ ] Responsive at 360 / 414 / 768 / 1024 / 1440 / 1920, no horizontal scroll
- [ ] Keyboard reachable, focus visible, inputs labelled
- [ ] Telemetry and audit events emitted
- [ ] Tests written and passing; lint and typecheck clean
- [ ] Seed data updated so the feature is demoable
- [ ] Behind a feature flag if incomplete
- [ ] Migration reviewed for locks; ADR written if a real decision was made

---

## Repository map

| Path | Contains |
|---|---|
| `frontend/` | Next.js 15 App Router, Tailwind |
| `backend/app/api/v1/routers/` | Thin HTTP layer only |
| `backend/app/services/` | All business logic |
| `backend/app/ai/` | LLM gateway, RAG, extraction, guardrails, agents, prompts, eval |
| `backend/app/tasks/` | Celery tasks (all heavy work; run via compose `worker`/`beat`) |
| `infra/seed/` | Synthetic seed data |
| `docs/` | Screens, data dictionary, error codes, events, copy, ADRs, runbook |

## Stack (do not substitute without an ADR)

Backend FastAPI + SQLAlchemy 2 async + Pydantic v2 + Alembic + Celery. Data Postgres 16 + pgvector + Redis + MinIO/S3, optional Neo4j. Frontend Next.js 15 + TypeScript strict + Tailwind + shadcn/ui + TanStack Query + react-hook-form + zod + next-intl. Everything runs in Docker Compose from day one.

## When you are unsure

Ask rather than guess if the question touches: medical safety wording, consent and access control, money, data deletion, or anything a patient could act on medically. For everything else, follow the closest existing pattern in the codebase and note the decision in the PR.
