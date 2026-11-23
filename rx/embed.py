"""Embedders: one small interface, an offline default, real models.

Every embedder returns float32 rows of unit length, so a dot product
is a cosine similarity and pgvector's <=> operator agrees with it.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from rx import config
from rx.textutil import analyze


# region: embedder-protocol
@runtime_checkable
class Embedder(Protocol):
    """Anything that turns text into fixed-width unit vectors."""

    dim: int

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """One row per text, shape (len(texts), dim)."""
        ...

    def embed_query(self, text: str) -> np.ndarray:
        """One vector, shape (dim,)."""
        ...
# endregion: embedder-protocol


# region: l2-normalize
def l2_normalize(rows: np.ndarray) -> np.ndarray:
    """Scale each row to length 1; leave all-zero rows alone."""
    norms = np.linalg.norm(rows, axis=1, keepdims=True)   # <1>
    return rows / np.where(norms == 0, 1.0, norms)        # <2>
# endregion: l2-normalize


# region: hashing-embedder
class HashingEmbedder:
    """Feature hashing: no training, no vocabulary, deterministic.

    Each analyzed token is hashed into one of `dim` buckets. It only
    matches shared words, so it is a fast stand-in for tests.
    """

    def __init__(self, dim: int = config.DIM):
        from sklearn.feature_extraction.text import HashingVectorizer
        self.dim = dim
        self._vectorizer = HashingVectorizer(
            n_features=dim, tokenizer=analyze, token_pattern=None,
            lowercase=False, alternate_sign=False, norm="l2")

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        rows = self._vectorizer.transform(texts).toarray()
        return rows.astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]
# endregion: hashing-embedder


# region: lsa-embedder
class LsaEmbedder:
    """Latent semantic analysis: TF-IDF, then truncated SVD.

    Fit it on the chunk texts. Words that co-occur across chunks end
    up close together, which gives a little paraphrase tolerance
    with no model download. If the corpus is too small for `dim`
    components, the vectors are zero-padded to `dim`.
    """

    def __init__(self, dim: int = config.DIM, min_df: int = 2,
                 seed: int = config.SEED):
        self.dim, self.min_df, self.seed = dim, min_df, seed
        self.tfidf = None
        self.svd = None

    # region: lsa-fit
    def fit(self, texts: list[str]) -> LsaEmbedder:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.tfidf = TfidfVectorizer(
            tokenizer=analyze, token_pattern=None, lowercase=False,
            sublinear_tf=True, min_df=self.min_df)            # <1>
        tfidf = self.tfidf.fit_transform(texts)
        k = min(self.dim, tfidf.shape[1] - 1, tfidf.shape[0] - 1)
        self.svd = TruncatedSVD(n_components=max(k, 1),
                                random_state=self.seed)       # <2>
        self.svd.fit(tfidf)
        return self

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if self.svd is None:
            raise RuntimeError("LsaEmbedder.fit() has not been run")
        rows = self.tfidf.transform(texts) @ self.projection()  # <3>
        pad = self.dim - rows.shape[1]
        if pad > 0:
            rows = np.pad(rows, ((0, 0), (0, pad)))
        return l2_normalize(rows).astype(np.float32)          # <4>
    # endregion: lsa-fit

    def projection(self) -> np.ndarray:
        """The SVD's components, transposed once and kept: the same
        product as svd.transform(), without copying the matrix (tens
        of MB for a large vocabulary) on every call."""
        proj = getattr(self, "_proj", None)
        if proj is None:
            proj = np.ascontiguousarray(self.svd.components_.T)
            self._proj = proj
        return proj

    def __getstate__(self) -> dict:
        state = dict(self.__dict__)
        state.pop("_proj", None)          # rebuilt on first use
        return state

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: str | Path) -> LsaEmbedder:
        with Path(path).open("rb") as f:
            return pickle.load(f)
# endregion: lsa-embedder


# region: sentence-transformer-embedder
# region: st-prefixes
QUERY_PREFIXES = {
    # e5 models were trained with these two markers.
    "e5": ("query: ", "passage: "),                           # <1>
    # bge models prefix queries only.
    "bge": ("Represent this sentence for searching relevant "
            "passages: ", ""),                                # <2>
}


def default_prefixes(model_name: str) -> tuple[str, str]:
    """(query, passage) prefixes for a known model family."""
    name = model_name.lower()
    family = next((f for f in QUERY_PREFIXES if f in name), None)  # <3>
    return QUERY_PREFIXES.get(family, ("", ""))               # <4>
# endregion: st-prefixes


class SentenceTransformerEmbedder:
    """A real embedding model via sentence-transformers.

    Install with `pip install -e .[models]`. Prefixes for e5 and bge
    are picked from the model name unless you pass your own. The
    width differs from 256, so change vector(256) in sql/ to match.
    """

    def __init__(self, model_name: str = "intfloat/e5-small-v2",
                 query_prefix: str | None = None,
                 passage_prefix: str | None = None,
                 device: str | None = None):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name, device=device)
        self.dim = self.model.get_sentence_embedding_dimension()
        q, p = default_prefixes(model_name)
        self.query_prefix = q if query_prefix is None else query_prefix
        self.passage_prefix = (p if passage_prefix is None
                               else passage_prefix)

    # region: st-encode
    def _encode(self, texts: list[str]) -> np.ndarray:
        rows = self.model.encode(texts, batch_size=32,
                                 normalize_embeddings=True,  # <1>
                                 convert_to_numpy=True)
        return rows.astype(np.float32)                       # <2>

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self._encode([self.passage_prefix + t
                             for t in texts])                # <3>

    def embed_query(self, text: str) -> np.ndarray:
        return self._encode([self.query_prefix + text])[0]   # <4>
    # endregion: st-encode
# endregion: sentence-transformer-embedder


# region: make-embedder
LSA_PATH = config.MODELS_DIR / "lsa.pkl"


def make_embedder(name: str = config.DEFAULT_EMBEDDER) -> Embedder:
    """'lsa' (fitted model from disk), 'hashing', or 'st:<model>'."""
    if name == "lsa":
        return LsaEmbedder.load(LSA_PATH)
    if name == "hashing":
        return HashingEmbedder()
    if name.startswith("st:"):
        return SentenceTransformerEmbedder(name[3:])
    raise ValueError(f"unknown embedder {name!r}")
# endregion: make-embedder
