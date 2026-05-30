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
ENVIRONMENT=production
GOOGLE_TOKEN_VERIFIER_MODE=google
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CALLBACK_URL=<your-google-callback-url>
```

Production-like environments reject demo verifier mode, unknown verifier modes,
missing Google configuration and callbacks without a valid signed OAuth state.

## Object Storage

Local development stores uploads under `LOCAL_STORAGE_ROOT`. Production can use
a private S3 or MinIO-compatible bucket:

```bash
STORAGE_PROVIDER=s3
OBJECT_STORAGE_BUCKET=<private-bucket>
OBJECT_STORAGE_ENDPOINT_URL=<optional-minio-endpoint>
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_ACCESS_KEY_ID=<access-key>
OBJECT_STORAGE_SECRET_ACCESS_KEY=<secret-key>
STORAGE_DOWNLOAD_EXPIRES_SECONDS=300
```

Download references are authorized and expire. Storage credentials must never
be exposed through frontend environment variables.

## AI Resource Isolation

AI endpoints use a separate bounded database pool configured with
`AI_DATABASE_POOL_SIZE`, `AI_DATABASE_MAX_OVERFLOW` and
`AI_DATABASE_POOL_TIMEOUT_SECONDS`. AI budgets, retrieval timeouts and ingestion
capacity return a safe retry or no-source response without consuming connections
reserved for claim, queue or dashboard traffic. Admins can inspect redacted
operational telemetry at `GET /api/v1/ai/operations`.

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
python -m scripts.run_ai_evaluations
```

## Worker

```bash
cd backend
python -m scripts.run_worker
```

## E2E Smoke

After migrations, demo seed, API server and worker are running:

```bash
cd backend
SMOKE_API_BASE_URL=http://localhost:8002/api/v1 python -m scripts.run_e2e_smoke
```
