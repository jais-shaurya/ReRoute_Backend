def test_organization_admin_can_list_and_add_members(client):
    members_response = client.get("/api/organizations/1/members")
    assert members_response.status_code == 200
    assert len(members_response.json()) == 1
    admin_membership_id = members_response.json()[0]["membership_id"]

    create_response = client.post(
        "/api/organizations/1/members",
        json={
            "email": "analyst@example.test",
            "full_name": "Test Analyst",
            "role": "analyst",
            "password": "analyst-password-for-tests",
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["role"] == "analyst"
    assert "password" not in create_response.json()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "analyst@example.test",
            "password": "analyst-password-for-tests",
            "organization_slug": "test-organization",
        },
    )
    assert login_response.status_code == 200

    update_response = client.patch(
        f"/api/organizations/1/members/{create_response.json()['membership_id']}",
        json={"role": "viewer"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["role"] == "viewer"

    assert admin_membership_id > 0


def test_admin_cannot_remove_last_active_admin(client):
    members = client.get("/api/organizations/1/members").json()
    admin_membership_id = members[0]["membership_id"]

    response = client.patch(
        f"/api/organizations/1/members/{admin_membership_id}",
        json={"is_active": False},
    )
    assert response.status_code == 409


def test_member_management_does_not_cross_organization(client):
    response = client.get("/api/organizations/999/members")
    assert response.status_code == 404


def test_duplicate_membership_is_rejected(client):
    client.post(
        "/api/organizations/1/members",
        json={
            "email": "analyst@example.test",
            "full_name": "Test Analyst",
            "role": "analyst",
            "password": "analyst-password-for-tests",
        },
    )
    response = client.post(
        "/api/organizations/1/members",
        json={
            "email": "analyst@example.test",
            "full_name": "Test Analyst",
            "role": "analyst",
        },
    )
    assert response.status_code == 409
