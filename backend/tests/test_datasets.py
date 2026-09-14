"""Dataset uploads: extension/size validation, storage, and deletion."""

import os

import pytest

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


async def test_upload_dataset_success(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/datasets/",
        data={"name": "Support Tickets", "task_type": "classification"},
        files={"file": ("tickets.csv", b"text,label\nhello,greeting\n", "text/csv")},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Support Tickets"
    assert body["file_format"] == "csv"
    assert body["size_bytes"] == len(b"text,label\nhello,greeting\n")


async def test_upload_rejects_unsupported_extension(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/datasets/",
        data={"name": "Suspicious", "task_type": "other"},
        files={"file": ("payload.exe", b"MZ\x90\x00", "application/octet-stream")},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


async def test_upload_sanitizes_path_traversal_filename(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/datasets/",
        data={"name": "Traversal Attempt", "task_type": "other"},
        files={"file": ("../../etc/passwd.csv", b"a,b\n1,2\n", "text/csv")},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    # Confirm the file actually landed inside this org's dataset directory,
    # not wherever the traversal-style name would otherwise point.
    from app.core.config import settings

    org_id = org_and_users["org"].id
    stored_files = os.listdir(os.path.join(settings.DATASETS_DIR, str(org_id)))
    assert all(".." not in f and "/" not in f for f in stored_files)


async def test_delete_dataset_removes_it_from_listing(client, org_and_users, admin_token):
    create_resp = await client.post(
        "/api/v1/datasets/",
        data={"name": "Temp Dataset", "task_type": "other"},
        files={"file": ("temp.csv", b"a,b\n1,2\n", "text/csv")},
        headers=auth_headers(admin_token),
    )
    dataset_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/datasets/{dataset_id}", headers=auth_headers(admin_token)
    )
    assert delete_resp.status_code == 200

    get_resp = await client.get(
        f"/api/v1/datasets/{dataset_id}", headers=auth_headers(admin_token)
    )
    assert get_resp.status_code == 404


async def test_dataset_not_visible_across_organizations(client, org_and_users, admin_token):
    create_resp = await client.post(
        "/api/v1/datasets/",
        data={"name": "Org A Dataset", "task_type": "other"},
        files={"file": ("data.csv", b"a,b\n1,2\n", "text/csv")},
        headers=auth_headers(admin_token),
    )
    dataset_id = create_resp.json()["id"]

    await client.post(
        "/api/v1/users/register",
        json={
            "email": "other-admin@test.example.com",
            "password": "TestPass123!",
            "name": "Other Admin",
            "org_name": "Other Org",
            "org_slug": "other-org-datasets",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "org_slug": "other-org-datasets",
            "email": "other-admin@test.example.com",
            "password": "TestPass123!",
        },
    )
    other_token = login.json()["access_token"]

    resp = await client.get(
        f"/api/v1/datasets/{dataset_id}", headers=auth_headers(other_token)
    )
    assert resp.status_code == 404
