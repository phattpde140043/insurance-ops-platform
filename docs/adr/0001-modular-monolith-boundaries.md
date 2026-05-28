# ADR 0001: Keep a Modular Monolith Boundary Model

## Status

Accepted

## Context

The platform currently runs as one FastAPI backend with bounded modules for `core`, `platform`, `shared`, `insurance`, `ai` and `dashboard`. The next roadmap expands feature depth but does not require independent service deployment yet.

## Decision

Keep the backend as a modular monolith. Enforce module ownership, layering and dependency contracts inside the codebase instead of splitting into microservices.

## Alternatives Considered

- Split into microservices now: rejected because it adds deployment, observability and data consistency cost before scale requires it.
- Single unstructured app module: rejected because it would blur ownership and make tenant/security review harder.

## Consequences

- Feature agents must preserve module boundaries.
- Cross-domain orchestration must use documented contracts or application workflow services.
- A future service split requires a new ADR and migration plan.

## Review Date

2026-08-28
