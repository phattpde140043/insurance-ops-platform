# Insurance Operations Platform Plan

## Completed Backbone

- Platform identity, tenant context, RBAC and audit log.
- Insurance plan, customer, policy and employee assignment APIs.
- Incident report workflow.
- Appointment and message skeleton.
- Role-specific dashboard APIs.
- Knowledge base upload, PDF extraction, chunking and retrieval.
- Guarded chatbot answer flow.
- NextJS app shell with insurance incident form.
- Docker, CI baseline and backend tests.

## Architecture vs Current Master Plan

The documented architecture is modular and already separates platform identity, shared infrastructure, insurance workflows, AI retrieval and dashboard aggregation. The current master plan correctly names the next product-depth areas, but it is too coarse for sequential agent execution and does not yet encode dependencies, test boundaries, tenancy enforcement or acceptance criteria.

Key alignment notes:

- `platform` is the foundation for all remaining work because every feature must resolve tenant, user and role from the authenticated request context.
- `insurance` is the primary dependency for customer self-service, employee queues and claim lifecycle work.
- `shared` should be used for files and background jobs before adding claim evidence uploads, queue workers or SLA notifications.
- `ai` is already service-isolated; the next chat UI should consume persisted conversations and guarded answers without coupling AI logic into insurance services.
- `dashboard` should remain an aggregation boundary and should not own workflow state.
- The frontend currently exposes the app shell and initial pages, so most remaining work needs API contracts plus user-facing screens, not only backend endpoints.

Planning assumptions:

- The existing demo header auth remains usable for local development, but production paths must use JWT-derived tenant and user context.
- The database is PostgreSQL through SQLAlchemy/Alembic, and every persisted tenant-owned row must include organization scoping.
- Each task below is intended to be completed in order; later tasks depend on schemas, states or UI surfaces introduced earlier.

Planning gate:

- Knowledge layer: Layer 1, standard FastAPI service/repository/module boundaries with NextJS feature screens and focused tests.
- Diamond audit: scalable through bounded modules, secure through tenant/RBAC checks, aesthetic through feature-complete operational UI rather than placeholder pages.
- BFRI: Architectural Fit 5 + Testability 4 - Complexity 3 - Data Risk 3 - Operational Risk 2 = 1. Proceed with explicit tests, migrations, monitoring hooks and isolated feature increments.

## Planning and Review Hardening Addendum

This addendum was produced by reviewing the plan through the implementation-planning, code-review, security-checklist, API-design, Postgres-performance and resilience-pattern lenses. The verdict is: request changes to execution order before feature work continues, because several security and performance foundations must become upstream dependencies rather than late follow-up tasks.

Review findings:

- Blocking: production auth and tenant resolution cannot wait until the end of the roadmap. All portal, queue, claim, chat and dashboard work depends on trusted identity and tenant context.
- Blocking: every new list endpoint must have pagination, bounded limits, deterministic sorting and tenant-scoped query tests before UI work consumes it.
- Blocking: customer-facing and employee-facing commands need idempotency keys or structurally idempotent service behavior before retries/background jobs are introduced.
- Important: API contracts should include rate-limit tiers and collection metadata envelopes before frontend and backend agents split work.
- Important: performance-sensitive queries need an index plan, query shape tests and N+1 checks before dashboard/SLA aggregation expands.
- Important: audit logs must avoid PII/token leakage while still recording actor, tenant, resource and trace identifiers.
- Important: AI chat must enforce tenant-scoped retrieval, safe citation references, prompt/data minimization and response-size bounds before persisted support chat becomes a customer feature.

## Architect Review Addendum

This addendum was produced by reviewing the plan through the backend-architect, system-architecture, architecture-design and clean-architecture lenses. The verdict is: continue with the modular monolith, but make architecture decisions explicit before expanding feature depth.

Architecture findings:

- Blocking: major decisions are not yet captured as ADRs. Auth mode, pagination envelope, claim lifecycle ownership, chat orchestration, SLA evaluation and dashboard read models must be decision-recorded before implementation agents encode them inconsistently.
- Blocking: module dependency direction is implicit. `insurance`, `ai`, `dashboard`, `platform` and `shared` need a dependency contract that prevents feature agents from importing across domains ad hoc.
- Blocking: dashboard and SLA work need read-model boundaries. Dashboard may query source tables through read repositories/projections, but it must not own workflow state or call command services.
- Important: cross-domain orchestration is not yet designed. Support chat touches `insurance`, `ai`, `shared` and `platform`; the plan needs an application-service/orchestrator boundary rather than direct circular coupling.
- Important: audit logging currently appears as a concrete platform service used by multiple domains. The architecture should define whether audit is an allowed platform dependency or exposed through a port/interface.
- Important: migrations and backfills need release sequencing. Claim lifecycle, queue fields, conversation links and SLA alerts must define expand/backfill/contract steps where existing data is affected.
- Important: background jobs need ownership rules. `shared` can host job infrastructure, but job handlers should live in the owning domain or a dedicated application workflow layer.

Global guardrails for every implementation task:

- Security: resolve tenant and actor from trusted request context only; never accept `organization_id`, role or customer identity from client payloads for authorization decisions.
- Authorization: every route declares role access and every service enforces object-level access before loading or mutating sensitive data.
- API design: every collection response includes `items` plus pagination metadata or an explicitly documented compatibility exception.
- Rate limiting: every new endpoint is assigned a tier: `auth-sensitive`, `write-command`, `read-list`, `ai-expensive` or `internal-job`.
- Idempotency: every create/update/transition/send command must define duplicate-request behavior and include tests for retry safety.
- Performance: every list/aggregate query must define maximum page size, sort order, projection shape and required indexes before implementation.
- Observability: every mutation and background job records traceable audit/observability metadata without logging secrets, tokens, raw prompts or unnecessary PII.
- Frontend security: no sensitive token storage in `localStorage`; no unsanitized HTML rendering; no placeholder `href="#"` as primary feature behavior after a feature is implemented.
- Architecture: every new feature must preserve Controller -> Service -> Repository -> Model layering; routers must not contain business rules and services must not return ORM models directly.
- Module boundaries: domain modules may depend on `core` and stable `shared` infrastructure; cross-domain calls must go through documented service contracts, ports or orchestrators.
- Data ownership: workflow state belongs to its source domain; dashboard, SLA and AI surfaces consume projections/read models unless a specific ADR grants ownership.
- Release safety: schema changes that affect existing rows must use expand/backfill/contract sequencing or document why a single-step migration is safe.

## API Collection, Pagination and Rate-Limit Contract

New collection endpoints must use this response envelope:

```json
{
  "items": [],
  "meta": {
    "limit": 25,
    "sort": "-created_at",
    "next_cursor": null,
    "offset": 0,
    "total": null,
    "has_more": false
  }
}
```

Compatibility note: existing endpoints that return only `{"items": [...]}` may remain temporarily, but any feature task that touches a list endpoint must either add `meta` backward-compatibly or document why the endpoint is still low-volume and scheduled for migration.

Pagination limits:

| Endpoint class | Default limit | Max limit | Pagination style | Default sort |
| --- | ---: | ---: | --- | --- |
| Small reference lists, such as plans | 50 | 100 | Offset allowed | `name` or `-created_at` |
| Customer/policy/admin lists | 25 | 100 | Offset allowed | `-created_at` |
| Employee queues | 25 | 100 | Cursor preferred when sorted by due/activity | `due_at,+priority,-updated_at` |
| Claim/incident history | 25 | 100 | Cursor preferred | `-created_at` |
| Conversation/message history | 50 | 100 | Cursor required for message history | `created_at` |
| Audit events and SLA alerts | 50 | 200 | Cursor required | `-created_at` |
| Dashboard chart series | Bounded by date bucket range | 366 buckets | Date range, not row pagination | `bucket_start` |

Rate-limit tiers:

| Tier | Applies to | Initial policy |
| --- | --- | --- |
| `auth-sensitive` | login, token exchange, auth verification | Strict per IP/user; log violations. |
| `write-command` | create/update/transition/send commands | Moderate per user/tenant; require idempotency where retryable. |
| `read-list` | list/search/filter endpoints | Higher per user/tenant; must be paginated. |
| `ai-expensive` | chat, retrieval, ingestion triggers | Strict per user/tenant; bounded prompt/retrieval size. |
| `internal-job` | worker-triggered evaluation/ingestion | Not public; bounded by worker concurrency and idempotency. |

Every planned API contract must name one of these tiers before implementation.

## Query and Index Budget

Agents must use the detailed query/index budget in `docs/ARCHITECTURE.md` before implementing portal, queue, claim, chat, dashboard, SLA or audit list endpoints.

Required review gates for every high-volume query:

- Name the source table or read model.
- Name tenant and object-scope predicates.
- Name default sort and pagination style.
- Return projection DTOs instead of ORM graphs.
- Confirm the migration includes indexes for new predicates.
- Add a test with multiple rows that would catch N+1-prone or cross-scope assembly logic.

Low-volume exceptions must be explicit and include the trigger for adding an index later.

## Idempotency, Audit and PII Logging Contract

Agents must use the idempotency matrix in `docs/ARCHITECTURE.md` before implementing any mutation endpoint, background job or AI-assisted command.

Required for every mutation task:

- State whether it uses `X-Idempotency-Key`, get-or-create behavior, repeat-safe state transition or documented non-retryable behavior.
- Define duplicate request behavior: return existing resource, no-op, 409 conflict or retry later.
- Record audit metadata with tenant, actor/job actor, action, resource type, resource id and trace id where available.
- Log ids, counts and state names, not raw sensitive content.
- Add tests for duplicate/retry behavior when the command is retryable.

Sensitive content that must not be logged or stored in audit metadata:

- bearer tokens, refresh tokens, session secrets or API keys
- raw AI prompts and full assistant answers
- raw uploaded document contents
- full support message bodies
- full claim descriptions or medical/incident detail narratives
- full PII values when ids/references are sufficient

## AI Retrieval and Prompt Security Contract

Agents must use the AI guardrails in `docs/ARCHITECTURE.md` before implementing or modifying chat, retrieval, ingestion or AI-assisted support workflows.

Required for AI tasks:

- Add tenant-scoped retrieval tests that prove tenant A cannot retrieve tenant B documents or chunks.
- Bound retrieval to at most 3 chunks by default.
- Store citation references, not full source text copies.
- Do not log raw prompts, raw uploaded document contents or full assistant answers.
- Implement deterministic fallback for no-source, provider timeout and provider error paths.
- Use `ai-expensive` rate-limit tier for chat, retrieval and ingestion triggers.
- Keep insurance conversation authorization in `insurance`; AI services must not mutate insurance claim/conversation state directly.

