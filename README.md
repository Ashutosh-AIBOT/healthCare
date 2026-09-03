# Aarogya

**Family health OS and care marketplace** — lab reports you can understand, plus the next right checkup, doctor, and lab booking.  
Not a medical device. Does not diagnose or prescribe.

> Single repo: **`backend/`** (FastAPI) + **`frontend/`** (Next.js).

---

## Repo layout

```text
.
├── backend/          # FastAPI API, Celery tasks, Alembic migrations, tests
├── frontend/         # Next.js 15 App Router (marketing + auth + app shells)
├── infra/seed/       # Synthetic demo seed (no real PHI)
├── docs/             # Screens, data dictionary, copy, auth audit
├── docker-compose.yml
├── Makefile
├── PLAN.md           # Master product plan + milestones
├── AGENTS.md         # Hard rules for humans and agents
└── CONTRIBUTING.md   # Branch / commit / PR workflow
```

Cursor/agent folders (`.cursor/`, `.agents/`, `.21st/`, `.claude/`, `.codex/`) stay on your machine only. They are gitignored and never appear on GitHub. The only hidden paths on GitHub are `.gitignore`, `.env.example`, and `.github/workflows/` (CI).

---

## Quick start

```bash
cp .env.example .env
make reset          # compose up --build, wait for health, seed demos
```

| Surface | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| API health | http://localhost:8000/health |
| Mailhog | http://localhost:8025 (if ports exposed) |

### Demo logins (after seed)

Password for all: `Demo@1234`

- `demo@aarogya.app` — family
- `doctor@aarogya.app` — doctor
- `lab@aarogya.app` — lab
- `admin@aarogya.app` — admin

### Local without Docker (API + FE)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (other terminal)
cd frontend
cp .env.example .env.local   # API_INTERNAL_URL=http://localhost:8000
npm install
npm run dev
```

```bash
make test                 # backend pytest
cd frontend && npm run build
```

---

## Stack

| Layer | Path | Tech |
|-------|------|------|
| Frontend | `frontend/` | Next.js 15, TypeScript, Tailwind, RHF + Zod |
| Backend | `backend/` | FastAPI, SQLAlchemy 2 async, Alembic, Celery |
| Data | Compose | Postgres 16 + pgvector, Redis, MinIO |

---

## Delivery workflow

One feature per branch → implement **backend + matching frontend** → test → commit → PR → merge `main`.  
See [CONTRIBUTING.md](CONTRIBUTING.md).

Milestones: [PLAN.md § 20](PLAN.md). Next product slice after current skeleton: **M7 providers**.

---

## Principles

1. Never diagnose — explain, cite, point to a clinician.
2. Triage before every model call.
3. Access is granted, not inherited (field-level family visibility).
4. No PHI in logs or notifications.
5. Heavy work runs in workers, not request paths.
