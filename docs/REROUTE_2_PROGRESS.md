# ReRoute 2.0 Progress

## Phase 1 — Complete and enforce industry customization

### Scope

- Validate backend configuration for supported industry profiles
- Apply sensible defaults and profile-specific planning guardrails
- Preserve the existing AI planner contract and recommendation flow
- Verify planner and API regressions

### Checklist

- [x] Baseline planner and API foundations confirmed
- [x] Industry profile module implemented
- [x] Default profile behavior set to `retail`
- [x] Invalid or unsupported profiles rejected
- [x] Excessive demand-spike values rejected for profile-specific limits
- [x] Planner request model updated to accept `industry`
- [x] Backend planner service validates the selected profile
- [x] API route passes industry through to the service
- [x] Targeted tests passed

### Files changed

- `app/config/industry.py`
- `app/config/__init__.py`
- `app/schemas/planner.py`
- `app/services/planner.py`
- `app/api/planner.py`
- `scripts/test_industry_config.py`

### Database migrations

- No new schema migration required for this phase.

### API changes

- Added optional `industry` request field to the planner request model.
- Accepted alias `industry_profile` as part of validation for compatibility.
- Enforced profile-aware planner validation before executing scenario planning.

### Commands used

- `cd d:\ReRoute\ReRoute_Backend; .\venv\Scripts\python.exe -m pytest -q scripts/test_industry_config.py scripts/test_planner_schema.py scripts/test_planner_service.py`
- `cd d:\ReRoute\ReRoute_Backend; .\venv\Scripts\python.exe -m pytest -q scripts/test_planner_api.py`

### Actual test results

- `17 passed in 6.81s`
- `8 passed in 7.24s`

### Known limitations

- This phase intentionally uses sensible defaults rather than adding deep, organization-specific business rules that would otherwise delay execution.
- Full organization-scoped profile persistence is left for later phases when the broader business API layer is implemented.

## Phase 2 — Business APIs and tenant enforcement

### Scope

- Add organization-aware business entity management for suppliers, customers, warehouses, factories, and routes
- Add scenario execution and history endpoints backed by the real planner
- Enforce cross-tenant restrictions and role checks on the business API
- Ensure all persisted planning-run payloads are JSON serializable for retrieval and comparison

### Checklist

- [x] Business API bootstraps and auth context created
- [x] Organization-scoped entity access table added
- [x] Supplier/customer/warehouse/factory/route list and create operations scoped to the current organization
- [x] Scenario execution stores real planning data and recommendation payloads
- [x] Recommendation comparison and explanation endpoints return real planner outputs
- [x] Cross-organization access rejected with `403`
- [x] Business API regression tests added and passing

### Files changed

- `app/database/models.py`
- `app/security/auth.py`
- `app/services/business.py`
- `app/api/business.py`
- `scripts/test_business_api.py`

### Commands used

- `cd d:\ReRoute\ReRoute_Backend; .\venv\Scripts\python.exe -m pytest -q scripts/test_business_api.py`
- `cd d:\ReRoute\ReRoute_Backend; .\venv\Scripts\python.exe -m pytest -q`

### Actual test results

- `7 passed in 101.69s` for the business API test set
- `93 passed in 142.93s` for the full backend regression suite

### Current status

Phase 2 is now implemented and verified against the live database and planner service, with tenant-scoped access enforced at the service level and the API contract documented accordingly.

### Git and checkpoint state

- Branch: local working state, no destructive operations performed
- Stable checkpoint reached: yes
- Current next step at that checkpoint: proceed to Phase 3 AI planning improvements

## Phase 3 — AI planning improvements

### Acceptance checklist

- [x] Industry minimum supplier-reliability constraint affects candidate eligibility
- [x] CSP checks path consistency, observed capacities, inventory, deadlines, and route-derived cost/time
- [x] CSP searches alternate paths after a rejected cheapest path and retains data-backed rejection reasons
- [x] Missing route reliability remains unknown; no synthetic route prior is used
- [x] Risk response marks incomplete evidence and explains supplier-only risk
- [x] Scoring validates weights and exposes the weights/formula and deterministic tie breaks
- [x] Demand spikes consistently round fractional whole-unit demand upward
- [x] Infeasible plans use a dedicated domain exception and `409`; internal planner errors remain `500`
- [x] Disruption simulations are verified not to mutate the base graph or persisted supplier availability
- [x] Focused Phase 3 and full regression suites pass on final code
- [x] Phase 3 files committed as a stable checkpoint

### Final verification

- Focused AI/planner command: `..\ReRoute_Backend\venv\Scripts\python.exe -m pytest -q scripts/test_astar.py scripts/test_bayesian_risk.py scripts/test_csp.py scripts/test_disruption.py scripts/test_graph.py scripts/test_industry_config.py scripts/test_planner_quantity.py scripts/test_planner_schema.py scripts/test_planner_service.py scripts/test_planner_api.py scripts/test_recommendation.py scripts/test_scoring.py`
- Focused result: `97 passed in 30.33s`
- Full backend command: `..\ReRoute_Backend\venv\Scripts\python.exe -m pytest -q`
- Full backend result: `106 passed in 160.32s`
- Warnings match the pre-change baseline: FastAPI startup-event deprecation and `test_database_connection` returning a value.

### Changed AI/planner surfaces

- `app/ai/csp.py`
- `app/ai/bayesian_risk.py`
- `app/ai/graph.py`
- `app/ai/scoring.py`
- `app/ai/disruption.py`
- `app/ai/recommendation.py`
- `app/config/industry.py`
- `app/services/planner.py`
- `app/api/planner.py`
- `app/schemas/planner.py`
- `app/services/planner_serializer.py`

### Known evidence limits

- The database provides supplier reliability but no route reliability history. Route and combined stockout probabilities are therefore returned as `null` for plans that include routes without observed reliability; `plan_risk` is explicitly partial and uses supplier evidence only.
- The configured profile service-level threshold is applied to stored supplier reliability as a feasibility proxy. It is not presented as measured end-to-end service-level performance.
- The Phase 2 identity-header limitation remains: identity headers require a trusted upstream auth layer and are not cryptographic authentication.
