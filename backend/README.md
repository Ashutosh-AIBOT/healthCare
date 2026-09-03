# Aarogya backend

FastAPI application: auth, family, visibility, documents/jobs, AI ask skeleton.

## Layout

```text
backend/
├── app/
│   ├── api/v1/routers/   # thin HTTP
│   ├── services/         # business logic
│   ├── models/
│   ├── ai/
│   ├── tasks/            # Celery
│   └── migrations/
├── tests/
├── requirements.txt
├── alembic.ini
└── Dockerfile
```

## Run

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
pytest -q
```

Or via repo root: `make dev` / `make test` / `make seed`.
