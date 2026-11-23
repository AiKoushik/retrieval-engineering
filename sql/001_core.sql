-- Core schema: documents, their chunks, and the golden questions.
-- The HNSW index on chunks.embedding is built by rx/store.py after
-- the bulk load, because building it once is faster than updating
-- it row by row.

-- region: extensions
CREATE EXTENSION IF NOT EXISTS vector;
-- endregion: extensions

-- region: documents-table
CREATE TABLE IF NOT EXISTS documents (
    doc_id       text PRIMARY KEY,
    kind         text NOT NULL,
    title        text,
    source_path  text,
    created_at   timestamptz,
    metadata     jsonb  NOT NULL DEFAULT '{}',
    acl          text[] NOT NULL DEFAULT '{everyone}',
    content_hash text
);
-- endregion: documents-table

-- region: chunks-table
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id  text PRIMARY KEY,
    doc_id    text NOT NULL
              REFERENCES documents ON DELETE CASCADE,  -- <1>
    idx       int  NOT NULL,
    text      text NOT NULL,
    tsv       tsvector GENERATED ALWAYS AS             -- <2>
              (to_tsvector('english', text)) STORED,
    embedding vector(256),                             -- <3>
    metadata  jsonb NOT NULL DEFAULT '{}'              -- <4>
);
-- endregion: chunks-table

-- region: chunks-indexes
CREATE INDEX IF NOT EXISTS chunks_tsv_gin
    ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS chunks_doc_idx
    ON chunks (doc_id, idx);
-- endregion: chunks-indexes

-- region: golden-table
CREATE TABLE IF NOT EXISTS golden (
    qid          text PRIMARY KEY,
    question     text NOT NULL,
    qtype        text NOT NULL,
    gold_doc_ids text[] NOT NULL DEFAULT '{}',
    answer       text,
    notes        text
);
-- endregion: golden-table
