"""Authentication and rate limiting."""

import pytest

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


async def test_login_success(client, org_and_users):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "org_slug": org_and_users["org"].slug,
            "email": org_and_users["admin"].email,
            "password": org_and_users["password"],
        },
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client, org_and_users):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "org_slug": org_and_users["org"].slug,
            "email": org_and_users["admin"].email,
            "password": "wrong",
        },
    )
    assert resp.status_code == 401
    assert "Incorrect" in resp.json()["detail"]


async def test_login_wrong_org_slug(client, org_and_users):
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "org_slug": "does-not-exist",
            "email": org_and_users["admin"].email,
            "password": org_and_users["password"],
        },
    )
    assert resp.status_code == 401
    # Generic message so we do not leak which orgs exist.
    assert "Incorrect" in resp.json()["detail"]


async def test_login_disabled_user(client, org_and_users, admin_token):
    # Deactivate the approver via the admin API
    resp = await client.put(
        f"/api/v1/users/{org_and_users['approver'].id}/status",
        json={"status": "disabled"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "org_slug": org_and_users["org"].slug,
            "email": org_and_users["approver"].email,
            "password": org_and_users["password"],
        },
    )
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"]


async def test_me_requires_token(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(client, org_and_users, admin_token):
    resp = await client.get(
        "/api/v1/users/me", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == org_and_users["admin"].email
    assert body["role"] == "admin"
