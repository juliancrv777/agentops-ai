# Retrieval and RAG Foundation

## What Phase 4 proves

Phase 4 verifies the storage and retrieval side of a RAG system:

1. authenticated, tenant-scoped document upload;
2. extraction from TXT, Markdown, and PDF;
3. overlapping chunk generation;
4. embedding generation through a provider interface;
5. vector persistence in PostgreSQL + pgvector;
6. HNSW cosine search;
7. source metadata preserved on every chunk;
8. retrieval restricted to the authenticated organization.

The answer-generation/citation layer is intentionally reserved for Phase 5.

## Embedding providers

### Deterministic provider

CI uses a deterministic feature-hash embedding implementation.

It converts normalized tokens into a fixed 1536-dimensional vector using a stable BLAKE2-based feature hash and L2 normalization.

Its purpose is engineering verification:

- deterministic tests;
- no external API secret;
- no network dependency;
- real pgvector storage/query execution;
- reproducible tenant-isolation tests.

It is **not** marketed as a semantic AI embedding model.

### OpenAI provider

The real provider is enabled with:

```text
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_EMBEDDING_MODEL=...
```

The provider calls the embeddings API asynchronously and requests the configured vector dimensions.

No API key is committed to the repository.

## Upload safety

Uploads are:

- limited in size;
- reduced to the basename of the supplied filename;
- limited to TXT, Markdown, and PDF;
- SHA-256 fingerprinted;
- rejected when the same content already exists in the same tenant.

The development storage adapter writes under:

```text
data/uploads/<organization_id>/<document_id>/<filename>
```

AWS deployment will replace local durable storage with S3.

## Tenant boundary

Every document and chunk carries an `organization_id`.

Retrieval includes the authenticated organization in the SQL predicate. The integration suite creates two separate organizations and verifies that the second organization receives no results for content uploaded by the first.

## Vector index

The migration creates a partial HNSW index for non-null embeddings using cosine distance:

```sql
CREATE INDEX ix_document_chunks_embedding_hnsw
ON document_chunks USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;
```

This migration is executed against a real pgvector PostgreSQL service in CI.
