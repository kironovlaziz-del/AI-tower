"""
Deployment Manager: lifecycle CRUD, weighted traffic routing, and the
predict/chat wiring into TrainingService.

For predict()/chat() success paths we write a real, tiny scikit-learn
model to disk with joblib (fit on trivial data) rather than mocking
TrainingService.predict - this exercises the actual joblib-load +
model.predict() code path in training_service.py, not just our
assumption about its interface. Running an actual training job to
produce that artifact would pull in the full Celery/pandas/sklearn
training pipeline, which is out of scope here; writing the artifact
directly is a reasonable, much cheaper substitute since the loader
only cares about the bundle's shape.
"""

import joblib
import pytest
from sklearn.linear_model import LogisticRegression

from app.models.dataset import Dataset
from app.models.training_job import TrainingJob
from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


async def _create_dataset_row(db_session, org_id):
    dataset = Dataset(
        org_id=org_id,
        name="Deployment Test Dataset",
        task_type="tabular_classification",
        file_path="/tmp/unused.csv",
        file_format="csv",
        size_bytes=10,
    )
    db_session.add(dataset)
    await db_session.flush()
    return dataset


async def _create_completed_job(db_session, org_id, admin_id, tmp_path, task_type="tabular_classification"):
    import uuid

    dataset = await _create_dataset_row(db_session, org_id)

    model = LogisticRegression()
    model.fit([[0, 0], [1, 1]], [0, 1])
    bundle_path = tmp_path / f"model-{uuid.uuid4().hex}.joblib"
    joblib.dump({"model": model, "feature_columns": ["a", "b"], "label_classes": None}, bundle_path)

    job = TrainingJob(
        org_id=org_id,
        dataset_id=dataset.id,
        name="Deployable Job",
        task_type=task_type,
        target_column="label",
        algorithm="logistic_regression",
        status="completed",
        model_path=str(bundle_path),
        created_by=admin_id,
    )
    db_session.add(job)
    await db_session.flush()
    return job


async def _create_incomplete_job(db_session, org_id, admin_id):
    dataset = await _create_dataset_row(db_session, org_id)
    job = TrainingJob(
        org_id=org_id,
        dataset_id=dataset.id,
        name="Still Running",
        task_type="tabular_classification",
        target_column="label",
        algorithm="logistic_regression",
        status="running",
        created_by=admin_id,
    )
    db_session.add(job)
    await db_session.flush()
    return job


# ---------------------------------------------------------------------------
# create_deployment
# ---------------------------------------------------------------------------

async def test_create_deployment_requires_completed_job(
    client, org_and_users, admin_token, db_session
):
    job = await _create_incomplete_job(
        db_session, org_and_users["org"].id, org_and_users["admin"].id
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job.id, "name": "my-model"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400


async def test_create_deployment_job_not_found(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": 999999, "name": "my-model"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


async def test_create_deployment_auto_increments_version(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job1 = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    job2 = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    first = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job1.id, "name": "shared-name"},
        headers=auth_headers(admin_token),
    )
    assert first.json()["version"] == 1

    second = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job2.id, "name": "shared-name"},
        headers=auth_headers(admin_token),
    )
    assert second.json()["version"] == 2


async def test_create_deployment_rejects_duplicate_name_version(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    payload = {"training_job_id": job.id, "name": "dupe-name", "version": 1}
    first = await client.post(
        "/api/v1/deployments/", json=payload, headers=auth_headers(admin_token)
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/deployments/", json=payload, headers=auth_headers(admin_token)
    )
    assert second.status_code == 400


async def test_non_admin_cannot_create_deployment(client, org_and_users, approver_token):
    resp = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": 1, "name": "x"},
        headers=auth_headers(approver_token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# update / delete
# ---------------------------------------------------------------------------

async def test_update_deployment_is_partial(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job.id, "name": "updatable", "traffic_weight": 1.0},
        headers=auth_headers(admin_token),
    )
    dep_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/deployments/{dep_id}",
        json={"traffic_weight": 0.5},
        headers=auth_headers(admin_token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["traffic_weight"] == 0.5
    assert update_resp.json()["status"] == "active"  # untouched


async def test_delete_deployment_archives_rather_than_removes(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job.id, "name": "archivable"},
        headers=auth_headers(admin_token),
    )
    dep_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/deployments/{dep_id}", headers=auth_headers(admin_token)
    )
    assert delete_resp.status_code == 200

    get_resp = await client.get(
        f"/api/v1/deployments/{dep_id}", headers=auth_headers(admin_token)
    )
    assert get_resp.status_code == 200  # still exists...
    assert get_resp.json()["status"] == "archived"  # ...just archived


