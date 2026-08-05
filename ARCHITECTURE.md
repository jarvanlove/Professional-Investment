# Architecture

## System Shape

- TODO: document project runtime and framework shape.

## Module Boundaries

| Module | Owns | Must not do |
|---|---|---|
| TODO | TODO | TODO |

## Data / Contract Boundaries

- Data model: TODO
- API contract: TODO
- Auth/permission model: TODO
- External integrations: TODO

## Invariants

- Do not change module boundaries without updating this file.
- Do not change public behavior without updating tests or acceptance criteria.
- Do not introduce new infrastructure without an explicit task and rationale.

## When To Update This File

Update this file when:

- Module boundaries, data flow, API contracts, auth boundaries, or external integrations change.
- A new runtime, service, queue, database, storage layer, or deployment dependency is introduced.
- A repeated implementation rule should become a durable architecture constraint.

For significant decisions, add an ADR in `docs/adr/` and optionally summarize it in the project wiki decisions page.

## Architecture Decisions

Record durable architecture decisions in `docs/adr/` or the project wiki decisions page.
