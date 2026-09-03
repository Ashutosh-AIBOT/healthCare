---
description: FastAPI structure, validation, errors, authorization and async rules
globs: backend/**/*.py
alwaysApply: false
---

# FastAPI conventions

## Routers stay thin

```python
# BAD - business logic, ORM access and no tenant scope in the router
@router.post("/lab-reports")
async def create(payload: dict, db=Depends(get_db)):
    if payload.get("member_id"):
        report = LabReport(**payload)
        db.add(report)
        ...

# GOOD
@router.post("/lab-reports", response_model=LabReportOut, status_code=202)
async def create_lab_report(
    payload: LabReportCreate,
    actor: Actor = Depends(current_actor),
    idempotency_key: str = Header(alias="Idempotency-Key"),
    svc: LabReportService = Depends(get_lab_report_service),
) -> LabReportOut:
    return await svc.create(actor, payload, idempotency_key)
```

A router may only: declare the schema, resolve dependencies, authorize via a dependency, call one service method, return. Business rules, transactions and queries belong in `services/`.

## Validation and typing

- Strict Pydantic v2 models for input and output. Never accept or return `dict`/`Any`.
- Never return ORM objects from an endpoint; map to a response schema.
- Full type hints; `mypy --strict` must pass.

## Errors

Raise domain exceptions from services; a single handler converts them to RFC 7807 `problem+json` with a stable `code` from `docs/error-codes.md`, a `request_id`, and a message safe to show a user.

```python
raise ConsentRequired(member_id=member_id)  # -> 403 {"code": "CONSENT_REQUIRED", ...}
```

Never leak a stack trace, SQL, provider error text or PHI in a response.

## Async

Everything is `async`. Never call a blocking library in an async handler — no `requests`, no sync SQLAlchemy, no `time.sleep`. Use `asyncpg` via SQLAlchemy 2 async, `httpx.AsyncClient`, and `asyncio.sleep`.

Anything over ~300ms is a Celery task. The handler creates a `jobs` row, enqueues, and returns `202` with a `job_id`.

## Idempotency and mutations

Every create endpoint requires an `Idempotency-Key`. The service checks `idempotency_keys` and replays the stored response for a duplicate key rather than creating a second row.

## Lists

One envelope for every list endpoint: cursor pagination (`?cursor=&limit=`), documented sort keys, filters as explicit query params. Never offset pagination on a large table. Include an `EXPLAIN ANALYZE` note in the PR for any new list query.
