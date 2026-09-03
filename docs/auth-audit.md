# Auth audit — existing vs PLAN

**Date:** 2026-09-03  
**Scope:** `apps/api` auth/OTP/sessions/RLS + web auth surfaces  
**Verdict:** Scaffold only. Safe enough for local family CRUD demos; **not** launch-ready identity.

Compared against [PLAN.md](../PLAN.md) §§ 7.1 / 13, [AGENTS.md](../AGENTS.md) hard rules, and [docs/screens.md](screens.md) auth routes.

---

## Scorecard (14 PLAN checks)

| # | Requirement | Status | Notes |
|---|---|---|---|
| 1 | Register: handle, strength, versioned consents | **Missing** | Email+password+name only; no handle; no `consents` |
| 2 | OTP verify gates the account | **Partial** | Send/verify exist; verify never sets `is_verified`; register auto-verifies in dev and issues tokens immediately |
| 3 | Access 15m + rotating refresh + httpOnly + Next proxy | **Partial** | Crypto/TTL/rotation yes; tokens returned in **JSON body** |
| 4 | Forgot-password identical body + timing | **Missing** | No endpoints |
| 5 | OTP: 5 fails kill code; 3 sends/hour | **Missing** | Unlimited send/verify |
| 6 | Login lockout + exponential backoff | **Missing** | |
| 7 | Handle + role immutable after verification | **Missing** | No handle; no immutability guards |
| 8 | Argon2id passwords | **Exists** | via passlib `argon2` |
| 9 | TOTP mandatory for doctor/lab/admin | **Missing** | |
| 10 | Backup codes, recovery, session list, logout-all, re-auth | **Missing** | `device_label` column only |
| 11 | RLS on every tenant table + SET LOCAL | **Partial** | SET LOCAL yes; RLS only on `users` + `sessions` |
| 12 | Auth rate limits (Redis) | **Missing** | Redis in compose, unused for auth |
| 13 | Invite TTL from `system_settings` + hourly sweep | **Partial** | Per-invite expiry (default 72h); no settings, no sweep |
| 14 | Versioned `consents` ≠ `consent_grants` | **Missing** | |

---

## What exists today

| Piece | Path |
|---|---|
| Register / login / refresh / me | `apps/api/app/api/v1/routers/auth.py`, `services/auth_service.py` |
| Argon2 hashing, JWT access 15m, refresh rotation | `core/security.py`, `core/config.py` |
| Sessions table (hash, revoke, device_label) | `models/user.py`, migration `001` |
| OTP send/verify (hashed, 10m TTL, dev code) | `services/otp_service.py`, `routers/otp.py` |
| Family shell created on register | `auth_service.register` |
| Bearer auth dependency | `core/deps.py` |
| `SET LOCAL app.family_id` | `db/session.py` |
| RLS on `users` + `sessions` | migration `005_rls_policies.py` |
| Invites with `expires_at` | `services/invite_service.py` |
| Happy-path tests | `tests/test_auth_integration.py`, `test_auth_unit.py` |

---

## Critical gaps in existing code (must change)

### 1. Tokens in JSON — high risk
`AuthResponse` / `TokenResponse` return `access_token` + `refresh_token` in the body. PLAN hard decision: refresh in **httpOnly Secure cookie**, all browser traffic through **Next route handlers**, no token in client JS.

**Change:** API sets cookie (or BFF sets it); web never stores tokens in memory/localStorage; add `apps/web/app/api/auth/*` proxy + `middleware.ts` role gates.

### 2. Verification is a no-op — high risk
```47:48:apps/api/app/services/auth_service.py
            is_verified=settings.otp_dev_mode,
```
Register issues tokens immediately. OTP `verify` only sets `consumed_at` — never flips `User.is_verified`. Login never checks verification.

**Change:** register → pending; OTP verify → `is_verified=true` + `email_verified_at`; login/token issue refused until verified (seed/dev exception documented).

### 3. OTP has no attempt / issue caps — high risk
`otp_service.verify` does not increment attempts. Failed guess → same code stays live. Unlimited `send`.

**Change:** `attempt_count` on `otp_codes` (kill after 5); Redis counter 3 sends / email / hour.

### 4. Refresh reuse only kills one session — high risk
On hash mismatch, only that session row is revoked. Docs/`AUTH_REFRESH_REUSED` imply logout-everywhere.

**Change:** revoke all sessions for `user_id` on reuse detection.

