# Recovery Companion: agent instructions

## Current authorization

Implementation and local verification are authorized. Installation of build and test tooling is authorized.

## Product purpose and reading order

Build an Android recovery diary connected to a clinic laptop portal. A patient records discharge instructions and recovery events. Authorized clinic staff retrieve the correct patient, prepare a printable report since the previous completed checkup, and record a new checkpoint. Patients can view clinic checkup records but cannot edit them.

Read:
1. PRODUCT.md: canonical capability contract, confirmed requirements, proposed rules, and open decisions.
2. DISCOVERY.md: source inventory and gaps; code presence is not proof of working behavior.
3. ARCHITECTURE.md: proposed interfaces, ownership, timestamps, report boundaries, and data evolution.
4. IMPLEMENTATION_PLAN.md: dependency-ordered delivery milestones.
5. ACCEPTANCE.md: observable scenarios and evidence requirements.

PROJECT-ASSESSMENT.md is an earlier source review. PRODUCT.md takes precedence for current product intent. README.md explains how to run the local demonstration. ACCEPTANCE.md records verification.

## Working method

- Inspect -> implement -> test -> fix -> validate -> finalize, within the user's active scope.
- Search for applicable nested AGENTS.md before editing. Preserve unrelated work.
- Discover and read relevant skills before using them. Briefly name each applied skill and record material decisions and verification evidence.
- Prefer existing suitable Flutter and FastAPI code; do not rewrite or upgrade dependencies solely because they are old.
- Select the smallest set of skills that helps the current milestone. Candidate lanes: product-capability, healthcare-emr-patterns, api-design, security-review, database-migrations, accessibility, dashboard-builder, flutter-dart-code-review, browser-qa, verification-loop.
- Do not spawn subagents unless the user or applicable instructions explicitly request delegation.
- Keep unresolved product decisions visible. Do not silently turn proposals into confirmed requirements.
- Update the existing canonical documents instead of creating duplicate plans.
- Do not claim perfection, production readiness, clinical validity, or end-to-end success without corresponding evidence.

## Invariants for future implementation

- Enforce patient ownership, clinic membership, staff role, and care-episode access on the server for every record and report operation.
- A hospital name string, patient identifier, QR code, or knowledge of a record UUID does not grant access.
- Patients may submit and correct their own observations with history. They cannot create, modify, finalize, or delete clinic checkup records.
- Keep patient-reported prescriptions and diet instructions distinguishable from clinic-confirmed instructions. Scanned/AI extracted text requires review before activation.
- Preserve signed/finalized records; corrections use linked amendments. Log reads, exports, clinical writes, and permission changes.
- Printing does not advance a checkpoint. Closing an authorized clinic visit does; repeat requests must not create duplicate checkpoints.
- Separate event time, receipt time, and audit time. Do not hide late uploads or treat missing entries as proof of skipped medication.
- Keep descriptive adherence, recorded symptoms, reference curves, and predictions visibly distinct. No invented causal food/medication recovery score.
- AI is optional enrichment. Core logging, synchronization, clinic review, and report generation must work without an AI provider.
- An unavailable interaction check is unknown, not "safe." Show the actual analysis status and retain the saved meal.
- Never change a prescribed dose or treatment on the basis of app-generated suggestions.
- Protect uploads, reports, local patient caches, and credentials. Do not include real patient data or secrets in examples, tests, logs, screenshots, or commits.
- Never say the care team has received or reviewed something unless the corresponding state is recorded.
- Do not silently drop the existing voice, reminders, food, medication, trends, or offline workflows; inventory, repair, or explicitly document their deferred status.

## Validation and delivery

Use ACCEPTANCE.md to choose meaningful checks. Verify server authorization directly, including denied requests; hiding a button is insufficient. Test PostgreSQL behavior when PostgreSQL is the target. Inspect generated report text and rendered pages. Distinguish mocks, local integration, browser testing, emulator testing, physical Android testing, and hosted verification.

Before finishing, inspect the diff, report what changed and why, state what was actually tested, and name remaining acceptance gaps. Do not deploy, publish, push, send patient data externally, or purchase services without applicable user authorization.
