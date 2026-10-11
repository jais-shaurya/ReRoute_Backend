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
- `weights` must still sum to `1.0` as before.

### Response shape

The planner response remains consistent with the existing recommendation payload and includes:

- `recommended_plan`
- `alternatives`
- `explanation`
- `actions`
- `scenario`
- `candidate_plans`

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
