# ADR 0005: Orchestrate Support Chat Between Insurance and AI Through a Contract

## Status

Accepted

## Context

Support conversations belong to `insurance`, while knowledge retrieval and guarded answers belong to `ai`. Persisted support chat needs both without circular coupling.

## Decision

`insurance` owns support conversation authorization and message thread state. AI assistance must be requested through a documented `ai` service contract or application orchestrator. `ai` must not mutate insurance claim or conversation state directly.

## Alternatives Considered

- Let `ai` own support conversations: rejected because support access rules depend on insurance customer/claim authorization.
- Let `insurance` import provider-specific AI internals: rejected because it couples support workflow to AI implementation details.

## Consequences

- AI retrieval remains tenant-scoped inside `ai`.
- Conversation messages can store safe citation references.
- Chat orchestration must define failure and timeout fallback behavior.

## Review Date

2026-08-28
