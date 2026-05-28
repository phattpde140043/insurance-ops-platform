# ADR 0007: Shared Job Infrastructure with Domain-Owned Handlers

## Status

Accepted

## Context

PDF ingestion, SLA evaluation and potentially AI answer generation can exceed request latency budgets or need retries.

## Decision

`shared` owns background job infrastructure. Domain or application modules own job payload semantics and handlers. Jobs must include tenant context, trace context and idempotency data where applicable.

## Alternatives Considered

- Put all job logic in `shared`: rejected because it turns shared infrastructure into a domain dumping ground.
- Run long work fire-and-forget in request handlers: rejected because failures are invisible and request context is unsafe after response.

## Consequences

- Job handlers must define retry, dedupe and poison-job behavior.
- Job payloads should contain minimal resource references, not raw sensitive content.
- Async workflows must not depend on transient request context.

## Review Date

2026-08-28
