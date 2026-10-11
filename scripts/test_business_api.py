from math import ceil
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.security.auth import create_access_token


def auth_headers(user_id=1, **extra):
    return {"Authorization": f"Bearer {create_access_token(user_id)}", **extra}


def test_business_entities_list_and_create():
    with TestClient(app) as client:
        headers = auth_headers()
        supplier_code = f"SUP-{uuid4().hex[:8].upper()}"
        suppliers = client.get("/api/business/suppliers", headers=headers)
        assert suppliers.status_code == 200
        assert len(suppliers.json()) >= 1

        created = client.post(
            "/api/business/suppliers",
            json={
                "supplier_code": supplier_code,
                "name": "Test Supplier",
                "capacity": 200,
                "unit_cost": 25.0,
                "reliability": 0.94,
                "available": True,
            },
            headers=headers,
        )
        assert created.status_code == 201
        assert created.json()["supplier_code"] == supplier_code


def test_business_scenario_execute_and_history():
    with TestClient(app) as client:
        headers = auth_headers()
        customer = client.get("/api/business/customers/1", headers=headers)
        assert customer.status_code == 200
        expected_quantity = ceil(customer.json()["demand"] * 1.2)

        scenario = client.post(
            "/api/business/scenarios",
            json={
                "name": f"Demand spike {uuid4().hex[:8]}",
                "scenario_type": "demand_spike",
                "customer_id": 1,
                "quantity": 42,
                "demand_spike_percentage": 20,
            },
            headers=headers,
        )
        assert scenario.status_code == 201, scenario.text
        run = client.post(
            f"/api/business/scenarios/{scenario.json()['id']}/execute",
            headers=headers,
        )
        assert run.status_code == 200, run.text
        run_data = run.json()
        assert run_data["requested_customer_id"] == 1
        assert run_data["status"] == "completed"
        assert run_data["result_payload"]["scenario"]["quantity"] == expected_quantity

        history = client.get("/api/business/planning-runs", headers=headers)
        assert history.status_code == 200
        assert any(item["id"] == run_data["id"] for item in history.json())


def test_legacy_identity_headers_are_not_authentication():
    with TestClient(app) as client:
        response = client.get(
            "/api/business/customers",
            headers={
                "X-User-Id": "1",
                "X-Organization-Id": "1",
                "X-User-Role": "admin",
            },
        )
        assert response.status_code == 401


def test_legacy_headers_cannot_change_authenticated_tenant():
    with TestClient(app) as client:
        response = client.get(
            "/api/business/customers",
            headers=auth_headers(
                X_User_Id="999999",
                X_Organization_Id="999999",
                X_User_Role="reader",
            ),
        )
        assert response.status_code == 200
        assert response.json()


def test_scenario_rejects_customer_outside_organization_scope():
    with TestClient(app) as client:
        response = client.post(
            "/api/business/scenarios",
            json={
                "name": f"Invalid customer {uuid4().hex[:8]}",
                "scenario_type": "none",
                "customer_id": 999999,
                "quantity": 12,
            },
            headers=auth_headers(),
        )
        assert response.status_code == 404


def test_business_scenario_infeasibility_returns_conflict_with_reasons():
    with TestClient(app) as client:
        headers = auth_headers()
        scenario = client.post(
            "/api/business/scenarios",
            json={
                "name": f"Over capacity {uuid4().hex[:8]}",
                "scenario_type": "none",
                "customer_id": 1,
                "quantity": 1000000,
            },
            headers=headers,
        )
        assert scenario.status_code == 201, scenario.text

        response = client.post(
            f"/api/business/scenarios/{scenario.json()['id']}/execute",
            headers=headers,
        )
        assert response.status_code == 409
        assert "No feasible recovery plans" in response.json()["detail"]
        assert "supplier capacity" in response.json()["detail"]


def test_route_validation_and_issue():
    with TestClient(app) as client:
        invalid = client.post(
            "/api/business/routes",
            json={
                "route_code": "ROUTE-ERR",
                "source_type": "supplier",
                "source_id": 999,
                "destination_type": "customer",
                "destination_id": 1,
                "transportation_cost": 0,
                "delivery_time_days": 0,
                "capacity": 0,
                "available": True,
            },
            headers=auth_headers(),
        )
        assert invalid.status_code == 422


def test_recommendation_comparison_endpoint():
    with TestClient(app) as client:
        headers = auth_headers()
        history = client.get("/api/business/planning-runs", headers=headers)
        assert history.status_code == 200
        payload = history.json()
        if not payload:
            scenario = client.post(
                "/api/business/scenarios",
                json={
                    "name": f"Compare plan {uuid4().hex[:8]}",
                    "scenario_type": "demand_spike",
                    "customer_id": 1,
                    "quantity": 10,
                    "demand_spike_percentage": 15,
                },
                headers=headers,
            )
            assert scenario.status_code == 201, scenario.text
            run = client.post(
                f"/api/business/scenarios/{scenario.json()['id']}/execute",
                headers=headers,
            )
            assert run.status_code == 200, run.text
            payload = client.get("/api/business/planning-runs", headers=headers).json()

        run_id = payload[0]["id"]
        comparison = client.get(
            f"/api/business/planning-runs/{run_id}/comparison",
            headers=headers,
        )
        assert comparison.status_code == 200
        assert "selected_plan" in comparison.json()

        explanation = client.get(
            f"/api/business/planning-runs/{run_id}/explanation",
            headers=headers,
        )
        assert explanation.status_code == 200
        assert "explanation" in explanation.json()