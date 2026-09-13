[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/kironovlaziz-del/AI-tower/actions/workflows/ci.yml/badge.svg)](https://github.com/kironovlaziz-del/AI-tower/actions/workflows/ci.yml)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

# AI Control Tower

An open-source platform for governance, oversight, and audit of
enterprise AI usage. It centralizes policies, approvals, request
tracing, incidents, vendor risk, shadow AI detection, and an MLOps
layer for training and running custom models — all self-hosted, with
no external SaaS dependency.

## What It Does

- **Policy Center** — author policies, version their JSON rules,
  approve versions, and bind them to use cases.
- **Usage Registry** — every AI call is registered with a purpose,
  risk level, and the full request → response trace.
- **Approval Workflow** — requests that require sign-off are routed
  to designated approvers; decisions are logged.
- **Prompt Firewall** — automatic masking of PII (email, credit card,
  SSN, phone, API keys) and blocking of terms listed in the active
  policy version. The provider never sees raw input.
- **Connections** — manage AI provider credentials (OpenAI,
  Anthropic, Azure OpenAI, or any custom HTTP endpoint). Keys are
  encrypted at rest with Fernet.
- **Incident Tracker** — register incidents, track root cause,
  resolve with audit trail.
- **Shadow AI Monitor** — catalog unsanctioned AI tools seen in the
  organization and either dismiss them or convert them into
  registered providers.
- **Vendor Risk Desk** — registry of AI providers with SLA and risk
  scoring.
- **Audit & Reporting** — every mutation in the platform is written
  to `ai_audit_logs` and queryable.
- **Notification Service** — route events (`incident_created`,
  `approval_pending`, `training_completed`, etc.) to email or
  webhook channels.
- **MLOps layer** — Dataset Manager, Compute Detector,
  Training Service (scikit-learn + Hugging Face Transformers),
  and per-job prediction API.

## Repository Layout

```
backend/             FastAPI + SQLAlchemy (async) + Alembic + Celery
frontend/            Next.js 16 (App Router) + TypeScript + axios
docker-compose.yml   Postgres 16 + Redis 7 (for local and prod)
LICENSE              Apache License 2.0
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Pydantic v2, SQLAlchemy 2 (async), asyncpg |
| Migrations | Alembic |
| Task queue | Celery 5 + Redis 7 |
| Database | PostgreSQL 16 |
| Auth | JWT (python-jose), bcrypt |
| Encryption | Fernet (cryptography) for provider keys |
| ML | scikit-learn, pandas, joblib, PyTorch + Transformers |
| Frontend | Next.js 16, React 19, TypeScript, axios |
| Infra | Docker Compose, systemd |

## Requirements

- Linux server (Ubuntu 22.04 / 24.04 recommended)
- Docker + Docker Compose v2
- Python 3.12
- Node.js 20.9+ (for frontend)
- ~4 GB RAM minimum for CPU-only training; 16+ GB and a GPU for
  transformer fine-tuning

## Quick Start (Local Development)

### 1. Clone

```bash
git clone git@github.com:kironovlaziz-del/AI-tower.git
cd AI-tower
```

### 2. Configure environment

The project reads secrets from two `.env` files — one for Docker
Compose (root) and one for the backend.

```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

Edit `.env` (root) — values used by `docker-compose.yml`:

```env
POSTGRES_USER=ai_user
POSTGRES_PASSWORD=change_me_in_dot_env
POSTGRES_DB=ai_control_tower
REDIS_PASSWORD=change_me_in_dot_env
```

Edit `backend/.env` — values used by FastAPI and Celery:

```env
SECRET_KEY=generate_a_long_random_string
ENCRYPTION_KEY=generate_with_Fernet.generate_key()
POSTGRES_USER=ai_user
POSTGRES_PASSWORD=change_me_in_dot_env
POSTGRES_DB=ai_control_tower
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=change_me_in_dot_env
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Generate the encryption key:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Start infrastructure

```bash
docker compose up -d
```

This starts Postgres on `127.0.0.1:5432` and Redis on
`127.0.0.1:6379`. Both are bound to localhost only — never exposed
to the internet.

### 4. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000 · Docs: http://localhost:8000/docs

### 5. Celery worker (separate terminal)

```bash
cd backend
source .venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info --concurrency=1
```

### 6. Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:3000 — start at `/register` to create your first
organization and admin user.

## Production Deployment (systemd)

The project ships with four systemd units that manage the entire
stack, plus a fifth *target* that groups them.

| Unit | Purpose |
|------|---------|
| `ai-ct-docker.service` | `docker compose up -d` (Postgres + Redis) |
| `ai-ct-backend.service` | FastAPI via uvicorn on port 8000 |
| `ai-ct-celery.service` | Celery worker |
| `ai-ct-frontend.service` | Next.js production server on port 3000 |
| `ai-ct.target` | Groups all four for one-command control |

Enable once:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-ct-docker ai-ct-backend ai-ct-celery ai-ct-frontend
```

Day-to-day:

```bash
aict-start      # start everything
aict-stop       # stop everything
aict-restart    # restart everything
aict-status     # one-line status of all four services
aict-logs       # tail backend, celery, frontend logs together
```

Helper functions for deployment:

```bash
aict-migrate    # apply Alembic migrations
aict-build      # rebuild frontend and restart ai-ct-frontend
aict-deploy     # migrate → build → restart everything
```

These aliases are defined in `~/.bashrc`. See the setup section at the
bottom of this file.

## Environment Variables

### Root `.env` (read by Docker Compose)

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` | Postgres superuser name |
| `POSTGRES_PASSWORD` | Postgres password — **change before first run** |
| `POSTGRES_DB` | Database name |
| `REDIS_PASSWORD` | Redis `requirepass` value |

### `backend/.env` (read by FastAPI + Celery)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (HS256). **Required.** |
| `ENCRYPTION_KEY` | Fernet key for encrypting provider API keys |
| `POSTGRES_*` | Connection parameters (host, port, user, password, db) |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` | Celery broker & backend |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime, default 30 |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` / `SMTP_USE_TLS` | Optional email notifications. If `SMTP_HOST` is empty, email delivery is silently skipped — webhooks still work. |
| `DATASETS_DIR` / `MODELS_DIR` | Where uploads and trained artifacts are stored |

### `frontend/.env.local`

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API base, e.g. `http://138.124.61.62:8000/api/v1` |

## Database Schema (high level)

| Table | Purpose |
|-------|---------|
| `organizations` | Tenant root |
| `users` | Users with role (admin / approver / user) |
| `ai_policies` + `ai_policy_versions` | Policies and immutable versioned rules |
| `ai_use_cases` | Registered AI use cases with risk level |
| `ai_providers` | AI vendors and connections (with encrypted API key) |
| `ai_requests` + `ai_responses` | Request → response trace |
| `ai_approvals` | Approval decisions |
| `ai_overrides` | Manual stop / edit / rollback |
| `ai_incidents` | Incident Tracker |
| `ai_audit_logs` | Append-only audit trail |
| `shadow_ai_sightings` | Shadow AI Monitor |
| `datasets` | Uploaded datasets |
| `training_jobs` | ML training jobs |
| `notification_channels` | Email / webhook targets per event type |

Migrations live in `backend/alembic/versions/`. Never edit a
migration that has been applied — create a new one.

## API Overview

All endpoints are under `/api/v1`. A few examples:

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/auth/login` | Email + password → JWT |
| `POST` | `/users/register` | Create organization + first admin |
| `GET` | `/policies` | List policies |
| `POST` | `/policies/{id}/versions` | Create a new rule version |
| `POST` | `/policies/{id}/versions/{v}/approve` | Approve a version |
| `POST` | `/requests` | Send a prompt through the firewall and policy engine |
| `POST` | `/approvals/{id}/decision` | Approve or reject |
| `POST` | `/datasets` | Upload a dataset (CSV / TSV / JSON) |
| `POST` | `/training-jobs` | Queue a training job |
| `GET` | `/training-jobs/{id}/download` | Download the trained model |
| `GET` | `/compute/status` | CPU, RAM, disk, GPU, VRAM snapshot |
| `GET` | `/compute/allowed-models` | Transformer models that fit current hardware |

Full interactive docs at `/docs` while the backend is running.

## Security Model

- **PII masking** — `Prompt Firewall` replaces emails, credit card
  numbers, SSNs, IP addresses, API keys, and phone numbers with
  `[MASKED:TYPE]` before storage and before the provider call.
- **Blocked terms** — the active policy version can declare a list
  of substrings; any prompt containing one is rejected with status
  `blocked` and never reaches a provider.
- **Provider credentials** — encrypted at rest with Fernet. The API
  never returns the key, only a `has_credentials: true/false` flag.
- **Network isolation** — Postgres and Redis are bound to
  `127.0.0.1` in `docker-compose.yml`. Only the backend (8000) and
  frontend (3000) are reachable externally.
- **Audit trail** — every mutation through the API writes a row to
  `ai_audit_logs` with actor, entity, action, and metadata.

## Training Service

The Training Service runs on Celery and supports four task types:

| Task type | Engine | Use case |
|-----------|--------|----------|
| `tabular_classification` | scikit-learn | Structured data, logistic regression or random forest |
| `tabular_regression` | scikit-learn | Linear or random forest regression |
| `transformer_text_classification` | Hugging Face | Fine-tune BERT / DistilBERT / MiniLM on text |
| `transformer_text_generation` | Hugging Face | Fine-tune GPT-2 family for text continuation |

Before a job is queued, the backend calls `Compute Detector` and
`transformer_models.check_model_fit` to verify the chosen base model
fits the detected VRAM (with a 1.3× safety margin). On CPU-only
servers, only three small models are allowed.

Trained artifacts land in `backend/data/models/<org_id>/job_<id>/`
and can be downloaded as `.joblib` (sklearn) or `.zip`
(transformers).

**Note:** PyTorch and `transformers` are not installed by default —
the requirements file lists them as optional. To enable fine-tuning,
install them into the backend virtualenv:

```bash
cd backend
source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only
pip install transformers
sudo systemctl restart ai-ct-celery
```

## Notebook of common operations

### Reset the local database (destructive)

```bash
docker compose down -v
docker compose up -d
cd backend && alembic upgrade head
```

### Rotate the Postgres password

```bash
# 1. Change POSTGRES_PASSWORD in both .env files
# 2. Inside the DB:
docker exec -it ai_ct_db psql -U ai_user -d ai_control_tower
> ALTER USER ai_user WITH PASSWORD 'new_password';
> \q
# 3. Restart:
aict-restart
```

### Rotate the Redis password

```bash
# 1. Change REDIS_PASSWORD in both .env files
# 2. Restart:
aict-restart
```

## Contributing

We welcome bug reports, feature requests, and pull requests. Please read
[CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md) — for reporting vulnerabilities privately
- [Changelog](CHANGELOG.md)

## License

Apache License 2.0 — see [LICENSE](LICENSE).

Copyright 2026 Laziz Kironov.