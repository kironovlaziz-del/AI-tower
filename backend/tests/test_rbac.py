"""Role-based access control."""

import pytest

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


async def test_admin_can_invite_user(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "newuser@test.example.com",
            "name": "New User",
            "password": "TestPass123!",
            "role": "user",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "user"


async def test_approver_cannot_invite_user(client, org_and_users, approver_token):
    resp = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "blocked@test.example.com",
            "name": "Blocked",
            "password": "TestPass123!",
            "role": "user",
        },
        headers=auth_headers(approver_token),
    )
    assert resp.status_code == 403


async def test_approver_cannot_create_policy(client, org_and_users, approver_token):
    resp = await client.post(
        "/api/v1/policies/",
        json={"name": "Test", "description": "should fail"},
        headers=auth_headers(approver_token),
    )
    assert resp.status_code == 403


async def test_admin_can_create_policy(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/policies/",
        json={"name": "Test Policy"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


async def test_users_list_admin_only(client, org_and_users, admin_token, approver_token):
    # Approver gets 403
    resp = await client.get(
        "/api/v1/users/", headers=auth_headers(approver_token)
    )
    assert resp.status_code == 403

    # Admin gets 200
    resp = await client.get(
        "/api/v1/users/", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_admin_cannot_deactivate_self(client, org_and_users, admin_token):
    resp = await client.put(
        f"/api/v1/users/{org_and_users['admin'].id}/status",
        json={"status": "disabled"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400


async def test_register_always_creates_admin(client):
    """The role from the payload is ignored - the first user of a new org
    is always admin."""
    resp = await client.post(
        "/api/v1/users/register",
        json={
            "email": "fresh@example.com",
            "password": "TestPass123!",
            "name": "Fresh",
            "org_name": "Fresh Org",
            "org_slug": "fresh-org",
            "role": "user",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


async def test_register_rejects_duplicate_slug(client, org_and_users):
    resp = await client.post(
        "/api/v1/users/register",
        json={
            "email": "different@example.com",
            "password": "TestPass123!",
            "name": "Different",
            "org_name": "Different Org",
            "org_slug": org_and_users["org"].slug,
            "role": "admin",
        },
    )
    assert resp.status_code == 400
    assert "already taken" in resp.json()["detail"]