## Frontend Security and Data Exposure Contract

Agents must use the frontend rules in `docs/ARCHITECTURE.md` before implementing portal, queue, claim, chat or dashboard screens.

Required for frontend feature tasks:

- Do not store JWTs or session secrets in `localStorage`.
- Do not expose secrets in `NEXT_PUBLIC_*` variables.
- Do not use silent demo-data fallback for authenticated sensitive screens after 401, 403 or backend errors.
- Render user-generated text as React text nodes, not unsanitized HTML.
- Replace primary `href="#"` placeholders with real routes, real form actions or disabled controls before marking a feature complete.
- Add explicit UI states for loading, empty, forbidden, unauthorized, validation error and backend error.
- Centralize API error handling so tenant/auth failures do not look like empty data.

## Current Implementation Status

This matrix records the current source-state before product-depth work continues.

| Area | Status | Evidence | Next action |
| --- | --- | --- | --- |
| Platform auth and tenant context | Partial, hardened foundation added | `backend/app/core/context.py`, `backend/app/core/session.py`, `backend/app/tests/test_auth_context.py` | Keep production-like auth tests green while adding feature endpoints. |
| API pagination/rate-limit contracts | Documented, not fully implemented | `docs/PLAN.md`, `docs/ARCHITECTURE.md`, existing `backend/app/domains/shared/schemas.py` still supports simple list responses | Extend list response metadata when touching endpoints. |
| Tenant isolation test harness | Exists for service-level checks | `backend/app/tests/support/tenant_isolation.py`, `backend/app/tests/test_insurance_tenant_scope.py` | Reuse helpers for every new endpoint/service. |
| Architecture docs and ADRs | Exists | `docs/ARCHITECTURE.md`, `docs/adr/*.md` | Keep ADR links current as decisions change. |
| Customer self-service portal | Missing product feature; backend primitives partial | `InsuranceCustomer.linked_user_id` in `backend/app/domains/insurance/models.py`; no portal route/page | Start with `T02.1` portal summary API after API/route inventory. |
| Employee workload queues | Partial skeleton | assignments model/service/router exist; no queue list/detail/action endpoints | Add queue fields and queue APIs in `T03.*`. |
| Claim lifecycle state machine | Missing | incidents have string `status`; no transition history/state machine | Implement `T04.*` after queue foundation. |
| Persisted support chat | Partial split skeleton | insurance conversations/messages create endpoints exist; AI chat sessions/messages exist separately | Add conversation list/detail and AI orchestration in `T05.*`. |
| Dashboard charts and SLA alerts | Basic summary only | `backend/app/domains/dashboard/service.py` counts customers/policies/incidents/audit; frontend dashboard uses demo data | Add metric contracts/read models/SLA in `T06.*`. |
| Frontend portal/queue/claim/chat/dashboard UX | Partial shell | `frontend/app/insurance/page.tsx`, `frontend/app/ai/page.tsx`, `frontend/app/dashboard/page.tsx` | Replace placeholders and demo fallbacks during feature tasks. |
| Background worker | Infrastructure exists | `backend/app/workers/background_worker.py`, `backend/app/domains/shared/job_service.py` | Assign domain-owned handlers for PDF/SLA/AI jobs. |

## Planned API Contracts

All contracts are additive unless explicitly marked otherwise. Every implementation must use DTOs, tenant-scoped services, bounded collection responses and the listed rate-limit tier.

| Contract | Method/path | Owner | Roles | Tier | Status | ADR |
| --- | --- | --- | --- | --- | --- | --- |
| Portal summary | `GET /api/v1/insurance/portal/summary` | `insurance` | `customer`, optional `admin` support view | `read-list` | New | ADR 0002, ADR 0003 |
| Portal policies | `GET /api/v1/insurance/portal/policies` | `insurance` | `customer` | `read-list` | New | ADR 0003 |
| Portal incidents/claims | `GET /api/v1/insurance/portal/incidents` | `insurance` | `customer` | `read-list` | New | ADR 0003, ADR 0004 |
| Portal appointments | `GET /api/v1/insurance/portal/appointments` | `insurance` | `customer` | `read-list` | New | ADR 0003 |
| Portal conversations | `GET /api/v1/insurance/portal/conversations` | `insurance` | `customer` | `read-list` | New | ADR 0003, ADR 0005 |
| Portal appointment request | `POST /api/v1/insurance/portal/appointments` | `insurance` | `customer` | `write-command` | New | ADR 0002 |
| Portal conversation start | `POST /api/v1/insurance/portal/conversations` | `insurance` | `customer` | `write-command` | New | ADR 0005 |
| Employee my queue | `GET /api/v1/insurance/queues/my` | `insurance` | `employee` | `read-list` | New | ADR 0003 |
| Admin queue | `GET /api/v1/insurance/queues` | `insurance` | `admin` | `read-list` | New | ADR 0003 |
| Queue detail | `GET /api/v1/insurance/queues/{item_id}` | `insurance` | `admin`, `employee` | `read-list` | New | ADR 0003 |
| Queue assign/reassign | `POST /api/v1/insurance/queues/{item_id}/assign` | `insurance` | `admin` | `write-command` | New | ADR 0004 |
| Queue status/priority action | `POST /api/v1/insurance/queues/{item_id}/actions` | `insurance` | `admin`, `employee` with object permission | `write-command` | New | ADR 0004 |
| Claim detail | `GET /api/v1/insurance/claims/{claim_id}` | `insurance` | `admin`, `employee`, owner `customer` | `read-list` | New or incident extension | ADR 0004 |
| Claim history | `GET /api/v1/insurance/claims/{claim_id}/history` | `insurance` | `admin`, `employee`, owner `customer` with redaction | `read-list` | New | ADR 0004 |
| Claim transition | `POST /api/v1/insurance/claims/{claim_id}/transitions` | `insurance` | `admin`, `employee` | `write-command` | New | ADR 0004 |
| Conversation list | `GET /api/v1/insurance/conversations` | `insurance` | `admin`, `employee`, `customer` scoped | `read-list` | Extends existing conversation create surface | ADR 0005 |
| Conversation detail/messages | `GET /api/v1/insurance/conversations/{conversation_id}` | `insurance` | scoped participant/admin | `read-list` | New | ADR 0005 |
| Send support message | `POST /api/v1/insurance/conversations/{conversation_id}/messages` | `insurance` | scoped participant/admin | `write-command` | Existing, must add idempotency | ADR 0005 |
| Send AI-assisted support message | `POST /api/v1/insurance/conversations/{conversation_id}/ai-messages` | `insurance` orchestrating `ai` | scoped participant/admin | `ai-expensive` | New | ADR 0005 |
| Dashboard summary | `GET /api/v1/dashboard/summary` | `dashboard` | `admin`, `employee`, `customer` scoped | `read-list` | Existing, extend additively | ADR 0006 |
| Dashboard chart series | `GET /api/v1/dashboard/charts` | `dashboard` | role scoped | `read-list` | New | ADR 0006 |
| SLA alerts | `GET /api/v1/dashboard/sla-alerts` | `dashboard` | role scoped | `read-list` | New | ADR 0006 |
| SLA alert detail | `GET /api/v1/dashboard/sla-alerts/{alert_id}` | `dashboard` | role scoped | `read-list` | New | ADR 0006 |
| Trigger knowledge ingestion | `POST /api/v1/ai/knowledge-documents/{document_id}/ingest` | `ai` and `shared` job infra | `admin` | `ai-expensive` | Existing, must align job contract | ADR 0007 |
| Guarded AI chat | `POST /api/v1/ai/chat` | `ai` | `admin`, `employee`, `customer` scoped | `ai-expensive` | Existing, must align prompt/citation guardrails | ADR 0005 |

Request/response shape notes:

- Collection responses use `items` plus `meta`.
- Command responses return the affected resource DTO or a command result DTO with `id`, `status` and safe metadata.
- Commands that are retryable must accept `X-Idempotency-Key` unless they use documented get-or-create or repeat-safe transition semantics.
- Customer portal command payloads must not accept arbitrary `customer_id`.
- Dashboard APIs are read-only and must not mutate workflow state.

## Planned Frontend Routes

Frontend routes must use API client functions and must not duplicate backend authorization or workflow rules.

| Route | Owner feature | Primary user | Mode | First implementation task | Notes |
| --- | --- | --- | --- | --- | --- |
| `/` | app shell/home | all | navigation/read-only | existing shell | Keep as entry point. |
| `/portal` | customer portal | customer | read + commands | T02.3 | No customer id input; backend resolves linked customer. |
| `/portal/policies` | portal policy history | customer | read-only | T02.3/T02.4 | Paginated list from portal APIs. |
| `/portal/incidents` | portal claim/incident history | customer | read-only | T02.3/T04.4 | Customer-safe redaction required. |
| `/portal/support` | portal support entry | customer | command + chat entry | T02.4/T05.4 | Opens/creates scoped support thread. |
| `/insurance` | employee/admin operations | admin, employee | queue workspace | T03.4 | Replaces current simple customer table as primary workflow. |
| `/insurance/claims/[id]` | claim detail | admin, employee, scoped customer if linked | read + role actions | T04.4 | Backend provides allowed actions. |
| `/ai` | persisted support/AI chat | admin, employee, customer scoped | chat/read + command | T05.3 | No primary `href="#"` placeholders after implementation. |
| `/dashboard` | metrics and SLA alerts | role scoped | read-only + drill-down | T06.5 | Uses dashboard APIs, not demo data. |
| `/admin` | admin console | admin | read + management commands | existing shell, future admin work | Must keep platform ownership. |

Frontend state requirements:

- Each feature route must render loading, empty, forbidden, unauthorized, validation error and backend error states.
- Sensitive authenticated screens must not silently fall back to demo data.
- Drill-down links must target authorized source routes.
- Primary commands use buttons/forms, not placeholder anchors.

## Sequential Continuation Plan

### Task 01 - Baseline Contract and Gap Audit

**Goal**

Create a precise implementation map from the documented architecture to existing backend routes, services, models, tests and frontend pages so later agents can work without rediscovering the same gaps.

**Depends On**

- Completed backbone modules and current Markdown documentation.

**Architecture Fit**

- Affects documentation only.
- Confirms ownership between `platform`, `insurance`, `ai`, `dashboard`, `shared` and frontend routes.

**Affected Layers and Components**

