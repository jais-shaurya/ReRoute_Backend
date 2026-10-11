# ReRoute API Contract

## Planner request

### Endpoint

`POST /api/planner/recommend`

### Request body

```json
{
  "customer_id": 1,
  "quantity": 42,
  "industry": "retail",
  "disruption_type": "demand_spike",
  "disruption_customer_id": 1,
  "demand_spike_percentage": 20,
  "weights": {
    "cost": 0.4,
    "time": 0.3,
    "risk": 0.3
  },
  "max_alternatives": 3
}
```

### Supported industry profiles

- `retail`
- `manufacturing`
- `ecommerce`
- `healthcare`

### Validation rules

- `industry` is optional and defaults to `retail`.
- Unknown industry names are rejected.
- `demand_spike_percentage` must remain within the selected profile ceiling.
- If `weights` is omitted, the selected profile's configured default weights are used.
- Explicit `weights` must be finite, non-negative, and sum to `1.0`.
- The profile's `min_service_level` is applied as a minimum observed supplier-reliability threshold during candidate feasibility. Suppliers below it, or with missing reliability, are not eligible. This threshold uses the supplier reliability field already stored in the database; it is not a measured end-to-end fulfillment rate.

### Demand-spike quantity policy

The planner computes the post-spike demand as `ceil(original_demand * (1 + percentage / 100))`, so fractional units round upward to the next whole unit. Normal planning uses the requested quantity unchanged. The same rounding helper is used by disruption simulation and planner execution.

### Score and ranking policy

Each objective is normalized over the feasible candidate set using a minimization min-max transform:

`normalized = (maximum - value) / (maximum - minimum)`

The best value is `1`, the worst is `0`, and equal values all receive `1` because that objective cannot distinguish candidates. The overall score is `cost_weight * normalized_cost + time_weight * normalized_time + risk_weight * normalized_risk`; weights are finite, non-negative, and sum to `1`. Scores are rounded to six decimal places for the response. Ties are resolved by lower known plan risk, lower cost, shorter time, lexicographic path, then supplier and customer IDs. Because normalization is relative to the current feasible candidate set, scores can change when that set changes.

### Reliability and risk evidence

- Supplier failure probability is `1 - supplier.reliability`, using the stored supplier reliability value. An unavailable supplier is a certain failure.
- Route failure probability is calculated from route reliability only when that value is present on the route data. Available routes without reliability evidence are not assigned a synthetic prior.
- When all route reliabilities on a path are observed, route and supplier failure probabilities are combined assuming conditional independence: `1 - product(1 - component_failure_probability)`.
- When any available route lacks reliability, `route_failure_probability` and `stockout_probability` are `null`; `plan_risk` contains only the observed supplier failure probability and `risk_is_partial` is `true`, with missing route identifiers listed in `missing_evidence`. This partial value is not a complete end-to-end risk estimate.
- The current route table has no reliability-history column, so route risk will normally be partial until supported route reliability data is introduced. No predictive accuracy is claimed.

### Feasibility diagnostics and errors

- Only candidates satisfying availability, reliability threshold, quantity, supplier/factory/warehouse/route capacities, inventory, deadlines, and path consistency are scored.
- `rejected_candidates` reports supplier/path rejection reasons that can be established from current data.
- If no candidate is feasible, the API returns `409 Conflict` and includes the collected rejection reasons.
- Invalid request/profile/weight data returns validation errors; missing requested entities retain `404` behavior. Unexpected planner failures return `500`, not a client validation response.

### Response shape

The planner response remains consistent with the existing recommendation payload and includes:

- `recommended_plan`
- `alternatives`
- `explanation`
- `actions`
- `scenario`
- `candidate_plans`
- `rejected_candidates`

Each scored candidate includes the weights used. The explanation presents the weighted normalized-score calculation and identifies partial supplier-only risk when route reliability is absent.

### Error behavior

- Invalid industry names return a `400` with a validation message.
- Excessive demand spikes for a profile return a `400` with a profile-specific message.
- Missing planner data still returns the established validation or `404`/`409` responses used by the route layer.

## Business API security and tenant isolation

All business and planner endpoints require a signed access token:

`POST /api/auth/token` accepts JSON `{ "email": "...", "password": "..." }` and returns an HS256 Bearer token valid for 15 minutes. Send it as `Authorization: Bearer <access_token>`. Passwords are stored using Argon2 hashes and are never returned by user-management endpoints.

