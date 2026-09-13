"""
Launch training jobs in isolated Docker containers.

Uses the docker SDK (not subprocess) so we can stream logs, inspect
exit codes, and pass resource limits without shell quoting issues.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("docker_runner")


def _client():
    """
    Lazy import so the backend can still run without the docker SDK
    installed when TRAINING_USE_DOCKER=false.
    """
    try:
        import docker
    except ImportError as exc:
        raise RuntimeError(
            "The 'docker' Python package is required when "
            "TRAINING_USE_DOCKER=true. Install it with: pip install docker"
        ) from exc
    return docker.from_env()


def run_job_in_container(job_id: int) -> None:
    """
    Launch a one-shot container for the given training job and block
    until it exits. Anything the container prints on stdout/stderr is
    forwarded to the worker log so operators see the same training trace
    as in legacy mode.
    """
    client = _client()

    # Paths on the host that the container must see. settings.MODELS_DIR
    # and DATASETS_DIR are absolute (resolved in config.py), so we can
    # mount them directly.
    backend_root = Path(__file__).resolve().parents[2]
    models_dir = Path(settings.MODELS_DIR).resolve()
    datasets_dir = Path(settings.DATASETS_DIR).resolve()
    hf_cache = Path.home() / ".cache" / "huggingface"
    hf_cache.mkdir(parents=True, exist_ok=True)

    environment = {
        "JOB_ID": str(job_id),
        "ENVIRONMENT": settings.ENVIRONMENT,
        "DEBUG": "false",
        "SECRET_KEY": settings.SECRET_KEY,
        "ENCRYPTION_KEY": settings.ENCRYPTION_KEY or "",
        "POSTGRES_USER": settings.POSTGRES_USER,
        "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
        "POSTGRES_DB": settings.POSTGRES_DB,
        # Inside the container, "localhost" is the container itself. The
        # host is reachable as host.docker.internal on Docker Desktop and
        # via the docker0 bridge IP on Linux; we pass an explicit override
        # so the operator can point this at the host's docker0 address.
        "POSTGRES_HOST": _host_gateway(),
        "POSTGRES_PORT": str(settings.POSTGRES_PORT),
        "REDIS_HOST": _host_gateway(),
        "REDIS_PORT": str(settings.REDIS_PORT),
        "REDIS_PASSWORD": settings.REDIS_PASSWORD or "",
        "DATASETS_DIR": str(datasets_dir),
        "MODELS_DIR": str(models_dir),
    }

    volumes = {
        str(datasets_dir): {"bind": str(datasets_dir), "mode": "ro"},
        str(models_dir): {"bind": str(models_dir), "mode": "rw"},
        str(hf_cache): {"bind": "/cache/huggingface", "mode": "rw"},
    }

    logger.info("Launching training container for job %s", job_id)

    container = client.containers.run(
        settings.TRAINING_RUNNER_IMAGE,
        detach=True,
        remove=False,
        environment=environment,
        volumes=volumes,
        # Resource limits keep a runaway job from pinning the host.
        nano_cpus=int(settings.TRAINING_CONTAINER_CPUS * 1_000_000_000),
        mem_limit=settings.TRAINING_CONTAINER_MEMORY,
        # Allow the container to reach services on the host (Postgres,
        # Redis). Linux only; on Docker Desktop the default bridge
        # already provides host.docker.internal.
        extra_hosts={"host.docker.internal": "host-gateway"},
        network="bridge",
    )

    try:
        exit_code = container.wait()
        logs = container.logs(stdout=True, stderr=True).decode(
            "utf-8", errors="replace"
        )
        logger.info(
            "Training container for job %s exited with %s", job_id, exit_code
        )
        for line in logs.splitlines():
            logger.info("[job-%s] %s", job_id, line)
    finally:
        # Remove the container but keep any artifacts it wrote into the
        # mounted models directory.
        try:
            container.remove(force=True)
        except Exception:  # noqa: BLE001
            pass


def _host_gateway() -> str:
    """
    Address the container can use to reach services on the Docker host.
    On Linux this is the docker0 bridge (typically 172.17.0.1); we expose
    the hostname `host.docker.internal` via extra_hosts and let the
    container resolve it.
    """
    return "host.docker.internal"