- Documentation: `docs/PLAN.md`, optional follow-up notes in `docs/ARCHITECTURE.md`.
- No controller, service, repository, model or database changes.

**Backward Compatibility and Data Impact**

- No API contract changes.
- No migration.
- No data impact.

**TDD Implementation Sequence**

1. Fail: list all expected APIs/screens from the plan and mark unknown implementation status.
2. Fix: inspect backend routers, services, schemas, models, migrations, tests and frontend routes.
3. Verify: produce a checked gap matrix with `exists`, `partial`, `missing` status for each product area.
4. Commit: `docs: map architecture gaps for next product depth`.

**Validation and Edge Cases**

- Include routes that exist but are skeleton-only.
- Distinguish missing UI from missing API.
- Distinguish demo-only auth from production-ready JWT paths.

**Security and Tenancy**

- Flag any endpoint or repository path without organization scoping.
- Flag any role-sensitive page without corresponding backend RBAC.

**Performance and Data Design**

- Identify list endpoints that need pagination before they become dashboard or queue inputs.
- Identify aggregation endpoints that could become N+1 risks.

**Acceptance Criteria**

- The gap matrix names each missing or partial item from this continuation plan.
- Every later task has a concrete file/module starting point.
- No code behavior changes are introduced.

### Task 02 - Customer Self-Service Portal Foundation

**Goal**

Let customers view their policies, claim/incident history, appointments and support conversations through tenant-safe self-service APIs and frontend screens.

**Depends On**

- Task 01 gap matrix.
- Existing platform identity, customer, policy, incident, appointment and message modules.

**Architecture Fit**

- Backend ownership stays in `insurance` for customer-facing insurance data.
- `platform` supplies authenticated user, membership, role and tenant context.
- Frontend adds customer portal screens without duplicating business logic.

**Affected Layers and Components**

- Controller: customer self-service routes under the existing API version.
- Service: customer portal read service and any narrow command services for appointment/support actions.
- Repository: tenant-scoped customer, policy, incident, appointment and message queries.
- Domain/Model: only add fields if the audit proves current models cannot represent the portal state.
- Infrastructure: request context, RBAC dependencies and audit logging.
- Frontend: customer portal route, policy detail view, claim history view and support entry points.

**Backward Compatibility and Data Impact**

- Additive API contracts only.
- Migration only if a user-to-customer link is missing.
- Existing admin/employee APIs must keep their response shape.

**TDD Implementation Sequence**

1. Fail: add backend tests proving a customer can only read policies and incidents linked to their own customer record.
2. Fix: implement tenant-scoped repository projections for customer portal summary data.
3. Verify: run focused backend tests for customer portal access.
4. Fail: add RBAC tests for admin, employee and customer access differences.
5. Fix: wire route dependencies and service authorization checks.
6. Verify: run auth/RBAC tests.
7. Fail: add frontend component tests or route smoke tests for loading, empty and error states.
8. Fix: build portal screens using the new contracts.
9. Verify: run frontend lint/build or the repo's available frontend checks.
10. Commit: `feat: add customer self-service portal foundation`.

**Validation and Edge Cases**

- Customer has no active policies.
- Customer has policies but no incidents.
- Appointment list is empty or contains past appointments.
- Support conversation exists but has no messages.
- Authenticated user has no linked customer record.

**Security and Tenancy**

- Tenant must come from JWT/request context, not user-supplied query params.
- Customer identity must be resolved server-side.
- Cross-customer policy, incident, appointment and message access must return forbidden or not found consistently.
- Audit customer portal reads and support/appointment commands where existing audit patterns support it.

**Performance and Data Design**

- Use projections for summary endpoints.
- Paginate claim/incident and conversation history.
- Avoid N+1 policy/customer lookups.
- Add indexes only when required by actual query predicates.

**Acceptance Criteria**

- Customer portal APIs are tenant-safe and covered by RBAC tests.
- Frontend customer portal exposes policies, incident history, appointments and support entry points.
- Empty, loading and forbidden states are handled intentionally.

### Task 03 - Employee Workload Queues

**Goal**

Give employees and admins operational queues for assigned policies, incidents, appointments and support work, with filters that match insurance operations workflows.

**Depends On**

- Task 01 gap matrix.
- Task 02 customer-facing data links, if queue items need customer portal actions reflected back to employees.
- Existing employee assignment, incident, appointment and message skeletons.

**Architecture Fit**

- `insurance` owns queue state and assignment queries.
- `dashboard` may later aggregate queue metrics but must not own queue mutations.
- Frontend `/insurance` or a dedicated operations route owns the queue UI.

**Affected Layers and Components**

- Controller: employee queue list/detail endpoints and assignment actions.
- Service: workload queue service, assignment validation and optional status transitions.
- Repository: filtered tenant-scoped queue queries.
- Domain/Model: assignment status, priority or due fields only if absent.
- Infrastructure: audit logging for assignment changes.
- Frontend: queue table, filters, detail drawer/page and action controls.

**Backward Compatibility and Data Impact**

- Additive endpoints preferred.
- Migration may be required for queue status, priority, due date or assignment metadata.
- Existing assignment APIs must remain valid.

**TDD Implementation Sequence**

1. Fail: add repository/service tests for queue filtering by assignee, status, priority and due date.
2. Fix: implement efficient queue query projections.
3. Verify: run focused queue tests.
4. Fail: add authorization tests for employee, admin and customer roles.
5. Fix: enforce role-specific queue visibility and assignment permissions.
6. Verify: run backend RBAC tests.
7. Fail: add frontend tests or smoke checks for filters, empty queues and action states.
8. Fix: implement queue UI with stable loading, empty, error and forbidden states.
9. Verify: run frontend checks.
10. Commit: `feat: add employee workload queues`.

**Validation and Edge Cases**

- Employee has no assignments.
- Assignment points to a deleted or inactive customer/policy.
- Admin reassigns an item already in progress.
- Queue filters return large result sets.
- Concurrent assignment update is attempted by two users.

**Security and Tenancy**

- Employees can only see tenant data and their permitted queue scope.
- Customers must not access employee queue endpoints.
- Assignment mutations require admin or explicitly allowed employee role.
- Audit all assignment and priority changes.

**Performance and Data Design**

- Paginate queue endpoints.
- Use stable sorting for due date and priority.
- Project only fields needed by queue rows.
- Add composite indexes for tenant, assignee, status and due date if query plans require them.

**Acceptance Criteria**

- Employees can triage assigned work without seeing other tenants.
- Admins can filter and reassign workload.
- Queue APIs and UI remain usable with empty and large result sets.

### Task 04 - Claim Lifecycle State Machine

**Goal**

Turn incident reports into a governed claim lifecycle with explicit states, valid transitions, history and role-aware actions.

**Depends On**

- Task 03 workload queues, because lifecycle actions should feed employee operations.
- Existing incident report workflow.

**Architecture Fit**

- `insurance` owns claim lifecycle state, transition rules and history.
- `shared` owns file assets if evidence uploads are added.
- `dashboard` consumes lifecycle metrics only after this task defines reliable states.

**Affected Layers and Components**

- Controller: claim transition endpoints and claim detail/history endpoints.
- Service: state machine, transition validation and audit/event recording.
- Repository: claim/incident state queries and history writes.
- Domain/Model: claim state enum, transition history and optional evidence references.
- Infrastructure: audit logs, optional file storage and background jobs.
- Frontend: claim detail timeline, action buttons and state badges.

**Backward Compatibility and Data Impact**

- Migration required if claims are currently represented only as incidents.
- Existing incident APIs must keep working or receive documented additive fields.
- Existing incident statuses need deterministic mapping into claim lifecycle states.

**TDD Implementation Sequence**

1. Fail: add unit tests for allowed and forbidden claim state transitions.
2. Fix: implement typed claim state enum and transition service.
3. Verify: run state machine tests.
4. Fail: add integration tests for transition endpoint authorization and tenant isolation.
5. Fix: wire endpoints, repository writes and audit history.
6. Verify: run backend integration/focused tests.
7. Fail: add migration test or smoke check for incident-to-claim state defaults.
8. Fix: add Alembic migration and model updates.
9. Verify: run migration and backend tests.
10. Fail: add frontend checks for timeline rendering and disabled invalid actions.
11. Fix: implement claim detail UI.
12. Verify: run frontend checks.
13. Commit: `feat: add claim lifecycle state machine`.

**Validation and Edge Cases**

- Invalid transition from closed back to in-review without reopen permission.
- Duplicate transition request.
- Transition with missing required reason or evidence.
- Legacy incident with no claim state.
- Claim belongs to another organization.

**Security and Tenancy**

- State transitions require role-specific authorization.
- Tenant filter applies to every claim lookup and history query.
- Transition history must not leak internal notes to customer-facing views unless explicitly allowed.
- Audit all state changes with actor and previous/new state.

**Performance and Data Design**

- Use enums or constrained values so invalid states are structurally difficult to store.
- Index tenant, claim state and updated/due date for queue and dashboard use.
- Paginate transition history if it can grow.
- Avoid loading full evidence blobs in claim summary endpoints.

**Acceptance Criteria**

- Claims have explicit lifecycle states and transition history.
- Invalid transitions are rejected before persistence.
- Employee queues and customer views reflect lifecycle changes.
- Tests cover allowed transitions, forbidden transitions, RBAC and tenant isolation.

### Task 05 - Persisted Chat and Support UI

**Goal**

Build a frontend chat experience backed by persisted conversations, support messages and guarded AI answers.

**Depends On**

- Task 02 customer portal support entry points.
- Task 04 claim lifecycle if conversations need to attach to claims.
- Existing `ai` guarded chatbot flow and `insurance` message skeleton.

**Architecture Fit**

- `insurance` owns persisted support conversations and messages.
- `ai` owns retrieval and guarded answer generation behind service contracts.
- `shared` may own background jobs if AI responses become asynchronous.
- Frontend `/ai` and support surfaces consume APIs without embedding provider logic.

**Affected Layers and Components**

- Controller: conversation list/detail, message send and AI response endpoints.
- Service: conversation service, message persistence and AI orchestration boundary.
- Repository: tenant-scoped conversations and messages.
- Domain/Model: message author, visibility, attachment and claim/customer links if missing.
- Infrastructure: audit/request logging and optional background queue.
- Frontend: chat list, thread view, composer, citations/sources and failure states.

**Backward Compatibility and Data Impact**

- Additive APIs preferred.
- Migration likely required for persisted conversation/message fields if skeleton is incomplete.
- Existing guarded chat endpoint must remain usable or be wrapped compatibly.

