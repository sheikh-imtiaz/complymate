# ADR 0002: pgvector for the rule library (RAG)

* Status: accepted
* Date: 2026-10-30

## Context
S3 Vectors and Bedrock Knowledge Bases are AWS-only. The rule library is small (thousands of chunks), shared
across tenants, and needs "last checked" metadata per source.

## Decision
Store chunks and 1024-dimension embeddings in `kb_chunks` (pgvector, HNSW cosine index) in the same database.
Embeddings come from the `EmbeddingProvider` port (Titan v2 on AWS, text-embedding-3-small truncated to 1024 on Azure).

## Consequences
* One store, one backup, one set of access controls; portable.
* Changing embedding model means re-indexing (Platform Admin → Rule library → Re-index).
* Citations carry source title, URL, publisher and last-checked date straight from SQL.
