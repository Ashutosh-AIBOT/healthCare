# Analytics event taxonomy

Defined before coding so instrumentation is consistent. Events go to a first-party `events` table and to GA4 for web acquisition.

**Hard rule: no PHI in any event.** No names, phone numbers, emails, test names, lab values, diagnoses or free text. IDs and enums only.

---

## Naming

`<domain>_<object>_<past_tense_verb>` in snake case: `report_upload_completed`, `advisor_run_completed`, `appointment_request_sent`.

Every event carries the standard envelope: `event_id`, `event_name`, `occurred_at`, `user_id`, `role`, `family_id` or `provider_id`, `session_id`, `device`, `locale`, `app_version`, `plan_tier`.

---

## Core funnels

**Acquisition to activation**

`landing_viewed` → `signup_started` → `signup_completed` → `otp_verified` → `onboarding_step_completed` (`step`) → `onboarding_completed` → `member_added` → `report_upload_completed` → `report_question_asked` → `report_answer_received`

**Activation is defined as**: a user who has added at least one member, uploaded at least one report, and received at least one AI answer, within 7 days of signup. This is the single number that says whether the product works.

**Advisor to booking (the monetizing loop)**

`advisor_run_started` → `advisor_run_completed` (`test_count`, `est_cost_paise`) → `advisor_test_expanded` → `lab_search_performed` → `lab_selected` → `booking_request_sent` → `booking_confirmed` → `sample_collected` → `report_received_from_lab` → `report_answer_received`

**Doctor discovery to consult**

`doctor_search_performed` (`filters_used`, `result_count`) → `doctor_profile_viewed` → `slot_selected` → `appointment_request_sent` → `appointment_accepted` → `consent_granted` → `consult_started` → `consult_completed` → `prescription_issued` → `review_submitted`

**Provider supply**

`provider_signup_started` → `provider_documents_uploaded` → `provider_verification_submitted` → `provider_verified` → `provider_availability_published` → `provider_first_booking_received`

---

## Event catalog by domain

**Auth** — `signup_started`, `signup_completed`, `otp_sent`, `otp_verified`, `login_succeeded`, `login_failed` (`reason_code`), `tfa_enabled`, `password_reset_completed`, `session_revoked`

**Family** — `member_added` (`relation`, `age_band`), `member_updated`, `member_transferred`, `invite_sent`, `invite_accepted`, `medical_profile_completed`

**Records** — `report_upload_started`, `report_upload_completed` (`page_count`, `size_band`, `source`), `report_extraction_completed` (`value_count`, `confidence_band`, `duration_ms`), `report_needs_review`, `report_manually_confirmed`, `report_amended`, `trend_viewed` (`test_code`, `point_count`), `critical_value_detected` (`test_code` only), `critical_value_acknowledged`

**AI** — `report_question_asked` (`question_length_band`), `report_answer_received` (`citation_count`, `latency_ms`, `cache_hit`, `provider`, `prompt_version`), `answer_refused` (`reason_code`), `guardrail_triggered` (`rule`), `emergency_detected`, `voice_session_started`, `voice_session_completed` (`duration_ms`, `locale`), `food_photo_recognized` (`confidence_band`, `was_edited`), `analytics_query_run`, `ai_degraded_shown`

**Care** — `doctor_search_performed`, `lab_search_performed`, `booking_request_sent`, `booking_confirmed`, `booking_cancelled` (`by_role`, `hours_before`), `no_show_recorded`, `consult_started`, `prescription_issued` (`item_count`), `interaction_warning_shown`, `consent_granted` (`scope`, `duration_days`), `consent_revoked`

**Lifestyle** — `food_logged` (`method`: search, barcode, photo, text), `water_logged`, `diet_plan_generated`, `workout_plan_generated`, `workout_session_logged`, `vital_logged` (`type`), `reminder_created`, `reminder_marked` (`state`: taken, snoozed, missed), `chronic_program_joined`

**Monetization** — `paywall_viewed` (`feature`), `quota_exceeded_shown` (`feature`), `plan_upgrade_started`, `plan_upgraded` (`from_tier`, `to_tier`), `payment_failed` (`reason_code`), `subscription_cancelled` (`reason_code`)

**Reliability and quality** (these tell us whether the product is actually good)
`job_failed` (`task`, `reason_code`), `api_error_shown` (`code`), `offline_write_queued`, `offline_write_synced`, `slow_screen` (`route`, `lcp_ms`)

---

## Retention and health metrics

- **D1 / D7 / D30 retention** by activation cohort
- **Weekly active families** and **weekly active providers**
- **Reports per active family per month** (core usage depth)
- **Advisor-to-booking conversion** (the revenue loop)
- **Provider response time** and **acceptance rate** (marketplace health)
- **Answer refusal rate** and **guardrail trigger rate** (AI safety health)
- **Extraction manual-confirm rate** (AI quality; a rising number means extraction is degrading)
- **AI cost per active family** (unit economics)
- **Cache hit rate** (cost efficiency)

## Implementation rules

- Emit from the service layer, in the same transaction path as the state change, via the outbox — never fire-and-forget from a component.
- Frontend emits interaction-only events (views, expands, filter use); all state-change events come from the backend so they cannot be spoofed or lost.
- Every new feature adds its events in the same PR. An unmeasured feature is a feature we cannot judge.
- Buckets, not raw values: `age_band`, `size_band`, `confidence_band`. Raw values invite PHI leakage.
