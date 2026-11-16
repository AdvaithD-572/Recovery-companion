# Source discovery

Reviewed 2026-11-08 at commit 5f0a67ad3632465b02f92f57a31d1757f3b4e546.
Method: static inspection of the repository. No application build, API execution, database migration, device test, or clinical validation was performed. Existing files were left unchanged during this documentation pass.

## Existing stack

- Android-capable Flutter application; Riverpod state, GoRouter navigation, Hive local boxes, secure token storage.
- FastAPI backend; SQLAlchemy async models, PostgreSQL configuration and a SQLite development default.
- Celery/Redis jobs for trend analysis, reminders, refill checks, and daily nudges.
- Gemini services, STT/TTS helpers, Firebase push, and S3 upload utilities.
- Docker Compose describes API, database, Redis, worker, and beat.
- Alembic configuration exists; no tracked revision files were found. No tracked CI workflow was found.
- No clinic browser frontend was found. Other generated Flutter platform directories do not establish tested support.

## Feature inventory

| Capability | Source evidence | Current limitation / planning implication |
| --- | --- | --- |
| Patient account and session | backend/app/api/v1/auth.py; mobile/lib/shared/services/auth_service.dart | Existing flows; verify refresh, expiry, logout, retry, and recovery behavior. |
| Demographics | Patient model; onboarding screen and patients.py | DOB, gender, height, weight, living situation. Step endpoint accepts a generic dict rather than the existing typed step schemas. |
| Discharge and condition | Same onboarding sources | Condition, surgery, discharge date, chronic conditions, allergies. No separate recovery episode model or structured discharge document lifecycle. |
| Lifestyle and emergency contact | Same onboarding sources | Diet type, exercise, smoking, alcohol, sleep/mood baseline, emergency contact. These do not capture a doctor's structured food instructions. |
| Onboarding prescriptions | OnboardingStep4 schema versus actual step-4 route/UI | Schema mentions prescriptions; route/UI finalize using emergency contact. Medication setup is not integrated into this onboarding sequence. |
| Home | home_page.dart; app_router.dart | Check-in, medicines, food, trends, reminders, profile, voice navigation. Persistent tab design is a future UX choice. |
| Check-in | questionnaire_page.dart; logs.py | Symptoms/scores, adherence self-report, note, daily history, clarification. Clarification currently suppresses associated flags automatically. |
| Medicines | prescription_page.dart; prescriptions.py | Add/list medicines, dose taken/skipped, stock decrement, refill threshold; OCR endpoint. No historical schedule versioning or duplicate-dose guard in the inspected dose route. |
| Prescription scanning | prescriptions.py scan-ocr | Extracts and immediately creates records; defaults unclear frequency/duration. Proposed workflow must use reviewable drafts instead. |
| Food | food_log_page.dart; food.py | Camera scan, meal type, save, today's meals, interaction cautions and recommendations; manual logging API exists. Scanning itself writes a log and the UI also offers save: verify and remove potential double-write behavior in implementation. |
| Food advice | food.py; ai_service.py | Static condition recommendations and provider-dependent interaction checking; not a structured clinician-entered diet plan. Provider errors can become empty results. |
| Trends | trends_page.dart; logs.py; twin_service.py | Actual versus hardcoded expected symptom curves. UI has 7/14/30 day controls, but provider is keyed only by metric, not selected period. |
| Escalation | trend_service.py; tasks; clinician.py | Five metrics drive weighted multi-entry deviation flags. This is not a food/missed-dose causal recovery model. Trend API uses different escalation logic. |
| Voice | voice_session_page.dart; voice.py; STT/TTS helpers | Mobile guided check-in/localization and separate server conversation routes. Verify their separate behavior; do not assume both are used by the app. Language choices include English, Hindi, Telugu, Tamil. |
| Reminders | reminders screen/router; tasks; push.py | Create/list/toggle/delete; schedules for medicines/water/meals/exercise/check-in; delivery and Android permissions unverified. |
| Offline | offline_service.dart; providers.dart | Pending daily/dose/food queues exist. Connectivity provider is a placeholder yielding true; durable automatic recovery is not established. Queues are not visibly scoped per account in the inspected service. |
| Profile | profile_page.dart; patients/me | Basic patient summary and logout; comprehensive profile editing not established. |
| Clinician access | clinician.py; Clinician and Patient models | Assigned patient list, flag summaries, reviewed marker. No receptionist role, organization membership, clinic linking, full longitudinal report, or visit lifecycle. |
| Consent | ConsentLedger model | Storage model alone does not establish a working sharing authorization flow. |
| Checkups and printing | No matching entity, route, or frontend in inspected sources | New core capability: checkpoint records, patient read-only view, interval report, print/PDF output, access/export audit. |

