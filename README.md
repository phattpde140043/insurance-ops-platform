# Insurance Ops Platform

Insurance Ops Platform is a modular full-stack system for managing insurance operations across customer self-service, employee workflows, claim lifecycle, support conversations, AI-assisted knowledge retrieval and SLA-driven dashboards.

The platform is designed around tenant isolation, explicit domain boundaries, auditable workflow transitions and production-ready API contracts. It combines a FastAPI backend, SQLAlchemy/Alembic persistence, a Next.js frontend and a documented architecture roadmap with ADRs.

## Repository Description

Insurance operations platform with FastAPI, Next.js, multi-tenant workflows, customer portal, claim lifecycle, support chat, AI knowledge retrieval, dashboards and SLA alerts.

## Key Features

- Multi-tenant authentication and role-aware request context.
- Customer portal for policies, incidents, appointments and support conversations.
- Employee workload queues with priority, due dates and assignment actions.
- Governed claim lifecycle with explicit states, transitions and audit history.
- Persisted support chat with optional AI-assisted answers and citations.
- Knowledge document ingestion and guarded retrieval behavior.
- Dashboard metrics, chart-ready APIs and SLA alert persistence.
- Background job support for async workflow evaluation.
- Architecture documentation, ADRs and verification checklist.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic, Pytest.
- Frontend: Next.js, React, TypeScript.
- Data and ops: PostgreSQL-ready schema, Docker Compose, background jobs.
- Architecture: modular monolith, bounded domains, C4 documentation and ADRs.

## Architecture

The backend follows explicit bounded modules:

- `app.core`: configuration, database, auth context, permissions, storage and observability.
- `app.domains.platform`: users, organizations, memberships, auth and audit.
- `app.domains.shared`: file assets and background jobs.
- `app.domains.insurance`: plans, customers, policies, assignments, claims, queues and support flows.
- `app.domains.ai`: knowledge bases, PDF ingestion, retrieval and guarded chat.
- `app.domains.dashboard`: insurance-focused metrics, charts and SLA alerting.

The frontend is a Next.js app focused on insurance operations, customer self-service, dashboards, AI support and admin workflows.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/PLAN.md](docs/PLAN.md) for the system architecture, ADRs and delivery roadmap.

## Local Run

Backend:

```bash
cd backend
python3 -m pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8002
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --port 3002
```

Docker Compose:

```bash
docker compose up --build
```

Open:

- Backend: `http://localhost:8002/docs`
- Frontend: `http://localhost:3002`

## Verification

```bash
python3 -m compileall backend/app
python3 -m pytest backend/app/tests -q -m 'not integration'
```
