"""
Training Service: LoRA parameter validation and the create/cancel/retry
job lifecycle.

Note on Celery: the autouse `mock_celery_send_task` fixture in conftest.py
covers `celery_app.send_task(...)` (used by create_job/retry_job), but
`cancel_job` also calls `celery_app.control.revoke(...)`, which is a
*different* call path that fixture does not touch. CI has no Redis
service at all (see .github/workflows/ci.yml - only postgres is
provisioned), so any cancel-job test that doesn't mock `control.revoke`
explicitly will pass locally against a real Redis and then fail in CI.
"""

import pytest

from app.core.celery_app import celery_app
from app.services.training_service import _validate_lora_params
from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# _validate_lora_params - pure function, no DB/API needed
# ---------------------------------------------------------------------------

def test_lora_validation_is_a_noop_when_lora_not_requested():
    result = _validate_lora_params({"some_other_key": 1})
    assert result == {"some_other_key": 1}


def test_lora_validation_fills_in_defaults():
    result = _validate_lora_params({"use_lora": True})
    assert result["lora_r"] == 8
    assert result["lora_alpha"] == 16
    assert result["lora_dropout"] == 0.05


@pytest.mark.parametrize("bad_r", [0, -1, 257, 1000])
def test_lora_r_out_of_range_is_rejected(bad_r):
    with pytest.raises(Exception) as exc_info:
        _validate_lora_params({"use_lora": True, "lora_r": bad_r})
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "training.lora_r_range"


@pytest.mark.parametrize("good_r", [1, 8, 128, 256])
def test_lora_r_in_range_is_accepted(good_r):
    result = _validate_lora_params({"use_lora": True, "lora_r": good_r})
    assert result["lora_r"] == good_r


@pytest.mark.parametrize("bad_alpha", [0, -5, 513])
def test_lora_alpha_out_of_range_is_rejected(bad_alpha):
    with pytest.raises(Exception) as exc_info:
        _validate_lora_params({"use_lora": True, "lora_alpha": bad_alpha})
    assert exc_info.value.detail["code"] == "training.lora_alpha_range"


@pytest.mark.parametrize("bad_dropout", [-0.1, 0.91, 1.0])
def test_lora_dropout_out_of_range_is_rejected(bad_dropout):
    with pytest.raises(Exception) as exc_info:
        _validate_lora_params({"use_lora": True, "lora_dropout": bad_dropout})
    assert exc_info.value.detail["code"] == "training.lora_dropout_range"


def test_lora_target_modules_must_be_list_of_strings():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        _validate_lora_params(
            {"use_lora": True, "lora_target_modules": "query_key_value"}
        )
    assert exc_info.value.status_code == 400


def test_lora_target_modules_rejects_empty_strings_in_list():
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        _validate_lora_params(
            {"use_lora": True, "lora_target_modules": ["query", "   "]}
        )


def test_lora_target_modules_are_stripped():
    result = _validate_lora_params(
        {"use_lora": True, "lora_target_modules": [" query ", "value"]}
    )
    assert result["lora_target_modules"] == ["query", "value"]


# ---------------------------------------------------------------------------
# create_job - validation branches, via the real API
# ---------------------------------------------------------------------------

