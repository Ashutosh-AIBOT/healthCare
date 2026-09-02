# Aarogya

**A family health operating system and care marketplace — records you can actually understand, plus the right doctor, test and meal plan in one place.**

> Status: planning complete, scaffold in progress. Aarogya is not a medical device and does not provide medical diagnosis or treatment.

---

## What it does

Upload a lab report PDF. Within seconds it becomes structured, unit-normalized values with reference-range flags, a plain-language explanation with citations, and a trend chart stitched across reports from **different labs**. If a value is critical, it escalates. The Checkup Advisor then suggests screening tests to discuss with your doctor, maps them to verified labs serving your pincode with real prices, and books one in a click — and that booking produces the next report, which sharpens the next recommendation.

Four sides, one platform:

- **Families** — members, report vault, AI explanations, trends, checkup advisor, vitals and chronic care, nutrition and workouts, reminders, doctor and lab booking, teleconsult, chat
- **Doctors** — verified profile, availability, appointments, consent-gated patient records, consult notes, e-prescriptions with allergy and interaction checks
- **Labs** — catalog and city pricing, home collection, sample tracking, direct report upload into the patient's vault, amendments
- **Platform admin** — provider verification, catalog curation, AI guardrail compliance, AI quality dashboard, support and moderation

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui | SSR/ISR for SEO-critical public pages; one styling system; accessible primitives |
| Backend | FastAPI, SQLAlchemy 2 async, Pydantic v2 | Async throughout, strict validation, OpenAPI as the frontend contract |
| Database | Postgres 16 + pgvector, RLS | One source of truth for records and embeddings; tenant isolation in the database, not just the app |
| Cache / queue | Redis | Cache, rate limits, semantic cache, locks, Celery broker, pub/sub fan-out |
| Jobs | Celery + Beat | All OCR, embedding and LLM work off the request path |
| Storage | MinIO / S3 | Encrypted private buckets, presigned uploads |
| Graph | Neo4j (optional profile) | Health knowledge graph, projected from Postgres and rebuildable |
| Deploy | Docker Compose | Whole product from one command |

## GenAI techniques

Document OCR and structured extraction · hybrid RAG with citations · guardrails (no diagnosis, PII redaction, injection defence, emergency escalation) · LangGraph checkup-advisor agent · content generation · multi-modal vision food logging · voice STT/TTS · knowledge graph · safe text-to-SQL analytics · semantic caching · explained recommendations · urgency and sentiment detection · AI evaluation harness.

Where each one lives: [PLAN.md § 8](PLAN.md).

## Documentation

| Document | Purpose |
|---|---|
| [PLAN.md](PLAN.md) | Master plan — architecture, flows, milestones, three gap passes |
| [AGENTS.md](AGENTS.md) | Rules any developer or AI agent must follow before writing code |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branch, commit, PR, migration and release rules |
| [.cursor/rules/](.cursor/rules/) | Scoped enforcement rules (Tailwind-only, layering, RLS, AI safety, testing, SEO) |
| [docs/screens.md](docs/screens.md) | Every screen and the states it must implement |
| [docs/data-dictionary.md](docs/data-dictionary.md) | Naming, enums, IDs, money, units, environments |
| [docs/error-codes.md](docs/error-codes.md) | Stable API error codes |
| [docs/copy-guide.md](docs/copy-guide.md) | Tone, error copy, empty states, **verbatim medical disclaimers** |
| [docs/analytics-events.md](docs/analytics-events.md) | Event taxonomy, funnels, activation and retention metrics |

## Getting started

Not yet runnable — the Docker scaffold is the first work item of M0 ([PLAN.md § 26](PLAN.md)). Once it lands:

```bash
cp .env.example .env     # set LLM_API_KEY (the only required secret)
docker compose up -d     # whole product, under 5 minutes
make seed                # demo family, doctors, labs, foods, reports
```

Demo logins after seeding: `demo@aarogya.app`, `doctor@aarogya.app`, `lab@aarogya.app`, `admin@aarogya.app` (password `Demo@1234`).

## Principles

1. Never diagnose. Explain, cite, and point to a doctor.
2. Cross-tenant access requires explicit, revocable, audited consent.
3. No PHI in logs, notifications, analytics or unredacted prompts.
4. Anything slow runs in a worker and streams progress.
5. Every screen has loading, empty and error states, or it is not done.
6. Tailwind only. No CSS files, no inline styles.
7. Synthetic data only outside production.

## Development status

Milestones M0–M24 in [PLAN.md § 20](PLAN.md). The product satisfies its assignment requirements from M11 onward; later milestones take it from compliant to commercial.
