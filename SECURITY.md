# Security

## Sensitive Areas

- Authentication and authorization.
- User data and private files.
- Secrets, API keys, tokens, and environment files.
- Database migrations and destructive operations.
- File upload/download and path handling.
- External integrations and callbacks.

## Rules

- Do not commit real secrets.
- Do not weaken authentication, authorization, or validation without explicit task scope.
- Treat database migrations, data deletion, payment, permission, and deployment changes as high risk.
- Add or identify security-relevant tests for auth, permission, file, and integration changes.

## When To Update This File

Update this file when:

- Auth, permission, privacy, secret handling, path handling, or destructive operations change.
- A security-relevant incident, regression, or prevention rule is discovered.
- A new external integration changes the trust boundary.

## Incident Response

1. Preserve logs and reproduction steps.
2. Rotate affected secrets if needed.
3. Patch with a regression test or documented manual verification.
4. Update this file or `OPERATIONS.md` if a repeatable prevention rule is learned.
