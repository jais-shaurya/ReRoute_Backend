# ReRoute 2.0 Implementation Plan

## Baseline status

The verified baseline included the planner foundation, service orchestration, core graph/AI pipeline, and API contract already in use. The remaining work is focused on completing the industry configuration and planner enforcement layer before moving to broader API and frontend work.

## Phase 1 — Complete and enforce industry customization

### Objective

Ensure the planner applies meaningful, validated industry constraints without altering the underlying AI execution flow.

### User-visible outcome

Users can select a supported industry profile; invalid profiles are rejected; valid profiles influence default planning behavior and feasibility thresholds; the planner keeps the same AI pipeline while enforcing profile-specific rules.

### Scope

- Validate industry configuration on the backend
- Apply sensible default planning settings per profile
- Enforce maximum disruption thresholds and service-level feasibility rules
- Preserve the existing AI algorithms and planner interfaces
- Provide clean validation errors for missing or invalid configurations
- Verify valid and invalid profile scenarios

### Backend changes

- Added backend profile validation in `app/config/industry.py`
- Added profile-aware planning checks to `app/services/planner.py`
- Added request validation support for the `industry` field in `app/schemas/planner.py`
- Passed industry into the planner API route in `app/api/planner.py`

### Frontend changes

- No frontend implementation required in Phase 1 because the backend contract is the gating requirement.

### Database migrations and API contract

- No data-model migration required for this phase.
- The planner contract now accepts an optional `industry` value on the request model and validates it server-side.
- The default profile is `retail` when no profile is specified.

### Dependencies

- Depends on the existing planner pipeline and scoring model.
- Must remain stable before broader business API expansion.

### Tests and acceptance criteria

- Supported profiles are recognized and default settings are applied
- Unknown profile names are rejected with a clear error
- Demand spikes above the configured max are rejected for the selected industry
- Existing planner behavior remains intact for valid requests

### Stable checkpoint

Phase 1 is considered stable only when the targeted planner and API tests pass without regressions.

### Checklist

- [x] Industry profile validation module added
- [x] Default industry profile behavior introduced
- [x] Demand-spike threshold enforcement added
- [x] Request validation for unknown profiles added
- [x] Planner API and service integration updated
- [x] Targeted regression tests passed

### Risks / decisions

- Nonessential profile customization was intentionally deferred in favor of sensible defaults and enforceable guardrails.
- No breaking API change was introduced beyond adding a supported optional `industry` field with validation.
