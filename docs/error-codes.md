# Error code catalog

Every API error returns RFC 7807 `problem+json` with a **stable machine-readable `code`**. The frontend maps codes to i18n messages ([copy-guide.md](copy-guide.md)) and never string-matches on `detail`.

```json
{
  "type": "https://aarogya.app/errors/consent-required",
  "title": "Consent required",
  "status": 403,
  "code": "CONSENT_REQUIRED",
  "detail": "You need the patient's permission to view this record.",
  "request_id": "01J8F3K2M9QW",
  "meta": { "member_id": "018f...", "action": "request_access" }
}
```

Rules: codes are `SCREAMING_SNAKE_CASE`, never renamed once released (add a new one and deprecate), never contain PHI in `detail` or `meta`, and always carry a `request_id`.

---

## Auth and identity (`AUTH_`, `OTP_`, `TFA_`)

| Code | HTTP | When |
|---|---|---|
| `AUTH_INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `AUTH_TOKEN_EXPIRED` | 401 | Access token expired; client should refresh |
| `AUTH_TOKEN_INVALID` | 401 | Malformed or tampered token |
| `AUTH_REFRESH_REUSED` | 401 | Refresh token reuse detected; all sessions revoked |
| `AUTH_EMAIL_EXISTS` | 409 | Registration with an existing email |
| `AUTH_EMAIL_UNVERIFIED` | 403 | Action requires a verified email |
| `AUTH_RATE_LIMITED` | 429 | Too many attempts |
| `AUTH_ACCOUNT_LOCKED` | 423 | Locked after repeated failures |
| `AUTH_REAUTH_REQUIRED` | 403 | Sensitive action needs a fresh login |
| `OTP_INVALID` | 400 | Wrong code |
| `OTP_EXPIRED` | 410 | Code past TTL |
| `OTP_ATTEMPTS_EXCEEDED` | 429 | Too many wrong codes |
| `OTP_RESEND_TOO_SOON` | 429 | Resend before cooldown |
| `TFA_REQUIRED` | 403 | Provider or admin account without 2FA verification |
| `TFA_INVALID` | 400 | Wrong TOTP or backup code |

## Authorization and consent (`PERM_`, `CONSENT_`)

| Code | HTTP | When |
|---|---|---|
| `PERM_DENIED` | 403 | Role lacks permission |
| `PERM_WRONG_TENANT` | 403 | Resource belongs to another family or provider |
| `PERM_ROLE_REQUIRED` | 403 | Action needs a specific role |
| `CONSENT_REQUIRED` | 403 | No active grant for this member and record type |
| `CONSENT_EXPIRED` | 403 | Grant lapsed |
| `CONSENT_REVOKED` | 403 | Patient revoked access |
| `CONSENT_SCOPE_INSUFFICIENT` | 403 | Grant does not cover this record type |
| `GUARDIAN_CONSENT_REQUIRED` | 403 | Minor's record needs guardian action |

## Validation and resources (`VALIDATION_`, `NOT_FOUND`, `CONFLICT_`)

| Code | HTTP | When |
|---|---|---|
| `VALIDATION_FAILED` | 422 | Schema validation failed; `meta.fields` lists errors |
| `NOT_FOUND` | 404 | Resource missing or not visible to this tenant |
| `CONFLICT_DUPLICATE` | 409 | Unique constraint violated |
| `CONFLICT_STATE` | 409 | Illegal state transition |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 | Create without the header |
| `IDEMPOTENCY_KEY_MISMATCH` | 409 | Same key, different payload |

## Files and extraction (`FILE_`, `EXTRACTION_`)

| Code | HTTP | When |
|---|---|---|
| `FILE_TOO_LARGE` | 413 | Over the size cap |
| `FILE_UNSUPPORTED_TYPE` | 415 | Not PDF, JPG or PNG (magic bytes checked) |
| `FILE_CORRUPT` | 422 | Unreadable file |
| `FILE_ENCRYPTED` | 422 | Password-protected PDF |
| `FILE_TOO_MANY_PAGES` | 422 | Over the page cap |
| `FILE_VIRUS_DETECTED` | 422 | AV scan positive |
| `EXTRACTION_LOW_CONFIDENCE` | 200 | Succeeded but needs manual confirmation |
| `EXTRACTION_FAILED` | 200 | Values unreadable; text-only fallback saved |

## AI (`AI_`)

| Code | HTTP | When |
|---|---|---|
| `AI_UNAVAILABLE` | 503 | All providers failed |
| `AI_DEGRADED` | 200 | Running on fallback provider or cache |
| `AI_TIMEOUT` | 504 | Model call exceeded timeout |
| `AI_NO_CONTEXT` | 200 | No retrieval support; refuses to guess |
| `AI_BLOCKED_BY_GUARDRAIL` | 200 | Output blocked; safe message returned |
| `AI_INPUT_TOO_LONG` | 400 | Prompt over the cap |
| `AI_UNSAFE_INPUT` | 200 | Prompt injection or disallowed request detected |
| `AI_EMERGENCY_DETECTED` | 200 | Red-flag input; emergency response returned |

## Booking and care (`SLOT_`, `BOOKING_`, `SAMPLE_`)

| Code | HTTP | When |
|---|---|---|
| `SLOT_UNAVAILABLE` | 409 | Slot taken during confirmation |
| `SLOT_EXPIRED` | 410 | Held slot lapsed |
| `BOOKING_WINDOW_CLOSED` | 422 | Outside the cancellation or reschedule window |
| `BOOKING_LIMIT_REACHED` | 429 | Too many reschedules |
| `PROVIDER_UNVERIFIED` | 403 | Provider cannot accept bookings yet |
| `PINCODE_NOT_SERVICEABLE` | 422 | Home collection unavailable there |
| `AREA_CAPACITY_FULL` | 409 | No collection capacity in that slot |
| `SAMPLE_REJECTED` | 200 | Lab rejected the sample; recollection offered |

## Quota, billing, platform (`QUOTA_`, `BILLING_`, `RATE_`, `INTERNAL`)

| Code | HTTP | When |
|---|---|---|
| `RATE_LIMITED` | 429 | Endpoint rate limit; `Retry-After` set |
| `QUOTA_EXCEEDED` | 429 | Plan feature quota used up |
| `COST_CEILING_REACHED` | 429 | Tenant AI cost ceiling hit |
| `PLAN_UPGRADE_REQUIRED` | 402 | Feature not on the current plan |
| `PAYMENT_FAILED` | 402 | Gateway declined |
| `FEATURE_DISABLED` | 404 | Behind a disabled feature flag |
| `MAINTENANCE` | 503 | Planned maintenance |
| `INTERNAL` | 500 | Unhandled; logged with `request_id` |