**TDD Implementation Sequence**

1. Fail: add backend tests for creating conversations, sending messages and listing tenant-scoped threads.
2. Fix: implement repository/service persistence.
3. Verify: run conversation tests.
4. Fail: add tests for guarded AI answer persistence, citations and fallback behavior.
5. Fix: wire AI service orchestration and store assistant responses.
6. Verify: run AI/chat tests with provider mocks.
7. Fail: add RBAC tests for customer, employee and admin conversation visibility.
8. Fix: enforce role-aware conversation access.
9. Verify: run backend RBAC tests.
10. Fail: add frontend checks for chat loading, streaming or pending state, failed answer state and citations.
11. Fix: build chat UI on `/ai` and portal/support entry points.
12. Verify: run frontend checks and manual smoke through local API mocks or dev server.
13. Commit: `feat: add persisted support chat UI`.

**Validation and Edge Cases**

- Empty conversation.
- AI retrieval returns no relevant source.
- AI provider fails or times out.
- User sends duplicate message.
- Customer tries to open another customer's conversation.
- Employee joins a claim-linked conversation.

**Security and Tenancy**

- Conversation access must be scoped by tenant and role.
- AI prompts must not include data from other organizations.
- Citations should expose only documents the actor can access.
- Sensitive internal notes should not be sent to customer-visible AI context.

**Performance and Data Design**

- Paginate conversation list and message history.
- Store compact message records; avoid duplicating large retrieved documents.
- Consider background job pattern if AI latency blocks request responsiveness.
- Add indexes for tenant, customer, claim, assignee and last-message timestamp as needed.

**Acceptance Criteria**

- Conversations and messages persist across refreshes.
- AI answers are stored with safe source references or fallback text.
- Customers and employees see only authorized threads.
- UI handles pending, empty, error and no-source answer states.

### Task 06 - Rich Dashboard Charts and SLA Alerts

**Goal**

Upgrade role-specific dashboards with charts, queue/claim metrics and SLA alert surfaces based on reliable workflow data.

**Depends On**

- Task 03 employee workload queues.
- Task 04 claim lifecycle state machine.
- Task 05 persisted conversations if support SLA is included.

**Architecture Fit**

- `dashboard` owns read-only aggregation services.
- `insurance` remains the source of truth for claims, assignments, appointments and support.
- `shared` owns alert jobs if SLA notification processing is required.
- Frontend `/dashboard` owns visualization and alert presentation.

**Affected Layers and Components**

- Controller: dashboard metrics and SLA alert endpoints.
- Service: aggregation service and SLA evaluation service.
- Repository: optimized read models or aggregate queries.
- Domain/Model: SLA policy/config and alert records only if alerts must persist.
- Infrastructure: background worker for scheduled SLA checks if required.
- Frontend: charts, metric cards, alert table and drill-down links.

**Backward Compatibility and Data Impact**

- Existing dashboard APIs should remain or gain additive fields.
- Migration required only for persisted SLA rules or alert history.
- No workflow mutation should happen inside dashboard aggregation endpoints.

**TDD Implementation Sequence**

1. Fail: add aggregation tests for claim counts, queue aging, policy volume and support/appointment metrics.
2. Fix: implement dashboard service projections using existing workflow tables.
3. Verify: run dashboard tests.
4. Fail: add SLA rule tests for due, breached and resolved alert states.
5. Fix: implement SLA evaluation and optional alert persistence/job.
6. Verify: run SLA tests.
7. Fail: add tenant/RBAC tests for dashboard metric visibility by role.
8. Fix: enforce role-specific metrics and filters.
9. Verify: run backend dashboard/RBAC tests.
10. Fail: add frontend checks for chart rendering, empty data and alert drill-down.
11. Fix: implement rich dashboard UI.
12. Verify: run frontend checks and a local visual smoke test.
13. Commit: `feat: add dashboard charts and sla alerts`.

**Validation and Edge Cases**

- No claims or queues exist for a tenant.
- SLA alert is exactly at threshold.
- Claim is closed after an alert was generated.
- Metrics differ by role.
- Large tenant has many claims and messages.

**Security and Tenancy**

- Dashboard queries must always include tenant scope.
- Role-specific dashboards must not expose customer PII unless allowed.
- SLA alerts must link only to resources visible to the actor.
- Background jobs must not rely on request `HttpContext` or transient user headers.

**Performance and Data Design**

- Use aggregate queries and projections, not per-row service loops.
- Add pagination to alert lists.
- Add indexes for tenant, state, due date, assigned employee and last activity.
- Consider cached/read-model metrics only after query tests show need.

**Acceptance Criteria**

- Dashboard shows actionable charts and SLA alerts for each supported role.
- Metrics are consistent with queue and claim lifecycle data.
- Alert links drill into authorized claim, queue or conversation views.
- Tests cover aggregation correctness, threshold boundaries, RBAC and tenant isolation.

## Detailed Sequential Agent Backlog

Use this backlog as the execution source of truth. Agents should run tasks in order, finish all acceptance criteria for the current task, then move to the next task. Each task is intentionally scoped so it can be implemented, verified and committed without requiring parallel work.

The `T00` tasks are mandatory hardening prerequisites. Do not start `T01` or product feature tasks until `T00.1` through `T00.7` are complete or explicitly waived in the plan with rationale.

### T00.1 - Move Production Auth and Tenant Resolution to the Front

**Status**

- Completed.

**Depends On**

- Current platform auth context and JWT session implementation.

**JTBD**

As a production operator, I need tenant, actor and role to come from trusted credentials before any customer, queue, claim, chat or dashboard feature can safely expose tenant-owned data.

**Description**

Harden auth mode before feature work by making demo-header auth explicitly local-only and production-like mode bearer-token-only.

**Implementation**

- Add tests for production-like config rejecting requests that rely only on `X-Organization-Id`, `X-User-Id` or `X-Role`.
- Add or verify a config flag that controls demo header auth.
- Ensure production mode resolves organization, user and role from JWT claims only.
- Reject malformed, expired or missing bearer tokens with consistent error responses.
- Update backend README to label demo headers as local-only and unsafe for production.

**Acceptance Criteria**

- Production-like config rejects header-only auth.
- Demo mode remains available for local seed/demo flows.
- Tests cover demo mode, production mode, expired token and missing token.
- No route can switch tenant or role through client-controlled headers in production-like config.

### T00.2 - Standardize API Collection, Pagination and Rate-Limit Contracts

**Status**

- Completed.

**Depends On**

- T00.1.

**JTBD**

As a frontend or backend agent, I need consistent collection contracts and rate-limit expectations so list screens remain stable and endpoints are protected from accidental overload.

**Description**

Define the platform-wide API contract for list endpoints, bounded query parameters and endpoint rate-limit tiers before adding new APIs.

**Implementation**

- Document a standard collection response shape with `items` and `meta`.
- Define default and maximum `limit` values for small lists, queues, conversations, audit/history and dashboard alerts.
- Define deterministic sort requirements for every list endpoint.
- Assign rate-limit tiers to planned endpoint classes: `auth-sensitive`, `write-command`, `read-list`, `ai-expensive`, `internal-job`.
- Add a compatibility note for existing `ListResponse` if it cannot be changed immediately.

**Acceptance Criteria**

- `docs/PLAN.md` names the collection envelope and pagination parameters all future list APIs must use.
- Every planned endpoint class has a rate-limit tier.
- Agents know whether to extend the current `ListResponse` or introduce a backward-compatible paginated response.
- No future list task is allowed to return an unbounded collection.

### T00.3 - Add Tenant Isolation and Object Authorization Test Harness

**Status**

- Completed.

**Depends On**

- T00.2.

**JTBD**

As an implementation agent, I need reusable tenant-isolation tests so every new feature proves it cannot read or mutate another tenant's data.

**Description**

Create reusable backend test fixtures/helpers for cross-tenant and cross-role access checks.

**Implementation**

- Add test helpers for creating two organizations, users, customers and role contexts.
- Add helper assertions for forbidden, not found and no-cross-tenant leakage behavior.
- Cover representative existing endpoints for plans, customers, policies, incidents and conversations.
- Document how feature tasks should reuse the helpers.

**Acceptance Criteria**

- Tenant isolation helpers exist and are used by at least one current insurance endpoint test.
- Tests prove an actor from tenant A cannot access tenant B records.
- Tests prove customer role cannot list all tenant customers through employee/admin endpoints.
- Future feature tasks can reference these helpers directly in their acceptance criteria.

### T00.4 - Add Query Budget, Index Plan and N+1 Review Gate

**Status**

- Completed.

**Depends On**

- T00.3.

**JTBD**

As the system scales, I need expensive list, queue, dashboard and chat queries to be bounded and indexed before UI usage turns them into operational bottlenecks.

**Description**

Define performance gates for repository queries and migrations before adding queue, claim, chat and dashboard features.

**Implementation**

- Add a `Query and Index Budget` subsection to the plan.
- For each current and planned high-volume table, list expected predicates and indexes: organization, customer, employee, status, due date, created date and conversation/claim references.
- Require projection-only list queries for queues, dashboards and portal summaries.
- Require a simple N+1 review step for every service that assembles related records.
- Document when offset pagination is acceptable and when cursor pagination is required.

**Acceptance Criteria**

- Planned portal, queue, claim, chat and dashboard list queries have index guidance.
- Dashboard aggregation tasks require aggregate SQL/projection queries, not per-row service loops.
- Conversation/message history tasks require bounded page sizes.
- Every future migration task includes index impact in acceptance criteria.

### T00.5 - Define Idempotency, Audit and PII Logging Rules

**Status**

- Completed.

**Depends On**

- T00.4.

**JTBD**

As a user on an unreliable network, I need retries to be safe; as an operator, I need audit trails without leaking sensitive data.

**Description**

Define retry-safe command behavior and audit/logging redaction rules for all mutations.

**Implementation**

- Define which command endpoints require `X-Idempotency-Key` or a get-or-create behavior.
- Define duplicate handling for appointment requests, conversation starts, message sends, queue actions and claim transitions.
- Add audit event minimum fields: tenant, actor, action, resource type, resource id, trace id and safe metadata.
- Add PII logging rules: no tokens, raw prompts, full message bodies, full claim descriptions or uploaded document contents in logs/audit metadata.

**Acceptance Criteria**

- Every planned command task states its idempotency strategy.
- Every mutation task states audit event expectations.
- Logs/audit metadata rules explicitly exclude sensitive raw content.
- AI and support-message tasks know which text may be stored versus logged.

