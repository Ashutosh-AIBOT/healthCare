# Xomni RAG and Personal Context Plan

## Audit Findings

| Area | Current behavior | Required change |
| --- | --- | --- |
| Learn retrieval | `_get_learn_context` scans up to 50 `LearnItem` rows with token overlap only. `BodyTest` rows are ignored. | Retrieve food and test knowledge together, rank by lexical relevance, and return source citations. |
| Report retrieval | `/ai/ask` can retrieve report chunks only when a `member_id` is supplied. Xomni chat never retrieves report chunks or lab values. | Scope report context to the signed-in user's linked member and inject values/chunks into chat. Keep explicit document scoping for report Q&A. |
| Embeddings | Learn and document embeddings are JSON placeholders; no retrieval path uses them. | Keep a deterministic lexical fallback, add a provider-neutral embedding field/interface, and use vector ranking when a real embedding is available. |
| Personal context | `users.ai_context` is one free-text field and is not structured or consent-gated. | Add a separate per-user context table with habits, likes, dislikes, goals, restrictions, and provenance. |
| Chat collection | Xomni can propose timetable/meal changes, but has no personal-context proposal action. | Ask before storing inferred preferences; accept/reject through the existing action flow. |
| Prompt routing | Reports and fitness currently use the general prompt in `chat()`, and only some modes persist actions. | Route every mode through the mode prompt and persist only supported, confirmation-gated actions. |
| Report ingestion | `document_tasks.py` writes hard-coded Hemoglobin/Glucose values and two fixed chunks. | Keep the processor boundary, but replace the stub with extracted document text/value output before production use. |
| Observability | Chat citations are always empty. | Return source metadata with every retrieved context and log retrieval counts without logging PHI. |

## Delivery Plan

1. **Context foundation**: add the personal-context table, migration, scoped API, and confirmation-gated Xomni proposal action.
2. **Chat retrieval**: add hybrid retrieval over Learn food/test content, the user's own report values/chunks, and confirmed personal context. Add citations to chat responses.
3. **Report fidelity**: replace the document worker stub with real extracted text and structured values, preserve page/confidence metadata, and re-index chunks on reprocessing.
4. **Evaluation**: add fixture-based retrieval tests for food questions, test-preparation questions, report-value questions, cross-user isolation, and personal-preference injection. Add end-to-end tests once PostgreSQL is reachable.
5. **Production hardening**: use pgvector or a configured embedding provider for semantic ranking, encrypt sensitive context at rest, add retention/export/delete controls, and monitor citation coverage and retrieval misses.

## Safety Invariants

- Report context is never retrieved across families or across users' linked members without an existing consent path.
- Personal context is stored only after explicit confirmation.
- Retrieved context is evidence, not a diagnosis or prescription; medical guardrails remain active.
- Every answer that uses report or Learn data carries source labels in the response.
- Secrets and environment files remain outside Git.
