"""Write documents and chunks to Postgres; search them two ways."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
import psycopg
from psycopg.types.json import Jsonb

from rx.chunking import Chunk
from rx.corpus import Document


# region: hit-dataclass
@dataclass(frozen=True)
class Hit:
    """One retrieved chunk. Higher score means more relevant."""

    chunk_id: str
    doc_id: str
    score: float
    text: str
# endregion: hit-dataclass


# region: write-documents
INSERT_DOCUMENT = """
    INSERT INTO documents (doc_id, kind, title, source_path,
                           created_at, metadata, acl, content_hash)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


def write_documents(conn: psycopg.Connection,
                    docs: Iterable[Document]) -> int:
    """Insert one row per document; return how many."""
    rows = [(d.doc_id, d.kind, d.title, str(d.path), d.created_at,
             Jsonb(d.metadata), d.acl, d.content_hash) for d in docs]
    with conn.cursor() as cur:
        cur.executemany(INSERT_DOCUMENT, rows)
    return len(rows)
# endregion: write-documents


# region: write-chunks
COPY_CHUNKS = """
    COPY chunks (chunk_id, doc_id, idx, text, embedding, metadata)
    FROM STDIN WITH (FORMAT BINARY)
"""


def write_chunks(conn: psycopg.Connection, chunks: Sequence[Chunk],
                 embeddings: np.ndarray) -> int:
    """Bulk-load chunks and their vectors with binary COPY."""
    with conn.cursor() as cur, cur.copy(COPY_CHUNKS) as copy:
        copy.set_types(["text", "text", "int4", "text",
                        "vector", "jsonb"])
        for chunk, vec in zip(chunks, embeddings, strict=True):
            offsets = Jsonb({"start": chunk.start, "end": chunk.end})
            copy.write_row([chunk.chunk_id, chunk.doc_id, chunk.idx,
                            chunk.text, vec, offsets])
    return len(chunks)
# endregion: write-chunks


# region: create-hnsw-index
def create_hnsw_index(conn: psycopg.Connection, m: int = 16,
                      ef_construction: int = 64) -> None:
    """Build the approximate-nearest-neighbor index for cosine."""
    conn.execute(f"""
        CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
        ON chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = {int(m)}, ef_construction = {int(ef_construction)})
    """)
# endregion: create-hnsw-index


# region: search-vector
SEARCH_VECTOR = """
    SELECT chunk_id, doc_id, 1 - (embedding <=> %(q)s) AS score, text
    FROM chunks
    ORDER BY embedding <=> %(q)s                         -- <1>
    LIMIT %(k)s                                          -- <2>
"""


def search_vector(conn: psycopg.Connection, qvec: np.ndarray,
                  k: int = 10, ef_search: int = 100) -> list[Hit]:
    """Nearest chunks by cosine similarity (HNSW when indexed)."""
    conn.execute(f"SET hnsw.ef_search = {max(int(ef_search), k)}")  # <3>
    rows = conn.execute(SEARCH_VECTOR, {"q": qvec, "k": k}).fetchall()
    return [Hit(*row) for row in rows]                   # <4>
# endregion: search-vector


# region: search-keyword
SEARCH_KEYWORD = """
    SELECT chunk_id, doc_id, ts_rank_cd(tsv, q) AS score, text
    FROM chunks, (SELECT {tsquery} AS q) AS query
    WHERE tsv @@ q
    ORDER BY score DESC, chunk_id
    LIMIT %(k)s
"""
ALL_TERMS = "websearch_to_tsquery('english', %(text)s)"
# websearch_to_tsquery ANDs every word. For "any", swap & for |.
ANY_TERM = ("replace(websearch_to_tsquery('english', %(text)s)"
            "::text, ' & ', ' | ')::tsquery")


def search_keyword(conn: psycopg.Connection, query: str,
                   k: int = 10, match: str = "all") -> list[Hit]:
    """Postgres full-text search ranked by ts_rank_cd.

    match="all" requires every query word (the default behaviour of
    websearch_to_tsquery); match="any" accepts any one of them.
    """
    tsquery = {"all": ALL_TERMS, "any": ANY_TERM}[match]
    sql = SEARCH_KEYWORD.format(tsquery=tsquery)
    rows = conn.execute(sql, {"text": query, "k": k}).fetchall()
    return [Hit(*row) for row in rows]
# endregion: search-keyword


# region: write-golden
INSERT_GOLDEN = """
    INSERT INTO golden (qid, question, qtype, gold_doc_ids, answer,
                        notes)
    VALUES (%(qid)s, %(question)s, %(qtype)s, %(gold_doc_ids)s,
            %(answer)s, %(notes)s)
"""


def write_golden(conn: psycopg.Connection,
                 questions: Iterable[dict]) -> int:
    """Store golden questions so they can be queried with SQL."""
    rows = [{"notes": None, **q} for q in questions]
    with conn.cursor() as cur:
        cur.executemany(INSERT_GOLDEN, rows)
    return len(rows)
# endregion: write-golden