### 5. No login lockout / rate limits — high risk
Credential stuffing and OTP brute-force are open.

**Change:** Redis token bucket (auth 5/min, OTP 3/hour); failed-login counter with exponential backoff → `AUTH_ACCOUNT_LOCKED`.

### 6. Registration missing PLAN fields
No `handle` (immutable unique), no password strength beyond `min_length=8`, no versioned ToS/privacy/disclaimer capture.

**Change:** add `users.handle`; reject weak passwords; `consent_documents` + `consents` rows at register; role/handle UPDATE blocked after verification starts.

### 7. RLS incomplete
Only `users` and `sessions` have RLS. `families`, `family_members`, `invites`, OTP tables unprotected at DB layer. Auth email lookups run with empty tenant context — fragile under FORCE RLS unless the API role bypasses.

**Change:** RLS on every tenant table; auth bootstrap via bypass/service role or explicit policies; keep `SET LOCAL` for app queries.

### 8. Provider 2FA / recovery / session UX — missing
No TOTP, backup codes, recovery, session list, logout, logout-all, re-auth.

**Change:** required before doctor/lab/admin go live (M1 exit criterion in PLAN).

### 9. Web auth routes — missing
Landing links to `/login` and `/register`; those pages do not exist.

**Change:** build screens from `docs/screens.md` Auth section once cookie/BFF transport is decided.

### 10. Invite TTL not settings-driven
Default 72h in schema, not 14d from `system_settings`; no hourly expiry sweep.

**Change:** `system_settings.invitation_ttl_days`; Celery beat job.

---

## Prioritized change list

### P0 — do before trusting auth with real data
1. Cookie + Next BFF token transport (stop JSON refresh)
2. Wire OTP → `is_verified`; gate login/tokens
3. OTP attempt + issue caps
4. Login rate limit + lockout
5. Refresh reuse → revoke all sessions
6. Handle + versioned consents at register
7. Make RLS compatible with auth + cover tenant tables

### P1 — before public / assignment demo with providers
8. Forgot / reset password (constant body + timing)
9. TOTP mandatory for doctor/lab/admin
10. Backup codes + recovery
11. Session list, logout, logout-all, re-auth
12. Auth web pages + middleware
13. Invite TTL from settings + sweep
14. Seed fixed OTP + negative tests (lockout, OTP caps, reuse-all, consent rows)

### P2 — hardening
15. Turnstile on register/OTP  
16. Stronger password scoring + UI meter  
17. Argon2 parameter documentation  
18. Default SMTP → Mailhog in dev; scrub DB error `exc!r` leaks  
19. Prefer `set_config` bind over f-string `SET LOCAL`

---

## Suggested implementation slice order

Do **not** invent a parallel auth system. Patch the existing `AuthService` / `OtpService` / models in place:

```
feat/auth-hardening   (P0: verify gate, OTP caps, lockout, reuse-all, handle, consents schema)
feat/auth-cookies     (P0: cookie + Next BFF; update tests)
feat/auth-2fa         (P1: TOTP + backup + recovery for providers)
feat/auth-web         (P1: login/register/verify/forgot screens)
```

M2 family work can continue on APIs behind Bearer for now, but **any browser UI must wait for cookie/BFF** or it will bake in the wrong token model.

---

## Files that will need edits (existing)

| File | Why |
|---|---|
| `services/auth_service.py` | Verify gate, lockout, reuse-all, handle, consents |
| `services/otp_service.py` | Attempts, issue caps, mark user verified |
| `models/user.py` + new migrations | `handle`, `email_verified_at`, OTP attempts, consents, totp |
| `schemas/auth.py` | Drop refresh from body (or cookie-only path); handle; consent versions |
| `routers/auth.py` / `otp.py` | New endpoints; rate-limit deps |
| `core/config.py` / `.env.example` | Cookie flags, lockout knobs, SMTP |
| `db/session.py` + RLS migrations | Bootstrap + more tables |
| `tests/test_auth_*.py` | Rewrite for cookie + negative cases |
| `apps/web/**` | BFF routes, middleware, auth screens |

---

## Bottom line

Existing auth is **real scaffolding with serious gaps**. Argon2, 15m JWT, refresh rotation, and OTP stubs are a start. The plan’s load-bearing rules — cookie transport, verification gating, abuse controls, handle/consents, 2FA, full RLS — are mostly **not implemented** and must be **changes to the current modules**, not a rewrite from scratch.
