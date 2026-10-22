# ReRoute Backend API Contract

Contract version: 1.0 (planner payload compatibility retained; authentication required)

## Authentication

Protected endpoints require `Authorization: Bearer <access_token>`. Access tokens
expire after 10 minutes. The login endpoint returns the access token and sets a
14-day refresh token in an HttpOnly, SameSite=Strict cookie. Refresh tokens are
rotated and are invalid after reuse or logout.

`POST /api/auth/login` accepts `email`, `password`, and `organization_slug`.
`POST /api/auth/refresh` rotates the refresh cookie. `POST /api/auth/logout`
revokes the refresh session. `GET /api/auth/me` returns the current user,
organization, and membership role.

## Planner

`POST /api/planner/recommend` retains its existing JSON request and response
schemas. It now requires the `planner:run` permission. Organization scope is
resolved from the authenticated active membership and is never accepted from
planner request JSON. Insufficient permissions return `403`; missing, expired,
revoked, or inactive credentials return `401`.

For `none` and `supplier_failure` scenarios, `quantity` is the exact simulated
customer demand. A `demand_spike` scenario applies the configured percentage to
the stored customer demand and rounds fractional units up to the next integer
before CSP validation.

Request fields and response serialization remain defined in
`app/schemas/planner.py`. Errors retain the existing FastAPI detail envelope.

## Organization members

- `GET /api/organizations/{organization_id}/members` lists the current
  organization's members and requires `members:manage`.
- `POST /api/organizations/{organization_id}/members` creates a member or links
  an existing account to the current organization. New users require a
  14-character minimum password.
- `PATCH /api/organizations/{organization_id}/members/{membership_id}` updates
  the role or active status. The last active organization administrator cannot
  be removed.

A path organization that differs from the authenticated organization returns
`404` to avoid confirming another organization's existence.

## Roles

Permissions are centralized in `app/security/permissions.py`:

| Role | Run planner | Read planner | Read supply chain | Manage supply chain | Manage organization | Manage members | Read audit |
|---|---:|---:|---:|---:|---:|---:|---:|
| Organization administrator | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Operations manager | Yes | Yes | Yes | Yes | No | No | No |
| Analyst | Yes | Yes | Yes | No | No | No | No |
| Viewer | No | Yes | Yes | No | No | No | No |

## Compatibility

The planner JSON contract is unchanged. Authentication is an intentional behavior
change required for multi-user access. Legacy clients must first authenticate
and send an access token; frontend integration should use the endpoints and
cookie behavior documented above. No `/api/v2` path is introduced at this
checkpoint.

Industry configuration, supply-chain CRUD, disruption history, persisted
planning runs, reporting, and pagination are not implemented yet.

The four industry templates, normalized parameter definitions, and versioned
organization settings are available. Configured objective weights and maximum
alternatives are used by the planner unless explicitly overridden in a request.
Industry-specific parameter values and rule descriptions are currently
validated and stored as configuration metadata; they are not yet enforced as
additional A*/CSP constraints. Do not treat food or healthcare rules as an
operational or regulatory guarantee.
