from pathlib import Path

import pytest

from rx.chunking import fixed_chunks
from rx.corpus import Document
from rx.embed import HashingEmbedder
from rx.store import (create_hnsw_index, search_keyword, search_vector,
                      write_chunks, write_documents, write_golden)

TEXTS = {
    "SPEC-1": "Porosity maximum 2.0% by area, verified by X-ray.",
    "TR-1": "Tensile strength 312 MPa against a minimum of 290 MPa.",
    "EML-1": "Lot H-2291 shipped on PO-4821 to Arcadia Automotive.",
}


@pytest.fixture
def loaded(conn):
    docs = [Document(doc_id, "test", doc_id, Path(f"{doc_id}.txt"),
                     "2026-01-01T00:00:00+00:00", text=text)
            for doc_id, text in TEXTS.items()]
    chunks = [c for d in docs for c in fixed_chunks(d.doc_id, d.text)]
    emb = HashingEmbedder()
    with conn.transaction():
        assert write_documents(conn, docs) == 3
        assert write_chunks(conn, chunks,
                            emb.embed_documents(list(TEXTS.values()))) == 3
    create_hnsw_index(conn)
    return conn, emb


def test_vector_search_finds_the_closest_chunk(loaded):
    conn, emb = loaded
    hits = search_vector(conn, emb.embed_query("tensile strength"), k=2)
    assert hits[0].doc_id == "TR-1" and hits[0].chunk_id == "TR-1#0"
    assert hits[0].score > hits[1].score


def test_keyword_search_all_versus_any(loaded):
    conn, _ = loaded
    assert [h.doc_id for h in search_keyword(conn, "porosity x-ray")] == [
        "SPEC-1"]
    assert search_keyword(conn, "porosity of lot H-2291") == []
    hits = search_keyword(conn, "porosity of lot H-2291", match="any")
    assert {h.doc_id for h in hits} == {"SPEC-1", "EML-1"}


def test_metadata_and_golden(loaded):
    conn, _ = loaded
    meta = conn.execute("SELECT metadata FROM chunks "
                        "WHERE chunk_id = 'TR-1#0'").fetchone()[0]
    assert meta == {"start": 0, "end": len(TEXTS["TR-1"])}
    write_golden(conn, [{"qid": "Q1", "question": "q", "qtype": "t",
                         "gold_doc_ids": ["TR-1"], "answer": "a"}])
    assert conn.execute("SELECT gold_doc_ids FROM golden").fetchone()[
        0] == ["TR-1"]
