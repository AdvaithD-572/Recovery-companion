# Recovery Companion: capability contract

The local implementation follows this capability contract. ACCEPTANCE.md records verification and outstanding work.
This is the canonical scope. "Confirmed" means stated by the user. "Proposed" means an engineering/product default pending clarification. "Open" means not decided; it is not permission to invent behavior.

## Capability

An Android patient app captures discharge details and day-to-day recovery history. A connected clinic laptop portal lets authorized staff find the patient, review records since the previous completed checkup, print a doctor-readable report, and record the next checkup. The patient can view clinic checkup records but cannot edit them.

## Confirmed requirements

- Android patient app.
- The station administrator creates and deletes clinic profiles and can read all active patient profiles. Patient web self-service supports registration and deletion of the patient’s own profile. Signed records, prepared reports and audit history survive profile deletion.
- Thorough setup: identity/demographics, height/weight, condition/procedure, doctor-provided prescriptions and food advice, and the related recovery details.
- Home navigation and patient tracking features based on the existing code, including medication and food logging.
- A dated attention tracker for skipped medication and meals, showing which recorded events raise a concern.
- Patient data persists in a database and is available to the connected clinic/hospital.
- Clinic staff use a laptop to retrieve the patient and print all relevant history since the last checkpoint/checkup for the doctor.
- Clinic-side checkup/checkpoint recording; patient view-only access to those records.
- The user subsequently authorized implementation, free local tooling and a portfolio release with a blank Google API-key setting.

## Actors and surfaces

| Actor | Surface | Proposed capability boundary |
| --- | --- | --- |
| Patient | Android | Own profile, discharge setup, patient-reported prescriptions/instructions, observations, reminders, history, sharing status; view clinic records. |
| Receptionist / clinic staff | Laptop browser | Authorized patient lookup, identity confirmation, report preparation/print, administrative visit recording. No implicit power to sign clinical findings. |
| Clinician | Laptop browser | Authorized clinical review, confirmed care-plan changes, checkup completion and clinical amendments. Clinician sign-off advances the checkpoint. |
| Clinic administrator | Laptop browser | Invited staff membership/roles and patient linking; administrative role alone does not imply unrestricted clinical access. |
| Caregiver | Undecided | No shared password or delegated access by default. Define consent/authority before adding this role. |

The user named a receptionist or clinician as the clinic operator. Selected first-build default: receptionists prepare and print reports and record attendance. A clinician finalizes the clinical checkup and advances the checkpoint.

## Patient onboarding

"Everything" means comprehensive relevant information, not forcing a recovering patient to answer every possible field. Proposed grouped, resumable onboarding with explicit required/optional/unknown states:

| Group | Capture |
| --- | --- |
| Identity | Full name, DOB or age with source/precision, contact/login details, language, timezone. Do not invent an exact DOB from an age. |
| Measurements | Height and weight with units and measurement date; distinguish unknown from zero. |
| Recovery episode | Clinic, admission/discharge and procedure dates when known, reason for hospitalization, diagnosis/procedure as documented, treating provider, discharge summary attachment. Support non-surgical discharge. |
| Background | Allergies including unknown/none distinction, relevant conditions, existing medicines, relevant lifestyle and living support, emergency contact. |
| Medicines | Name, strength, dose/unit, route, scheduled versus as-needed use, frequency/times, start/end, food/timing instructions, stock/refill details, source document and confirmation state. Never fabricate unreadable directions. |
| Care instructions | Doctor/dietitian food instructions, restrictions, hydration/activity/rest/wound-care instructions where provided, duration, follow-up advice/contact details, source and entered-by identity. |
| Connection and review | Clinic linking and sharing authorization, attachment review, summary confirmation, ability to return and complete unknown items. |

Final mandatory fields, supported ages, and procedure-specific questions are open. Preserve existing useful questions without assuming every one is clinically required. Extracted attachments are drafts; confirmation is explicit and traceable.

## Patient daily workflow

Proposed main destinations: Today, Medicines, Food, Progress, and Records; profile/settings and voice reachable without crowding the primary navigation. Exact labels and visual design remain open.

- Today: next scheduled actions, dose and check-in completion, relevant care instructions, sync/connection status.
- Check-in: pain, sleep, appetite, mood, fatigue, mobility and note; review swelling and adherence fields already present in schemas. Score endpoints and meaning must be consistent, including energy versus fatigue.
- Medicines: current plan, each scheduled dose, taken time or explicit skipped state/reason, stock/refill reminders, history. Unreported is distinct from skipped. As-needed use is represented separately.
- Food: manual entry plus optional image assistance; meal time/type/items, correction before save, food instructions, clearly sourced cautions and analysis status.
- Progress: measured/self-reported symptom charts and descriptive medication/food history, date filters, visible missing days.
- Records: discharge documents, care-plan versions, clinic checkups/checkpoints and their amendments. Clinic-authored records are read-only to patients.
- Reminders: medicine, water, food, activity, check-in preferences and delivery/permission status. These do not override the prescribed plan.
- Voice: preserve English/Hindi/Telugu/Tamil pathways as candidates, with review-before-submit and manual fallback. Language parity needs actual validation.
- Offline: save eligible logs locally, show pending state, synchronize without duplicates, and retain original event dates.

