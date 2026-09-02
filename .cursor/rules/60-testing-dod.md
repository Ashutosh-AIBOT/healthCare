---
description: Testing requirements and the Definition of Done that blocks merge
alwaysApply: true
---

# Testing and Definition of Done

## Definition of Done (all items, every feature)

A feature is not done until every box is true. This is a merge blocker, not a suggestion.

- [ ] API with strict validation and typed errors from `docs/error-codes.md`
- [ ] Tenant scoping and consent enforced, with a **negative test** proving another tenant or an unconsented provider gets `403`
- [ ] Loading, empty and error states implemented in the UI
- [ ] Responsive at 360 / 414 / 768 / 1024 / 1440 / 1920 with no horizontal scroll
- [ ] Keyboard reachable, focus visible, inputs labelled, contrast checked
- [ ] Telemetry event and audit log entry emitted
- [ ] Tests written and passing; lint, format and typecheck clean
- [ ] Seed data updated so the feature is demoable from a clean boot
- [ ] Behind a feature flag if incomplete
- [ ] Migration reviewed for locks; ADR written if a real decision was made

## What to test

**Always required**

- Service-level unit tests for business rules, especially state machines, pricing, unit conversion and guardrails.
- A tenant isolation test for every new tenant table or endpoint.
- An idempotency replay test for every new create endpoint.
- Concurrency tests where two actors can race (slot booking, invite acceptance, job claiming).

**Frontend**

- Component tests for state logic, not for markup shape.
- An E2E test for any new user-visible journey, running on the deterministic seed.
- `axe-core` assertions on new screens.

**AI**

- Guardrail tests: every blocked category has a case proving it is blocked.
- Eval run on any prompt, retrieval or extraction change; faithfulness, citation accuracy, refusal correctness and extraction accuracy must not regress.
- Adversarial prompt-injection suite stays at 100% blocked.

## How to test

- Mock the LLM with the deterministic provider — CI never needs an API key and never makes a paid call.
- Use testcontainers for Postgres and Redis. Never mock the database; RLS behaviour only shows up against real Postgres.
- Synthetic data only. Factories over fixtures. Never real patient data.
- Assert on behaviour and outcomes, not implementation details.
- Test the failure paths: LLM timeout, corrupt PDF, oversize upload, revoked consent, expired slot, network drop. These are what the rubric and real users both hit.

## Never

- Never mark work complete without running the tests.
- Never re-run CI hoping for green. Fix or quarantine the flake in the same PR.
- Never delete or skip a failing test to unblock a merge.
