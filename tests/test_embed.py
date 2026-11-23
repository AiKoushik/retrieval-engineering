import numpy as np
import pytest

from rx.embed import (Embedder, HashingEmbedder, LsaEmbedder,
                      l2_normalize, make_embedder)

TEXTS = ["porosity maximum by area verified by x-ray",
         "x-ray porosity gas holes in the casting",
         "tensile strength minimum measured per iso 6892",
         "tensile strength of the bar stock",
         "packaging crate with cardboard dividers",
         "crate label with part number and lot"] * 2


def test_l2_normalize_leaves_zero_rows():
    rows = l2_normalize(np.array([[3.0, 4.0], [0.0, 0.0]]))
    assert rows.tolist() == [[0.6, 0.8], [0.0, 0.0]]


def test_hashing_is_deterministic_and_unit_length():
    emb = HashingEmbedder(dim=64)
    a = emb.embed_documents(TEXTS)
    assert a.shape == (12, 64) and a.dtype == np.float32
    assert np.allclose(np.linalg.norm(a, axis=1), 1.0)
    assert np.array_equal(a, HashingEmbedder(dim=64).embed_documents(TEXTS))
    assert isinstance(emb, Embedder)


def test_lsa_pads_to_dim_and_finds_neighbors():
    emb = LsaEmbedder(dim=256, min_df=1).fit(TEXTS)
    docs = emb.embed_documents(TEXTS[:6])
    assert docs.shape == (6, 256)
    assert np.allclose(np.linalg.norm(docs, axis=1), 1.0)
    sims = docs @ emb.embed_query("porosity x-ray")
    assert set(np.argsort(-sims)[:2]) == {0, 1}


def test_lsa_save_load_roundtrip(tmp_path):
    emb = LsaEmbedder(dim=8, min_df=1).fit(TEXTS)
    emb.save(tmp_path / "m" / "lsa.pkl")
    again = LsaEmbedder.load(tmp_path / "m" / "lsa.pkl")
    assert np.array_equal(emb.embed_documents(TEXTS),
                          again.embed_documents(TEXTS))


def test_lsa_must_be_fitted_first():
    with pytest.raises(RuntimeError):
        LsaEmbedder().embed_query("x")


def test_make_embedder():
    assert isinstance(make_embedder("hashing"), HashingEmbedder)
    with pytest.raises(ValueError):
        make_embedder("word2vec")
