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
