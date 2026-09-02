# Screen inventory and specification

Every screen in the product, with the states it must implement. An agent building UI should not invent structure — build what is specified here, and if something is genuinely missing, add it to this file in the same PR.

**Universal requirements for every screen** (from [`12-ui-states-a11y.md`](../.cursor/rules/12-ui-states-a11y.md)): skeleton loading, empty state with CTA, error state with retry, responsive 360→1920 with no horizontal scroll, keyboard reachable, dark and light, i18n keys only, Tailwind only.

---

## Public / marketing — `(marketing)`, SSR/ISR, SEO-critical

| Route | Purpose | Notes |
|---|---|---|
| `/` | Landing | Hero with the report-to-insight demo, the compounding loop, social proof, trust signals (verified providers, privacy, "not a medical device"), pricing teaser, FAQ with `FAQPage` schema |
| `/features` | Feature depth | Sectioned by the four sides |
| `/pricing` | Plans | Family and provider tiers, quota table, upgrade CTA |
| `/for-doctors` | Provider acquisition | Value prop, verification steps, earnings, signup CTA |
| `/for-labs` | Lab acquisition | Catalog management, home collection, direct upload |
| `/doctors/[city]` | Directory | Programmatic, quality-gated, faceted URLs noindexed |
| `/doctors/[city]/[specialization]` | Directory | Filters, ranking explanation, map |
| `/doctors/[city]/[specialization]/[slug]` | Doctor profile | `Physician` JSON-LD, availability preview, reviews, book CTA |
| `/labs/[city]` | Lab directory | Accreditation, turnaround, home collection |
| `/labs/[city]/[slug]` | Lab profile | Branches, catalog, prices, serviceable pincodes |
| `/tests/[slug]` | Test explainer | What it measures, prep, ranges, `MedicalTest` schema |
| `/tests/[slug]/[city]` | Test pricing | Price comparison across labs, `AggregateOffer` |
| `/blog`, `/blog/[slug]` | Content | Author + medical reviewer byline, last-reviewed date |
| `/about`, `/contact`, `/help` | Trust and support | Help center with searchable articles |
| `/legal/terms`, `/legal/privacy`, `/legal/refund`, `/legal/medical-disclaimer`, `/legal/accessibility` | Legal | Grievance officer contact on privacy |
| `/status` | Status page | Service health, incident history |

Empty/edge: a directory page with no verified providers renders the quality-gate fallback (`noindex`, nearby-cities suggestions), never an empty grid.

---

## Auth — `(auth)`

`/login` · `/register` · `/verify-otp` · `/two-factor` · `/forgot-password` · `/reset-password` · `/account-recovery` · `/onboarding` (4-step wizard) · `/invite/[token]` (accept family or provider invite)

States that must exist: field-level validation, password strength meter, submit disabled until valid, rate-limit countdown, OTP resend cooldown with attempts remaining, expired-link state, locked-account state, 2FA with backup-code fallback, invite already-used and expired states.

---

## Family app — `(family)`

| Route | Purpose | Key states beyond the universal four |
|---|---|---|
| `/dashboard` | Home | Health score with explanation, next appointment, today's reminders, latest report, unacknowledged critical banner; first-run state guides to add member then upload |
| `/members` | Member list | Member switcher, privacy indicator per member |
| `/members/[id]` | Member timeline | Chronological records; guardian-managed banner for minors; frozen state for deceased |
| `/members/[id]/medical-profile` | Conditions, allergies, medications | Completion progress; allergy entries feed prescription checks |
| `/reports` | Report vault | Per-report status chips (queued, processing, ready, needs review, failed); filter by member |
| `/reports/upload` | Upload | Drag-drop, camera capture, resumable progress, password prompt for encrypted PDF, named job stages |
| `/reports/[id]` | Report detail | Values table with flags, original document viewer, "corrected by lab" badge on amended versions, low-confidence confirm banner |
| `/reports/[id]/confirm` | Manual confirm | Side-by-side original and extracted values, editable fields |
| `/reports/[id]/ask` | Report Q&A | Streaming answer, inline citations, cache badge, refusal state, degraded-AI state, disclaimer |
| `/trends` | Lab trends | Per-test chart; cross-lab caveat note; "need two reports" empty state |
| `/checkup-advisor` | Advisor | Run progress by node, per-test rationale with citations, prep notes, estimated cost, book CTA, quota-exceeded state |
| `/vitals` | Vitals | Manual entry, device import, range indicators |
| `/chronic/[program]` | Chronic program | Targets, adherence streak, monthly summary, share-with-doctor |
| `/nutrition` | Nutrition home | Daily targets vs logged, nutrient gaps, insights linking to lab flags |
| `/nutrition/log` | Food logging | Four methods (search, barcode, photo, text); photo confirm step marked "estimate"; offline queued state |
| `/nutrition/plan` | Diet plan | Generated plan with citations, regenerate, condition-aware notes |
| `/workout`, `/workout/plan` | Workout | Plans, session logging, progress, condition guardrail notes |
| `/reminders` | Reminders | Medicine and checkup, taken/snoozed/missed, timezone-correct times |
| `/doctors` | Find doctors | Filters, ranking explanation, labeled sponsored results, no-results state |
| `/appointments`, `/appointments/[id]` | Appointments | Full state machine surfaced; cancellation window closed state; join teleconsult |
| `/consult/[id]` | Teleconsult room | Pre-call device check, consent recording notice, reconnect state, fallback to chat |
| `/labs` | Find labs | Price comparison, serviceability by pincode, non-serviceable state |
| `/lab-bookings`, `/lab-bookings/[id]` | Lab bookings | Sample timeline, rejection with free recollection, partial-report state |
| `/prescriptions`, `/prescriptions/[id]` | Prescriptions | Signed PDF download, linked reminders |
| `/chat`, `/chat/[threadId]` | Chat | Consent-scoped, typing and read receipts, attachment upload, emergency banner, provider-unlinked state |
| `/billing` | Plan and usage | Quota meters, invoices, upgrade, payment-failed state |
| `/settings/profile`, `/settings/privacy`, `/settings/consent`, `/settings/notifications`, `/settings/security`, `/settings/data` | Settings | Consent grants list with revoke; access log; notification preferences with quiet hours; sessions and 2FA; export and delete with confirmation friction |