### T00.6 - Define AI Retrieval and Prompt Security Guardrails

**Status**

- Completed.

**Depends On**

- T00.5.

**JTBD**

As a tenant using AI support, I need the chatbot to answer only from authorized tenant knowledge and avoid exposing raw internal data through prompts, logs or citations.

**Description**

Add security and performance constraints for guarded chat before persisted support chat is exposed in customer workflows.

**Implementation**

- Require tenant filter on every knowledge document, chunk and chat lookup.
- Require source/citation references to expose IDs/titles only when the actor can access them.
- Bound prompt context size, retrieved chunk count and stored citation payload size.
- Define fallback behavior for no-source, provider timeout and provider error cases.
- Define logging policy for prompts and answers.

**Acceptance Criteria**

- AI chat tasks include tenant-scoped retrieval tests.
- AI chat tasks include no-source, timeout and provider-error tests.
- Prompt and citation payload limits are documented.
- No task may log raw prompts, raw uploaded document contents or full assistant answers at INFO level.

### T00.7 - Add Frontend Security and Data Exposure Guardrails

**Status**

- Completed.

**Depends On**

- T00.6.

**JTBD**

As a user, I need frontend screens to avoid exposing tokens, tenant identifiers or unauthorized data through browser storage, static demo fallbacks or unsafe rendering.

**Description**

Define frontend security requirements before implementing portal, queue, claim, chat and dashboard screens.

**Implementation**

- Document that sensitive tokens must not be stored in `localStorage`.
- Require API clients to handle forbidden and unauthorized states without falling back to another user's demo data.
- Require user-generated text rendering through React text nodes, not unsanitized HTML.
- Require `NEXT_PUBLIC_*` variables to contain only non-sensitive configuration.
- Add frontend checks for placeholder links on implemented feature paths.

**Acceptance Criteria**

- Feature UIs cannot use static demo data as a silent fallback for authenticated sensitive screens.
- No implemented feature introduces unsanitized HTML rendering.
- No implemented feature stores JWT/session secrets in browser local storage.
- Implemented feature pages replace primary `href="#"` actions with real buttons, links or disabled states.

### T00.8 - Add C4 Context and Container Architecture Documentation

**Status**

- Completed.

**Depends On**

- T00.7.

**JTBD**

As an implementation agent, I need a shared architecture picture so I can see which module owns each responsibility and how frontend, backend, database, worker, storage and AI retrieval interact.

**Description**

Document the current and target system architecture using lightweight C4 context/container views before feature expansion.

**Implementation**

- Add a `C4 Architecture Snapshot` section to `docs/ARCHITECTURE.md` or `docs/PLAN.md`.
- Document the system context: users, NextJS frontend, FastAPI backend, PostgreSQL, local storage, worker and AI/retrieval components.
- Document backend containers/modules: `core`, `platform`, `shared`, `insurance`, `ai`, `dashboard`.
- Include data flow for customer portal, claim lifecycle, support chat and dashboard/SLA.
- State that the current deployment remains a modular monolith unless a future ADR explicitly splits services.

**Acceptance Criteria**

- Architecture docs include context and container-level diagrams or structured text equivalent.
- Each module has an owner responsibility and forbidden responsibility.
- Feature agents can identify the owning module for portal, queue, claim, chat and dashboard work.
- No code behavior changes are introduced.

### T00.9 - Add Architecture Decision Records for Core Choices

**Status**

- Completed.

**Depends On**

- T00.8.

**JTBD**

As a future maintainer, I need major architectural decisions recorded with trade-offs so agents do not repeatedly reopen or contradict foundational choices.

**Description**

Create lightweight ADRs for high-impact decisions that affect every feature task.

**Implementation**

- Add an ADR folder, such as `docs/adr/`, if one does not exist.
- Create ADRs for modular monolith boundaries, production auth mode, collection pagination envelope, claim lifecycle ownership, support chat AI orchestration, dashboard read models and SLA job execution.
- Each ADR must include context, decision, alternatives considered, consequences and review date.
- Link ADRs from `docs/ARCHITECTURE.md` and `docs/PLAN.md`.

**Acceptance Criteria**

- At least seven ADRs exist for the decisions listed above.
- Each ADR names accepted alternatives and rejected alternatives.
- Future backlog tasks reference the relevant ADR when changing the decision.
- No implementation task proceeds by inventing a conflicting architecture pattern.

### T00.10 - Define Module Dependency and Port Contracts

**Status**

- Completed.

**Depends On**

- T00.9.

**JTBD**

As an implementation agent, I need explicit dependency rules so new services do not create circular imports or leak domain concerns across modules.

**Description**

Define allowed dependencies and the port/interface contracts for cross-domain interactions.

**Implementation**

- Add a `Module Dependency Contract` section to architecture docs.
- Define allowed dependencies: routers -> services -> repositories/models; domains -> `core`; domains -> selected `shared` infrastructure; cross-domain calls only through documented service contracts or ports.
- Decide how audit logging is consumed: direct platform service dependency, `core` audit port, or shared application service. Record the decision in ADR.
- Define how `insurance` can request AI assistance without importing provider-specific AI internals.
- Define how `dashboard` reads insurance data without owning workflow mutations.

**Acceptance Criteria**

- Architecture docs list allowed and forbidden imports by module.
- Audit, AI orchestration, dashboard reads and shared job usage have explicit contracts.
- No planned task requires a circular dependency.
- Future agents know where to place orchestrator services.

### T00.11 - Define Domain Event and Background Job Ownership

**Status**

- Completed.

**Depends On**

- T00.10.

**JTBD**

As the platform grows, I need async workflows to be reliable and owned by the correct domain so background jobs do not become an unstructured shared dumping ground.

**Description**

Define how domain events, audit events and background jobs are represented and owned across modules.

**Implementation**

- Document whether the platform will use direct service calls, domain events, outbox-like records or queued jobs for cross-domain side effects.
- Define ownership rules: `shared` owns job infrastructure; domain/application modules own job payloads and handlers.
- Define retry, dedupe, poison-job and observability behavior for jobs.
- Specify which future workflows must be async: PDF ingestion, SLA evaluation and potentially AI answer generation.

**Acceptance Criteria**

- Background job ownership rules are documented.
- Async workflows list retry and failure behavior.
- Job payloads include tenant, trace id and idempotency key where applicable.
- No future task can add fire-and-forget work inside request handlers.

### T00.12 - Define Data Ownership, Read Models and Migration Sequencing

**Status**

- Completed.

**Depends On**

- T00.11.

**JTBD**

As a data-owning system, I need clear source-of-truth boundaries and safe migration sequencing so new workflow state does not corrupt existing incidents, policies, conversations or dashboard metrics.

**Description**

Document source-of-truth ownership, read-model rules and expand/backfill/contract sequencing for upcoming schema changes.

**Implementation**

- Add a `Data Ownership and Migration Strategy` section.
- Assign source-of-truth tables to modules: platform identity/audit, insurance workflows, AI knowledge/chat, shared files/jobs, dashboard read projections.
- Define when dashboard/SLA may use direct aggregate queries versus persisted read models.
- Define migration sequencing for claim lifecycle, queue fields, conversation links and SLA alerts.
- Add rollback and compatibility notes for every migration class of work.

**Acceptance Criteria**

- Every planned schema-changing task has a named owner module.
- Existing data backfill needs are identified before migrations are implemented.
- Dashboard/SLA read ownership is explicit and cannot mutate workflow state.
- Migration tasks include expand/backfill/contract or a documented single-step exception.

### T01.1 - Create Architecture Gap Matrix

**Status**

- Completed.

**Depends On**

- T00.12.
- Current Markdown docs and existing backend/frontend source tree.

**JTBD**

When an implementation agent starts work, it needs a precise map of what exists, what is partial and what is missing so it can avoid rediscovery and choose the correct next file/module.

**Description**

Create a documentation-only gap matrix for the six continuation areas: customer portal, workload queues, claim lifecycle, persisted chat, dashboard/SLA and production auth/tenancy.

**Implementation**

- Add a `Current Implementation Status` section to `docs/PLAN.md`.
- For each area, record `exists`, `partial`, `missing` and the source files proving that status.
- Include backend routes, services, models, tests and frontend pages.
- Call out demo-header auth fallback as a known production-hardening gap.

**Acceptance Criteria**

- `docs/PLAN.md` contains a status matrix with evidence file paths.
- Every row has an explicit next action.
- No runtime behavior or code files are changed.

### T01.2 - Define API Contract Inventory

**Status**

- Completed.

**Depends On**

- T01.1.

**JTBD**

When frontend and backend agents work independently, they need stable endpoint names and payload expectations so UI work does not invent contracts that backend later rejects.

**Description**

Document the intended additive API contracts for customer portal, queues, claim lifecycle, conversations and dashboard/SLA.

**Implementation**

- Add a `Planned API Contracts` subsection under the detailed backlog.
- List method, path, role access, request shape summary and response shape summary.
- Mark contracts as `existing`, `extend existing` or `new`.
- Keep contracts additive unless a later task explicitly migrates a legacy behavior.
- Link each contract to its owning module and relevant ADR.

**Acceptance Criteria**

- Each product area has at least one planned endpoint or an explicit note that no endpoint is needed.
- Role access is listed for every planned endpoint.
- Existing routes are not renamed in the plan.
- Every contract has a module owner and avoids cross-domain ownership ambiguity.

### T01.3 - Define Frontend Route Inventory

**Status**

- Completed.

**Depends On**

- T01.2.

**JTBD**

When UI agents build screens, they need to know which route owns each workflow so dashboard, insurance operations, AI and portal surfaces do not overlap awkwardly.

**Description**

Document frontend route ownership and expected pages/components for the next implementation wave.

**Implementation**

- Add a `Planned Frontend Routes` subsection.
- Map `/portal`, `/insurance`, `/insurance/claims/[id]`, `/ai`, `/dashboard` and `/admin` to the owning feature.
- Note which screens are read-only, command-capable or dashboard-only.

**Acceptance Criteria**

- Every backlog feature maps to a frontend route or explicitly says backend-only.
- Existing routes are preserved unless a migration task is listed.
- The route list names the first screen each agent should implement.

### T02.1 - Add Customer Portal Summary Read API

**Status**

- Completed.

**Depends On**

- T01.1, T01.2, T01.3.

**JTBD**

As a customer, I want to see a private summary of my policies, incidents, appointments and support activity so I can understand my insurance status without contacting an employee.

**Description**

