# Acceptance and evidence checklist

The scenarios below define acceptance targets. The current result records the checks exercised locally and their evidence.
Each scenario below requires a result, environment, date, build/commit, and evidence reference during implementation. Passing a mocked test does not prove a real device, external service, production deployment or clinical outcome.

## Canonical synthetic scenario

Use synthetic patients A and B in Clinic One and Clinic Two. Staff roles include receptionist and clinician with explicitly configured permissions. Patient A has a non-empty episode, versioned prescription/diet plan, scheduled and as-needed medication, meals, observations, two clinic visits, missing entries, one correction and a late offline upload. Patient B is the cross-access control fixture.

Give each record a stable fixture ID and declare expected report membership and totals before executing tests. Use exact boundary timestamps plus date-only records. Never populate examples with real patient data.

## Product acceptance

| ID | Observable scenario and required result |
| --- | --- |
| A01 | Android registration/login/session expiry/logout: correct user state, recoverable errors, no cross-account data. |
| A02 | Onboarding persists identity, age/DOB precision, measurements, discharge condition/procedure, relevant background, medicines and doctor food/care instructions; review screen matches storage. |
| A03 | Interrupted setup resumes; repeat completion creates no duplicate reminders, prescriptions or episodes. Required-field errors are actionable; unknown fields remain unknown. |
| A04 | OCR ambiguity leaves a draft; no guessed dose, frequency or duration becomes an active plan. Manual setup works without a provider. |
| A05 | Today/navigation reaches medicines, food, check-in, trends, reminders, voice and records; loading/error/empty states are distinguishable. |
| A06 | Taken, explicitly skipped, unreported and as-needed medication are distinct. Retries/concurrent taps cannot duplicate a dose or decrement stock twice. |
| A07 | Prescription changes apply by effective date/version. Past adherence remains tied to the historical schedule; as-needed doses do not inflate scheduled adherence. |
| A08 | Meal scan -> review/correction -> save stores one event. Manual entry works without camera/AI. Analysis outage shows unavailable, not safe/no interactions. |
| A09 | Check-in dates, score direction and notes match manual and voice submissions. Duplicate/revised logs follow a visible correction policy. |
| A10 | 7/14/30 day filters actually alter requested/returned periods; gaps stay gaps. Symptom charts and report values agree. |
| A11 | Offline queue survives app restart and reconnect, preserves event times and retries safely. Account change cannot replay A's records as B's. |
| A12 | Reminder settings, timezone, denied notification permission and selected quiet-hour behavior are visible. Device delivery is tested on the declared Android target. |
| A13 | English/Hindi/Telugu/Tamil claims require each supported flow to be tested. Low-confidence voice extraction is reviewable; manual fallback is available. |
| A14 | Clinic staff can find authorized patients and confirm identity; search never exposes Clinic Two's patients to Clinic One. |
| A15 | Patient can read their finalized clinic records/amendments and cannot create/edit/finalize/delete them by direct API requests. |
| A16 | Receptionist/clinician permissions match R1. Patient-entered instructions cannot impersonate staff confirmation. |
| A17 | Visit drafts/cancellation do not advance the checkpoint; authorized finalization is atomic/idempotent. Signed records retain original content after amendments. |
| A18 | Initial report covers discharge onward. Next report covers the declared interval since the previous finalized checkpoint with exact fixture membership. |
| A19 | Repeated preview/print neither creates a visit nor moves a checkpoint. Reprinting a snapshot retains its data; refresh yields a distinct version. |
| A20 | Exact boundary events, date-only boundary-day observations, midnight, offset changes and permitted backdated records follow ARCHITECTURE.md or a documented superseding decision. |
| A21 | A late upload/correction for an earlier interval appears in the next report's explicit late-additions section; prior snapshots remain intact. |
| A22 | Report has useful summary AND complete interval detail: symptoms, medicines/adherence counts, meals, patient notes, care-plan versions, relevant clinic records, gaps and attachment index. |
| A23 | No-log and long-history reports render correctly. All printed pages have patient/report identity and pagination; no clipped rows, missing chart labels or blank overflow pages. |
| A24 | Synthetic reviewed rules flag an explicit skipped dose and a meal matching a recorded restriction. Critical appears only at the configured severity. Unknown ingredients, missing rule coverage or a failed check show unable to assess. An unlogged dose stays unreported. Check labels, reasons and rule versions against the clinic report. |
| A25 | Save, sync, available-to-clinic, exported and staff-reviewed states are distinct; UI never invents care-team acknowledgement. |

