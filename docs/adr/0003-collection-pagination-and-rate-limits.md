# ADR 0003: Standardize Collection Pagination and Rate-Limit Tiers

## Status

Accepted

## Context

The current API has `{"items": [...]}` list responses. Upcoming portal, queue, chat, audit and dashboard screens need bounded lists and stable metadata.

## Decision

New or touched collection endpoints must return `items` plus `meta` with pagination/sort metadata. Existing `items`-only endpoints are temporary compatibility exceptions. Every endpoint contract must name a rate-limit tier.

## Alternatives Considered

- Keep unbounded `items` responses: rejected because queues, messages and audit logs can grow without limit.
- Introduce a breaking envelope immediately for every endpoint: rejected to avoid unnecessary frontend churn.

## Consequences

- Feature agents must add pagination before building list UIs.
- Cursor pagination is required for high-volume append-only histories.
- Rate limiting can be implemented consistently after endpoint tiers are documented.

## Review Date

2026-08-28
