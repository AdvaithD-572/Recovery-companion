# Implementation plan

Implementation was authorized after planning. The local build includes the Android patient diary, FastAPI clinic desk, print reports and checkpoint workflow. ACCEPTANCE.md records verification and outstanding work.

## M0: settle the capability and design

Inputs: PRODUCT.md and DISCOVERY.md.
Use the attention tracker, clinician sign-off and patient-confirmed clinic invitation defined in PRODUCT.md. Confirm target users/conditions, deployment goal, report format, budget and languages. Produce patient and clinic journey wireframes, including first-use, empty, offline and error states. Keep this decision log in PRODUCT.md.

Exit: agreed actor matrix and graph interpretation; no speculative clinical claims treated as requirements.

## M1: reproducible foundation and access controls

- Verify local Flutter/Android, backend, PostgreSQL and Redis setup; capture actual build/runtime failures.
- Repair the hardcoded/duplicated API configuration, dependency/build issues, invalid ignore pattern and starter test when code work is authorized.
- Separate access and refresh token validation; add staff membership/role and patient/clinic access guards.
- Add typed onboarding validation; test denied requests and ownership on existing routes, especially flag review.
- Establish migrations, synthetic fixtures, meaningful backend tests and appropriate CI checks.
- Keep deployment and credentials separate from local setup.

Exit: reproducible local setup and relevant analyzer/tests pass; negative authorization tests pass. A running app alone is insufficient.

## M2: episodes, discharge setup and clinical provenance

- Add episodes, clinic links, resumable onboarding and structured instructions.
- Capture all information groups in PRODUCT.md with unknown/optional states, units, dates and validation.
- Integrate prescription entry into onboarding, including document extraction drafts and explicit confirmation.
- Add source/author/confirmation state and care-plan versions. Preserve old records through tested migrations.
- Test interrupted onboarding, repeat submit, missing prescriptions, unreadable scan, allergies unknown versus none and non-surgical discharge.

Exit: a synthetic patient completes and resumes setup without fabricated information or duplicate records.

## M3: dependable Android tracking

- Implement the chosen home navigation; keep Today focused on the next action.
- Align manual/voice check-ins, metric meanings, notes and date filters.
- Add scheduled-dose occurrences, taken/skipped/unreported distinctions, as-needed tracking and stock handling with idempotency.
- Repair food scan/review/save lifecycle; manual logging works without AI. Preserve failed/unknown interaction-analysis status.
- Make offline persistence durable, encrypted/account-scoped, restart-safe and visibly synchronized.
- Verify reminder permissions and behavior; keep provider/service delivery evidence separate from device evidence.
- Test corrections without destroying history and without silently suppressing clinically relevant flags.

Exit: a synthetic multi-day episode retains correct symptom, medication and food history through retries, offline restart, reconnect and account change.

## M4: clinic laptop portal and checkup records

- Select a maintainable browser stack based on actual scope; build invited staff login and authorized clinic patient search.
- Add patient identity confirmation, episode history, care-plan provenance and freshness/gap indicators.
- Build administrative visit draft, authorized completion and immutable finalized checkpoint with amendments.
- Implement patient read-only access to clinic records in Android.
- Add staff actions and export/read audit events.

Exit: permitted staff find the correct patient; another clinic and the patient cannot perform protected writes; concurrent retries produce one finalized checkpoint.

## M5: interval report and print

- Implement the canonical interval query and descriptive calculations once, reused by preview/PDF.
- Add summary plus complete interval detail, attachments index, late additions, missing data and plan versions.
- Produce print preview and protected downloadable output. Default A4/grayscale until user preference is settled.
- Bind report IDs to immutable input versions and as-of timestamps.
- Verify first visit, subsequent visit, repeated print, empty and long histories, timezone boundaries and late synchronization.

Exit: the patient-to-clinic-to-doctor workflow succeeds with exact expected fixture counts and inspected print pages. Printing never advances a checkpoint.

## M6: food/medication visualization and optional intelligence

- Implement the chosen G1 graph contract with explicit labels, missing data and uncertainty.
- Preserve factual recovery trends and event context even if prediction is unavailable.
- Apply versioned, reviewed rules to logged doses and meals. Persist the matched rule, assessed event, status, reason and uncertainty for report reproduction.
- Optional summaries reference source records and never replace the full factual report.
- Validate every supported voice/language and provider failure path; do not expand language claims from source strings alone.

Exit: charts match fixture values, UI and report agree, method provenance is visible, and unsupported predictions remain unavailable rather than fabricated.

## M7: integrated validation and release preparation

- Execute ACCEPTANCE.md across backend, clinic browser, print artifacts and Android.
- Inspect small screens, large text, TalkBack, keyboard use, contrast and non-color chart labels.
- Verify migration rehearsal, backup/restore, private file access, redacted logs and operational failure visibility.
- Document hosting, country/jurisdiction, retention, clinical-content review and deployment requirements appropriate to P1.
- Record actual evidence and unresolved gaps. Ask for deployment/publication authorization only when a concrete tested release is ready and such authorization is still needed.

Exit: claimed delivery level matches evidence. A demo can ship with clearly labeled synthetic data; real-patient readiness has additional unresolved gates.

## Implementation discipline

For each milestone, record changed files, decisions, relevant test results, screenshots/report artifacts where applicable and remaining failures. Use meaningful tests for authorization, history, synchronization, intervals and reports. Do not test incidental widget layout or mirror implementation just to increase test counts. Re-run only affected checks until new evidence justifies broader verification.

No duration, spending, full rewrite, paid provider choice or public deployment is assumed.
