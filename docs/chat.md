# Knowledge workspace — delivered vertical slice

This increment connects the authenticated Next.js workspace to persistent, tenant-private FastAPI conversations and existing pgvector knowledge retrieval. It is not a fully autonomous AI agent.

## Walkthrough
1. Copy `.env.example` to `.env`, run `docker compose up --build`.
2. Open http://localhost:3000/workspace, create an account and organization.
3. Upload `.txt`, `.md`, or text-based `.pdf` runbooks (up to 5 MB).
4. Create an investigation and ask a question.
5. Expand citation references to review exact document excerpts. Reload the browser; the refresh cookie restores the session and conversations remain in PostgreSQL.

By default `EMBEDDING_PROVIDER=deterministic`, which is **not a semantic model**. With no `OPENAI_CHAT_MODEL`, the chat returns **extractive source snippets** instead of generating an answer. For model-generated text, set `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL`, and ideally `EMBEDDING_PROVIDER=openai` with `OPENAI_EMBEDDING_MODEL`. API/model usage may incur charges. Embedding dimensions must remain 1536 with the current database schema.

## HTTP contract

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/chat/conversations` | Create conversation, optional title |
| GET | `/chat/conversations` | Last 50 conversations owned by caller |
| GET | `/chat/conversations/{id}` | Conversation with most recent 100 messages |
| DELETE | `/chat/conversations/{id}` | Delete conversation and messages |
| POST | `/chat/conversations/{id}/messages` | Ask a question; returns user and assistant records, mode, and citations |

All endpoints require a valid Bearer access token. A conversation is accessible only when **both organization ID and user ID** match the authenticated principal. Unknown and unauthorized conversation IDs return the same 404. Each chat response includes `mode`: `ai`, `extractive` or `no_evidence`.

Citation records store document and chunk IDs, source name, similarity score and a capped excerpt. Messages persist **atomically** after generation succeeds. If the external model is unavailable, the API returns 503 and does not save a partial turn.

## Security and limitations
- Access tokens live in browser component state, not localStorage. HttpOnly refresh cookies rotate server-side.
- Document content is provided to the model as untrusted evidence. Prompt injection and hallucination remain risks: citations must be inspected before operational use.
- Results are ranked by embedding similarity; a matching citation alone does not prove a claim.
- Retrieval returns at most 5 excerpts, each capped at 1000 characters for generation.
- Chat history is limited to the last 8 messages as model context; retrieval is based on the current question.
- No streaming token transport yet, no background queue, no per-user usage quotas, no document delete workflow, and no production audit log.
- Production across separate origins requires a deliberate CORS/cookie/domain review; default CORS is localhost only.
- No provider secrets or private documents belong in version control.

## Validation
The backend CI migration runs against PostgreSQL with pgvector and Redis. `test_chat_integration.py` verifies login requirements, cross-organization isolation, citations, history persistence, delete cascades and validation. `test_chat_unit.py` verifies that the no-model fallback is explicitly extractive. Frontend `tsc` and `next build` run in CI.

This is a usable knowledge-chat workflow, but the broader AgentOps AI roadmap remains unfinished.
