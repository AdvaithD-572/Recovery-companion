# Proposed architecture and data contract

This document records the proposed architecture. The local release uses Flutter, FastAPI, a portable Windows clinic station and a role-scoped clinic portal. The default local database is SQLite. PostgreSQL migration and restore checks run against a disposable cluster. ACCEPTANCE.md records the verified scope, including the distinction between implemented features and proposals below.

## Components and trust boundaries

Android Flutter app -> authenticated FastAPI API -> PostgreSQL.
Clinic browser portal -> same API -> organization/role/episode-scoped queries.
API transaction -> durable job/outbox -> Celery/Redis -> optional notifications/analysis.
Private object storage -> authorized short-lived attachment/report downloads.

A clinic frontend is new work; its framework is not selected. Keep third-party provider credentials on the backend. A common database supplies our clinic portal; "sent to hospital" does not imply an existing external hospital system is connected.

## Proposed entities

| Entity | Purpose and required relationships |
| --- | --- |
| PatientProfile | Identity/contact; stable patient ID; age precision/DOB; corrections attributable. |
| Organization / StaffMembership | Clinic and active invited staff roles; no authority inferred from email or hospital name alone. |
| PatientClinicLink | Patient/clinic relationship, verification, sharing scope, grant/revocation timestamps, actor. |
| RecoveryEpisode | Patient, reason/procedure, dates, discharge context, care team, timezone; separate repeat admissions. |
| DischargeDocument | Episode, private object reference, uploader, source date, review state. |
| CarePlanVersion | Episode, version/effective interval, instructions, source, patient-reported/clinic-confirmed provenance. |
| PrescriptionVersion / DoseOccurrence | Historical prescription and scheduled instance; scheduled and as-needed semantics remain distinct. |
| DoseEvent | Occurrence/version, taken/skipped/correction, event time, received time, actor, client event ID. |
| DailyObservation / MealEvent | Episode, original event date/time precision, values/items, note, source, corrections and attachments. |
| AnalysisResult | Input IDs/versions, provider/rule version, checked/unavailable/pending/not-applicable state, result and provenance. |
| ClinicVisit / Checkpoint | Episode, staff actor, occurred_at, boundary_at, draft/finalized/cancelled state, finalized_at and permitted summary. |
| ClinicalAddendum | Immutable linked amendment with actor/time/reason; preserves original signed content. |
| ReportSnapshot | Episode, interval, checkpoint IDs, as-of time, included record revisions, algorithm version, generated-by and private output. |
| AuditEvent / OutboxEvent | Attributed access/export/write/role changes; reliable after-commit processing without raw medical payloads in ordinary logs. |

Existing Patient, Clinician, Prescription, DoseLog, DailyLog, FoodLog, DigitalTwin, EscalationFlag, Reminder and ConsentLedger require incremental mapping/migration, not blind replacement. Add constraints and indexes for scoped lookup and uniqueness. Preserve UUIDs and existing history where feasible.

## Proposed record lifecycle

- Onboarding: draft -> reviewed -> active episode; resumable saves and explicit unknown fields.
- Extracted document/voice: draft -> user review -> confirmed patient submission; clinic confirmation is separately attributable.
- Patient events: pending local -> received -> accepted, or needs resolution; corrections append linked revisions.
- Visit: draft -> finalized or cancelled. Finalize atomically creates one checkpoint; idempotency and concurrent-finalize protection are required.
- Finalized records: unchanged original + addendum; no in-place deletion/edit by a patient.
- Clinic link: pending verification -> active -> revoked/ended. Ended links lose new access according to the chosen sharing policy; revocation does not erase legal records or already printed paper. The first build denies new portal reads and downloads once the link ends.

Administrative attendance and a clinical checkup are separate facts. Do not let a receptionist-only appointment marker reset clinical reporting under R1: a clinician finalizes the checkup.

## Time and interval semantics (proposed default)

Store timestamped events in UTC, retain episode timezone, original local date/offset and timestamp precision. A date-only questionnaire must remain date-only, not gain a fabricated time. Keep occurred_at, received_at, corrected_at and finalized_at distinct.

Define since-last-checkup as a half-open interval [start, end):
- First report starts at discharge/episode start.
- Later report starts at the previous finalized checkpoint boundary.
- Preview end defaults to a captured server as-of timestamp. When closing a visit, capture its explicit boundary; print time alone never sets it.
- Each exact-time event belongs to one adjacent interval. At the boundary it belongs to the next interval.
- Date-only events on a checkpoint date appear in a separately labeled "boundary-day records, time unknown" group. Do not silently omit or arbitrarily assign them; mark overlap if they are shown for context in adjacent reports.
- Backdated visits and out-of-order boundaries require a reviewed correction workflow. Proposed initial behavior rejects ordinary non-monotonic checkpoint finalization.

