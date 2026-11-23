import numpy as np

from rx import config, db


def test_reset_schema_builds_tables(conn):
    names = {r[0] for r in conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
    assert {"documents", "chunks", "golden"} <= names


def test_vectors_round_trip_after_reset(conn):
    conn.execute("INSERT INTO documents (doc_id, kind) VALUES ('d', 'x')")
    vec = np.arange(256, dtype=np.float32) / 256
    conn.execute("INSERT INTO chunks (chunk_id, doc_id, idx, text, "
                 "embedding) VALUES ('d#0', 'd', 0, 'Porosity checks', %s)",
                 (vec,))
    emb, tsv = conn.execute(
        "SELECT embedding, tsv::text FROM chunks").fetchone()
    assert np.allclose(emb.to_numpy(), vec)
    assert "'poros':1" in tsv          # the generated tsvector column


def test_reset_is_repeatable():
    with db.connect(config.TEST_DSN) as c:
        db.reset_schema(c)
        db.reset_schema(c)
        assert c.execute("SELECT count(*) FROM chunks").fetchone()[0] == 0