---

## Doctor app — `(doctor)`

`/doctor/dashboard` (today's schedule, pending requests, unacknowledged criticals) · `/doctor/onboarding` (profile, documents, verification status with rejected-reason state) · `/doctor/availability` (rules, buffers, holidays, exceptions, conflict warnings) · `/doctor/appointments` and `/doctor/appointments/[id]` (accept, decline, reschedule, SLA countdown) · `/doctor/patients` (consented only; request-access state) · `/doctor/patients/[memberId]` (consent-gated record view, scope-insufficient state) · `/doctor/consult/[id]` (notes, video room) · `/doctor/prescriptions/new` (drug search, allergy cross-check warning, interaction warning, signature) · `/doctor/chat` · `/doctor/reviews` (with reply) · `/doctor/profile` (public preview, completeness gate) · `/doctor/earnings`

Verification gate: an unverified doctor sees a restricted shell — profile and documents only, with a clear status explanation. No bookings, no patient data.

---

## Lab app — `(lab)`

`/lab/dashboard` (today's collections, pending uploads, SLA warnings) · `/lab/onboarding` · `/lab/bookings` and `/lab/bookings/[id]` · `/lab/collections` (route and capacity view, phlebotomist assignment) · `/lab/samples/[id]` (event timeline, reject with reason, schedule recollection) · `/lab/reports/upload` (patient lookup, member selection, direct-to-vault upload) · `/lab/reports/[id]/amend` (amendment reason required, supersedes previous version) · `/lab/catalog` (tests, packages, prices per branch, CSV import with validation preview) · `/lab/branches` (serviceable pincodes, capacity) · `/lab/sla` · `/lab/profile`

---

## Admin — `(admin)`

`/admin/dashboard` (platform metrics) · `/admin/verification` (provider queue with document viewer, approve, reject with reason, request-more-info) · `/admin/claims` (profile claim review) · `/admin/catalog/tests`, `/admin/catalog/foods`, `/admin/catalog/drugs` (curation, CSV import, provenance and verified flags) · `/admin/reviews` (moderation queue, flags, spam signals) · `/admin/extraction-review` (low-confidence extraction queue) · `/admin/guardrails` (compliance report: triggers by rule, blocked outputs, emergency detections) · `/admin/ai-quality` (eval scores over time, cost per tenant, cache hit rate, refusal rate) · `/admin/jobs` (queue depth, DLQ, retry) · `/admin/criticals` (unacknowledged critical values) · `/admin/support` (tickets) · `/admin/users` (impersonate with reason and audit) · `/admin/flags` · `/admin/announcements` · `/admin/blog` (editorial workflow with medical reviewer sign-off)

---

## Cross-cutting components

Global: role-aware app shell (bottom nav mobile, sidebar desktop), member switcher, command palette, notification center, theme toggle, locale switcher, offline banner, degraded-AI banner, emergency banner, consent request modal, disclaimer footer.

Domain: `LabValueRow` (flag colour plus icon plus text, never colour alone), `TrendChart` (cross-lab caveat), `JobProgress` (named stages), `StreamingAnswer` (citations, `aria-live`), `CitationChip` (opens the source page), `ConsentBadge`, `VerifiedBadge`, `SlotPicker` (timezone-correct), `QuotaMeter`, `EmptyState`, `ErrorState`, skeletons per surface.
