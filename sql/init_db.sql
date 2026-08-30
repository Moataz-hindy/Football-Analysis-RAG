CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS football_chunks (
    id SERIAL PRIMARY KEY,
    doc_id TEXT NOT NULL,
    chunk_index INT NOT NULL,
    url TEXT,
    title TEXT,
    text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    UNIQUE (doc_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS football_chunks_embedding_idx
ON football_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);