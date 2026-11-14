"""Settings shared by every module: where things live, how big."""
from __future__ import annotations

import os
from pathlib import Path

# region: config
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CORPUS_DIR = Path(os.environ.get(       # a generated corpus with a
    "RX_CORPUS", DATA_DIR / "corpus"))  # manifest.jsonl
GOLDEN_PATH = CORPUS_DIR / "golden.jsonl"
TARNWICK_DIR = Path(os.environ.get(       # the desk set, unzipped
    "RX_TARNWICK", DATA_DIR / "tarnwick"))
MODELS_DIR = DATA_DIR / "models"
SQL_DIR = ROOT / "sql"

DSN = os.environ.get(
    "RX_DSN", "postgresql://postgres@/rx?host=/tmp")
TEST_DSN = os.environ.get(
    "RX_TEST_DSN", "postgresql://postgres@/rx_test?host=/tmp")

DIM = 256                  # embedding width; matches vector(256)
DEFAULT_EMBEDDER = "lsa"   # offline TF-IDF + SVD, see rx/embed.py
CHUNK_SIZE = 256           # tokens per chunk (approximate)
CHUNK_OVERLAP = 32         # tokens shared by neighboring chunks
SEED = 42                  # every random generator starts here
# endregion: config
