"""Notification channels: target validation, duplicates, and admin-only writes."""

import pytest

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


async def test_create_email_channel_normalizes_case(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/notification-channels/",
        json={
            "channel_type": "email",
            "target": "Ops@Example.COM",
            "events": ["incident_created"],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["target"] == "ops@example.com"


async def test_invalid_email_target_rejected(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/notification-channels/",
        json={"channel_type": "email", "target": "not-an-email", "events": []},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


async def test_webhook_must_have_http_scheme(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/notification-channels/",
        json={
            "channel_type": "webhook",
            "target": "ftp://example.com/hook",
            "events": ["incident_created"],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


async def test_webhook_trailing_slash_is_normalized(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/notification-channels/",
        json={
            "channel_type": "webhook",
            "target": "https://example.com/hook/",
            "events": ["incident_created"],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["target"] == "https://example.com/hook"


async def test_duplicate_channel_in_same_org_rejected(client, org_and_users, admin_token):
    payload = {
        "channel_type": "email",
        "target": "dupe@example.com",
        "events": ["incident_created"],
    }
    first = await client.post(
        "/api/v1/notification-channels/", json=payload, headers=auth_headers(admin_token)
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/notification-channels/", json=payload, headers=auth_headers(admin_token)
    )
    assert second.status_code == 400


async def test_non_admin_cannot_create_channel(client, org_and_users, approver_token):
    resp = await client.post(
        "/api/v1/notification-channels/",
        json={"channel_type": "email", "target": "x@example.com", "events": []},
        headers=auth_headers(approver_token),
    )
    assert resp.status_code == 403


async def test_non_admin_cannot_delete_channel(client, org_and_users, admin_token, approver_token):
    create_resp = await client.post(
        "/api/v1/notification-channels/",
        json={"channel_type": "email", "target": "keep@example.com", "events": []},
        headers=auth_headers(admin_token),
    )
    channel_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/notification-channels/{channel_id}", headers=auth_headers(approver_token)
    )
    assert resp.status_code == 403


async def test_delete_channel_removes_it(client, org_and_users, admin_token):
    create_resp = await client.post(
        "/api/v1/notification-channels/",
        json={"channel_type": "email", "target": "gone@example.com", "events": []},
        headers=auth_headers(admin_token),
    )
    channel_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/notification-channels/{channel_id}", headers=auth_headers(admin_token)
    )
    assert delete_resp.status_code == 200

    list_resp = await client.get(
        "/api/v1/notification-channels/", headers=auth_headers(admin_token)
    )
    assert list_resp.json()["items"] == []


async def test_send_test_dispatches_without_real_network_call(
    client, org_and_users, admin_token, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        "app.services.notification_service._dispatch",
        lambda channel, subject, message, metadata: calls.append(channel.target),
    )

    create_resp = await client.post(
        "/api/v1/notification-channels/",
        json={"channel_type": "webhook", "target": "https://example.com/hook", "events": []},
        headers=auth_headers(admin_token),
    )
    channel_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/notification-channels/{channel_id}/test",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert calls == ["https://example.com/hook"]


async def test_list_event_types_requires_no_auth(client, org_and_users):
    """
    This endpoint has no auth dependency at all (see notification_channels.py) -
    it only returns the static list of event-type constants, so that's fine,
    but the test documents the behavior explicitly rather than assuming it.
    """
    resp = await client.get("/api/v1/notification-channels/event-types")
    assert resp.status_code == 200
    assert "incident_created" in resp.json()["event_types"]
