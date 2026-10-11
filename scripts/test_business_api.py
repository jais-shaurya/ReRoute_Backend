from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


def test_business_entities_list_and_create():
    with TestClient(app) as client:
        headers = {"X-User-Id": "1", "X-Organization-Id": "1"}
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
        headers = {"X-User-Id": "1", "X-Organization-Id": "1"}
        scenario_name = f"Demand spike {uuid4().hex[:8]}"

        scenario = client.post(
            "/api/business/scenarios",
            json={
                "name": scenario_name,
                "scenario_type": "demand_spike",
                "customer_id": 1,
                "quantity": 42,
                "demand_spike_percentage": 20,
            },
            headers=headers,
        )
        assert scenario.status_code == 201, scenario.text
        scenario_id = scenario.json()["id"]

        run = client.post(f"/api/business/scenarios/{scenario_id}/execute", headers=headers)
        assert run.status_code == 200, run.text
        run_data = run.json()
        assert run_data["requested_customer_id"] == 1
        assert run_data["status"] == "completed"

        history = client.get("/api/business/planning-runs", headers=headers)
        assert history.status_code == 200
        assert any(item["id"] == run_data["id"] for item in history.json())


def test_cross_organization_access_forbidden():
    with TestClient(app) as client:
        headers = {"X-User-Id": "1", "X-Organization-Id": "2"}

        response = client.get("/api/business/customers", headers=headers)
        assert response.status_code == 403


def test_business_api_requires_authentication_and_rejects_role_escalation():
    with TestClient(app) as client:
        missing_auth = client.get("/api/business/customers")
        assert missing_auth.status_code == 401

        escalated_role = client.get(
            "/api/business/customers",
            headers={
                "X-User-Id": "1",
                "X-Organization-Id": "1",
                "X-User-Role": "reader",
            },
        )
        assert escalated_role.status_code == 403


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
            headers={"X-User-Id": "1", "X-Organization-Id": "1"},
        )
        assert response.status_code == 404


def test_route_validation_and_issue():
    with TestClient(app) as client:
        headers = {"X-User-Id": "1", "X-Organization-Id": "1"}

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
            headers=headers,
        )
        assert invalid.status_code == 422


def test_recommendation_comparison_endpoint():
    with TestClient(app) as client:
        headers = {"X-User-Id": "1", "X-Organization-Id": "1"}
        history = client.get("/api/business/planning-runs", headers=headers)
        if history.status_code != 200:
            assert False, history.text

        payload = history.json()
        if not payload:
            scenario_name = f"Compare plan {uuid4().hex[:8]}"
            scenario = client.post(
                "/api/business/scenarios",
                json={
                    "name": scenario_name,
                    "scenario_type": "demand_spike",
                    "customer_id": 1,
                    "quantity": 10,
                    "demand_spike_percentage": 15,
                },
                headers=headers,
            )
            assert scenario.status_code == 201, scenario.text
            run = client.post(f"/api/business/scenarios/{scenario.json()['id']}/execute", headers=headers)
            assert run.status_code == 200, run.text
            payload = client.get("/api/business/planning-runs", headers=headers).json()

        run_id = payload[0]["id"]
        comparison = client.get(f"/api/business/planning-runs/{run_id}/comparison", headers=headers)
        assert comparison.status_code == 200
        assert "selected_plan" in comparison.json()

        explanation = client.get(f"/api/business/planning-runs/{run_id}/explanation", headers=headers)
        assert explanation.status_code == 200
        assert "explanation" in explanation.json()
