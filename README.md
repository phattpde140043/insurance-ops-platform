# Insurance Operations Platform

Standalone project for Câu 2: an operations platform for insurance companies managing admins, employees and customers.

## Scope

- Google SSO adapter, JWT sessions, RBAC and audit history.
- Insurance plan, customer, policy and employee assignment workflows.
- Incident reports, appointments, conversations and support messages.
- Role-specific dashboard API surface.
- Company knowledge upload, PDF ingestion, retrieval and guarded chatbot flow.
- Admin user management and traceable request logging.

## Architecture

The backend follows explicit bounded modules:

- `app.core`: configuration, database, auth context, permissions, storage and observability.
- `app.domains.platform`: users, organizations, memberships, auth and audit.
- `app.domains.shared`: file assets and background jobs.
- `app.domains.insurance`: plans, customers, policies, assignments, incidents and support flows.
- `app.domains.ai`: knowledge bases, PDF ingestion, retrieval and guarded chat.
- `app.domains.dashboard`: insurance-focused dashboard aggregation.

The frontend is a NextJS app focused on insurance operations, dashboards, AI support and admin.

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