No existing feature is silently removed from scope. Provider-dependent features may be staged, but their actual availability and acceptance status must be explicit.

## Attention tracker

G1 is settled. The patient and clinic need to see whether a recorded event needs attention. Show skipped doses and logged meals on a dated timeline with a text label and a reason for each assessment. Example with synthetic data: a confirmed skipped dose matches a clinic-configured rule for prescription A. Show the affected dose, the rule's attention level, the matching condition and any clinic-authored instruction. A meal entry can similarly match an explicit food restriction or a reviewed interaction rule.

Use “Critical” only when a reviewed rule explicitly assigns that level for the available facts. Distinguish “Needs review”, “No configured concern found” and “Unable to assess”. An unlogged dose stays unreported. If the medicine, meal ingredients, or applicable rules are unknown, show the uncertainty. Record the source and version of each rule and reproduce the assessment and reason in the clinic report. Clinical thresholds require a qualified author before use with patients.

## Clinic workflow

1. Staff signs in with clinic-scoped access.
2. Search authorized patients by clinic patient ID and permitted identifiers; confirm at least two displayed identity attributes before reporting.
3. Open the recovery episode and prior checkup, with latest sync time, source labels, missing days, active plan and amendments.
4. Prepare the since-last-checkup report; preview before printing.
5. Print for the doctor. A print operation does not create or complete a checkup.
6. Authorized staff records visit date/time, administrative status and any permitted findings/instructions; a clinician signs clinical content before finalization.
7. Complete the visit to create the next checkpoint atomically; patient can view the record and later amendments.
8. Future reports start from the latest completed checkpoint. Draft/cancelled visits never silently move the boundary.

Proposed clinic portal is part of this product with shared backend storage. Integration into an existing hospital system is a separate open decision; do not claim that data has been sent to an external EHR.

## Report contract

The short opening summary supports a busy doctor; an attached chronological detail section retains all records in the interval. It is not just an AI summary.

Include patient/episode identity, previous checkpoint, exact interval/timezone, generation/as-of time, data freshness, condition/procedure/discharge context, allergies, care-plan versions, medication schedule and taken/skipped/unreported counts, dated symptoms and charts, meals and recorded advice/cautions, patient notes, missing/unavailable data, and relevant clinic entries/amendments. Show source and confirmation state. Include full interval detail and an attachment index; raw voice recordings and full-size images are not automatically printed. Explicit attachment selection can be a later feature.

Number pages, repeat patient identifiers and report ID, and ensure charts work in grayscale. First follow-up begins at discharge/episode start. No logs produces a useful "no records" report, not an error or invented data. Technical output defaults: browser print and downloadable PDF, A4; final format remains open.

## Constraints and invariants

- Patient ownership and clinic/role/episode authorization are server-enforced.
- Clinic sharing is an explicit, auditable link; no global patient lookup by unauthenticated users.
- Distinguish database synchronization, clinic availability, report export, and actual staff review.
- Finalized clinic records cannot be overwritten. Preserve attribution, timestamps and amendments.
- Version prescription and diet instructions so a future change cannot rewrite earlier adherence.
- Preserve gaps, conflicting records, failed analysis, late uploads and corrections visibly.
- AI failure cannot block core logging or factual reporting. Clinical recommendations require separate reviewed rules/content.
- Use synthetic data for development. Define jurisdiction, retention, consent and hosting before real-patient release; no compliance certification is implied.
- No continuous monitoring or emergency response promise is established.

## Non-goals for this planning scope

No application-code changes, deployment, purchases, or external patient-data transfer. The proposed product is not a full EMR, appointment/billing platform, autonomous diagnosis system, or automated prescribing tool. iPhone support is not confirmed.

## Selected first-build defaults and remaining decisions

R1: Reception records attendance and prints; clinicians finalize checkups. C1: The clinic issues an expiring, single-use invitation tied to an episode. The signed-in patient confirms the named clinic and sharing scope. The server verifies the match and active staff membership. Revocation blocks future portal access and downloads. Start with one clinic per episode. Develop first with synthetic records, our own laptop portal, Android, A4 printing and a local setup without paid services. Production hosting and clinical rule ownership remain deployment decisions.

| ID | Decision | Blocks |
| --- | --- | --- |
| P1 | Demo, submission, pilot, or production; supported ages, conditions and country | Release claims, mandatory fields, clinical review and privacy decisions. |
| T1 | Own portal only or integration with an existing hospital system? | External integration design. Proposed first build uses our own portal. |
| B1 | Hosting/provider budget, available credentials, deadline and deployment ownership | Provider selection and release schedule; no spending assumed. |
| U1 | Branding, language priorities, Android baseline and print/report preferences | Final design and device acceptance matrix. |
| D1 | Correction/backdating policy, checkpoint interval semantics and retention | Final historical data/report contract. Proposed defaults are in ARCHITECTURE.md. |

Handoff: ready for product/architecture review, not direct unrestricted implementation. A later request to implement may authorize foundation work while unresolved clinical, role, sharing and release decisions remain explicitly gated. No dates or clinical validity are promised by this plan.