## Technical and security acceptance

| ID | Verification |
| --- | --- |
| S01 | Patient B/Clinic Two cannot access A's records, attachments, reports, flags or visits by guessed IDs or forged body scope. Check reads and writes. |
| S02 | Refresh tokens fail on access-only routes; expired/invalid/revoked credentials and inactive staff membership are handled correctly. |
| S03 | Clinic enrolment/link verification and consent/revocation enforce the chosen policy. Knowing a lookup identifier grants no record access. |
| S04 | Protected report/download URLs cannot be reused by unauthorized users; authorization, expiry and private storage behavior are verified. |
| S05 | Patient/logging and factual reporting succeed with AI unavailable. Provider failures are observable without medical data leaking into ordinary logs. |
| S06 | Database uniqueness, request idempotency, concurrent submissions and after-commit job dispatch preserve exactly-once business effects. |
| S07 | PostgreSQL migration rehearsal preserves identifiers, timestamps, historical source labels and expected record counts; restore is rehearsed before live rollout. |
| S08 | Audit trail records authorized reads/exports, checkpoint finalization/amendments and permission changes with actor and time. |
| S09 | Android local cache/queue handling meets the chosen encryption/account-scoping policy; sensitive values are absent from fixtures, screenshots and logs. |
| S10 | Large text, TalkBack labels, keyboard clinic workflow, contrast and non-color states remain usable on declared targets. |

## Evidence levels and release gates

- Static inspection: source findings only.
- Automated unit/contract checks: calculations, authorization, idempotency, validation and state transitions.
- Local integration: real API/PostgreSQL/worker plus actual generated reports.
- Browser: clinic navigation, denied access, print preview and downloaded report inspection.
- Android emulator: main patient journey, lifecycle and permission behavior.
- Physical Android: install/launch, camera, microphone, notifications, offline/reconnect and readability.
- Hosted/pilot: only after authorized deployment and the selected release/privacy/clinical-content gates.

Do not mark a milestone complete from a lower evidence level than its stated requirement. Record unavailable devices/services as gaps, not passes. Review PDF text, page count, report membership and rendered pages; opening a file alone is insufficient. Clinical prediction validity and real-world health outcomes require separate evidence beyond software tests.

## Current result

The station administrator and patient web account workflows passed in Edge on 2026-11-16. The browser created a clinic, signed in its first clinician, created a patient, found the unlinked patient in the administrator directory, canceled then confirmed clinic deletion, and deleted the patient's own profile. The directory no longer returned the deleted patient.

SQLite and PostgreSQL 18 integration checks exercised role denials, password confirmation, old access and refresh credentials, clinic invitation revocation, email reuse, recreated clinic isolation and preservation of signed checkups and report snapshots. PostgreSQL migrated a previous clinic link, passed the Alembic schema comparison, and restored a populated backup. The extracted Windows kit provisioned an administrator and verified administrator access after backup and restore. The combined kit SHA-256 for this web release is `5B4D64A9E513D4D2958C07936E3FA7A3BA6624AEB5EE0196C92A45E0EDE2FA84`. Android source and the previously signed APK were outside this change.

On 2026-11-16 the rebuilt signed APK and the Edge clinic portal passed a two-way local test on an Android 15 emulator. With `RC_TEST_OFFLINE=1` and `RC_TEST_CLINIC_BROWSER=1`, the patient saved a meal offline, force-stopped and reopened the app, and reconnected. The staff report contained the meal once. Staff saw it in Edge, finalized a checkup, and the patient saw the new note after reopening Records without restarting. The screenshot is `docs/demo/clinic-checkup-on-android.png`. Both Flutter widget tests passed, including refresh while Records is already open.

