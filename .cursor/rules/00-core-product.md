---
description: Core product context and layering rules for the Aarogya health SaaS
alwaysApply: true
---

# Aarogya — core context

Multi-tenant AI health SaaS marketplace. Four sides: family (patients), doctor, lab, platform admin. Handles real medical data (PHI). Read [PLAN.md](../../PLAN.md) for scope and [AGENTS.md](../../AGENTS.md) for the hard rules.

## Stack (no substitutions without an ADR)

FastAPI + SQLAlchemy 2 async + Pydantic v2 + Alembic + Celery. Postgres 16 + pgvector, Redis, MinIO/S3, optional Neo4j. Next.js 15 App Router + TypeScript strict + Tailwind + shadcn/ui + TanStack Query + zod. Docker Compose from day one.

## Layering (strict, one direction)

```
router  ->  service  ->  repository/model
   |           |
 schema      ai/ , integrations/ , tasks/
```

- **Router**: parse input, authorize, delegate to a service, return a schema. No domain `if`s, no ORM queries, no LLM calls.
- **Service**: all business logic, transactions, authorization decisions, event emission.
- **Task**: anything slow. Services enqueue; tasks never import routers.
- Never import a router from a service, or a service from a model.

## Tenancy

Every tenant row carries `family_id` or `provider_id`. RLS is enabled; tenant context is set with `SET LOCAL` inside the transaction (PgBouncer runs in transaction mode, so session-level `set_config` leaks across pooled clients).

Cross-tenant access requires an active `consent_grant`. An appointment is not authorization.

```python
# BAD - trusts the caller's claim, no tenant scope
report = await db.get(LabReport, report_id)

# GOOD - tenant scoped, consent checked in the service
report = await report_service.get_for_actor(db, actor, report_id)
```

## Async boundary

No LLM, OCR or embedding call inside an HTTP request path. Enqueue, return `202` with a `job_id`, stream progress over SSE.

## Scope discipline

Work only inside the current milestone from [PLAN.md](../../PLAN.md) section 20. If you discover unrelated work, note it in the PR instead of expanding the branch.
