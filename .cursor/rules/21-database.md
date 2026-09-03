---
description: Database naming, indexing, RLS, migrations and data-type rules
globs: backend/app/{models,db,migrations}/**/*.py
alwaysApply: false
---

# Database rules

## Naming

`snake_case` everywhere. Tables plural (`lab_reports`), foreign keys `<singular>_id`, booleans `is_`/`has_` prefixed, timestamps `_at` suffixed, enums singular (`appointment_status`). Never a reserved word as a column name (`user`, `order`, `end`). Never abbreviate ambiguously — `reference_range_low`, not `ref_lo`.

## Required columns

Every table: `id` (UUIDv7 primary key), `created_at`, `updated_at` (both `timestamptz`, UTC). Every tenant table: `family_id` or `provider_id`, indexed. Soft-deletable tables: `deleted_at`, and every query must filter it.

## Data types (get these right the first time)

- Money: `bigint` **paise**. Never `float`, never `numeric` for currency amounts.
- Timestamps: `timestamptz`, always stored UTC. Display conversion happens in the frontend using the member timezone.
- Lab values: store the raw value and unit as reported, **plus** the normalized value in the canonical unit. Store the reference range from that specific report — never a global range.
- IDs: UUIDv7. Never expose a sequential integer publicly. Public URLs use `slug + short hash`.
- Enums: Postgres enum types, mirrored into generated TS unions. Never duplicate an enum list by hand in two languages.

## RLS

Every tenant table has RLS enabled with a policy keyed on the tenant setting. Because PgBouncer runs in transaction mode, tenant context must be set with `SET LOCAL` inside the transaction:

```python
await session.execute(text("SET LOCAL app.family_id = :fid"), {"fid": str(actor.family_id)})
```

Never `set_config(..., false)` at session level — it leaks to the next client on the pooled connection. Never bypass RLS with a superuser role. Every tenant table needs a negative test proving another tenant gets no rows.

## Indexes

- Composite `(family_id, created_at DESC)` on anything listed chronologically.
- Partial indexes for hot subsets: `WHERE status IN ('queued','processing')`.
- GIN trigram for name and food search; GIN for jsonb columns that get queried.
- HNSW on `doc_chunks.embedding`, and always filter by `embedding_model` so a model change cannot mix vector spaces.
- Unique constraints to enforce invariants (idempotency keys, one booking per slot) — never rely on application checks alone for uniqueness.

## Migrations

One Alembic migration per PR, forward-only, reviewed for locks. Use **expand/contract**: add the column, backfill in a job, switch reads, drop the old column in a later release. `CREATE INDEX CONCURRENTLY` on large tables. Never couple a destructive change to a code change. Test every migration against seeded data before merge.
