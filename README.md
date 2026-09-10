[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# AI Control Tower

A platform for managing and auditing enterprise AI usage: policies, usage
registry, approvals, request→response tracing, incidents, and a vendor
registry.

## Repository Layout

```

backend/    FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic
frontend/   Next.js (App Router) + TypeScript + axios
docker-compose.yml   Postgres + Redis for local development

```

## What's Implemented (MVP)

- **Auth** — organization registration + email/password login, JWT.
- **Policy Center** — policies, rule versions (JSON), version approval.
- **Usage Registry** — use cases, vendor registry (Vendor Risk Desk, basic
  CRUD), creation and listing of AI requests.
- **Action Trace** — the full chain request → (approval) → provider
  response on a single page.
- **Approval Workflow** — submitting a request for approval, approve/reject
  decision with a comment.
- **Incident Tracker** — incident registration, status, root cause.

## What's Not Implemented (Remaining from the Original Architecture)

These modules exist in the DB schema or in the overall plan but are not
implemented as working logic — they are left as the next stage:

- **Prompt Firewall** — `masked_input_text` is not populated yet; there is
  no pipeline for masking/blocking sensitive fields.
- **Shadow AI Monitor** — detection of unauthorized AI usage.
- **Override Console** — manual stop/edit/rollback of a request.
- **Audit & Reporting** — the `ai_audit_logs` table exists, but nothing
  writes to it; there are no compliance report exports or dashboards.
- **Notification Service**, **Event Bus / Redis queue**, workers
  (`app/workers` is an empty package).
- The provider call in `RequestService.process_request` is a stub
  (`Mock response`); there is no real call to OpenAI/Anthropic/etc.

## Running the Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# start Postgres/Redis
cd .. && docker compose up -d

cd backend
cp .env.example .env   # adjust hosts/passwords if needed
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000, with documentation at
http://localhost:8000/docs.

Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. By default the frontend talks to the API at
http://localhost:8000/api/v1 — override this via the NEXT_PUBLIC_API_URL
environment variable (.env.local file) if needed.

The first step in the UI is /register: it creates an organization and the
first user with the admin role.

Typical Verification Scenario

1. /register — create an organization.
2. /providers — add a provider (e.g., OpenAI / openai).
3. /use-cases — create a use case.
4. /policies — create a policy, add a version with
   {"effect": "require_approval"}, approve it, then link
   approved_policy_version_id to the use case (currently via API/DB
   directly; editing this link from the use case card is not exposed in
   the UI).
5. /requests — create a request: if the use case requires approval, the
   status becomes pending_approval.
6. On the request page — "Submit for approval", then on /approvals —
   approve or reject.
7. /incidents — if needed, log an incident and resolve it to resolved
   with a specified root cause.

License

This project is distributed under the Apache 2.0 license.
See the LICENSE file for details.

```
