# Security Model

## Authentication

Passwords are hashed with Argon2. Plaintext passwords are never stored.

Access tokens are short-lived JWTs signed with HS256. They identify a user and organization, but authorization does not rely on token role claims alone: the persisted organization membership is loaded for protected requests.

Refresh tokens are random opaque values. The raw value is sent only in an HttpOnly cookie. PostgreSQL stores only a SHA-256 hash.

## Refresh rotation

Every successful refresh:

1. verifies the hashed token exists;
2. rejects expired or revoked sessions;
3. revokes the current refresh session;
4. generates a new opaque refresh token;
5. persists only the new token hash;
6. returns a new access token and refresh cookie.

A rotated token cannot be replayed successfully.

## Tenant isolation

A protected request resolves:

- authenticated user;
- selected organization;
- persisted organization membership;
- current role.

Organization-scoped routes reject requests when the path tenant differs from the authenticated tenant.

Future document, retrieval, agent, and tool queries must carry the organization scope through every database operation.

## Cookie policy

The refresh cookie is:

- HttpOnly
- SameSite=Lax
- scoped to `/auth`
- Secure when `APP_ENV=production`

## Secrets

The repository contains development-only placeholder configuration. Production secrets must be injected through a managed secret store and never committed to Git.

AWS deployment is planned to use Secrets Manager and least-privilege IAM.

## Future hardening

Later phases will add:

- audit events for sensitive actions;
- rate limiting;
- production key rotation strategy;
- security headers and CSP;
- dependency/security scanning;
- human approval for privileged AI tool calls;
- a final threat-model and security review.
