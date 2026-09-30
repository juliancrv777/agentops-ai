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
- refresh rotation/revocation and replay rejection
- organization owner membership on signup
- database-backed membership checks
- explicit cross-tenant access denial

### Phase 4 — ingestion and vector retrieval

- tenant-scoped TXT, Markdown, and PDF uploads
- content SHA-256 duplicate detection
- safe local object storage for development
- text extraction and overlapping chunking
- embedding provider abstraction
- deterministic feature-hash embedding provider for CI
- configurable OpenAI embedding provider
- pgvector vector(1536) persistence
- HNSW cosine index
- tenant-scoped cosine similarity retrieval
- integration tests that prove one organization cannot retrieve another organization's chunks

## Current data model

```text
Organization
  ├── OrganizationMember ── User
  │                           └── RefreshSession
  └── Document
        ├── content SHA-256
        └── DocumentChunk
              ├── source metadata
              └── vector(1536)
```

## Current retrieval flow

```text
authenticated user
      |
      v
organization membership
      |
      v
document upload
      |
      v
extract text
      |
      v
chunk with overlap
      |
      v
embedding provider
      |
      v
PostgreSQL + pgvector
      |
      v
HNSW cosine search
      |
      v
results filtered by organization_id
```

Tenant scope is applied to both persistence and retrieval queries.

## Embedding provider boundary

```text
EmbeddingProvider
   ├── DeterministicEmbeddingProvider
   │      └── CI / architecture verification
   └── OpenAIEmbeddingProvider
          └── real external embeddings when configured
```

No production semantic quality claim is made for the deterministic provider.

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
  |      +--> RAG + citations
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
- bounded retry policies
- idempotency for side effects
- deterministic CI substitutes for external paid dependencies where appropriate
- automated unit, integration, and E2E coverage
- CI required before merge
