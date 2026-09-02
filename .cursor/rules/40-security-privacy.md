---
description: Security, PHI handling, authorization and secrets rules
alwaysApply: true
---

# Security and privacy

This codebase holds other people's medical records. Treat every line that touches patient data as security-sensitive.

## Authorization on every path

- Authenticate, then authorize. A valid JWT proves who someone is, not what they may read.
- Every tenant query is scoped by `family_id` or `provider_id`, with RLS as the backstop, not the only defence.
- Cross-tenant access requires an active `consent_grant` covering that member and record type. An appointment, a chat thread or a past consult is not authorization.
- Every consent-gated read is written to `consent_access_log`. The patient can see who read what.
- Providers and admins require TOTP 2FA. Sensitive actions (export, delete, impersonate) require re-authentication.

## PHI handling

Never allow PHI into: application logs, traces, error responses, notification payloads, analytics events, LLM prompts without redaction, or third-party services.

```python
# BAD
logger.info(f"report ready for {member.full_name}, hb={value}")

# GOOD
logger.info("report_ready", extra={"report_id": str(report.id), "member_ref": member.id})
```

Push and email notifications say "A new report is ready" and link into the app. They never contain a name, test name or value.

## Secrets

Only via environment variables, documented in `.env.example` with no real value. Never in code, never in a commit, never in a log, never in a test fixture. gitleaks runs in CI. If a secret is ever committed, rotate it — removing the commit is not sufficient.

## Files

Private buckets only, server-side encryption at rest, short-lived presigned URLs. Validate magic bytes, size and page count; run the AV scan; dedupe by checksum. Never serve a user file from a public URL, and never trust a client-supplied content type.

## Input handling

- Bound parameters for SQL, always. Never f-string interpolation.
- Validate every input with Pydantic, including sizes and enum membership.
- Treat all model output as untrusted text: escape it, never render it as HTML, never execute it, never feed it into a shell or SQL.
- Text-to-SQL runs as a read-only role against allowlisted views only, with a forced tenant predicate, AST validation and a hard `LIMIT`.

## Test data

Synthetic only. Never copy production data into dev, tests, fixtures or seeds — not even "anonymized".
