# AgentOps AI

AI-native operations platform for knowledge retrieval, incident analysis, and tool-driven workflows.

> **Status:** Phase 4 — document ingestion and vector retrieval verified in CI.

## Why this project exists

AgentOps AI is a portfolio-grade engineering project designed to demonstrate production-oriented full-stack and AI engineering:

- Next.js + React + TypeScript frontend
- Python + FastAPI backend
- PostgreSQL + pgvector
- Redis
- secure authentication, RBAC, and tenant isolation
- document ingestion for TXT, Markdown, and PDF
- chunking, embeddings, and vector retrieval
- streaming AI UX
- Retrieval-Augmented Generation (RAG) with grounded citations
- tool/function calling and agent orchestration
- Model Context Protocol (MCP)
- human-in-the-loop approvals and guardrails
- AWS infrastructure managed with Terraform
- Docker, CI/CD, automated testing, observability, and security practices

## Verified architecture

```text
┌──────────────────────────┐
│ Next.js / React / TS     │
└─────────────┬────────────┘
              │ REST
┌─────────────▼────────────┐
│ FastAPI / Python         │
│ Auth + tenant-aware API  │
└───────┬─────────┬────────┘
        │         │
  PostgreSQL    Redis
  + pgvector
        │
        ├── documents
        └── document_chunks
              └── vector(1536)
```

## Authentication and tenancy

- Argon2 password hashing
- short-lived JWT access tokens
- opaque refresh tokens stored only as SHA-256 hashes
- HttpOnly refresh cookie
- refresh-token rotation, revocation, and replay rejection
- database-backed organization membership checks
- explicit cross-tenant access denial

See [docs/security.md](docs/security.md).

## Retrieval pipeline

The verified Phase 4 flow is:

```text
Upload
  ↓
TXT / Markdown / PDF extraction
  ↓
overlapping word chunks
  ↓
embedding provider
  ↓
pgvector vector(1536)
  ↓
HNSW cosine index
  ↓
tenant-scoped similarity search
```

The repository includes two embedding implementations:

1. **Deterministic feature-hash provider** — used by CI so ingestion and retrieval are fully testable without paid external services.
2. **OpenAI embedding provider** — production-capable provider selected through environment configuration.

The deterministic provider is deliberately not presented as a semantic AI model. It exists to verify the architecture, persistence, vector queries, tenant boundaries, and failure behavior without requiring a secret in CI.

See [docs/rag.md](docs/rag.md).

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

The API container applies all Alembic migrations before startup.

Open:

- Web: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Liveness: http://localhost:8000/health
- Readiness: http://localhost:8000/ready

## Verification

The backend CI job starts real PostgreSQL/pgvector and Redis services, applies migrations, and tests:

- authentication and refresh rotation;
- tenant boundaries;
- document ingestion;
- duplicate-content rejection;
- pgvector persistence;
- vector retrieval;
- cross-tenant retrieval isolation.

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
- [x] Phase 4 — document ingestion, chunking, embeddings, vector retrieval
- [ ] Phase 5 — streamed AI chat with citations and conversation memory
- [ ] Phase 6 — LangGraph agents, tool calling, guardrails
- [ ] Phase 7 — custom MCP server and human approval workflows
- [ ] Phase 8 — background workers, queues, retries, idempotency
- [ ] Phase 9 — AWS infrastructure with Terraform, secrets, logs, metrics
- [ ] Phase 10 — security review, E2E tests, public demo, portfolio polish

## Engineering principles

- No feature is documented as complete before it is implemented and verified.
- AI-generated code is reviewed, tested, and treated as untrusted until proven correct.
- Security, tenant isolation, and auditability are first-class requirements.
- External AI providers are abstracted behind interfaces so tests do not depend on paid services.
- CI must remain green as the architecture evolves.

## License

A license will be selected before any external reuse or distribution beyond portfolio purposes.
