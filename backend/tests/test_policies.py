"""Policy Center: policies, versions, and the approval flow."""

import pytest

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


async def test_new_policy_starts_as_draft(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/policies/",
        json={"name": "Data Retention", "description": "How long we keep prompts"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "draft"
    assert body["name"] == "Data Retention"


async def test_first_version_is_created_automatically(client, org_and_users, admin_token):
    policy_resp = await client.post(
        "/api/v1/policies/",
        json={"name": "Auto Version Policy"},
        headers=auth_headers(admin_token),
    )
    policy_id = policy_resp.json()["id"]

    versions_resp = await client.get(
        f"/api/v1/policies/{policy_id}/versions",
        headers=auth_headers(admin_token),
    )
    assert versions_resp.status_code == 200
    versions = versions_resp.json()
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["approved_by"] is None


async def test_new_version_increments_and_approval_activates_policy(
    client, org_and_users, admin_token, approver_token
):
    policy_resp = await client.post(
        "/api/v1/policies/",
        json={"name": "Require Approval Policy"},
        headers=auth_headers(admin_token),
    )
    policy_id = policy_resp.json()["id"]

    version_resp = await client.post(
        f"/api/v1/policies/{policy_id}/versions",
        json={"rules_json": {"effect": "require_approval"}},
        headers=auth_headers(admin_token),
    )
    assert version_resp.status_code == 200
    version = version_resp.json()
    # Version 1 was auto-created on policy creation, so this is version 2.
    assert version["version"] == 2
    version_id = version["id"]

    # Policy is still a draft before anything is approved.
    get_resp = await client.get(
        f"/api/v1/policies/{policy_id}", headers=auth_headers(admin_token)
    )
    assert get_resp.json()["status"] == "draft"

    approve_resp = await client.post(
        f"/api/v1/policies/{policy_id}/versions/{version_id}/approve",
        headers=auth_headers(approver_token),
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["approved_by"] is not None

    get_resp = await client.get(
        f"/api/v1/policies/{policy_id}", headers=auth_headers(admin_token)
    )
    assert get_resp.json()["status"] == "active"


async def test_versions_are_listed_newest_first(client, org_and_users, admin_token):
    policy_resp = await client.post(
        "/api/v1/policies/",
        json={"name": "Multi Version Policy"},
        headers=auth_headers(admin_token),
    )
    policy_id = policy_resp.json()["id"]

    for _ in range(2):
        await client.post(
            f"/api/v1/policies/{policy_id}/versions",
            json={"rules_json": {}},
            headers=auth_headers(admin_token),
        )

    versions_resp = await client.get(
        f"/api/v1/policies/{policy_id}/versions",
        headers=auth_headers(admin_token),
    )
    versions = versions_resp.json()
    assert [v["version"] for v in versions] == [3, 2, 1]


async def test_policy_not_found_returns_404(client, org_and_users, admin_token):
    resp = await client.get(
        "/api/v1/policies/999999", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 404


async def test_policy_is_not_visible_across_organizations(client, org_and_users, admin_token):
    policy_resp = await client.post(
        "/api/v1/policies/",
        json={"name": "Org A Only Policy"},
        headers=auth_headers(admin_token),
    )
    policy_id = policy_resp.json()["id"]

    await client.post(
        "/api/v1/users/register",
        json={
            "email": "other-admin@test.example.com",
            "password": "TestPass123!",
            "name": "Other Admin",
            "org_name": "Other Org",
            "org_slug": "other-org-policies",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "org_slug": "other-org-policies",
            "email": "other-admin@test.example.com",
            "password": "TestPass123!",
        },
    )
    other_token = login.json()["access_token"]

    resp = await client.get(
        f"/api/v1/policies/{policy_id}", headers=auth_headers(other_token)
    )
    assert resp.status_code == 404
