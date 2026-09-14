"""Shadow AI Monitor: sightings, review workflow, and registering as a provider."""

import pytest

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


async def test_create_sighting_starts_as_new(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/shadow-ai/",
        json={"tool_name": "ChatGPT (personal account)", "detected_via": "expense_report"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "new"
    assert body["resolved_at"] is None


async def test_dismissing_sighting_sets_resolved_at(client, org_and_users, admin_token):
    create_resp = await client.post(
        "/api/v1/shadow-ai/",
        json={"tool_name": "Random AI Tool"},
        headers=auth_headers(admin_token),
    )
    sighting_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/shadow-ai/{sighting_id}",
        json={"status": "dismissed", "notes": "False positive"},
        headers=auth_headers(admin_token),
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["status"] == "dismissed"
    assert body["resolved_at"] is not None
    assert body["notes"] == "False positive"


async def test_reviewing_sighting_does_not_set_resolved_at(client, org_and_users, admin_token):
    create_resp = await client.post(
        "/api/v1/shadow-ai/",
        json={"tool_name": "Some Tool"},
        headers=auth_headers(admin_token),
    )
    sighting_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/shadow-ai/{sighting_id}",
        json={"status": "reviewing"},
        headers=auth_headers(admin_token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["resolved_at"] is None


async def test_summary_groups_counts_by_status(client, org_and_users, admin_token):
    await client.post(
        "/api/v1/shadow-ai/", json={"tool_name": "Tool A"}, headers=auth_headers(admin_token)
    )
    second = await client.post(
        "/api/v1/shadow-ai/", json={"tool_name": "Tool B"}, headers=auth_headers(admin_token)
    )
    await client.put(
        f"/api/v1/shadow-ai/{second.json()['id']}",
        json={"status": "dismissed"},
        headers=auth_headers(admin_token),
    )

    resp = await client.get(
        "/api/v1/shadow-ai/summary", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["new"] == 1
    assert body["dismissed"] == 1


async def test_register_as_provider_creates_provider_and_marks_registered(
    client, org_and_users, admin_token
):
    sighting_resp = await client.post(
        "/api/v1/shadow-ai/",
        json={"tool_name": "Rogue Assistant"},
        headers=auth_headers(admin_token),
    )
    sighting_id = sighting_resp.json()["id"]

    register_resp = await client.post(
        f"/api/v1/shadow-ai/{sighting_id}/register",
        json={"provider_type": "custom", "provider_sla": "best-effort"},
        headers=auth_headers(admin_token),
    )
    assert register_resp.status_code == 200
    body = register_resp.json()
    assert body["status"] == "registered"
    assert body["registered_provider_id"] is not None

    providers_resp = await client.get(
        "/api/v1/providers/", headers=auth_headers(admin_token)
    )
    provider_names = [p["name"] for p in providers_resp.json()["items"]]
    assert "Rogue Assistant" in provider_names


async def test_registering_twice_is_rejected(client, org_and_users, admin_token):
    sighting_resp = await client.post(
        "/api/v1/shadow-ai/",
        json={"tool_name": "Double Register Tool"},
        headers=auth_headers(admin_token),
    )
    sighting_id = sighting_resp.json()["id"]

    first = await client.post(
        f"/api/v1/shadow-ai/{sighting_id}/register",
        json={},
        headers=auth_headers(admin_token),
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/shadow-ai/{sighting_id}/register",
        json={},
        headers=auth_headers(admin_token),
    )
    assert second.status_code == 400


async def test_non_admin_cannot_register_sighting(client, org_and_users, approver_token):
    sighting_resp = await client.post(
        "/api/v1/shadow-ai/",
        json={"tool_name": "Approver Cannot Register This"},
        headers=auth_headers(approver_token),
    )
    sighting_id = sighting_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/shadow-ai/{sighting_id}/register",
        json={},
        headers=auth_headers(approver_token),
    )
    assert resp.status_code == 403
