# Copy guide

All user-facing text lives in i18n message catalogs (`en`, `hi`). Never inline a string in a component.

---

## Tone

Calm, plain, specific. We are a careful assistant, not a doctor and not a marketer.

- Short sentences. No jargon unless the report used it, and then explain it once.
- Second person, active voice: "Upload a report to see explained results."
- Never alarming, never falsely reassuring. State the fact, then the action.
- Never claim accuracy we cannot back: "estimated", "based on your report", "discuss with your doctor".
- No exclamation marks in medical contexts. No emoji anywhere in product UI.

Say "lab report", "value", "reference range", "screening test". Avoid "normal/abnormal" as a verdict; use "within range" and "outside range".

---

## Medical disclaimers (use verbatim, never paraphrase)

These strings are legally load-bearing. They must appear as written, and any change requires review.

**`disclaimer.ai_output`** — attached to every AI-generated response
> Aarogya explains information found in your records and general health guidelines. It does not diagnose conditions or recommend treatment. Always discuss your results with a qualified doctor.

**`disclaimer.checkup_advisor`** — on every advisor result
> These are screening suggestions based on your profile and past reports, intended to help you plan a conversation with your doctor. They are not a diagnosis and not a prescription for tests.

**`disclaimer.nutrition`** — on diet plans and food insights
> Nutrition information is an estimate based on our food database and your logged portions. It is general guidance, not clinical dietary advice. If you have a medical condition, follow your doctor's or dietitian's plan.

**`disclaimer.report_values`** — on extracted lab values
> Values were read automatically from your report and may contain errors. The original report is always available and takes precedence. Please confirm anything important against the original document.

**`disclaimer.not_medical_device`** — footer of every AI surface
> Aarogya is not a medical device and does not provide medical diagnosis or treatment.

**`emergency.banner`** — shown when red-flag input is detected
> What you have described may need urgent medical attention. Please contact emergency services or go to the nearest emergency department now. Aarogya cannot assess emergencies.

Emergency banners always show local helpline numbers and never continue the AI conversation.

---

## Error messages

Every error code in [error-codes.md](error-codes.md) maps to a user-facing message. Rules: say what happened, say what to do, never show a status code, stack trace, SQL or provider text.

| Code | Message |
|---|---|
| `AUTH_INVALID_CREDENTIALS` | That email and password do not match. Check them and try again. |
| `AUTH_RATE_LIMITED` | Too many attempts. Please wait {seconds} seconds and try again. |
| `OTP_EXPIRED` | That code has expired. Request a new one. |
| `OTP_INVALID` | That code is not correct. You have {attempts} attempts left. |
| `CONSENT_REQUIRED` | You need the patient's permission to view this record. Request access to continue. |
| `FILE_TOO_LARGE` | That file is larger than 10 MB. Try a smaller file or split the report. |
| `FILE_UNSUPPORTED_TYPE` | We can only read PDF, JPG and PNG files. |
| `FILE_ENCRYPTED` | This PDF is password protected. Enter the password to continue. |
| `EXTRACTION_LOW_CONFIDENCE` | We could not read some values clearly. Please confirm them against your report. |
| `EXTRACTION_FAILED` | We could not read the values from this report, but you can still ask questions about its text. |
| `AI_UNAVAILABLE` | Our AI service is temporarily unavailable. Your data is safe. Please try again in a few minutes. |
| `AI_DEGRADED` | AI is running in reduced mode, so answers may be slower or shorter. |
| `AI_NO_CONTEXT` | I could not find this in your reports. Try rephrasing, or upload the relevant report. |
| `QUOTA_EXCEEDED` | You have used your {feature} limit for today. It resets at midnight, or upgrade for more. |
| `SLOT_UNAVAILABLE` | That slot was just taken. Here are the next available times. |
| `BOOKING_WINDOW_CLOSED` | This appointment can no longer be cancelled online. Please contact the clinic. |
| `PINCODE_NOT_SERVICEABLE` | This lab does not collect samples in {pincode} yet. Try another lab or a walk-in visit. |
| `NETWORK_OFFLINE` | You are offline. We saved this and will sync it when you reconnect. |
| `INTERNAL` | Something went wrong on our side. We have logged it. Please try again. |

---

## Empty states

Every empty state needs a title, one explanatory line, and a primary action.

- **Reports** — "No reports yet" / "Upload a lab report to see explained results and trends." / *Upload report*
- **Members** — "Only you so far" / "Add your family members to track their health together." / *Add member*
- **Appointments** — "No appointments" / "Find a verified doctor and book a time that suits you." / *Find doctors*
- **Food log (today)** — "Nothing logged today" / "Add a meal to track calories and nutrients." / *Add food*
- **Reminders** — "No reminders set" / "Add medicine or checkup reminders so nothing gets missed." / *Add reminder*
- **Trends (one report)** — "Not enough data yet" / "Trends appear once you have two or more reports with the same test." / *Upload report*
- **Doctor inbox** — "No appointment requests" / "Requests appear here. Keep your availability updated so patients can book." / *Edit availability*
- **Search, no results** — "No matches for those filters" / "Try widening the distance or clearing a filter." / *Clear filters*

---

## Loading and progress

Named stages, never a bare spinner: "Reading your report", "Extracting values 3 of 4", "Checking reference ranges", "Almost done".

## Buttons

Verb first, specific: *Upload report*, *Add member*, *Book appointment*, *Request access*, *Grant access*, *Regenerate plan*. Never *Submit*, *OK* or *Click here*.

## Hindi

Hindi is a first-class locale, not a machine translation of English. Keep medical test names in English with Devanagari transliteration where common. Disclaimers are professionally translated and reviewed — never machine-translated.
