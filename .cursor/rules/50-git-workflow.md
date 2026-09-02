---
description: Branch, commit and PR rules enforced for humans and agents
alwaysApply: true
---

# Git workflow

Full detail in [CONTRIBUTING.md](../../CONTRIBUTING.md). These are the rules that must never be broken.

## One slice, one branch, one PR

Branch from up-to-date `main`, named `feat/…`, `fix/…`, `chore/…`, `docs/…`, `refactor/…`, `test/…` or `perf/…`. Rebase on `main`; never merge `main` into your branch. Delete the branch after merge.

Never expand a branch's scope. Unrelated work found mid-task is noted in the PR, not fixed in place.

## Conventional Commits

```
feat(ai): add page-aware chunking with metadata pre-filter
fix(api): prevent double-booking under concurrent slot requests
chore(infra): add pgbouncer to compose with healthcheck
```

Types: `feat` `fix` `chore` `docs` `refactor` `test` `perf` `build` `ci` `revert`.
Scopes: `api` `web` `worker` `db` `ai` `auth` `infra` `seo` `docs` `seed`.

Never commit `update`, `fix bug`, `wip`, `changes`, or `asked by review`.

## Commit as you work

Commit incrementally, in logical steps, as the work progresses. Never a single dump at the end — this project is graded partly on evidence of incremental development, and a one-commit history is treated as a failure signal.

## Hard prohibitions

- Never `git push --force` to `main`. Use `--force-with-lease`, and only on your own unshared branch.
- Never `--no-verify`. If a hook fails, fix the cause.
- Never merge with red CI, and never bypass branch protection.
- Never commit `.env`, secrets, keys, `node_modules`, `__pycache__`, build artefacts, large binaries or real patient data.
- Never amend or rewrite a commit that has been pushed and shared.
- If a pre-commit hook modifies files, add them in a **new** commit.

## Before opening a PR

Run lint, typecheck and tests locally. Fill in the PR template completely, including screenshots (desktop and mobile, light and dark) for UI changes and the Definition of Done checklist. Keep the diff under roughly 400 lines; split larger work into stacked PRs.

## Migrations and ADRs

One migration per PR, forward-only, expand/contract, reviewed for locks. If the PR embodies a real technical decision, add a numbered ADR in `docs/adr/` and link it.
