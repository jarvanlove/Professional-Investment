# Testing

## Commands

TODO: document install, lint, test, build, and manual verification commands.

## Minimum Verification Matrix

| Change type | Required checks |
|---|---|
| Documentation/config only | Read-through and affected-link check |
| UI/frontend | Build/typecheck/lint where available plus manual UI smoke |
| Backend/domain/API | Targeted test plus startup/request smoke |
| Database/auth/security/deployment | Dedicated review, migration/rollback notes, and manual smoke |

## Completion Rule

Report exact commands run. If commands are TODO or cannot run locally, state the blocker and the remaining risk.

## When To Update This File

Update this file when:

- Verification commands change.
- A new test class, smoke path, or manual check becomes required.
- A bug fix adds a regression path that future agents must keep running.
