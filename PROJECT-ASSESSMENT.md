# Recovery Companion: initial assessment

Source review only. The application has not been built or run on this laptop.

## Verdict

There is a usable prototype foundation: Flutter screens, a FastAPI backend, database models, background jobs, and separated service code. The source does not yet establish a dependable product. Improve the core journey and its verification before expanding features.

## Concrete findings

- `mobile/lib/shared/services/api_client.dart`: the API address is hardcoded to an old LAN IP. Configuration is duplicated in `core/config/api_config.dart`.
- `backend/app/api/v1/clinician.py`: `mark_reviewed` loads a flag by ID without checking that its patient belongs to the authenticated clinician. The list endpoints do check assignment.
- `backend/app/core/security.py`: protected-route dependencies check role but do not reject refresh-token type. Refresh tokens contain the same role and subject, so those dependencies accept them as bearer credentials.
- `mobile/test/widget_test.dart`: the starter counter test references `MyApp`, while the app defines `RecoveryCompanionApp`. It does not verify this product's behavior.
- `backend/app/services/twin_service.py`: recovery templates are hardcoded. The file calls them evidence-based but supplies no references. The risk adjustment divides pain and fatigue by a larger risk multiplier, lowering expected scores despite its comment about slowing improvement. Creating a twin omits the computed mobility curve, and the read path falls back to the pain curve.

These are static findings, not runtime exploit or clinical validation results. No backend tests or CI workflow were found in the checked-out file inventory.

## Proposed direction

Target one clearly defined post-discharge patient group first. Make the main loop dependable: understand today's plan, record a check-in, record prescribed doses, review personal history, and share a useful summary with a care provider.

The home screen should make today's next action and completion state obvious. Patient and clinician views should show whether data was saved, synced, or reviewed. Recovery predictions need traceable justification and validation before they underpin product claims.

## Priority

1. Establish a reproducible local setup and run the app; fix authorization and token separation; replace the starter test with meaningful checks for those boundaries and the main journey.
2. Verify onboarding, daily check-in, medication logging, history, error recovery, and offline sync end to end.
3. Refine the interface around that journey and validate it with intended users. Reassess voice, food scanning, and predictive features after the core proves useful.

No usage, retention, user research, or clinical validation evidence was supplied. Product-market fit and clinical usefulness cannot be scored from this repository.
