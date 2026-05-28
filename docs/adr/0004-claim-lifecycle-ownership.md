# ADR 0004: Own Claim Lifecycle in the Insurance Module

## Status

Accepted

## Context

Incident reports already belong to the `insurance` module. The roadmap adds claim lifecycle state, transition history and role-aware actions.

## Decision

`insurance` owns claim lifecycle state, transition rules and transition history. Dashboard, queues, portal and chat may read claim state through projections but must not own or mutate transitions.

## Alternatives Considered

- Add claim lifecycle to `dashboard`: rejected because dashboard is read-only aggregation.
- Create a separate claims service now: rejected because the modular monolith can represent the bounded context without service split cost.

## Consequences

- Claim migrations and transition APIs live under `insurance`.
- Queue and dashboard tasks consume claim state as read data.
- Invalid transitions must be impossible through the claim service contract.

## Review Date

2026-08-28
