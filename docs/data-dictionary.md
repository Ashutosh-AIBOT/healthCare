# Data dictionary and conventions

Read before adding a column, an enum or a unit. These conventions exist so 24 milestones of migrations stay consistent.

---

## Naming

- `snake_case` everywhere in the database. Tables plural (`lab_reports`), foreign keys `<singular>_id`.
- Booleans prefixed `is_` or `has_`. Timestamps suffixed `_at`. Counts suffixed `_count`. Money suffixed `_paise`.
- Postgres enum types are singular: `appointment_status`, `lab_flag`.
- No reserved words as identifiers (`user`, `order`, `end`, `group`). No ambiguous abbreviations — `reference_range_low`, not `ref_lo`.

## Required columns

Every table: `id` UUIDv7 primary key, `created_at`, `updated_at` (`timestamptz`).
Every tenant table: `family_id` or `provider_id`, indexed, RLS policy attached.
Soft-deletable tables: `deleted_at timestamptz NULL` — and every query must filter it.
Auditable tables: `created_by`, `updated_by` referencing `users.id`.

## Identifiers

- Primary keys are **UUIDv7** (time-ordered, so index locality is preserved).
- Sequential integers are never exposed publicly.
- Public URLs use a slug plus a short hash: `/doctors/delhi/cardiologist/dr-ravi-mehta-9f2a`.
- External references (booking numbers shown to users) use a prefixed short code: `APT-7K2M9Q`, `LAB-3F8T1X`.

## Money

`bigint` **paise**, always. Column name ends `_paise` (`price_paise`, `fee_paise`, `commission_paise`).
Never `float`. Never `numeric` for currency. Formatting happens only at the display layer. INR only at launch; a `currency` column is added when a second currency is real, not before.

## Time

- Stored as `timestamptz` in **UTC**, always.
- Display converts to the member's timezone (`family_members.timezone`, IANA string, default `Asia/Kolkata`).
- Reminders store the local wall-clock time plus the timezone, so DST and travel do not shift them.
- Dates without a time (date of birth, report date) use `date`.
- Display format `d MMM yyyy` (`14 Mar 2026`); never ambiguous numeric formats.

## Units and lab values

This is the highest-risk area for silent correctness bugs.

- `lab_results` stores **both** the value as reported (`raw_value`, `raw_unit`) **and** the normalized value in the test's canonical unit (`value`, `unit`).
- Reference ranges are stored **per report** (`reference_low`, `reference_high`, `reference_source`) — never taken from a global table, because ranges vary by lab, method, age, sex and pregnancy.
- Trend charts plot normalized values and must display a note when reports come from different labs.
- Canonical units are declared on `lab_tests.canonical_unit`. Conversion factors live in code with unit tests.
- Vitals: weight in grams, height in millimetres, temperature in decidegrees Celsius, blood pressure as two integers (mmHg). Integers avoid float drift; display converts.

## Enum registry (single source of truth)

Declared as Postgres enums, mirrored into generated TypeScript unions. Never hand-typed in two places.

- `user_role` — `family_owner`, `family_admin`, `family_member`, `doctor`, `lab_admin`, `lab_staff`, `phlebotomist`, `platform_admin`, `support_agent`
- `relation` — `father`, `mother`, `spouse`, `son`, `daughter`, `brother`, `sister`, `grandfather`, `grandmother`, `other` (with `relation_custom` required when `other`)
- `gender` — `male`, `female`, `other`, `prefer_not_to_say`
- `blood_group` — `a_pos`, `a_neg`, `b_pos`, `b_neg`, `ab_pos`, `ab_neg`, `o_pos`, `o_neg`, `unknown`
- `provider_type` — `doctor`, `lab`
- `verification_status` — `unverified`, `pending`, `verified`, `rejected`, `suspended`
- `job_status` — `queued`, `processing`, `ready`, `needs_review`, `failed`, `cancelled`
- `lab_flag` — `low`, `normal`, `high`, `critical_low`, `critical_high`, `indeterminate`
- `appointment_status` — `requested`, `accepted`, `confirmed`, `in_progress`, `completed`, `declined`, `expired`, `cancelled_by_patient`, `cancelled_by_provider`, `no_show_patient`, `no_show_provider`
- `booking_status` — `requested`, `confirmed`, `sample_pending`, `sample_collected`, `processing`, `partial`, `completed`, `cancelled`, `rejected`
- `sample_event` — `collected`, `received`, `rejected`, `recollection_scheduled`, `processing`, `reported`
- `consent_scope` — `lab_reports`, `prescriptions`, `vitals`, `medical_profile`, `nutrition`, `all`
- `visibility` — `private`, `family`, `consented_providers`
- `plan_tier` — `free`, `plus`, `family_pro`, `provider_growth`
- `notification_channel` — `in_app`, `email`, `sms`, `push`
- `meal_type` — `breakfast`, `lunch`, `dinner`, `snack`
- `diet_preference` — `vegetarian`, `non_vegetarian`, `eggetarian`, `vegan`, `jain`

## Audit event naming

`<domain>.<entity>.<past_tense_verb>` — `care.appointment.confirmed`, `records.report.amended`, `consent.grant.revoked`, `admin.user.impersonated`. Fixed taxonomy keeps the audit log queryable. Same names are reused for `outbox_events` topics.

## Feature flags

`<area>_<capability>` in lower snake case: `ai_voice_enabled`, `care_teleconsult_enabled`, `billing_payments_enabled`. Default `false` in prod, `true` in dev. A flag fully rolled out must be removed within one milestone — stale flags are debt.

## Environments

| Environment | Data | LLM | Payments | Flags |
|---|---|---|---|---|
| dev | synthetic seed | mock or cheap model | test mode | all on |
| staging | synthetic seed, real providers invited | real, low quota | test mode | release candidates on |
| prod | real | real, quotas enforced | live | explicit per flag |

Seeding is disabled in production. Real patient data never enters dev or staging.

## Browser support

Last two versions of Chrome, Safari, Firefox and Edge, plus Android Chrome and iOS Safari 16+. Anything older gets a supported-browser notice, not a broken layout.