async def _upload_csv_dataset(client, admin_token, name="Training Dataset"):
    resp = await client.post(
        "/api/v1/datasets/",
        data={"name": name, "task_type": "tabular_classification"},
        files={
            "file": (
                "data.csv",
                b"feature_a,feature_b,label\n1,2,yes\n3,4,no\n",
                "text/csv",
            )
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def test_create_job_requires_existing_dataset(client, org_and_users, admin_token):
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": 999999,
            "name": "test",
            "task_type": "tabular_classification",
            "target_column": "label",
            "algorithm": "logistic_regression",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


async def test_create_job_rejects_unsupported_dataset_format(client, org_and_users, admin_token):
    dataset_resp = await client.post(
        "/api/v1/datasets/",
        data={"name": "JSON Dataset", "task_type": "other"},
        files={"file": ("data.json", b'{"a": 1}', "application/json")},
        headers=auth_headers(admin_token),
    )
    dataset_id = dataset_resp.json()["id"]

    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "tabular_classification",
            "target_column": "label",
            "algorithm": "logistic_regression",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "csv/tsv" in resp.json()["detail"]


async def test_tabular_job_requires_target_column(client, org_and_users, admin_token):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "tabular_classification",
            "algorithm": "logistic_regression",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "target_column" in resp.json()["detail"]


async def test_tabular_job_requires_algorithm(client, org_and_users, admin_token):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "tabular_classification",
            "target_column": "label",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "algorithm" in resp.json()["detail"]


async def test_algorithm_task_type_mismatch_is_rejected(client, org_and_users, admin_token):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "tabular_classification",
            "target_column": "label",
            # linear_regression is only valid for tabular_regression.
            "algorithm": "linear_regression",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "does not match task_type" in resp.json()["detail"]


async def test_valid_tabular_job_is_created_and_queued(client, org_and_users, admin_token):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "My Model",
            "task_type": "tabular_classification",
            "target_column": "label",
            "algorithm": "logistic_regression",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    assert body["celery_task_id"] == "test-task-id"  # from the autouse fake


async def test_auto_tune_flags_are_stored_in_hyperparameters(client, org_and_users, admin_token):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "Auto-tuned Model",
            "task_type": "tabular_classification",
            "target_column": "label",
            "algorithm": "logistic_regression",
            "auto_tune": True,
            "auto_tune_trials": 15,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    hyperparams = resp.json()["hyperparameters_json"]
    assert hyperparams["_auto_tune_requested"] is True
    assert hyperparams["n_trials"] == 15


async def test_transformer_job_requires_base_model(client, org_and_users, admin_token):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "transformer_text_classification",
            "target_column": "label",
            "hyperparameters": {"text_column": "feature_a"},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "base_model is required" in resp.json()["detail"]


async def test_transformer_job_requires_text_column(client, org_and_users, admin_token):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "transformer_text_classification",
            "target_column": "label",
            "base_model": "google/bert_uncased_L-2_H-128_A-2",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "text_column is required" in resp.json()["detail"]


async def test_transformer_classification_requires_target_column(client, org_and_users, admin_token):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "transformer_text_classification",
            "base_model": "google/bert_uncased_L-2_H-128_A-2",
            "hyperparameters": {"text_column": "feature_a"},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "target_column" in resp.json()["detail"]


async def test_transformer_generation_does_not_require_target_column(client, org_and_users, admin_token):
    """Generation is self-supervised - target_column is auto-set to the
    text column rather than being required from the caller."""
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "transformer_text_generation",
            "base_model": "sshleifer/tiny-gpt2",
            "hyperparameters": {"text_column": "feature_a"},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["target_column"] == "feature_a"


async def test_gpu_only_model_is_rejected_without_gpu(client, org_and_users, admin_token):
    """
    bert-base-uncased is in GPU_ADDITIONAL_MODELS - on this CPU-only test
    host, compute_detector reports gpu_available=False for real (no
    mocking needed - there genuinely is no GPU in CI or on a typical dev
    box), so this must be rejected.
    """
    dataset_id = await _upload_csv_dataset(client, admin_token)
    resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "transformer_text_classification",
            "target_column": "label",
            "base_model": "bert-base-uncased",
            "hyperparameters": {"text_column": "feature_a"},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "training.model_requires_gpu"


# ---------------------------------------------------------------------------
# cancel_job / retry_job - state machine
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_celery_revoke(monkeypatch):
    """
    cancel_job() calls celery_app.control.revoke(...), a real network call
    to the Celery broker that the autouse mock_celery_send_task fixture in
    conftest.py does NOT cover. Mock it here so these tests don't depend
    on a live Redis - CI has none (see module docstring above).
    """
    monkeypatch.setattr(celery_app.control, "revoke", lambda *a, **kw: None)


async def test_cancel_queued_job_succeeds(client, org_and_users, admin_token):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    create_resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "tabular_classification",
            "target_column": "label",
            "algorithm": "logistic_regression",
        },
        headers=auth_headers(admin_token),
    )
    job_id = create_resp.json()["id"]

    cancel_resp = await client.post(
        f"/api/v1/training-jobs/{job_id}/cancel", headers=auth_headers(admin_token)
    )
    assert cancel_resp.status_code == 200
    body = cancel_resp.json()
    assert body["status"] == "cancelled"
    assert body["finished_at"] is not None


async def test_cancel_already_completed_job_is_rejected(client, org_and_users, admin_token, db_session):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    create_resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "tabular_classification",
            "target_column": "label",
            "algorithm": "logistic_regression",
        },
        headers=auth_headers(admin_token),
    )
    job_id = create_resp.json()["id"]

    from app.models.training_job import TrainingJob

    job = await db_session.get(TrainingJob, job_id)
    job.status = "completed"
    await db_session.commit()

    cancel_resp = await client.post(
        f"/api/v1/training-jobs/{job_id}/cancel", headers=auth_headers(admin_token)
    )
    assert cancel_resp.status_code == 400


async def test_retry_failed_job_resets_state_and_requeues(client, org_and_users, admin_token, db_session):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    create_resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "tabular_classification",
            "target_column": "label",
            "algorithm": "logistic_regression",
        },
        headers=auth_headers(admin_token),
    )
    job_id = create_resp.json()["id"]

    from app.models.training_job import TrainingJob

    job = await db_session.get(TrainingJob, job_id)
    job.status = "failed"
    job.error_message = "boom"
    job.metrics_json = {"accuracy": 0.5}
    await db_session.commit()

    retry_resp = await client.post(
        f"/api/v1/training-jobs/{job_id}/retry", headers=auth_headers(admin_token)
    )
    assert retry_resp.status_code == 200
    body = retry_resp.json()
    assert body["status"] == "queued"
    assert body["error_message"] is None
    assert body["metrics_json"] is None


async def test_retry_running_job_is_rejected(client, org_and_users, admin_token, db_session):
    dataset_id = await _upload_csv_dataset(client, admin_token)
    create_resp = await client.post(
        "/api/v1/training-jobs/",
        json={
            "dataset_id": dataset_id,
            "name": "test",
            "task_type": "tabular_classification",
            "target_column": "label",
            "algorithm": "logistic_regression",
        },
        headers=auth_headers(admin_token),
    )
    job_id = create_resp.json()["id"]

    from app.models.training_job import TrainingJob

    job = await db_session.get(TrainingJob, job_id)
    job.status = "running"
    await db_session.commit()

    retry_resp = await client.post(
        f"/api/v1/training-jobs/{job_id}/retry", headers=auth_headers(admin_token)
    )
    assert retry_resp.status_code == 400


async def test_training_job_not_found_returns_404(client, org_and_users, admin_token):
    resp = await client.get(
        "/api/v1/training-jobs/999999", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 404
