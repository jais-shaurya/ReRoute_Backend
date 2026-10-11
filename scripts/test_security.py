from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.database.models import (
    AppUser,
    Customer,
    Factory,
    Organization,
    PlanningRun,
    PlanningScenario,
    Route,
    Supplier,
    Warehouse,
)
from app.main import app
from app.security.auth import create_access_token, hash_password, verify_password


@pytest.fixture
def tenant_user():
    db = SessionLocal()
    marker = uuid4().hex
    organization = Organization(name=f"Security {marker}", slug=f"security-{marker}")
    db.add(organization)
    db.flush()
    user = AppUser(
        email=f"security-{marker}@example.test",
        full_name="Security Test User",
        role="planner",
        organization_id=organization.id,
        password_hash=hash_password("correct-horse-battery-42"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    values = (user.id, organization.id, user.email)
    db.close()
    try:
        yield values
    finally:
        cleanup = SessionLocal()
        cleanup.query(AppUser).filter_by(id=values[0]).delete()
        cleanup.query(Organization).filter_by(id=values[1]).delete()
        cleanup.commit()
        cleanup.close()


def bearer(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def test_password_login_and_generic_invalid_credentials(tenant_user):
    user_id, _, email = tenant_user
    with TestClient(app) as client:
        invalid = client.post(
            "/api/auth/token",
            json={"email": email, "password": "incorrect"},
        )
        assert invalid.status_code == 401
        assert invalid.json()["detail"] == "Invalid email or password."

        response = client.post(
            "/api/auth/token",
            json={"email": email, "password": "correct-horse-battery-42"},
        )
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert "password" not in response.text
        assert "password_hash" not in response.text
        profile = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {response.json()['access_token']}"},
        )
        assert profile.status_code == 200
        assert profile.json()["id"] == user_id
        assert profile.json()["role"] == "planner"
        assert profile.json()["organization"]["id"] == tenant_user[1]
        protected = client.get(
            "/api/business/suppliers",
            headers={"Authorization": f"Bearer {response.json()['access_token']}"},
        )
        assert protected.status_code == 200
        assert protected.json() == []


def test_missing_tampered_and_expired_tokens_are_rejected(tenant_user, monkeypatch):
    user_id, _, _ = tenant_user
    secret = "test-only-secret-never-use-in-production-000000"
    token = create_access_token(user_id, secret)
    parts = token.split(".")
    parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
    tampered = ".".join(parts)
    expired = jwt.encode(
        {
            "sub": str(user_id),
            "iss": "reroute-api",
            "iat": datetime.now(timezone.utc) - timedelta(minutes=20),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            "type": "access",
        },
        secret,
        algorithm="HS256",
    )
    monkeypatch.setenv("REROUTE_AUTH_SECRET", secret)
    with TestClient(app) as client:
        assert client.get("/api/business/customers").status_code == 401
        assert client.get(
            "/api/business/customers", headers={"Authorization": f"Bearer {tampered}"}
        ).status_code == 401
        assert client.get(
            "/api/business/customers", headers={"Authorization": f"Bearer {expired}"}
        ).status_code == 401


def test_missing_signing_secret_fails_closed(tenant_user, monkeypatch):
    user_id, _, _ = tenant_user
    token = create_access_token(user_id, "test-only-secret-never-use-in-production-000000")
    monkeypatch.delenv("REROUTE_AUTH_SECRET", raising=False)
    with TestClient(app) as client:
        response = client.get(
            "/api/business/customers",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "Authentication is not configured."


def test_rbac_blocks_planner_admin_actions_and_api_admin_assignment(tenant_user):
    user_id, organization_id, _ = tenant_user
    with TestClient(app) as client:
        headers = bearer(user_id)
        denied = client.post(
            "/api/business/organizations/1/users",
            json={
                "email": f"blocked-{uuid4().hex}@example.test",
                "full_name": "Blocked User",
                "password": "correct-horse-battery-43",
                "role": "planner",
            },
            headers=headers,
        )
        assert denied.status_code == 403

        admin_assignment = client.post(
            f"/api/business/organizations/{organization_id}/users",
            json={
                "email": f"admin-{uuid4().hex}@example.test",
                "full_name": "Unexpected Admin",
                "password": "correct-horse-battery-44",
                "role": "admin",
            },
            headers=bearer(1),
        )
        assert admin_assignment.status_code == 422


def test_admin_user_provisioning_hashes_password_and_returns_no_credential(tenant_user):
    user_id, organization_id, _ = tenant_user
    db = SessionLocal()
    db.query(AppUser).filter_by(id=user_id).update({"role": "admin"})
    db.commit()
    db.close()
    email = f"provisioned-{uuid4().hex}@example.test"
    password = "new-account-secret-987654"
    with TestClient(app) as client:
        created = client.post(
            f"/api/business/organizations/{organization_id}/users",
            json={
                "email": email,
                "full_name": "Provisioned Planner",
                "password": password,
                "role": "planner",
            },
            headers=bearer(user_id),
        )
        assert created.status_code == 201, created.text
        assert "password" not in created.json()
        assert "password_hash" not in created.json()

        db = SessionLocal()
        user = db.query(AppUser).filter_by(email=email).one()
        created_user_id = user.id
        assert user.password_hash != password
        assert verify_password(user.password_hash, password)
        db.close()

        login = client.post("/api/auth/token", json={"email": email, "password": password})
        assert login.status_code == 200
    cleanup = SessionLocal()
    cleanup.query(AppUser).filter_by(id=created_user_id).delete()
    cleanup.commit()
    cleanup.close()


def test_cors_allows_only_configured_origins():
    with TestClient(app) as client:
        allowed = client.options(
            "/api/business/customers",
            headers={
                "Origin": "http://localhost:5500",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5500"

        denied = client.options(
            "/api/business/customers",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert "access-control-allow-origin" not in denied.headers


def test_cross_tenant_entity_scenario_planning_and_history_isolation(tenant_user):
    db = SessionLocal()
    foreign_user = db.query(AppUser).filter_by(id=tenant_user[0]).one()
    foreign_user.role = "admin"
    db.commit()
    owner = db.query(AppUser).filter_by(id=1).first()
    resources = [
        (
            "suppliers",
            db.query(Supplier).order_by(Supplier.id).first(),
            lambda item: {
                "supplier_code": item.supplier_code,
                "name": item.name,
                "capacity": item.capacity,
                "unit_cost": item.unit_cost,
                "reliability": item.reliability,
                "available": item.available,
            },
        ),
        (
            "customers",
            db.query(Customer).order_by(Customer.id).first(),
            lambda item: {
                "customer_code": item.customer_code,
                "name": item.name,
                "demand": item.demand,
                "deadline_days": item.deadline_days,
            },
        ),
        (
            "warehouses",
            db.query(Warehouse).order_by(Warehouse.id).first(),
            lambda item: {
                "warehouse_code": item.warehouse_code,
                "name": item.name,
                "capacity": item.capacity,
                "inventory": item.inventory,
            },
        ),
        (
            "factories",
            db.query(Factory).order_by(Factory.id).first(),
            lambda item: {
                "factory_code": item.factory_code,
                "name": item.name,
                "capacity": item.capacity,
                "available": item.available,
            },
        ),
        (
            "routes",
            db.query(Route).order_by(Route.id).first(),
            lambda item: {
                "route_code": item.route_code,
                "source_type": item.source_type,
                "source_id": item.source_id,
                "destination_type": item.destination_type,
                "destination_id": item.destination_id,
                "transportation_cost": item.transportation_cost,
                "delivery_time_days": item.delivery_time_days,
                "capacity": item.capacity,
                "available": item.available,
            },
        ),
    ]
    resources = [(path, item.id, payload(item)) for path, item, payload in resources]
    marker = uuid4().hex
    scenario = PlanningScenario(
        organization_id=owner.organization_id,
        created_by_id=owner.id,
        name=f"Tenant isolation {marker}",
        scenario_type="none",
        customer_id=1,
        quantity=10,
    )
    db.add(scenario)
    db.flush()
    run = PlanningRun(
        organization_id=owner.organization_id,
        created_by_id=owner.id,
        scenario_id=scenario.id,
        status="completed",
        requested_customer_id=1,
        requested_quantity=10,
        disruption_type="none",
        recommendation="test-only",
        explanation="test-only",
        result_payload={"recommended_plan": {}, "alternatives": [], "actions": []},
    )
    db.add(run)
    db.commit()
    scenario_id, run_id = scenario.id, run.id
    db.close()

    try:
        with TestClient(app) as client:
            headers = bearer(tenant_user[0])
            for path, item_id, payload in resources:
                assert client.get(f"/api/business/{path}", headers=headers).json() == []
                assert client.get(f"/api/business/{path}/{item_id}", headers=headers).status_code == 404
                assert client.put(
                    f"/api/business/{path}/{item_id}",
                    json=payload,
                    headers=headers,
                ).status_code == 404
                assert client.delete(
                    f"/api/business/{path}/{item_id}",
                    headers=headers,
                ).status_code == 404
            assert client.get("/api/business/customers/1", headers=headers).status_code == 404
            assert client.get("/api/business/scenarios", headers=headers).json() == []
            assert client.get(f"/api/business/scenarios/{scenario_id}", headers=headers).status_code == 404
            assert client.post(f"/api/business/scenarios/{scenario_id}/execute", headers=headers).status_code == 404
            assert client.get("/api/business/planning-runs", headers=headers).json() == []
            assert client.get(f"/api/business/planning-runs/{run_id}", headers=headers).status_code == 404
            assert client.get(f"/api/business/planning-runs/{run_id}/comparison", headers=headers).status_code == 404
            assert client.get(f"/api/business/planning-runs/{run_id}/explanation", headers=headers).status_code == 404
            planning = client.post(
                "/api/planner/recommend",
                json={"customer_id": 1, "quantity": 10},
                headers=headers,
            )
            assert planning.status_code == 404
    finally:
        cleanup = SessionLocal()
        cleanup.query(PlanningRun).filter_by(id=run_id).delete()
        cleanup.query(PlanningScenario).filter_by(id=scenario_id).delete()
        foreign = cleanup.query(AppUser).filter_by(id=tenant_user[0]).one()
        foreign.role = "planner"
        cleanup.commit()
        cleanup.close()