Freeze report content by included record/revision IDs and as-of receipt cutoff. Reprinting a snapshot preserves its data. A refreshed report creates a new snapshot. Late uploads that occurred before a prior boundary appear in a "late additions/corrections since the previous report" section on the next report, with both timestamps and original interval. Do not move the patient's event date to make it fit.

## Descriptive calculations

Medication adherence uses scheduled occurrences within the report interval and effective prescription version. Show taken, explicitly skipped and unreported counts separately. State denominators and any late-dose threshold; the threshold is still a decision. Exclude as-needed medication from scheduled-dose adherence. Do not infer ingestion from a reminder or a tap retry.

Food timeline records what the patient reported. Agreement with an explicit diet instruction requires an interpretable, versioned rule or a patient/staff report, with provenance. Never imply a meal photo confirms its complete ingredients.

Charts use consistent metric directions, visible gaps and requested date ranges. A reference range or prediction is a separate typed series with method version and provenance. Clinical thresholds and outcome predictions are not specified here.

## Candidate API contracts

Paths below are proposed, not existing endpoints. Preserve current v1 clients through a deliberate compatibility/migration plan.

| Resource operation | Contract |
| --- | --- |
| Episode onboarding draft/review/complete | Typed schemas, required-field errors, optimistic version, resume token/state. |
| Patient event submit/sync | Client-generated event ID, episode, event time/precision, payload; per-item accepted/duplicate/conflict/rejected result. |
| Episode timeline query | Authorized patient/clinic scope, interval, cursor pagination, included correction/version metadata. |
| Clinic patient search/link | Authorized clinic membership and verified linkage; search is not authorization. |
| Visit create/finalize/addendum | Required role, expected version, idempotency key; patient read-only GET. |
| Report preview/generate/read/export | Episode and interval/checkpoint IDs, as-of timestamp, record versions; audited generation/download. |
| Care-plan confirm/version | Separate patient-reported draft from staff confirmation; effective dates and author. |
| Access/consent change | Attributed grant/revoke, scope, version and enforcement at every protected route. |

Never accept actor ID or organization scope from the body without deriving/validating it against the authenticated principal. Access tokens and refresh tokens have separate accepted uses. Staff enrolment is invitation/verification controlled, not open self-registration into trusted clinical roles.

## Failure, security and operator design

- Persist patient events independently of enrichment availability. Dispatch after transaction commit via outbox or equivalent verified mechanism.
- Enforce database uniqueness and idempotency; request retries cannot decrement stock or add a meal twice.
- Offline data is encrypted where supported, account-scoped, and protected against cross-account replay on logout/account change. Let users resolve unsynced data explicitly.
- Persist errors and retry state; distinguish no data, no flags, unavailable analysis, and failed synchronization.
- Use transport encryption outside explicit local development, managed secrets, least-privilege DB/storage, private files, protected downloads and audit access.
- Document consent/sharing effects, retention, backup/restore and deletion/archive behavior before live use.
- Audit profile access, report generation/download, checkpoint and care-plan changes, failed authorization and membership changes.
- Monitor queue lag, notification delivery state, sync failures, report failures and suspicious access without leaking medical content into ordinary logs.
- Notification delivery is not clinician acknowledgement. No unattended 24/7 response promise.
- Provider interfaces must have validated inputs/outputs and explicit failure states. Select current provider APIs and clinical sources only after documentation research and budget decisions.

## Migration approach

Inventory existing data first. Introduce versioned Alembic migrations and a synthetic migration rehearsal. Backfill provisional episodes, preserve existing IDs/source timestamps, mark unknown source/clinic data as unknown, and quarantine unmappable records. Test PostgreSQL constraints and report counts before enabling the new portal. Do not manufacture clinical confirmations or patient consents during a backfill.

## Station directory and account lifecycle

The administrator is a separate local identity with its own token role. Directory reads and clinic lifecycle writes are audited. Clinic display names can be reused after deletion. Each new clinic has its own immutable scope for memberships, links, invitations and clinical records. Migration registers existing clinic scopes in place. Patient self-deletion verifies the password, removes active profile fields and diary data, ends sharing, releases the login email, and leaves a closed identifier for signed history and audit. Existing backups and independently saved exports remain outside the active database operation.
