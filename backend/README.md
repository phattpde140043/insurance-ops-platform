# Insurance Operations Backend

FastAPI backend for the Insurance Operations Platform.

## Local Run

```bash
cd backend
python3 -m pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8002
```

Open:

- `http://localhost:8002/api/v1/health`
- `http://localhost:8002/docs`

## Demo Context

Demo headers are local-only. They are accepted only when the backend is running
with `ENVIRONMENT=local`, `ENVIRONMENT=dev`, `ENVIRONMENT=development` or
`ENVIRONMENT=test` and `DEMO_HEADER_AUTH_ENABLED=true`.

```text
X-Organization-Id: org_demo
X-User-Id: user_admin
X-Role: admin
```

For production-like verification, disable demo header auth and use bearer tokens:

```bash
ENVIRONMENT=production
DEMO_HEADER_AUTH_ENABLED=false
```

## Google SSO

```bash
GOOGLE_TOKEN_VERIFIER_MODE=demo
```

For production-like verification:

```bash
GOOGLE_TOKEN_VERIFIER_MODE=google
GOOGLE_CLIENT_ID=<your-google-client-id>
```

## Database Bootstrap

```bash
cd backend
alembic upgrade head
python -m scripts.seed_demo
```

## Tests

```bash
cd backend
pytest -q -m 'not integration'
```

## Worker

```bash
cd backend
python -m scripts.run_worker
```
