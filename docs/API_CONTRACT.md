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

All business endpoints under `/api/business` require identity headers:

- `X-User-Id`
- `X-Organization-Id`
- optional `X-User-Role` (must match the persisted role)

Requests without the required user and organization headers return `401`. The service validates that the user belongs to the target organization and rejects cross-tenant access with `403`.

These headers provide identity context only; they do not cryptographically authenticate a client. Production deployments must set them through trusted authentication middleware or an API gateway and must not expose direct client control over these values.

Organization-scoped entity access is enforced against the live database using an `organization_entity_access` join table. This prevents a user from changing an ID to read or write another organization's supplier, customer, warehouse, factory, or route records.

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
