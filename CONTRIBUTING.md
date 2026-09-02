# Contributing — branch, commit, PR and release rules

Applies to humans and agents equally. See [AGENTS.md](AGENTS.md) for coding rules and [PLAN.md](PLAN.md) for scope.

---

## Branching

Trunk-based. `main` is always deployable and protected: no direct pushes, PR plus green CI plus one review required.

One branch per feature slice, short-lived (merge within days, not weeks):

```
feat/<slice>     new capability          feat/lab-report-extraction
fix/<slice>      bug fix                 fix/slot-double-booking
chore/<slice>    tooling, deps, infra    chore/bootstrap
docs/<slice>     documentation only      docs/submission
refactor/<slice> no behaviour change     refactor/extract-consent-service
test/<slice>     tests only              test/rls-isolation
perf/<slice>     performance work        perf/report-list-indexes
```

Rules:

- Branch from up-to-date `main`. Rebase on `main`; do not merge `main` into your branch.
- One milestone slice per branch. If you find unrelated work, open a separate branch.
- Delete the branch after merge.

## Commits

[Conventional Commits](https://www.conventionalcommits.org), enforced by commitlint.

```
<type>(<scope>): <imperative summary under 72 chars>

<why the change was needed, wrapped at 100 chars>

Refs: M5
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `style`, `revert`.
Scopes: `api`, `web`, `worker`, `db`, `ai`, `auth`, `infra`, `seo`, `docs`, `seed`.

Good:

```
feat(ai): add page-aware chunking with metadata pre-filter
fix(api): prevent double-booking under concurrent slot requests
refactor(api): move consent checks out of appointment router
```

Bad: `update`, `fix bug`, `wip`, `changes`, `asked by review`.

Rules:

- Commit incrementally as work progresses. Never one giant dump at the end.
- Each commit should build and pass tests on its own where practical.
- Never `--no-verify`. If a hook fails, fix the cause.
- Never commit secrets, `.env`, credentials, real patient data, `node_modules`, `__pycache__`, build output or large binaries.
- If a pre-commit hook modifies files, include them in a **new** commit rather than amending a pushed one.

## Pull requests

Title follows the same Conventional Commit format. Body must include:

```markdown
## What
One paragraph describing the change.

## Why
The problem this solves. Link the milestone (e.g. M9) from PLAN.md.

## How
Key decisions. Link an ADR if one was written.

## Screenshots
Desktop and mobile, light and dark, for any UI change.

## Test evidence
Commands run and their result. New tests listed.
For list endpoints: EXPLAIN ANALYZE output.

## Definition of Done
- [ ] Validation and typed errors
- [ ] RLS/consent enforced with a negative test
- [ ] Loading, empty, error states
- [ ] Responsive 360 -> 1920, no horizontal scroll
- [ ] Keyboard reachable, focus visible, labels present
- [ ] Telemetry and audit events
- [ ] Tests pass, lint and typecheck clean
- [ ] Seed data updated
- [ ] Feature flag if incomplete
- [ ] Migration reviewed for locks

## Rollback
How to undo this safely.
```

Rules:

- Keep PRs reviewable: under ~400 changed lines where possible. Split large work into stacked PRs.
- Squash merge. The squashed title becomes the changelog entry.
- Never merge red CI. Never bypass branch protection.
- Never force push to `main`. Force push only to your own unshared branch, and only with `--force-with-lease`.

## Migrations

- Alembic, one migration per PR, forward-only.
- **Expand/contract**: add the new column, backfill as a job, switch reads, drop the old column in a *later* release. Never couple a destructive change to a code change.
- Review for table locks on large tables; prefer `CREATE INDEX CONCURRENTLY`.
- Every migration must be tested against seeded data before merge.

## CI

Fast checks on every PR (Turborepo affected-targeting): lint, typecheck, unit, integration, Docker build, Playwright E2E on Compose, SEO and Lighthouse budgets.

Nightly heavy jobs: AI eval suite, k6 load tests, full visual regression, dependency and secret audits.

If CI is flaky, fix or quarantine the test in the same PR — never re-run until green.

## Releases

- Semver tags on `main`. `CHANGELOG.md` generated from commit history.
- A release requires: green nightly, k6 thresholds met, restore drill still valid.
- ADRs in `docs/adr/` for every significant decision, numbered sequentially, never edited after acceptance (supersede instead).

## Commit history expectations

This project is also an assignment submission that explicitly grades incremental development. The history must read as real work over time: many small descriptive commits, one PR per feature slice, no single-commit dumps.
