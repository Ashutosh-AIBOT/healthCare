# ADR 0001 — Record architecture decisions

- **Status**: Accepted
- **Date**: 2026-09-02

## Context

Aarogya spans 24 milestones and will be built partly by AI agents across many sessions. Decisions made in one milestone (why Postgres holds vectors, why RLS uses `SET LOCAL`, why money is integer paise) are invisible to whoever works next, and get silently reversed. The assignment also grades whether tech choices are justified rather than accidental.

## Decision

Every significant technical decision is recorded as a numbered ADR in `docs/adr/`, linked from the PR that implements it.

A decision is significant if it: adds or replaces a dependency or service, changes a data or auth model, changes a public contract, trades off correctness against performance or cost, or would surprise a competent developer reading the code later.

Format: Context (the forces), Decision (what we chose), Consequences (what this costs us and what it rules out), Alternatives considered (and why rejected).

Rules:

- Numbered sequentially, `NNNN-kebab-title.md`.
- Never edited after acceptance. To change a decision, write a new ADR and mark the old one `Superseded by ADR NNNN`.
- Statuses: `Proposed`, `Accepted`, `Superseded`, `Deprecated`.
- Short. One page. If it needs more, the decision is probably two decisions.

## Consequences

Positive: new contributors and agents can reconstruct reasoning without archaeology; the README tech-stack justification writes itself; reversals become deliberate.

Negative: a small tax on every meaningful PR. Accepted, because the alternative — re-litigating settled choices mid-build — is far more expensive.

## ADRs expected early

- 0002 — Monorepo over polyrepo
- 0003 — Postgres + pgvector over a separate vector database
- 0004 — Row-level security with `SET LOCAL` under PgBouncer transaction pooling
- 0005 — Celery over FastAPI BackgroundTasks
- 0006 — httpOnly cookies with a Next route-handler proxy instead of client-held tokens
- 0007 — Postgres as source of truth with Neo4j as a rebuildable projection
- 0008 — Provider-agnostic LLM gateway with a fallback chain and a mock provider
- 0009 — Money as integer paise
- 0010 — Single region plus CDN
