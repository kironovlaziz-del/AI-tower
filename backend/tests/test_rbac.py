"""Role-based access control."""

import pytest

from tests.conftest import auth_headers
from tests.test_approvals import _make_use_case_with_approval_policy


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
    assert len(resp.json()["items"]) == 2


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


async def _invite_and_login_plain_user(client, org_and_users, admin_token):
    """Create a role='user' account and return its access token."""
    await client.post(
        "/api/v1/users/invite",
        json={
            "email": "plainuser@test.example.com",
            "name": "Plain User",
            "password": "TestPass123!",
            "role": "user",
        },
        headers=auth_headers(admin_token),
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "org_slug": org_and_users["org"].slug,
            "email": "plainuser@test.example.com",
            "password": "TestPass123!",
        },
    )
    return login_resp.json()["access_token"]


async def test_plain_user_cannot_create_override(client, org_and_users, admin_token):
    """
    Regression test: creating an override (stop / edit / rollback an AI
    request) is an operator-level action and must be gated the same way
    approval decisions are - admin or approver only, not a plain 'user'.
    """
    use_case_id, provider_id, _ = await _make_use_case_with_approval_policy(
        client, admin_token
    )
    req_resp = await client.post(
        "/api/v1/requests/",
        json={
            "use_case_id": use_case_id,
            "provider_id": provider_id,
            "input_text": "test",
            "purpose": "test",
        },
        headers=auth_headers(admin_token),
    )
    request_id = req_resp.json()["id"]

    plain_user_token = await _invite_and_login_plain_user(
        client, org_and_users, admin_token
    )

    resp = await client.post(
        "/api/v1/overrides/",
        json={"request_id": request_id, "override_type": "stop"},
        headers=auth_headers(plain_user_token),
    )
    assert resp.status_code == 403


async def test_approver_can_create_override(client, org_and_users, approver_token, admin_token):
    """Approvers remain allowed to intervene on a request."""
    use_case_id, provider_id, _ = await _make_use_case_with_approval_policy(
        client, admin_token
    )
    req_resp = await client.post(
        "/api/v1/requests/",
        json={
            "use_case_id": use_case_id,
            "provider_id": provider_id,
            "input_text": "test",
            "purpose": "test",
        },
        headers=auth_headers(admin_token),
    )
    request_id = req_resp.json()["id"]

    resp = await client.post(
        "/api/v1/overrides/",
        json={"request_id": request_id, "override_type": "stop"},
        headers=auth_headers(approver_token),
    )
    assert resp.status_code == 200
