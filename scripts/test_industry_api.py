def test_supported_industry_templates_are_available_to_members(client):
    response = client.get("/api/industries")
    assert response.status_code == 200

    templates = {item["code"]: item for item in response.json()}
    assert set(templates) == {
        "manufacturing",
        "retail_distribution",
        "food_distribution",
        "healthcare_logistics",
    }
    assert "supplier" in templates["manufacturing"]["entity_types"]
    assert "supplier_failure" in templates["food_distribution"]["disruptions"]
    assert all(
        rule["mandatory"]
        for template in templates.values()
        for rule in template["rules"]
    )


def test_organization_can_select_profile_and_version_settings(client):
    before = client.get("/api/organizations/1/settings")
    assert before.status_code == 200
    assert before.json()["profile"]["code"] == "manufacturing"
    assert before.json()["configuration_version"] == 1

    response = client.put(
        "/api/organizations/1/settings",
        json={
            "profile_code": "food_distribution",
            "weights": {"cost": 0.2, "time": 0.4, "risk": 0.4},
            "max_alternatives": 5,
            "parameters": {
                "shelf_life_days": 4,
                "cold_chain_required": True,
                "delivery_window_hours": 12,
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["code"] == "food_distribution"
    assert data["configuration_version"] == 2
    assert data["weights"] == {"cost": 0.2, "time": 0.4, "risk": 0.4}
    parameters = {item["key"]: item["value"] for item in data["profile"]["parameters"]}
    assert parameters["shelf_life_days"] == 4
    assert parameters["cold_chain_required"] is True
    assert data["max_alternatives"] == 5

    reread = client.get("/api/organizations/1/settings")
    assert reread.json() == data


def test_industry_settings_reject_invalid_values_without_persisting(client):
    invalid_profile = client.put(
        "/api/organizations/1/settings",
        json={
            "profile_code": "food_distribution",
            "parameters": {"shelf_life_days": 0},
        },
    )
    assert invalid_profile.status_code == 422

    unknown_parameter = client.put(
        "/api/organizations/1/settings",
        json={
            "profile_code": "food_distribution",
            "parameters": {"run_python": "not allowed"},
        },
    )
    assert unknown_parameter.status_code == 422

    invalid_weights = client.put(
        "/api/organizations/1/settings",
        json={
            "profile_code": "food_distribution",
            "weights": {"cost": 0.5, "time": 0.5, "risk": 0.5},
        },
    )
    assert invalid_weights.status_code == 422

    settings = client.get("/api/organizations/1/settings").json()
    assert settings["profile"]["code"] == "manufacturing"
    assert settings["configuration_version"] == 1


def test_industry_configuration_is_organization_scoped(client):
    response = client.get("/api/organizations/999/settings")
    assert response.status_code == 404


def test_planner_uses_organization_defaults_and_honors_request_override(client):
    configured = client.put(
        "/api/organizations/1/settings",
        json={
            "profile_code": "manufacturing",
            "max_alternatives": 0,
            "weights": {"cost": 0.7, "time": 0.2, "risk": 0.1},
        },
    )
    assert configured.status_code == 200

    defaulted = client.post(
        "/api/planner/recommend",
        json={"customer_id": 1, "quantity": 42},
    )
    assert defaulted.status_code == 200
    assert defaulted.json()["alternatives"] == []

    overridden = client.post(
        "/api/planner/recommend",
        json={
            "customer_id": 1,
            "quantity": 42,
            "max_alternatives": 2,
        },
    )
    assert overridden.status_code == 200
    assert len(overridden.json()["alternatives"]) == 2
