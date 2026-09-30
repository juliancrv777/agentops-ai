# Architecture

## Goal

AgentOps AI is designed as a multi-tenant AI operations platform where users can retrieve grounded knowledge, run agent workflows, invoke tools, and approve sensitive actions.

The architecture will evolve incrementally. Components are only marked as implemented after code, tests, and runtime verification exist.

## Phase 1 — implemented

- Next.js / React / TypeScript web application
- FastAPI / Python API
- API health endpoint
- Server-side web-to-API health integration
- PostgreSQL + pgvector development container
- Redis development container
- Docker Compose development environment
- Backend unit/API tests
- Frontend typecheck and production build checks
- GitHub Actions CI

## Target application architecture

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
  |
  +--> Redis
  |
  +--> Background workers
  |
  +--> LLM gateway
  |      |
  |      +--> RAG / embeddings
  |      +--> LangGraph agents
  |      +--> tool calling
  |
  +--> MCP server
         |
         +--> knowledge tools
         +--> incident tools
         +--> metrics tools
```

## Target AWS architecture

Planned AWS deployment will prefer managed services and least-privilege IAM:

- CloudFront for edge delivery where appropriate
- ECS/Fargate for containerized application services
- RDS PostgreSQL with pgvector support
- ElastiCache Redis
- S3 for document storage
- SQS for asynchronous work
- Secrets Manager for credentials
- CloudWatch for logs, metrics, alarms, and dashboards
- Terraform for infrastructure as code

Exact services remain subject to implementation and cost review.

## Security principles

1. Multi-tenant data access must be explicitly scoped.
2. Secrets must never be committed to source control.
3. Sensitive agent actions require authorization and, where appropriate, human approval.
4. Tool inputs and LLM outputs are untrusted data.
5. Retrieval results must preserve source metadata for citations.
6. Background work must be retry-safe and idempotent.
7. Authentication, authorization, and audit trails are tested as product behavior.

## Reliability principles

- Timeouts around external dependencies
- Structured logs with request correlation
- Health/readiness checks
- Retry policies with bounded backoff
- Idempotency for side-effecting operations
- Automated unit, integration, and E2E coverage
- CI required before merge
