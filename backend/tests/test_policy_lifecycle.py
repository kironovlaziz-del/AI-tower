"""
Tests for the policy lifecycle endpoints (archive / activate) added so
unwanted policies can be taken out of effect without deleting them (audit
history is preserved — there is intentionally no hard delete).
"""

import pytest

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


async def _make_policy(client, token, name="Lifecycle Policy"):
    resp = await client.post(
        "/api/v1/policies/", json={"name": name}, headers=auth_headers(token)
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def test_archive_sets_status_archived(client, org_and_users, admin_token):
    pid = await _make_policy(client, admin_token)
    resp = await client.post(f"/api/v1/policies/{pid}/archive", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


async def test_activate_sets_status_active(client, org_and_users, admin_token):
    pid = await _make_policy(client, admin_token)
    await client.post(f"/api/v1/policies/{pid}/archive", headers=auth_headers(admin_token))
    resp = await client.post(f"/api/v1/policies/{pid}/activate", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


async def test_archive_is_admin_only(client, org_and_users, admin_token, approver_token):
    pid = await _make_policy(client, admin_token)
    resp = await client.post(f"/api/v1/policies/{pid}/archive", headers=auth_headers(approver_token))
    assert resp.status_code == 403


async def test_activate_is_admin_only(client, org_and_users, admin_token, approver_token):
    pid = await _make_policy(client, admin_token)
    resp = await client.post(f"/api/v1/policies/{pid}/activate", headers=auth_headers(approver_token))
    assert resp.status_code == 403


async def test_archive_missing_policy_is_404(client, org_and_users, admin_token):
    resp = await client.post("/api/v1/policies/999999/archive", headers=auth_headers(admin_token))
    assert resp.status_code == 404


async def test_no_delete_endpoint(client, org_and_users, admin_token):
    """Hard delete was intentionally removed to preserve the audit trail;
    DELETE must not be a valid method on a policy."""
    pid = await _make_policy(client, admin_token)
    resp = await client.delete(f"/api/v1/policies/{pid}", headers=auth_headers(admin_token))
    assert resp.status_code in (404, 405)  # method not allowed / not found
