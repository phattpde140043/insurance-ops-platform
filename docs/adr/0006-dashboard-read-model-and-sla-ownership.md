# ADR 0006: Keep Dashboard and SLA Surfaces Read-Oriented

## Status

Accepted

## Context

Dashboard metrics and SLA alerts depend on insurance workflow data, platform audit data and support activity. They should not become a second workflow owner.

## Decision

`dashboard` owns read-only aggregation, chart DTOs, SLA alert read surfaces and optional dashboard read models. Workflow state remains in source modules. Dashboard/SLA must not call command services or mutate insurance workflow state.

## Alternatives Considered

- Let dashboard update workflow state directly: rejected because it creates split ownership.
- Compute every metric in the browser: rejected because it leaks data and performs poorly.

## Consequences

- Dashboard queries must use projections, aggregate SQL or read models.
- SLA evaluation may persist alert/read-model state, but source workflow transitions stay in owning modules.
- Alert links must point back to authorized source resources.

## Review Date

2026-08-28
