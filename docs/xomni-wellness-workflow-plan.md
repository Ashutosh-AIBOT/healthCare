# Xomni Wellness Workflow Plan

## Current Audit

The repository already contains separate persistence and pages for timetables,
todos, holidays, meal plans, nutrition profiles, fitness profiles, activity
logs, Xomni conversations, and the dashboard. The missing part is the shared
workflow that makes those features behave as one product.

Current gaps:

- Xomni timetable parsing can mutate a timetable block immediately, while the
  chat UI uses a separate proposal shape that creates only a same-day todo.
- Xomni proposals are not persisted as server-side pending actions, so a
  confirmation cannot be safely resumed from Telegram or another device.
- The todo model has no recurrence or series representation for daily or
  selected-day tasks.
- Timetable templates can be read and partially edited through the API, but the
  page does not expose complete block/template editing and the week/month/year
  views are placeholders.
- The meal-plan proposal UI sends an array as `plan_json`, while the food page
  expects meal-keyed data such as `breakfast`, `lunch`, `snacks`, and `dinner`.
- Nutrition summary values are currently hard-coded, so dashboard calories,
  water, macros, and adherence are not real user data.
- Fitness logging and profile editing exist, but Xomni does not create a
  confirmed fitness action or connect activity totals to the dashboard plan.
- The time page still calls a legacy Telegram chat-id endpoint that does not
  match the per-user bot-token connection API.

## Delivery Order

### 1. Canonical time actions

- Add a persisted pending-action record with owner, conversation, action type,
  normalized payload, status, and expiry.
- Normalize natural-language schedule proposals into one action schema.
- Support add, replace, and edit operations with explicit confirmation.
- Support `today`, `daily`, `weekdays`, and selected-date scopes by creating
  linked todo instances and/or template blocks.
- Make all mutations enforce the current user and family scope.

### 2. Editable time UI

- Add block create/edit/delete controls to each timetable template.
- Add holiday weekday and specific-date editing.
- Add recurrence controls to manual todo creation.
- Refresh the selected day, stats, and dashboard after every mutation.

### 3. Food and fitness actions

- Validate and normalize meal-plan proposals before saving them.
- Add explicit accept/reject endpoints shared by web chat and Telegram.
- Add persisted daily food and water entries; compute summaries from entries.
- Keep fitness activity/profile edits manual and expose confirmed Xomni actions
  through the same service functions.

### 4. Dashboard and assistant continuity

- Replace fallback demo numbers with a single daily-summary response.
- Show current schedule block, todo completion, meal status, water progress,
  and activity totals from the same date/timezone.
- After an accepted action, return affected resources so clients can refresh
  without guessing which page changed.

### 5. Verification

- Add migration and integration tests for ownership, recurrence, conflicts,
  confirmation, rejection, and Telegram round trips.
- Run the full backend suite and frontend production build.
- Confirm `.env`, `.env.*`, and local credential files remain untracked.

## Safety Rules

- Never mutate a timetable, meal plan, or fitness plan from an LLM response
  alone.
- A clear user confirmation is required before every assistant-proposed change.
- Medical and nutrition suggestions remain informational and preserve the
  application's clinical disclaimer.
- Environment files and credentials are local-only and are never committed.
