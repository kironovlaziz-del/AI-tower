# Changelog

All notable changes to this project are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Prompt Firewall NER layer** — person names, organizations, and
  locations are now masked in addition to the regex detectors.
  Configurable via `PROMPT_FIREWALL_NER_ENABLED` / `PROMPT_FIREWALL_NER_MODEL`.
- **Dashboard metrics** — `/dashboard` shows a 7/14/30/90-day request
  trend line, distributions by status/severity, and live counters.
- **Deployment Manager** — versioned model deployments with
  `POST /deployments/{id}/predict` and `POST /deployments/{id}/chat`.
- **A/B routing** — `POST /deployments/by-name/{name}/predict` picks a
  version proportional to `traffic_weight`.
- **In-UI Playground** — `/playground` lets you chat with any active
  deployment without leaving the app.
- **Webhook events** for deployment lifecycle:
  `deployment_created`, `deployment_updated`, `deployment_archived`.
- **Docker isolation per training job** — each job runs in a dedicated
  container when `TRAINING_USE_DOCKER=true`.
- **SSE progress stream** for training jobs
  (`GET /training-jobs/{id}/stream`).
- **i18n** — full English + Uzbek coverage, plus machine-readable error
  codes translated on the frontend.
- **Pagination** on every list endpoint (`?skip=0&limit=50`).
- **CI pipeline** on GitHub Actions: backend tests, frontend build,
  security scan, compose validation. Dependabot for dependency updates.
- **28+ pytest cases** covering auth, RBAC, approvals, firewall,
  requests, and pagination.

### Changed

- `input_text` is now stored encrypted at rest and no longer returned by
  the API; only `masked_input_text` is exposed.
- Approver assignment is server-side: policies can name a specific
  approver, otherwise an available admin/approver is selected.
- Rate limit on `/auth/login`: 10 attempts per IP and 5 per email
  within 5 minutes.
- `users.email` is unique per organization instead of globally; login
  requires `org_slug`.
- `training_jobs.task_type` widened to 50 chars.
- `users.role` is now a plain VARCHAR — adding a role no longer
  requires an enum migration.

### Fixed

- Prompt Firewall no longer masks ISO dates as phone numbers.
- Event loop mismatch in pytest-asyncio fixtures (session/function scope).
- Race in `_update_progress` that could overwrite `status` / `finished_at`.
- `cancel_job` and `retry_job` race conditions.
- `_detect_gpu` fallback when torch is installed but built for CPU only.
- Various N+1 query fixes via cached model loading (`lru_cache`).
