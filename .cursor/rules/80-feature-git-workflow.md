---
description: One feature at a time — branch, commit, PR, merge to main
alwaysApply: true
---

# Feature delivery workflow (hard)

Every capability ships as **one feature slice**, never a dump of unrelated work.

## Sequence (do not skip)

1. **Pick one feature** from PLAN §20 (e.g. auth hardening, family visibility, documents). Name it clearly.
2. **Start from up-to-date `main`:** `git fetch origin && git checkout main && git pull`
3. **Create a branch:** `feat/<slice>`, `fix/<slice>`, `chore/<slice>`, or `docs/<slice>`
4. **Implement only that slice** — no drive-by refactors, no later milestones
5. **Commit** with Conventional Commits (`feat(api): …`, `feat(web): …`). Never `--no-verify`
6. **Push:** `git push -u origin HEAD`
7. **Open a PR** into `main` with What / Why / How / Test evidence (see CONTRIBUTING.md)
8. **Merge to `main`** after CI is green. Delete the branch after merge
9. **Only then** start the next feature from fresh `main`

## Scope reminders

- Frontend product UI lives in `frontend/` (Next.js). Backend stays under `apps/api/`
- Marketing UI: Soft Structuralism — brand-first hero, calm clinical tokens; no purple-on-white / cream-terracotta AI clichés
- Do not push directly to `main`
- Do not open a PR that mixes unrelated milestones
