# Architecture

## Goal

AgentOps AI is a multi-tenant AI operations platform where users can retrieve grounded knowledge, run agent workflows, invoke tools, and approve sensitive actions.

Components are only marked as implemented after code, tests, and runtime verification exist.

## Implemented

### Phase 1 — platform bootstrap

- Next.js / React / TypeScript web application
- FastAPI / Python API
- Docker Compose
- health checks, tests, and GitHub Actions CI

### Phase 2 — persistence foundation

- PostgreSQL 17
- pgvector enabled through Alembic
- SQLAlchemy 2 models
- Redis async client
- dependency readiness checks
- CI integration tests against real services

### Phase 3 — authentication and tenant isolation

- Argon2 password hashes
- JWT access tokens
- opaque, hashed refresh sessions
- HttpOnly refresh cookie
- refresh rotation and revocation
- organization owner membership created on signup
- database-backed membership validation on protected requests
- explicit cross-tenant access denial
- integration coverage for authentication and token replay rejection

## Current data model

```text
Organization
  ├── OrganizationMember ── User
  │                           └── RefreshSession
  └── Document
        └── DocumentChunk
              └── vector(1536)
```

## Current request security flow

```text
Bearer access token
       |
       v
JWT signature + expiry verification
       |
       v
user + organization parsed
       |
       v
membership re-checked in PostgreSQL
       |
       v
current persisted role used for authorization
```

## Target AI architecture

```text
Browser
  |
  v
Next.js Web
  |
  | REST / SSE / WebSocket
  v
FastAPI Application
  |
  +--> PostgreSQL + pgvector
  +--> Redis
  +--> Background workers
  +--> LLM gateway
  |      +--> RAG / embeddings
  |      +--> LangGraph agents
  |      +--> tool calling
  +--> MCP server
         +--> knowledge tools
         +--> incident tools
         +--> metrics tools
```

## Target AWS architecture

Planned AWS deployment will prefer managed services and least-privilege IAM:

- CloudFront
- ECS/Fargate
- RDS PostgreSQL + pgvector
- ElastiCache Redis
- S3
- SQS
- Secrets Manager
- CloudWatch
- Terraform

Exact services remain subject to implementation and cost review.

## Reliability principles

- timeouts around external dependencies
- structured logs with request correlation
- liveness and dependency readiness checks
- retry policies with bounded backoff
- idempotency for side effects
- automated unit, integration, and E2E coverage
- CI required before merge