Add the first customer self-service backend endpoint that resolves the customer from the authenticated user and returns a tenant-scoped portal summary.

**Implementation**

- Add failing backend tests for a customer reading only their linked `InsuranceCustomer` record.
- Add repository helpers to fetch customer summary data by `organization_id` and `linked_user_id`.
- Add a customer portal service that returns policies, recent incidents, upcoming appointments and open conversations.
- Add `GET /api/v1/insurance/portal/summary` or the documented equivalent.
- Enforce `customer` role, while optionally allowing `admin` for support/debug access if explicitly documented.

**Acceptance Criteria**

- A customer with a linked customer record receives only their own data.
- A customer without a linked record receives a clear 404 or empty portal response as documented.
- Cross-customer access is impossible because no `customer_id` is accepted from the client.
- Tests cover success, no linked customer and cross-tenant isolation.

### T02.2 - Add Customer Portal History APIs

**Status**

- Completed.

**Depends On**

- T02.1.

**JTBD**

As a customer, I want paginated history for policies, incidents, appointments and conversations so I can review details without one giant payload.

**Description**

Split portal summary into paginated resource history endpoints owned by the customer portal service.

**Implementation**

- Add failing tests for pagination and tenant/customer scoping.
- Add `GET` endpoints for portal policies, incidents, appointments and conversations.
- Use limit/offset or the repo's existing list response pattern.
- Return projection DTOs instead of raw models.

**Acceptance Criteria**

- Each history endpoint is paginated.
- Every query filters by organization and resolved linked customer.
- Empty histories return stable empty lists.
- Tests cover pagination boundaries and forbidden role access.

### T02.3 - Build Customer Portal Frontend Shell

**Status**

- Completed.

**Depends On**

- T02.1, T02.2.

**JTBD**

As a customer, I want one portal page that clearly shows my active coverage, recent claim activity and next support step so I can self-serve quickly.

**Description**

Create the first customer portal route and render the portal summary with robust loading, empty and error states.

**Implementation**

- Add a frontend route such as `frontend/app/portal/page.tsx`.
- Add API client methods for portal summary and history endpoints.
- Render policy summary, recent incidents, upcoming appointment and support conversation entry cards.
- Avoid demo fallback data for authenticated portal content unless clearly marked as local demo behavior.

**Acceptance Criteria**

- Portal route renders summary data from the backend contract.
- Empty, loading, forbidden and backend-error states are visible and stable.
- The page does not expose another customer's identifier as an input.
- Frontend checks pass.

### T02.4 - Add Portal Support and Appointment Commands

**Status**

- Completed.

**Depends On**

- T02.3.

**JTBD**

As a customer, I want to request appointments and start support conversations from the portal so I do not need internal employee tools.

**Description**

Add safe customer commands for appointment request and support conversation creation.

**Implementation**

- Add backend tests proving customer commands resolve customer identity server-side.
- Add portal-specific appointment request and conversation start endpoints or adapt existing endpoints with stricter service methods.
- Audit command events using the existing audit service pattern.
- Add frontend forms/actions for appointment request and new support conversation.

**Acceptance Criteria**

- Customer command payloads do not accept arbitrary `customer_id`.
- Appointment and conversation records are tenant-scoped and linked to the resolved customer.
- Audit events are recorded for command creation.
- UI confirms success and handles validation errors.

### T03.1 - Add Workload Queue Data Model Fields

**Status**

- Completed.

**Depends On**

- T02.4.

**JTBD**

As an employee, I need assigned work to have status, priority and due dates so I can decide what to handle first.

**Description**

Add the minimum durable fields required to support operational queues for assignments, incidents, appointments and support conversations.

**Implementation**

- Inspect existing models before adding fields.
- Add Alembic migration for missing `priority`, `due_at` or queue-related status fields where needed.
- Use constrained values or documented enums for queue states.
- Update schemas only for fields exposed through queue APIs.

**Acceptance Criteria**

- Migration applies cleanly from the current schema.
- Existing create/list endpoints still work.
- Queue state values are documented and not free-form in service code.
- Database contract test includes any new core queue table/field assumptions.

### T03.2 - Add Employee Queue List API

**Status**

- Completed.

**Depends On**

- T03.1.

**JTBD**

As an employee, I want a filtered list of my assigned work so I can triage customers, incidents, appointments and messages from one queue.

**Description**

Add read-only queue endpoints for employee and admin views.

**Implementation**

- Add failing service/repository tests for assignee, status, priority and due date filters.
- Implement tenant-scoped queue projection queries.
- Add `GET /api/v1/insurance/queues/my` for employees.
- Add `GET /api/v1/insurance/queues` for admins with filter support.
- Include stable sorting and pagination.

**Acceptance Criteria**

- Employee queue only returns items in the employee's permitted scope.
- Admin queue supports documented filters.
- Customer role receives forbidden.
- Tests cover empty queue, filter combinations and tenant isolation.

### T03.3 - Add Queue Detail and Assignment Actions

**Status**

- Completed.

**Depends On**

- T03.2.

**JTBD**

As an admin or employee, I want to open a queue item and perform permitted assignment/status actions so work can move forward without switching tools.

**Description**

Add queue item detail endpoints and controlled mutation actions for assignment, priority and status.

**Implementation**

- Add tests for allowed and forbidden assignment/status changes.
- Add endpoints for queue detail, assign/reassign, update priority and update queue status.
- Record audit events for every mutation.
- Add optimistic concurrency or last-updated validation if the existing stack supports it.

**Acceptance Criteria**

- Invalid role mutations are forbidden.
- Assignment updates are tenant-scoped and audited.
- Concurrent or stale updates fail safely or are documented.
- Existing assignment create API remains backward-compatible.

### T03.4 - Build Employee Queue Frontend

**Status**

- Completed.

**Depends On**

- T03.3.

**JTBD**

As an employee, I want a scannable operations queue with filters and actions so I can work through assigned cases efficiently.

**Description**

Upgrade the insurance operations UI from a customer table into a queue workspace.

**Implementation**

- Add API client methods for queue list/detail/actions.
- Add queue table with filters for type, status, priority, due date and assignee where permitted.
- Add detail panel or route for selected queue item.
- Add action buttons for permitted transitions.

**Acceptance Criteria**

- Queue UI works for employee and admin role contracts.
- Empty, loading, error and forbidden states are handled.
- Filter changes do not break layout or require full page hacks.
- Frontend checks pass.

### T04.1 - Define Claim State Machine Contract

**Status**

- Completed.

**Depends On**

- T03.4.

**JTBD**

As the platform, I need claim states and transitions to be explicit so invalid lifecycle movement cannot happen through arbitrary status strings.

**Description**

Define claim lifecycle states, transition rules, actor roles and required metadata before implementing persistence.

**Implementation**

- Add a documented state table to `docs/PLAN.md` or `docs/ARCHITECTURE.md`.
- Define states such as `reported`, `triage`, `in_review`, `approved`, `rejected`, `closed` and `reopened` if appropriate.
- Define allowed transitions, allowed roles and required fields.
- Add failing unit tests for the transition matrix.

**Acceptance Criteria**

- Transition matrix is documented.
- Unit tests fail before implementation.
- Invalid states are not represented only as ad hoc strings in new service code.

### T04.2 - Add Claim Lifecycle Persistence

**Status**

- Completed.

**Depends On**

- T04.1.

**JTBD**

As an operations team, we need every claim transition persisted with actor, timestamp and reason so claim handling is traceable.

**Description**

Add model/migration support for claim state and transition history while preserving existing incident APIs.

**Implementation**

- Add migration for claim lifecycle fields or new transition history table.
- Map existing incident reports to an initial claim state.
- Add SQLAlchemy models and schemas for transition history.
- Keep existing incident response fields backward-compatible.

**Acceptance Criteria**

- Migration preserves existing incident rows.
- New transition history table or fields are tenant-scoped.
- Existing incident create/list endpoints still pass tests.
- Database metadata tests include lifecycle persistence.

### T04.3 - Add Claim Transition Service and API

**Status**

- Completed.

**Depends On**

- T04.2.

**JTBD**

As an authorized employee, I want to move a claim through valid states so work progresses with business rules enforced.

**Description**

Implement the state machine service and expose claim detail/history/transition endpoints.

**Implementation**

- Implement a claim lifecycle service around the documented transition matrix.
- Add `GET` claim detail and history endpoints.
- Add `POST` transition endpoint with required reason/evidence fields.
- Add RBAC and tenant checks on every lookup.
- Record audit events for state changes.

**Acceptance Criteria**

- Allowed transitions succeed and write history.
- Forbidden transitions fail before persistence.
- Unauthorized roles cannot transition claims.
- Tests cover transition success, invalid transition, missing reason and tenant isolation.

### T04.4 - Build Claim Detail Frontend

**Status**

- Completed.

**Depends On**

- T04.3.

**JTBD**

As an employee, I want to see claim state, timeline and available actions so I can process a claim confidently.

**Description**

Add claim detail UI with timeline, state badge and role-aware transition actions.

**Implementation**

- Add claim detail route such as `/insurance/claims/[id]`.
- Add API client methods for claim detail, history and transition.
- Render timeline and current state.
- Disable or hide invalid actions based on backend-provided allowed actions.

**Acceptance Criteria**

- Claim detail page renders state and transition history.
- Invalid actions are not presented as active controls.
- Transition form handles validation and server errors.
- Frontend checks pass.

### T05.1 - Add Conversation List and Detail APIs

**Status**

- Completed.

**Depends On**

- T04.4.

**JTBD**

As a customer or employee, I want to reopen previous support conversations so support context is not lost between messages.

**Description**

Add read APIs for persisted insurance conversations and message history.

**Implementation**

- Add tests for conversation list/detail by role.
- Add tenant-scoped repository methods for conversations and messages.
- Add paginated `GET` conversation list and detail endpoints.
- Enforce customer, employee and admin visibility rules.

**Acceptance Criteria**

- Customers only see their own conversations.
- Employees only see assigned/permitted conversations unless admin.
- Message history is paginated.
- Empty conversation renders as an empty message list.

### T05.2 - Connect Insurance Conversations to AI Answers

**Status**

- Completed.

**Depends On**

- T05.1.

**JTBD**

As a support user, I want AI answers inside the same conversation thread so answers, citations and human follow-up stay together.

**Description**

Bridge the existing guarded AI chat service into persisted insurance conversations without coupling provider logic into insurance routes.

**Implementation**

