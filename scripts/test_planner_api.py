from fastapi.testclient import TestClient

from app.main import app
from app.security.auth import create_access_token


client = TestClient(
    app,
    headers={"Authorization": f"Bearer {create_access_token(1)}"},
)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy"
    }


def test_planner_normal_request():
    response = client.post(
        "/api/planner/recommend",
        json={
            "customer_id": 1,
            "quantity": 42,
            "disruption_type": "none",
            "weights": {
                "cost": 0.4,
                "time": 0.3,
                "risk": 0.3,
            },
            "max_alternatives": 3,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "recommended_plan" in data
    assert "alternatives" in data
    assert "explanation" in data
    assert "actions" in data
    assert "scenario" in data
    assert "candidate_plans" in data
    assert "rejected_candidates" in data

    assert data["scenario"]["type"] == "none"
    assert data["scenario"]["customer_id"] == 1
    assert data["scenario"]["quantity"] == 42

    assert data["recommended_plan"]["rank"] == 1
    assert data["recommended_plan"]["cost_weight"] == 0.4
    assert "Score = 0.400 * cost" in data["explanation"]
    assert data["recommended_plan"]["risk"]["route_failure_probability"] is None
    assert data["recommended_plan"]["risk"]["stockout_probability"] is None
    assert data["recommended_plan"]["risk"]["risk_is_partial"] is True


def test_internal_value_error_is_not_reported_as_bad_request():
    from unittest.mock import patch

    with patch(
        "app.services.planner.PlannerService.calculate_risks",
        side_effect=ValueError("corrupt risk evidence"),
    ):
        response = client.post(
            "/api/planner/recommend",
            json={"customer_id": 1, "quantity": 42},
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "The planner encountered an internal error."


def test_planner_supplier_failure():
    response = client.post(
        "/api/planner/recommend",
        json={
            "customer_id": 1,
            "quantity": 42,
            "disruption_type": "supplier_failure",
            "supplier_id": 1,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["scenario"]["type"] == "supplier_failure"
    assert data["scenario"]["supplier_id"] == 1


def test_invalid_customer():
    response = client.post(
        "/api/planner/recommend",
        json={
            "customer_id": 9999,
            "quantity": 42,
        },
    )

    assert response.status_code == 404


def test_missing_supplier_for_failure():
    response = client.post(
        "/api/planner/recommend",
        json={
            "customer_id": 1,
            "quantity": 42,
            "disruption_type": "supplier_failure",
        },
    )

    assert response.status_code == 422


def test_invalid_weights():
    response = client.post(
        "/api/planner/recommend",
        json={
            "customer_id": 1,
            "quantity": 42,
            "weights": {
                "cost": 0.5,
                "time": 0.5,
                "risk": 0.5,
            },
        },
    )

    assert response.status_code == 422


def test_invalid_quantity():
    response = client.post(
        "/api/planner/recommend",
        json={
            "customer_id": 1,
            "quantity": 0,
        },
    )

    assert response.status_code == 422


def test_infeasible_plan_returns_real_rejection_reasons():
    response = client.post(
        "/api/planner/recommend",
        json={
            "customer_id": 1,
            "quantity": 1000000,
        },
    )

    assert response.status_code == 409

    data = response.json()

    assert "detail" in data
    assert "No feasible recovery plans" in data["detail"]
    assert "supplier capacity" in data["detail"]