# ---------------------------------------------------------------------------
# predict() - against a real tiny sklearn artifact on disk
# ---------------------------------------------------------------------------

async def test_predict_on_inactive_deployment_is_rejected(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job.id, "name": "inactive-test"},
        headers=auth_headers(admin_token),
    )
    dep_id = create_resp.json()["id"]
    await client.put(
        f"/api/v1/deployments/{dep_id}",
        json={"status": "inactive"},
        headers=auth_headers(admin_token),
    )

    resp = await client.post(
        f"/api/v1/deployments/{dep_id}/predict",
        json={"features": {"a": 1, "b": 1}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "deployment.not_active"


async def test_predict_success_returns_real_model_output(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job.id, "name": "predictable"},
        headers=auth_headers(admin_token),
    )
    dep_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/deployments/{dep_id}/predict",
        json={"features": {"a": 1, "b": 1}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deployment_id"] == dep_id
    assert body["version"] == 1
    # The LogisticRegression was fit so that [1, 1] -> class 1.
    assert body["prediction"] == 1


# ---------------------------------------------------------------------------
# route_predict - weighted traffic split
# ---------------------------------------------------------------------------

async def test_route_predict_no_active_deployments_returns_404(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/deployments/by-name/does-not-exist/predict",
        json={"features": {"a": 1, "b": 1}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "deployment.name_not_found"


async def test_route_predict_all_zero_weight_rejected(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job.id, "name": "zero-weight", "traffic_weight": 0.0},
        headers=auth_headers(admin_token),
    )

    resp = await client.post(
        "/api/v1/deployments/by-name/zero-weight/predict",
        json={"features": {"a": 1, "b": 1}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "deployment.no_active_traffic"


async def test_route_predict_always_picks_the_only_nonzero_weight_deployment(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job1 = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    job2 = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    zero = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job1.id, "name": "weighted", "traffic_weight": 0.0},
        headers=auth_headers(admin_token),
    )
    full = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job2.id, "name": "weighted", "traffic_weight": 1.0},
        headers=auth_headers(admin_token),
    )

    # Run a few times - it must never route to the zero-weight deployment.
    for _ in range(5):
        resp = await client.post(
            "/api/v1/deployments/by-name/weighted/predict",
            json={"features": {"a": 1, "b": 1}},
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["routed_to"]["id"] == full.json()["id"]


# ---------------------------------------------------------------------------
# chat() - validation branches only (transformer inference is out of scope
# here - it needs a real HF model directory on disk, which is much more
# expensive to fake convincingly than a joblib bundle).
# ---------------------------------------------------------------------------

async def test_chat_rejects_tabular_deployments(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job.id, "name": "not-chattable"},
        headers=auth_headers(admin_token),
    )
    dep_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/deployments/{dep_id}/chat",
        json={"message": "hello"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "deployment.tabular_not_chat"


async def test_chat_on_inactive_deployment_is_rejected(
    client, org_and_users, admin_token, db_session, tmp_path
):
    org_id = org_and_users["org"].id
    admin_id = org_and_users["admin"].id
    job = await _create_completed_job(db_session, org_id, admin_id, tmp_path)
    await db_session.commit()

    create_resp = await client.post(
        "/api/v1/deployments/",
        json={"training_job_id": job.id, "name": "inactive-chat"},
        headers=auth_headers(admin_token),
    )
    dep_id = create_resp.json()["id"]
    await client.put(
        f"/api/v1/deployments/{dep_id}",
        json={"status": "inactive"},
        headers=auth_headers(admin_token),
    )

    resp = await client.post(
        f"/api/v1/deployments/{dep_id}/chat",
        json={"message": "hello"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "deployment.not_active"