- Add service tests for sending a message that optionally requests AI assistance.
- Add an orchestration method that stores the user message, calls the AI service and stores assistant response with citations.
- Reuse guarded retrieval behavior and no-source fallback.
- Avoid storing full retrieved documents in message records.

**Acceptance Criteria**

- User and assistant messages persist in the same conversation.
- AI no-source fallback is stored and visible.
- Citations are stored as safe references.
- AI cannot retrieve or cite another tenant's documents.

### T05.3 - Add Chat UI for Persisted Threads

**Status**

- Completed.

**Depends On**

- T05.2.

**JTBD**

As a user, I want a thread-based chat UI with message history and citations so I can continue support conversations naturally.

**Description**

Replace the placeholder `/ai` page with a functional conversation list, thread view and composer.

**Implementation**

- Add frontend API methods for conversation list, detail and message send.
- Render conversation sidebar/list, active thread and message composer.
- Show citations for assistant messages.
- Handle pending, failed, empty and no-source states.

**Acceptance Criteria**

- `/ai` no longer uses placeholder `href="#"` actions for primary chat behavior.
- Refreshing the page preserves conversation history from backend data.
- Sending a message updates the thread without losing existing messages.
- Frontend checks pass.

### T05.4 - Add Claim and Portal Conversation Entry Points

**Status**

- Completed.

**Depends On**

- T05.3.

**JTBD**

As a customer or employee, I want to start or continue conversation from the related portal or claim page so support context stays attached to the workflow.

**Description**

Add conversation entry points from customer portal and claim detail surfaces.

**Implementation**

- Add optional claim/customer link fields if missing and required by the documented contract.
- Add buttons/links from portal summary and claim detail to the relevant conversation.
- Ensure creation flows attach the conversation to customer and claim when present.

**Acceptance Criteria**

- Portal support entry opens or creates a customer-scoped conversation.
- Claim detail entry opens or creates a claim-linked conversation.
- Visibility rules remain enforced.
- No duplicate conversation is created when an open thread already exists and reuse is documented.

### T06.1 - Add Dashboard Metric Aggregation Contracts

**Status**

- Completed.

**Depends On**

- T05.4.

**JTBD**

As an admin or employee, I want reliable metrics from workflow data so I can spot workload and claim bottlenecks.

**Description**

Expand dashboard backend contracts beyond simple counts into queue, claim, policy and support metrics.

**Implementation**

- Add tests for aggregate counts by claim state, queue status, overdue work and support activity.
- Add read-only service methods in `dashboard`.
- Use tenant-scoped aggregate queries and projections.
- Keep existing `/dashboard/summary` backward-compatible where possible.

**Acceptance Criteria**

- Dashboard metrics are derived from persisted workflow tables.
- Aggregates are tenant-scoped.
- Existing summary consumers still work or receive documented additive fields.
- Tests cover empty tenant and non-empty tenant.

### T06.2 - Add SLA Rule and Alert Persistence

**Status**

- Completed.

**Depends On**

- T06.1.

**JTBD**

As an operations lead, I want SLA alerts persisted so breached work can be reviewed, resolved and audited.

**Description**

Introduce SLA rules and alert records for claims, queues and support conversations.

**Implementation**

- Add migration for SLA policy/config and alert records if persistence is required.
- Add service tests for due, breached, resolved and boundary-threshold states.
- Add tenant-scoped models and repositories.
- Define default demo SLA thresholds for local seed data if needed.

**Acceptance Criteria**

- SLA alert records are tenant-scoped.
- Boundary tests cover exactly-at-threshold behavior.
- Closed/resolved workflow items stop producing active alerts.
- Migration applies cleanly.

### T06.3 - Add SLA Evaluation Job

**Status**

- Completed.

**Depends On**

- T06.2.

**JTBD**

As the system, I need SLA checks to run outside request handling so alerts stay current without relying on user traffic.

**Description**

Add background evaluation for SLA alerts using the existing shared job/worker infrastructure.

**Implementation**

- Add a scheduled or enqueueable SLA evaluation job.
- Capture organization and rule data explicitly; do not depend on request context.
- Add tests for idempotent alert creation and alert resolution.
- Log or audit evaluation outcomes using existing observability patterns.

**Acceptance Criteria**

- Running the job twice does not create duplicate active alerts.
- Resolved workflow items resolve or suppress related alerts.
- Job code does not depend on request headers or transient auth context.
- Worker smoke test or focused unit test passes.

### T06.4 - Add Dashboard Charts and Alert API

**Status**

- Completed.

**Depends On**

- T06.3.

**JTBD**

As a dashboard user, I want chart-ready series and alert lists so the frontend can render useful operational insights without doing backend aggregation in the browser.

**Description**

Add chart data endpoints and paginated SLA alert endpoints.

**Implementation**

- Add endpoints for chart series, metric cards and alert list/detail.
- Return compact chart-ready DTOs.
- Add RBAC filters so users see only permitted metrics and alerts.
- Add pagination for alerts.

**Acceptance Criteria**

- Chart endpoints return stable labels, values and time buckets.
- Alert endpoints are paginated and tenant-scoped.
- Role-specific dashboards do not expose unauthorized PII.
- Backend tests cover role visibility and empty data.

### T06.5 - Build Rich Dashboard Frontend

**Status**

- Completed.

**Depends On**

- T06.4.

**JTBD**

As an admin or employee, I want a dashboard with charts and actionable SLA alerts so I can decide where to focus operational attention.

**Description**

Replace demo dashboard cards with real API-driven metrics, charts and alert drill-downs.

**Implementation**

- Add frontend API methods for dashboard summary, charts and alerts.
- Render chart components using the project's chosen chart approach or lightweight accessible HTML/CSS if no chart library exists.
- Render SLA alert table with status, age, owner and drill-down link.
- Add empty, loading, error and forbidden states.

**Acceptance Criteria**

- Dashboard page no longer relies on static `demo-data` for primary metrics.
- Charts render from backend chart DTOs.
- Alert links open authorized claim, queue or conversation pages.
- UI remains stable on empty and large datasets.
- Frontend checks pass.

### T07.1 - Run Final Security and Performance Regression Gate

**Status**

- Completed.

**Depends On**

- T00.7.
- T06.5.

**JTBD**

As a maintainer, I need a final review gate that proves the full platform still satisfies the security, tenancy and performance guardrails after all product features have been added.

**Description**

Run a structured final review across auth, tenant isolation, object authorization, API bounds, query performance, idempotency, audit redaction, AI guardrails and frontend data exposure.

**Implementation**

- Re-run production-auth tests from `T00.1`.
- Re-run tenant isolation and role/object authorization tests from `T00.3`.
- Review every list endpoint for pagination metadata, max limits, stable sorting and rate-limit tier.
- Review every mutation endpoint for idempotency behavior and audit metadata redaction.
- Review dashboard/queue/claim/chat queries for index coverage and absence of N+1 service loops.
- Review frontend screens for silent demo-data fallback, sensitive token storage and unsafe HTML rendering.

**Acceptance Criteria**

- No route can bypass trusted auth or tenant scoping in production-like config.
- No list endpoint is unbounded.
- No mutation endpoint has undefined retry behavior.
- No audit/log path stores tokens, raw prompts, full support messages or unnecessary PII.
- Dashboard, queue, portal and chat queries have documented index coverage or an explicit low-volume exception.
- Final review findings are recorded as resolved, accepted risk or follow-up before release.

**Gate Result - 2026-05-28**

- Resolved: legacy insurance and AI list routes now expose bounded `limit` query params with max 100.
- Resolved: frontend `insurance-api` no longer silently falls back to `demo-data` when the API fails.
- Passed: production auth and tenant/object scope focused tests.
- Passed: backend non-integration suite, metadata integration contract, frontend production build and frontend unsafe-pattern scan.
- Accepted risk: mutation idempotency is documented as required but not fully implemented for every command; keep as a follow-up before external production traffic.

### T07.2 - Add End-to-End Regression Checklist

**Status**

- Completed.

**Depends On**

- T07.1.

**JTBD**

As a maintainer, I want a repeatable regression checklist so future agents can verify the whole platform after feature work.

**Description**

Document and, where practical, script the platform-level verification flow across backend tests, frontend checks and local smoke paths.

**Implementation**

- Add a `Verification Checklist` section to `docs/PLAN.md` or README.
- Include backend unit tests, integration tests, migration check, frontend lint/build and manual smoke routes.
- Note required demo seed data and headers.
- Add any missing package scripts only if the repo convention supports it.

**Acceptance Criteria**

- Checklist covers customer portal, queues, claims, chat and dashboard.
- Commands are copy-pasteable from the repo root or clearly scoped to `backend`/`frontend`.
- Manual smoke paths include expected successful and forbidden cases.
- No unrelated refactors are introduced.

### T08.1 - Add Transactional Domain Event Outbox

**Status**

- Pending.

**Depends On**

- T07.2.

**JTBD**

As a maintainer, I need reliable cross-module domain event delivery so claim, incident, support, SLA and notification side effects cannot be lost after a successful database write.

**Description**

Add a transactional outbox for domain events inside the modular monolith. This keeps the current single-database architecture while preventing the failure mode where a business transaction commits but an event dispatch or background side effect is lost.

**Implementation**

- Add an additive migration for `domain_outbox_events` with tenant, event type, aggregate identity, producer module, safe payload, idempotency key, status, attempts, retry timestamps and truncated error fields.
- Add a shared outbox repository/service that can append events inside the same SQLAlchemy transaction as the owning domain change.
- Emit outbox events from high-value workflows first: incident report, claim transition, appointment request, support conversation start/message send, knowledge document ingestion and SLA alert raise/resolve.
- Add a background worker dispatcher with bounded batch size, retry limit, status updates and safe error metadata.
- Make event consumers idempotent by event id or aggregate/idempotency key.
- Keep payloads PII-safe: ids, state values, reason categories and citation ids only; no raw prompts, full messages, uploaded documents or full claim narratives.

**Acceptance Criteria**

- Business write and outbox insert happen in one transaction for the selected workflows.
- Re-running the dispatcher does not duplicate SLA alerts, notifications or audit side effects.
- Failed dispatch attempts are retried with bounded attempts and visible status.
- Outbox queries are tenant/index-friendly and do not full-scan pending events.
- Tests cover successful dispatch, retry behavior, duplicate event delivery and PII-safe payload shape.

### T08.2 - Enforce AI Rate Limit and Provider Budget

**Status**

- Pending.

**Depends On**

- T08.1.

**JTBD**

