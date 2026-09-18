"""
docker_runner.py: launching training jobs in isolated containers via the
`docker` SDK.

`docker` (docker-py) is only imported lazily inside `_client()`, so every
test here installs a fake module into sys.modules instead of requiring a
real Docker daemon - this suite runs the same whether or not Docker is
even installed on the box running it.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import docker_runner


class _FakeContainer:
    def __init__(self, wait_result=0, logs=b"", raise_on_wait=None, raise_on_remove=False):
        self.wait_calls = 0
        self.remove_calls = []
        self._wait_result = wait_result
        self._logs = logs
        self._raise_on_wait = raise_on_wait
        self._raise_on_remove = raise_on_remove

    def wait(self):
        self.wait_calls += 1
        if self._raise_on_wait:
            raise self._raise_on_wait
        return self._wait_result

    def logs(self, stdout=True, stderr=True):
        return self._logs

    def remove(self, force=False):
        self.remove_calls.append(force)
        if self._raise_on_remove:
            raise RuntimeError("container already gone")


class _FakeContainersAPI:
    def __init__(self, container):
        self._container = container
        self.run_calls = []

    def run(self, image, **kwargs):
        self.run_calls.append({"image": image, **kwargs})
        return self._container


class _FakeDockerClient:
    def __init__(self, container):
        self.containers = _FakeContainersAPI(container)


def _install_fake_docker(monkeypatch, container):
    fake_client = _FakeDockerClient(container)
    fake_docker_module = SimpleNamespace(from_env=lambda: fake_client)
    monkeypatch.setitem(sys.modules, "docker", fake_docker_module)
    return fake_client


@pytest.fixture(autouse=True)
def _isolate_hf_cache_dir(monkeypatch, tmp_path):
    """run_job_in_container() does Path.home()/'.cache'/'huggingface'.mkdir(...) -
    redirect that to a temp dir so tests never touch the real home dir."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


@pytest.fixture(autouse=True)
def _configure_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "TRAINING_RUNNER_IMAGE", "ai-control-tower/training:test")
    monkeypatch.setattr(settings, "MODELS_DIR", str(tmp_path / "models"))
    monkeypatch.setattr(settings, "DATASETS_DIR", str(tmp_path / "datasets"))
    monkeypatch.setattr(settings, "TRAINING_CONTAINER_CPUS", 2.0)
    monkeypatch.setattr(settings, "TRAINING_CONTAINER_MEMORY", "4g")
    monkeypatch.setattr(settings, "SECRET_KEY", "test-secret")
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "test-encryption-key")
    monkeypatch.setattr(settings, "POSTGRES_USER", "test_user")
    monkeypatch.setattr(settings, "POSTGRES_PASSWORD", "test_password")
    monkeypatch.setattr(settings, "POSTGRES_DB", "test_db")
    monkeypatch.setattr(settings, "POSTGRES_PORT", 5432)
    monkeypatch.setattr(settings, "REDIS_PORT", 6379)
    monkeypatch.setattr(settings, "REDIS_PASSWORD", "test-redis-pw")


# ---------------------------------------------------------------------------
# _client()
# ---------------------------------------------------------------------------

def test_client_raises_helpful_error_when_docker_sdk_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "docker", None)  # forces ImportError

    with pytest.raises(RuntimeError, match="pip install docker"):
        docker_runner._client()


def test_client_returns_docker_from_env_result(monkeypatch):
    container = _FakeContainer()
    fake_client = _install_fake_docker(monkeypatch, container)

    assert docker_runner._client() is fake_client


# ---------------------------------------------------------------------------
# run_job_in_container()
# ---------------------------------------------------------------------------

def test_run_job_passes_secrets_and_resource_limits(monkeypatch):
    container = _FakeContainer(wait_result=0, logs=b"training done\n")
    fake_client = _install_fake_docker(monkeypatch, container)

    docker_runner.run_job_in_container(42)

    assert len(fake_client.containers.run_calls) == 1
    call = fake_client.containers.run_calls[0]

    assert call["image"] == "ai-control-tower/training:test"
    assert call["detach"] is True
    assert call["environment"]["JOB_ID"] == "42"
    assert call["environment"]["SECRET_KEY"] == "test-secret"
    assert call["environment"]["ENCRYPTION_KEY"] == "test-encryption-key"
    assert call["environment"]["POSTGRES_PASSWORD"] == "test_password"
    assert call["environment"]["REDIS_PASSWORD"] == "test-redis-pw"
    # Nano CPUs is TRAINING_CONTAINER_CPUS * 1e9.
    assert call["nano_cpus"] == 2_000_000_000
    assert call["mem_limit"] == "4g"
    assert call["extra_hosts"] == {"host.docker.internal": "host-gateway"}
    assert call["network"] == "bridge"


def test_run_job_points_host_gateway_at_containers_needing_host_services(monkeypatch):
    container = _FakeContainer()
    fake_client = _install_fake_docker(monkeypatch, container)

    docker_runner.run_job_in_container(1)

    # Inside the container, "localhost" is itself - Postgres/Redis must be
    # reached via the host gateway hostname, not settings.POSTGRES_HOST.
    call = fake_client.containers.run_calls[0]
    assert call["environment"]["POSTGRES_HOST"] == "host.docker.internal"
    assert call["environment"]["REDIS_HOST"] == "host.docker.internal"


def test_run_job_mounts_datasets_readonly_and_models_readwrite(monkeypatch, tmp_path):
    container = _FakeContainer()
    fake_client = _install_fake_docker(monkeypatch, container)

    docker_runner.run_job_in_container(1)

    call = fake_client.containers.run_calls[0]
    datasets_dir = str((tmp_path / "datasets").resolve())
    models_dir = str((tmp_path / "models").resolve())
    assert call["volumes"][datasets_dir]["mode"] == "ro"
    assert call["volumes"][models_dir]["mode"] == "rw"


def test_run_job_always_removes_container_even_on_wait_failure(monkeypatch):
    container = _FakeContainer(raise_on_wait=RuntimeError("container crashed"))
    _install_fake_docker(monkeypatch, container)

    with pytest.raises(RuntimeError, match="container crashed"):
        docker_runner.run_job_in_container(1)

    # The finally-block cleanup must still have run.
    assert container.remove_calls == [True]


def test_run_job_swallows_errors_from_container_remove_itself(monkeypatch):
    container = _FakeContainer(wait_result=0, raise_on_remove=True)
    _install_fake_docker(monkeypatch, container)

    # Must not raise, even though container.remove() itself blows up.
    docker_runner.run_job_in_container(1)
    assert container.remove_calls == [True]


def test_run_job_logs_are_decoded_and_split_by_line(monkeypatch, caplog):
    container = _FakeContainer(wait_result=0, logs="line one\nline two\n".encode("utf-8"))
    _install_fake_docker(monkeypatch, container)

    import logging

    with caplog.at_level(logging.INFO, logger="docker_runner"):
        docker_runner.run_job_in_container(7)

    messages = [r.message for r in caplog.records]
    assert any("line one" in m for m in messages)
    assert any("line two" in m for m in messages)


# ---------------------------------------------------------------------------
# _host_gateway()
# ---------------------------------------------------------------------------

def test_host_gateway_is_the_docker_internal_hostname():
    assert docker_runner._host_gateway() == "host.docker.internal"