## Concrete risks to address in implementation

1. ApiClient and ApiConfig duplicate an old hardcoded LAN URL.
2. mark_reviewed selects a flag by ID without enforcing patient assignment; surrounding list routes do check assignment.
3. Protected route dependencies check token role without rejecting refresh-token type.
4. Recovery templates claim evidence-based origins without references in the file; risk scaling lowers expected pain/fatigue as the multiplier grows. New twin construction omits its computed mobility curve, and the read path can substitute the pain curve.
5. The only inspected Flutter test is the starter counter test referencing MyApp; the application defines RecoveryCompanionApp.
6. Daily logging dispatches a Celery task before the request transaction is committed; validate commit/worker ordering and reliable job dispatch.
7. No complete workflow for organization boundaries, checkpoint immutability, event corrections, report snapshots, or late synchronized records exists.
8. .gitignore has an invalid brace pattern that makes ordinary rg discovery fail; use explicit --no-ignore during this planning pass. Fix later as an authorized repository change.

## Skills applied

- product-capability: canonical capability contract, invariants, interfaces, unresolved decisions, and implementation handoff.
- healthcare-emr-patterns: role separation, attributable clinical records, locked-record amendments, printable workflow, and accessible medical data presentation. This project is not being expanded into a full EMR or prescribing system.
- The capability skill's referenced docs/examples/product-capability-template.md is absent from the installed skill directory. The contract follows the section structure provided directly in SKILL.md.
- No clinical guidance or legal compliance claims are established by this source inventory. Research and qualified review are later implementation/release tasks where needed.

## Handoff

Use PRODUCT.md as the current scope. Source presence means "exists to inspect and verify," not "finished." Preserve the old assessment and README as historical context; do not silently discard existing features.

## Documentation verification and self-review

Applied agent-self-evaluation after preparing the package. This rates the planning deliverable, not the untested application.

| Axis | Score | Evidence and improvement |
| --- | --- | --- |
| Accuracy | 4/5 | Findings are tied to inspected source; runtime behavior is unverified. Reproduce findings during M1 before treating them as runtime defects. |
| Completeness | 4/5 | Patient setup/tracking, clinic access, checkpoints, reporting and failure cases are covered; eight product decisions remain explicitly open. Resolve affected contracts with the user before coding them. |
| Clarity | 4/5 | PRODUCT.md separates confirmed requirements, proposals and open decisions; the technical timestamp/report rules need a concrete UI example during design review. |
| Actionability | 4/5 | M0-M7 supply ordered work and exit criteria; final graph and role acceptance depends on G1/R1. Start with those decisions when implementation is requested. |
| Conciseness | 4/5 | Six documents have distinct owners; a few safety/history invariants repeat intentionally in agent instructions and the contract. Keep future updates in the canonical owner instead of adding another plan. |

Overall: 4.0/5. No critical documentation issue identified. Highest-impact next refinement: settle graph meaning and clinic checkpoint authority, then illustrate a first and second visit with sample report dates. Self-check: the package should match the requested documentation-only scope; the user must still judge whether the proposed defaults match their intended product.

Verification: six document titles and UTF-8 text checked; reading-order references resolve; eight decision IDs and 35 unique acceptance IDs checked. All 188 existing tracked files retained their original SHA-256 aggregate, 4B8409DF1A2147034E0C3AC781B9B10AE31EC49978672E395536A14ED9458AA4. git diff --check passed for tracked changes; all new planning files were also explicitly checked for trailing whitespace. The pre-existing PROJECT-ASSESSMENT.md was preserved.
