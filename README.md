# AgentOps AI

AI-native operations platform for knowledge retrieval, incident analysis, and tool-driven workflows.

> **Status:** Phase 1 — platform bootstrap. The repository currently contains a working Next.js frontend, FastAPI backend, Docker development environment, automated tests, and CI. AI/RAG/agent features are intentionally tracked as upcoming phases until they are implemented and verified.

## Why this project exists

AgentOps AI is a portfolio-grade engineering project designed to demonstrate production-oriented full-stack and AI engineering:

- Next.js + React + TypeScript frontend
- Python + FastAPI backend
- PostgreSQL + pgvector for relational and vector data
- Redis for caching and asynchronous workflows
- Streaming AI UX
- Retrieval-Augmented Generation (RAG)
- Tool/function calling and agent orchestration
- Model Context Protocol (MCP)
- Human-in-the-loop approvals and guardrails
- AWS infrastructure managed with Terraform
- Docker, CI/CD, automated testing, observability, and security practices

## Current architecture

```text
┌──────────────────────────┐
│ Next.js / React / TS     │
│ Web application          │
└─────────────┬────────────┘
              │ REST
┌─────────────▼────────────┐
│ FastAPI / Python         │
│ Application API          │
└───────┬─────────┬────────┘
        │         │
  PostgreSQL    Redis
  + pgvector   (planned wiring)
```

## Repository structure

```text
apps/
  api/        FastAPI service and tests
  web/        Next.js application
docs/
  architecture.md
.github/
  workflows/ci.yml
docker-compose.yml
```

## Run locally

### Docker

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Web: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Without Docker

Backend:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd apps/web
npm install
npm run dev
```

## Verification

Backend:

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

GitHub Actions runs these checks for pushes and pull requests.

## Roadmap

- [x] Phase 1 — monorepo bootstrap, web/API health integration, Docker, tests, CI
- [ ] Phase 2 — PostgreSQL, pgvector, Redis, migrations, persistence layer
- [ ] Phase 3 — authentication, organizations, RBAC, multi-tenancy
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
