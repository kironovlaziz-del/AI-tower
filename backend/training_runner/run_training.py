"""
Entrypoint for the isolated training container.

The Celery worker on the host invokes this inside a fresh container per
job, passing JOB_ID and ORG_ID via environment variables. Everything else
(database URL, Redis URL, encryption key) comes from the same environment
the worker uses, so behaviour matches the in-process path.

The actual training logic is imported from app.workers.training_tasks -
that module is unchanged whether it runs here or in-process; the only
difference is that it must not depend on anything outside this image.
"""

import os
import sys


def main() -> int:
    job_id_str = os.environ.get("JOB_ID")
    if not job_id_str:
        print("ERROR: JOB_ID env var is required", file=sys.stderr)
        return 2
    job_id = int(job_id_str)

    # Import lazily so env vars from the launcher are in place first.
    from app.workers import training_tasks

    # Reuse the existing implementation by calling the underlying function
    # directly (not the Celery task wrapper, which would try to talk to
    # the broker from inside this container).
    training_tasks._train_model_sync(job_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