`GET /api/auth/me` requires that Bearer token and returns the authenticated user's database-backed `id`, `email`, `full_name`, `role`, and `organization` (`id`, `name`, `slug`). The frontend uses this endpoint instead of reading identity or role from browser-controlled headers or unverified token claims.

Tokens require a configured `REROUTE_AUTH_SECRET` of at least 32 bytes. If it is missing or too short, token-protected requests fail closed with `503`; no default production secret is supplied. Generate and inject a high-entropy value through the deployment secret manager. The user ID in the signed token is resolved against the database on each request, so inactive/deleted users are rejected and the persisted role is authoritative.

Legacy `X-User-Id`, `X-Organization-Id`, and `X-User-Role` headers are ignored and do not authenticate or select a tenant. Their previous limitation still applies: identity/role headers are not cryptographic credentials and must not be trusted if reintroduced by a deployment gateway.

RBAC policy:

- `admin` and `planner` can create/update supply-chain entities and create/execute scenarios.
- Only `admin` can delete entities or provision organization users.
- User provisioning accepts `planner`, `analyst`, or `reader`; API callers cannot assign the `admin` role. Initial or replacement administrators are provisioned through the operator-only `scripts/provision_admin.py` CLI.
- The public planner route also requires Bearer authentication and builds its graph only from the authenticated organization's `organization_entity_access` rows.

`REROUTE_CORS_ORIGINS` is a comma-separated exact-origin allowlist. Its local development default is `http://localhost:5500,http://127.0.0.1:5500`; wildcards are rejected, credentials are disabled, and only the required methods and `Authorization`/`Content-Type` headers are allowed.

Organization-scoped entity access is enforced against the live database using an `organization_entity_access` join table. This prevents a user from changing an ID to read or write another organization's supplier, customer, warehouse, factory, or route records.

## Schema migrations and operator setup

Schema changes are applied explicitly with `alembic upgrade head`; application startup no longer runs `create_all` or inserts a default administrator. `DATABASE_URL` must target the intended database. The initial Alembic revision idempotently creates missing tables without altering existing ones; the next revision adds nullable `app_users.password_hash` and assigns legacy supply-chain rows to the sole existing organization only when exactly one organization is present. It does not delete or overwrite rows. If a legacy database has multiple organizations, ownership is ambiguous and no automatic legacy assignments are made.

After migration, operators provision the first/reset administrator with `python scripts/provision_admin.py` using a trusted database-capable environment. Legacy accounts have no password hash and cannot log in until an operator sets one. New deployments must provision an organization/admin before API use. Future schema changes require explicit reviewed Alembic revisions; automatic downgrade is intentionally disabled for these data-bearing revisions.

This boundary verifies signed application tokens but does not provide refresh tokens, MFA, brute-force/rate limiting, email verification, or external identity federation. Deployments must protect the signing key, rate-limit `/api/auth/token`, use TLS, restrict database access, and perform password reset/provisioning through trusted operators.

## Business entity endpoints

### Supplier management

- `GET /api/business/suppliers`
- `POST /api/business/suppliers`
- `GET /api/business/suppliers/{supplier_id}`
- `PUT /api/business/suppliers/{supplier_id}`
- `DELETE /api/business/suppliers/{supplier_id}`

### Customer management

- `GET /api/business/customers`
- `POST /api/business/customers`
- `GET /api/business/customers/{customer_id}`
- `PUT /api/business/customers/{customer_id}`
- `DELETE /api/business/customers/{customer_id}`

### Warehouse, factory, and route management

- `GET /api/business/warehouses`
- `GET /api/business/factories`
- `GET /api/business/routes`
- corresponding `POST`, `PUT`, and `DELETE` endpoints follow the same organization-scoped rules

### Scenario and planning-run management

- `GET /api/business/scenarios`
- `POST /api/business/scenarios`
- `GET /api/business/scenarios/{scenario_id}`
- `POST /api/business/scenarios/{scenario_id}/execute`
- `GET /api/business/planning-runs`
- `GET /api/business/planning-runs/{run_id}`
- `GET /api/business/planning-runs/{run_id}/comparison`
- `GET /api/business/planning-runs/{run_id}/explanation`

These endpoints return real planner-generated payloads, and the stored run result payload is JSON-serializable so it can be queried and compared later without custom object serialization.