As a platform operator, I need AI usage bounded by user, tenant and worker budgets so external provider cost, latency and rate-limit failures cannot degrade the whole insurance platform.

**Description**

Implement the `ai-expensive` tier as an enforceable policy for chat, retrieval and ingestion triggers. AI endpoints should fail safely under load and preserve tenant-scoped RAG guardrails.

**Implementation**

- Add rate-limit configuration for `ai-expensive` with stricter per-user and per-tenant defaults than normal writes.
- Apply the tier to `POST /ai/chat`, support AI-assisted message send, retrieval search and knowledge ingestion trigger endpoints.
- Bound prompt size, retrieved chunk count, assistant response size, provider timeout and concurrent ingestion/AI worker jobs.
- Persist safe provider telemetry such as model, timeout/error status, latency and token/cost estimate without raw prompts or full retrieved source text.
- Return `429` with safe retry guidance when a user or tenant exceeds budget.
- Add tests for per-user limit, per-tenant limit, provider timeout fallback, no-source fallback and prompt/log redaction.

**Acceptance Criteria**

- AI endpoints cannot exceed configured per-user or per-tenant request budgets.
- Provider timeout/error returns a safe fallback without losing the original user message.
- Rate-limit violations do not widen retrieval scope, skip tenant filtering or bypass citation requirements.
- Provider telemetry is useful for operations while remaining PII-safe.
- Normal insurance read/write endpoints continue to work when AI budget is exhausted.

### T08.3 - Complete Command Idempotency Hardening

**Status**

- Pending.

**Depends On**

- T08.2.

**JTBD**

As a customer or employee on an unreliable network, I need retried create, send and transition commands to be safe so duplicate clicks or retrying clients do not create duplicate claims, messages, appointments or invalid history.

**Description**

Turn the documented idempotency matrix into implementation for high-risk mutation endpoints before external production traffic.

**Implementation**

- Add shared idempotency persistence keyed by organization, actor, endpoint/command name and `X-Idempotency-Key`.
- Apply explicit retry behavior to incident creation, appointment request, support message send, AI-assisted message send and claim transition commands.
- For claim transitions, combine the idempotency key with state-machine validation so identical retries return the original transition and conflicting retries return a clear conflict.
- Store only response references and safe metadata in idempotency records, not full request bodies containing PII.
- Add tests for duplicate key same payload, duplicate key conflicting payload, missing key where required and concurrent retry behavior.

**Acceptance Criteria**

- Retryable command endpoints document and enforce their idempotency behavior.
- Repeating the same command with the same key returns the existing result or a safe no-op.
- Reusing a key with conflicting payload returns a deterministic conflict response.
- Idempotency records are tenant-scoped and cannot be used across organizations.
- Audit metadata remains PII-safe and includes enough trace context to investigate duplicate submissions.

### T08.4 - Move Dashboard to Event-Fed Read Models

**Status**

- Pending.

**Depends On**

- T08.3.

**JTBD**

As a dashboard maintainer, I need operational metrics to be isolated from private insurance schema changes so reporting can evolve without breaking claim, policy or support workflows.

**Description**

Refactor dashboard reads toward dashboard-owned read models populated from domain events. This removes long-term shared-database coupling while keeping the modular monolith deployment model.

**Implementation**

- Define dashboard read model tables for claim status counts, policy activation metrics, support activity and SLA targets.
- Populate read models from outbox events such as `ClaimTransitioned`, `PolicyActivated`, `AppointmentRequested`, `SupportConversationStarted` and `SupportMessageSent`.
- Replace dashboard queries that depend on private insurance table layout with dashboard projections or stable query-service DTO contracts.
- Add reconciliation job support so read models can be rebuilt from source data during migration or repair.
- Add indexes for tenant, metric dimension, time bucket and target resource lookups.

**Acceptance Criteria**

- Dashboard summary/chart endpoints can read from dashboard-owned projections for the selected metrics.
- A change to private insurance table layout does not require dashboard route/controller changes when the event contract is stable.
- Replaying the same event does not double-count metrics or duplicate active SLA alerts.
- Projection queries are tenant-scoped, bounded and index-backed.
- Tests cover event projection, replay idempotency, empty projection state and reconciliation behavior.

### T08.5 - Unify AI and Human Support Conversation Handoff

**Status**

- Pending.

**Depends On**

- T08.4.

**JTBD**

As a customer, I need one continuous support conversation where AI can help first and an employee can take over without forcing me to start a separate chat.

**Description**

Make `Conversation` the single product-facing support surface. AI responses become assistant messages in the same thread, and low-confidence/no-source/customer-requested human escalation assigns or queues an employee follow-up.

**Implementation**

- Extend conversation/message DTOs to distinguish user, assistant and employee messages without exposing internal orchestration details.
- Add handoff state or tags such as `needs_human`, `ai_no_source`, `low_confidence` and `assigned_employee_id`.
- Route AI-assisted messages through the existing conversation authorization and idempotency flow.
- Add service behavior that creates/updates queue work when AI cannot answer safely or the customer requests a human.
- Update frontend chat UI to show one conversation timeline and employee takeover state.

**Acceptance Criteria**

- Customer uses one conversation route for AI and human support.
- AI no-source or low-confidence result creates a visible handoff/queue signal.
- Employee replies appear in the same authorized thread.
- AI cannot mutate claims, policies or payments during handoff.
- Tests cover customer handoff, employee takeover, duplicate AI retry and cross-tenant conversation access denial.

### T08.6 - Isolate AI Resource Consumption

**Status**

- Pending.

**Depends On**

- T08.5.

**JTBD**

As an operator, I need heavy AI ingestion, retrieval and provider calls isolated so they cannot exhaust resources required by core claim transactions.

**Description**

Separate AI workload resource budgets from core insurance commands through connection-pool configuration, worker concurrency limits and operational telemetry.

**Implementation**

- Add configuration for AI-specific database/session pool limits or a future storage adapter boundary where supported by the current infrastructure.
- Limit concurrent PDF ingestion, embedding, retrieval and provider-call jobs independently from normal background jobs.
- Add timeout and cancellation behavior for AI provider calls and long retrieval operations.
- Add telemetry for AI queue depth, provider latency, timeout count and pool saturation.
- Document fallback behavior when AI resources are exhausted: safe no-source/try-again response while core insurance workflows continue.

**Acceptance Criteria**

- AI worker concurrency is independently configurable from normal shared jobs.
- AI timeout or pool saturation does not block claim transition, queue or dashboard non-AI tests.
- Provider/retrieval timeout paths return safe fallback responses.
- Telemetry exposes AI saturation without logging raw prompts or document contents.
- Tests cover exhausted AI budget and continued non-AI workflow availability.

### T08.7 - Add AI Evaluation Harness and Semantic Guardrails

**Status**

- Pending.

**Depends On**

- T08.6.

**JTBD**

As a product and risk owner, I need objective evidence that AI answers stay grounded, cited and safe against prompt injection before customers rely on them.

**Description**

Add an AI quality and safety evaluation workflow. Prompt rules remain useful, but they must be backed by input/output checks and repeatable evaluation cases.

**Implementation**

- Add an evaluation dataset for insurance knowledge questions, no-source questions, prompt-injection attempts, stale-knowledge cases and forbidden claim-decision prompts.
- Add pre-generation semantic checks for injection, cross-tenant requests and attempts to force claim/policy/payment decisions.
- Add post-generation checks for unsupported commitments, missing citations, citation mismatch and unsafe financial/coverage language.
- Record evaluation metrics such as no-source precision, citation accuracy, hallucination rate and forbidden-decision block rate.
- Add a release checklist step requiring AI prompt/provider changes to run the evaluation harness.

**Acceptance Criteria**

- Evaluation harness can run locally without external production data.
- Guardrails block or safely fallback on prompt-injection and forbidden-decision cases.
- AI answer tests assert citations are present and mapped to allowed tenant knowledge chunks.
- Metrics are documented in test output or a generated report artifact.
- New AI provider/prompt changes have a clear pass/fail quality gate.

## Verification Checklist

Use this checklist after feature work that touches auth, tenant data, insurance workflows, AI chat or dashboards.

### Automated Backend Checks

Run from `backend`:

```bash
python3 -m compileall app
python3 -m pytest app/tests/test_auth_context.py app/tests/test_insurance_tenant_scope.py -q
python3 -m pytest app/tests -q -m 'not integration'
python3 -m pytest app/tests/integration/test_database_contract.py -q
```

Expected result: all commands pass. Integration metadata must include queue fields, claim lifecycle, insurance message AI fields, conversation claim links and SLA tables.

### Automated Frontend Checks

Run from `frontend`:

```bash
npm run build
```

Expected result: production build succeeds and `/portal`, `/insurance`, `/insurance/claims/[id]`, `/ai` and `/dashboard` are dynamic routes when they read API data.

### Security And Exposure Scan

Run from the repo root:

```bash
rg -n "dangerouslySetInnerHTML|localStorage|sessionStorage|href=\"#\"|fallbackCustomers" frontend/app
```

Expected result: no matches for primary application surfaces. Any match must be reviewed and documented before release.

### Manual Smoke Paths

Backend API base: `/api/v1`. Demo headers are local-only:

```text
X-Organization-Id: org_demo
X-User-Id: user_admin | user_employee | user_customer
X-Role: admin | employee | customer
```

- Customer portal: `GET /insurance/portal/summary` as `user_customer/customer` returns only the linked customer profile, policies, incidents, appointments and open conversations.
- Queue: `GET /insurance/queues/my` as `user_employee/employee` returns assigned queue items; `GET /insurance/queues` as `customer` is forbidden.
- Claim lifecycle: `GET /insurance/claims/{claim_id}` as an assigned employee returns state and allowed transitions; `POST /insurance/claims/{claim_id}/transitions` as `customer` is forbidden.
- Support chat: `GET /insurance/conversations` returns role-visible threads; `POST /insurance/conversations/{conversation_id}/messages` with `use_ai=true` stores both user and assistant messages.
- Dashboard: `GET /dashboard/summary` returns additive `metrics`; `GET /dashboard/alerts` is admin-only.
- Production auth: with `ENVIRONMENT=production` and no bearer token, demo headers alone must return `401 missing_access_token`.

### Migration And Data Checks

- Apply Alembic migrations in order from `0001_schema_backbone` through the latest revision.
- Confirm additive migrations preserve existing rows: queue fields default priority, claim state defaults to `reported`, message role defaults to `user`, conversation `claim_id` is nullable.
- For SLA alerts, running evaluation twice must not create duplicate active alerts for the same tenant, target type and target id.
