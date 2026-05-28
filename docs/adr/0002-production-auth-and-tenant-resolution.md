# ADR 0002: Resolve Production Tenant Context from JWT

## Status

Accepted

## Context

Local demo headers are useful for development, but client-controlled tenant, user or role headers are unsafe in production.

## Decision

Production-like environments must require bearer-token authentication. Tenant id, user id, role and permissions must come from validated JWT claims. Demo header auth is local-only.

## Alternatives Considered

- Trust headers in all environments: rejected because users could switch tenant or role.
- Remove demo headers entirely: rejected because local demo workflows benefit from simple seeded contexts.

## Consequences

- Tests must cover demo mode and production-like mode.
- Route and service authorization must not trust client-provided organization or role values.
- Deployment config must explicitly disable demo header auth outside local/test.

## Review Date

2026-08-28
