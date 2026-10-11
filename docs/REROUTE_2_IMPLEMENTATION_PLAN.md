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

## Phase 2 — Business APIs and tenant-scoped operations

### Objective

Expose the real supply-chain entity management layer and scenario execution API while enforcing stricter organization-level data isolation and role-aware access.

### Scope

- Create and manage suppliers, customers, warehouses, factories, and routes through the business API
- Create and run planning scenarios tied to a user organization
- Maintain planning-run history and recommendation comparison/explanation endpoints
- Enforce role and tenant access restrictions using the live DB-backed auth model
- Continue to use the real planner pipeline instead of mocked or duplicated business logic

### Backend changes

- Added organization-scoped auth bootstrap in `app/security/auth.py`
- Added `OrganizationEntityAccess` to enforce tenant boundaries at the database row level
- Updated `BusinessService` to scope entity list/get/create/update/delete operations to the current organization
- Kept scenario execution and planning-run storage tied to the real planner service and JSON-serializable payloads

### Tests and acceptance criteria

- Business CRUD routes work for the current organization
- Cross-organizational ID access is rejected with `403`
- Scenario execution creates a real planning run with a JSON-safe result payload
- Recommendation comparison and explanation endpoints return planner data without serialization errors

### Stable checkpoint

Phase 2 is considered complete when the business API and regression suite pass without planner regressions.

## Phase 3 — AI planning improvements

### Objective

Improve planner feasibility, reliability evidence, industry-aware decisions, deterministic scoring, and operational explanations without inventing missing evidence or changing persistent supply-chain data during simulations.

### Scope

- Enforce each industry's minimum supplier reliability in candidate eligibility
- Search alternate routes after a cheapest-path candidate fails CSP constraints
- Validate path consistency, route/resource capacity, inventory, deadlines, and path-derived metrics
- Calculate reliability risk from stored supplier values and route values only when present; label incomplete risk evidence explicitly
- Expose deterministic score weights, normalization, tie-breaking, and rejected-candidate reasons
- Apply one demand-spike quantity policy: ceiling fractional post-spike demand to whole units
- Distinguish infeasible requests from internal planner failures
- Keep disruption simulations isolated from the persisted database and base graph

### Evidence and policy decisions

- `IndustryProfile.min_service_level` is treated as the minimum supplier reliability for eligibility; this is based on the existing observed supplier reliability column, not a claim about end-to-end service fulfillment.
- The database has supplier reliability but no route reliability history. Missing route evidence remains unknown instead of receiving a default probability.
- Cost, delivery time, and risk use min-max normalization across the current feasible candidates. Scores are a deterministic weighted sum and are not comparable across candidate sets without that context.
- Fractional demand after a spike is rounded upward with `ceil` so planning never understates required whole units.
- No feasible route/candidate is a domain result (`409`); unexpected computation errors are not reported as client mistakes (`500`).

### Stable checkpoint

Phase 3 is accepted when the focused AI tests and full backend regression suite pass, the API contract reflects the evidence limits, and only intended Phase 3 files are committed.
