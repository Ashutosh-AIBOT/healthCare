---
description: AI safety, RAG correctness, guardrails, prompts and cost rules
globs: backend/app/ai/**/*.py
alwaysApply: false
---

# AI rules

This is a health product. AI output that a person acts on medically is the highest-risk surface in the codebase.

## Medical safety (absolute)

AI may explain what is on a report, cite guidelines, and suggest screening tests to discuss with a doctor. AI may **never** diagnose, name a likely disease, give a dosage, predict a prognosis, or instruct treatment.

- Every AI response passes the output guardrail before reaching a user. No exceptions, no "internal" bypass.
- Every AI response carries the approved disclaimer verbatim from `docs/copy-guide.md`.
- Red-flag input (chest pain, breathlessness, suicidal ideation, stroke signs) short-circuits to the emergency response with helpline numbers. It does not attempt triage.
- Every guardrail decision is written to `guardrail_events`, whether it passed or blocked.

## RAG correctness

```python
# BAD - retrieves across the whole family, then filters
hits = await vector_search(query, k=20)
hits = [h for h in hits if h.member_id == member_id]

# GOOD - pre-filter in the query; other members' data never enters the prompt
hits = await vector_search(query, k=20, where={"member_id": member_id,
                                                "embedding_model": ACTIVE_EMBEDDING_MODEL})
```

- Always pre-filter by tenant and member. Post-filtering means the leak already happened.
- Always scope retrieval to the active `embedding_model`; mixing model versions silently ruins relevance.
- Every claim in an answer must carry a citation to a report page or guideline chunk. An answer with no retrieved support returns "I could not find this in your reports", never a guess.
- Chunking is page-aware and table-aware, with member, report date, page and test names stored as metadata.

## Prompts

Prompts are versioned files in `ai/prompts/`, registered in `prompt_versions`. Every `ai_messages` row records the prompt version used, so any answer is reproducible and A/B tests are measurable. Never inline a prompt string at a call site. Never edit a released prompt in place — add a version.

## Gateway discipline

All model calls go through `ai/llm/gateway.py`. Never import a provider SDK anywhere else. The gateway owns timeouts, retry with jitter, the circuit breaker, the provider fallback chain, token and cost accounting, and the deterministic mock provider used in CI.

## Cost and quota

Record tokens, cost and latency on every call. Check the tenant quota and plan cost ceiling before calling. Try the semantic cache first. Cap prompt length so a long paste cannot burn the budget.

## Extraction

Structured extraction is schema-validated with per-field confidence. Low confidence routes to the manual confirm UI and the `extraction_reviews` queue. Never silently trust a parsed lab value — a wrong number here is a clinical risk, not a bug.

## Evaluation

Changes to prompts, retrieval or extraction require an eval run. Faithfulness, citation accuracy, refusal correctness and extraction field accuracy must not regress. The adversarial prompt-injection suite must stay at 100% blocked.