Additional synthetic emulator checks covered registration and all four onboarding screens, manual prescription entry, a taken dose decrementing stock, a skipped-dose reason, a daily check-in, discharge instructions, selecting a 30-day trend, creating a reminder, the Android notification permission prompt, the voice-to-manual fallback, and taking simulated camera pictures for meal and prescription scans. With the provider disabled both scans returned an unavailable response. In a separate clinic-link exercise, disconnecting removed the patient from the Edge directory. Staff issued a fresh invitation and the patient reviewed and accepted it on Android. The Edge report then displayed the phone's meal, instructions and skipped-dose reason.

Two defects found during this run were fixed. Reopening Records now fetches the clinic's latest visits. Signing in as a different patient on the same device now reloads patient-specific views. A two-account test with different prescriptions verified the final signed APK across sign-out and sign-in. Android Studio was installed and launched. The emulator test used ADB. IDE Run-button operation, physical-device hardware, actual notification delivery, speech recognition and live Gemini results remain unverified.

The updated `dist/Recovery-Companion.zip` passed ZIP integrity checks and contains a byte-identical copy of the v2-signed `dist/app-release.apk`. The updated kit SHA-256 is `e71a4539e79fce0e6d1014b8837584101e0368e74254393f56b2543650d016cb`. The synthetic server authorization test passed again on SQLite. The regenerated two-page sample handout was rendered and inspected for patient identity, review reason, meal and pagination.

On 2026-11-15 the signed APK passed the Android 15 emulator workflow in `tools/verify-android.py` with `RC_TEST_OFFLINE=1`. The synthetic patient signed in, saved a meal in airplane mode, and force-stopped and reopened the app while offline. Today displayed one pending entry. After reconnection the periodic sync delivered the meal exactly once to the authenticated clinic report. The patient then opened the linked care record and attention tracker. Physical phone, microphone, camera, reminder delivery and live Gemini behavior remain separate acceptance items.

The combined local release in `dist/Recovery-Companion.zip` contains the signed Android APK, the portable Windows runtime, the clinic launchers and the sample handout. On 2026-11-15, Android's apksigner verified the APK's v2 signature. The bundled APK matched the standalone release byte for byte. The extracted Windows runtime provisioned a synthetic clinic account, backed up the populated station, restored it into a fresh directory, and authenticated that account against the restored database. The verification used an empty Google API-key setting. The SHA-256 of this combined release is `AB1054768D31FABB34F26D9187F1C604B326DF70BA617F850C82D86CE9ABF23B`.

The synthetic HTTP integration workflow in backend/tests/test_workflow.py passed against fresh SQLite and PostgreSQL 18 databases. The test registers a patient, completes all four discharge steps, repeats prescription intake to check idempotency, provisions two clinics, checks direct API denials, exercises invitation consent and revocation, logs doses and meals, checks receipt replay, verifies rule labels, finalizes a checkup twice with the same ID, submits a linked amendment, reads the original snapshot and finds a late upload in the next report. Both empty-database migrations reached head with no schema drift.

The Android widget test covers the read-only checkup display. The final debug APK compiled and installed on an Android 15 emulator. A synthetic patient signed in, entered and reviewed a meal, saved it, and opened Records. An independently authenticated staff request found that meal in the linked patient’s report. The emulator home-screen capture is in docs/demo/patient-home.png. The clinic browser exercise used synthetic records, staff sign-in, report preparation, PDF output, a completed checkup and reprinting the older snapshot. The two PDF pages were rendered and inspected, and their extracted text checked for the patient, chart, clinical reason and meal.

The PostgreSQL 18 rehearsal now creates populated, unversioned legacy diary tables, adopts their schema, runs the clinic integration flow, takes a custom-format dump and restores it to a new database. It verifies historical identifiers, timestamps, values and a digest of the clinic ledger. Both pages of the sample PDF include the patient identity and page number. Open acceptance work includes a physical Android pass covering notifications, camera, voice and offline recovery, accessibility testing with assistive technology, and clinical and operational review before real patient use. The synthetic workflow covers a subset of the scenarios above.
