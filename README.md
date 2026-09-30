# AgentOps AI

AI-native operations platform for knowledge retrieval, incident analysis, and tool-driven workflows.

> **Status:** Phase 3 — authentication and multi-tenancy verified in CI.

## Why this project exists

AgentOps AI is a portfolio-grade engineering project designed to demonstrate production-oriented full-stack and AI engineering:

- Next.js + React + TypeScript frontend
- Python + FastAPI backend
- PostgreSQL + pgvector for relational and vector data
- Redis for caching and asynchronous workflows
- secure authentication, tenant isolation, and RBAC
- Streaming AI UX
- Retrieval-Augmented Generation (RAG)
- Tool/function calling and agent orchestration
- Model Context Protocol (MCP)
- Human-in-the-loop approvals and guardrails
- AWS infrastructure managed with Terraform
- Docker, CI/CD, automated testing, observability, and security practices

## Implemented architecture

```text
┌──────────────────────────┐
│ Next.js / React / TS     │
│ Web application          │
└─────────────┬────────────┘
              │ REST
┌─────────────▼────────────┐
│ FastAPI / Python         │
│ Auth + tenant-aware API  │
└───────┬─────────┬────────┘
        │         │
  PostgreSQL    Redis
  + pgvector    readiness
```

### Authentication

- Argon2 password hashing
- short-lived JWT access tokens
- opaque refresh tokens stored only as SHA-256 hashes
- HttpOnly refresh cookie
- refresh-token rotation and revocation
- replay rejection for rotated/revoked refresh sessions
- request-time membership verification
- organization-level tenant isolation
- role carried from the persisted membership, not blindly trusted from JWT claims

See [docs/security.md](docs/security.md).

## Data foundation

The current schema includes:

- organizations
- users
- organization memberships
- refresh sessions
- documents
- document chunks with `vector(1536)`

The vector column is infrastructure only at this stage. RAG is not marked complete until ingestion, embedding generation, retrieval, and citations are verified.

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

The API container runs all Alembic migrations before startup.

Open:

- Web: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Liveness: http://localhost:8000/health
- Readiness: http://localhost:8000/ready

## Verification

The API CI job starts real PostgreSQL/pgvector and Redis containers, applies every migration, and runs unit/integration tests.

```bash
cd apps/api
pytest -q
```

Frontend:

```bash
cd apps/web
npm install
npm run typecheck
npm run build
```

## Roadmap

- [x] Phase 1 — monorepo bootstrap, web/API health integration, Docker, tests, CI
- [x] Phase 2 — PostgreSQL, pgvector, Redis, migrations, persistence layer
- [x] Phase 3 — authentication, organizations, RBAC, multi-tenancy
- [ ] Phase 4 — document ingestion, chunking, embeddings, vector retrieval
- [ ] Phase 5 — streamed AI chat with citations and conversation memory
- [ ] Phase 6 — LangGraph agents, tool calling, guardrails
- [ ] Phase 7 — custom MCP server and human approval workflows
- [ ] Phase 8 — background workers, queues, retries, idempotency
- [ ] Phase 9 — AWS infrastructure with Terraform, secrets, logs, metrics
- [ ] Phase 10 — security review, E2E tests, public demo, portfolio polish

## Engineering principles

- No feature is documented as complete before it is implemented and verified.
- AI-generated code is reviewed, tested, and treated as untrusted until proven correct.
- Security, data isolation, and auditability are first-class requirements.
- CI must remain green as the architecture evolves.

## License

A license will be selected before any external reuse or distribution beyond portfolio purposes.
