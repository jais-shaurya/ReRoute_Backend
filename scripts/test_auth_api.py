import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.database.models import (
    Customer,
    Organization,
    OrganizationMembership,
    User,
)
from app.main import app
from app.security.auth import hash_password


@pytest.fixture
def auth_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setenv("REROUTE_SECRET_KEY", "test-only-signing-key-" + "x" * 40)
    monkeypatch.setenv("REROUTE_COOKIE_SECURE", "false")

    with Session(engine) as session:
        organization = Organization(name="Test Org", slug="test-org")
        admin = User(
            email="admin@example.test",
            full_name="Test Admin",
            password_hash=hash_password("correct-horse-battery-staple"),
        )
        viewer = User(
            email="viewer@example.test",
            full_name="Test Viewer",
            password_hash=hash_password("viewer-password-for-tests"),
        )
        session.add_all([organization, admin, viewer])
        session.flush()
        session.add_all(
            [
                OrganizationMembership(
                    organization_id=organization.id,
                    user_id=admin.id,
                    role="organization_admin",
                ),
                OrganizationMembership(
                    organization_id=organization.id,
                    user_id=viewer.id,
                    role="viewer",
                ),
            ]
        )
        session.commit()
        admin_id = admin.id

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, engine, admin_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def login(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": (
                "correct-horse-battery-staple"
                if email == "admin@example.test"
                else "viewer-password-for-tests"
            ),
            "organization_slug": "test-org",
        },
    )
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    return response.json()


def test_planner_requires_authentication(auth_client):
    client, _, _ = auth_client
    response = client.post(
        "/api/planner/recommend",
        json={"customer_id": 1, "quantity": 10},
    )
    assert response.status_code == 401


def test_login_and_current_user(auth_client):
    client, _, _ = auth_client
    token = login(client, "admin@example.test")
    cookie = client.cookies.get("reroute_refresh")

    assert token["token_type"] == "bearer"
    assert token["expires_in"] == 600
    assert cookie

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "organization_admin"
    assert response.json()["organization_slug"] == "test-org"


def test_viewer_cannot_run_planner(auth_client):
    client, _, _ = auth_client
    token = login(client, "viewer@example.test")
    response = client.post(
        "/api/planner/recommend",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={"customer_id": 1, "quantity": 10},
    )
    assert response.status_code == 403


def test_viewer_cannot_change_organization_settings(auth_client):
    client, _, _ = auth_client
    token = login(client, "viewer@example.test")
    response = client.put(
        "/api/organizations/1/settings",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={"profile_code": "manufacturing", "max_alternatives": 0},
    )
    assert response.status_code == 403


def test_planner_cannot_read_another_organizations_customer(auth_client):
    client, engine, _ = auth_client
    token = login(client, "admin@example.test")
    with Session(engine) as session:
        other_organization = Organization(
            name="Other Organization",
            slug="other-organization",
        )
        session.add(other_organization)
        session.flush()
        session.add(
            Customer(
                id=999,
                organization_id=other_organization.id,
                customer_code="PRIVATE-CUSTOMER",
                name="Private customer",
                demand=10,
                deadline_days=5,
            )
        )
        session.commit()

    response = client.post(
        "/api/planner/recommend",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        json={
            "customer_id": 999,
            "quantity": 10,
            "organization_id": 2,
        },
    )
    assert response.status_code == 404


def test_refresh_rotation_rejects_replay_and_logout(auth_client):
    client, _, _ = auth_client
    login(client, "admin@example.test")
    first_refresh = client.cookies.get("reroute_refresh")
    assert first_refresh

    refreshed = client.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    second_refresh = client.cookies.get("reroute_refresh")
    assert second_refresh and second_refresh != first_refresh

    replay = client.post(
        "/api/auth/refresh",
        headers={"Cookie": f"reroute_refresh={first_refresh}"},
    )
    assert replay.status_code == 401

    client.post("/api/auth/refresh")
    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert client.post("/api/auth/refresh").status_code == 401


def test_deactivated_user_cannot_use_existing_access_token(auth_client):
    client, engine, admin_id = auth_client
    token = login(client, "admin@example.test")
    with Session(engine) as session:
        user = session.get(User, admin_id)
        assert user is not None
        user.is_active = False
        session.commit()

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert response.status_code == 401


def test_role_change_invalidates_existing_access_token(auth_client):
    client, _, _ = auth_client
    token = login(client, "admin@example.test")
    authorization = {"Authorization": f"Bearer {token['access_token']}"}
    added_admin = client.post(
        "/api/organizations/1/members",
        headers=authorization,
        json={
            "email": "second-admin@example.test",
            "full_name": "Second Admin",
            "role": "organization_admin",
            "password": "second-admin-password-for-tests",
        },
    )
    assert added_admin.status_code == 201
    members = client.get(
        "/api/organizations/1/members",
        headers=authorization,
    ).json()
    membership_id = next(
        member["membership_id"]
        for member in members
        if member["email"] == "admin@example.test"
    )

    changed = client.patch(
        f"/api/organizations/1/members/{membership_id}",
        headers=authorization,
        json={"role": "viewer"},
    )
    assert changed.status_code == 200

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert response.status_code == 401
