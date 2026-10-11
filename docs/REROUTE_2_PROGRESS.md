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
- Current next step: continue with Phase 2 backend business API expansion
