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

## Phase 4 — Backend security and quality hardening

### Acceptance checklist

- [x] Signed 15-minute Bearer tokens replace identity and role headers
- [x] Passwords use Argon2 hashes; legacy accounts without hashes fail login
- [x] Missing/weak token signing configuration fails closed
- [x] Planner and business routes require verified active users
- [x] Persisted database roles control access; only admins provision users and the API cannot assign admin
- [x] Tenant scope covers entity CRUD, scenarios/execution, planner graph, run history, comparison, and explanation
- [x] CORS uses exact allowlisted origins, limited methods/headers, and no credentialed wildcard
- [x] Authentication errors are generic; passwords/hashes are not returned
- [x] Alembic migration preserves legacy rows, adds nullable password hashes, and avoids ambiguous multi-tenant backfill
- [x] Startup no longer creates schema or a default privileged user
- [x] Operator provisioning path exists for initial/legacy administrator credentials
- [x] Focused security and migration tests pass
- [x] One final full backend regression run passes
- [x] Phase 4-only files committed as a stable checkpoint

### Migration status

- Live backend database was at Alembic-unversioned legacy state with 1 organization and 75 entity-access rows.
- `alembic upgrade head` applied revisions `20261011_0001` and `20261011_0002`.
- Verified head: `20261011_0002`; `app_users.password_hash` is present.
- Before migration row counts: organizations 1, users 1, suppliers 21, customers 8, warehouses 4, factories 2, routes 40, tenant access 75. After the final regression suite: organizations 1, users 1, suppliers 27, customers 8, warehouses 4, factories 2, routes 40, tenant access 81. Six supplier/access additions were test-created integration data; existing rows were preserved and migration seeded no duplicate links.

### Focused verification

- Command: `..\ReRoute_Backend\venv\Scripts\python.exe -m pytest -q scripts/test_security.py scripts/test_migrations.py scripts/test_business_api.py scripts/test_planner_api.py`
- Result: `25 passed in 68.59s`

### Final regression

- Command: `..\ReRoute_Backend\venv\Scripts\python.exe -m pytest -q`
- Result: `114 passed in 100.54s`
- Remaining warning: `scripts/test_database.py::test_database_connection` returns a value instead of asserting; this warning existed before Phase 4.
- Baseline before Phase 4: `93 passed`; no pre-existing failing tests were observed.

### Deployment requirements and remaining limitations

- Set `REROUTE_AUTH_SECRET` to a high-entropy secret of at least 32 bytes through a deployment secret manager. The current local environment did not contain it; authenticated production requests therefore remain unavailable until set.
- Set `REROUTE_CORS_ORIGINS` to the exact deployed frontend origins; local defaults are only for development.
- Provision/reset an admin using `python scripts/provision_admin.py`; never expose its direct database access to application users.
- Configure TLS and rate-limiting/brute-force controls at the reverse proxy or gateway. MFA, refresh tokens, verification emails, and identity-provider integration are not implemented.
- The old identity headers are ignored. As documented in Phase 2, those headers are not cryptographic credentials and must not be trusted if a deployment reintroduces them through a gateway.

## Phase 5 — Frontend rebuild and backend integration

### Acceptance checklist

- [x] Signed-token login, session restore, sign-out, and `/api/auth/me` organization/role context
- [x] Role-aware navigation and controls; backend remains authoritative for authorization
- [x] Real API dashboard and supplier/customer/warehouse/factory/route management
- [x] Saved disruption scenarios and real planner execution
- [x] Industry preference and profile-default cost/time/risk weights
- [x] Planner results, alternatives, rejected candidates, explanation, and partial-risk evidence
- [x] Planning history with run comparison and feasibility explanation
- [x] Admin-only member provisioning with backend-enforced roles
- [x] API 401 session expiry and 403 handling
- [x] Responsive browser check at 390px with no horizontal overflow
- [x] Frontend scripts pass Node syntax checks
- [x] Phase 5 frontend files and `/api/auth/me` backend contract change committed

### Verification

- Frontend syntax: `node --check app.js` and `node --check workspace.js` passed.
- Backend current-user integration: `..\ReRoute_Backend\venv\Scripts\python.exe -m pytest -q scripts/test_security.py::test_password_login_and_generic_invalid_credentials` passed (`1 passed`).
- Real browser/database integration verified login and current-user profile; live dashboard counts; supplier create/delete (`201`/`200`); healthcare profile weights (`20/30/50`); a real planner recommendation displaying `Supplier-only 7.9%` with route evidence unknown; scenario save and execute (run `26`); history comparison/explanation; member provisioning; invalid-token `401` return to login; analyst role controls and `403`; and 390px viewport overflow check.
- Browser checks used a temporary local signing key and temporary test accounts. Those accounts and the test scenario/run were removed after verification. No signing secret was written to repository files.
- The frontend has no npm manifest/build framework; the static client is served with `python -m http.server 5500`.
- Frontend commit: `75bdbcb` (`feat: rebuild ReRoute operations frontend`); backend endpoint/contract commit: `7874578` (`feat: expose authenticated user profile for client`).

### Scope and limitations

- Organization name/role are read from `/api/auth/me`. Organization creation remains operator-provisioned because the current business API does not provide a safe self-enrollment/organization-owner workflow.
- Industry choice is a per-user browser preference because the backend does not persist an organization-level industry profile.
- The existing identity-header limitation remains documented; the browser sends only the signed Bearer token and does not send identity or role headers.
