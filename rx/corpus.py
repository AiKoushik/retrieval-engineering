"""Load a generated corpus through its manifest."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from rx import config
from rx.extract import extract

# Manifest keys that become Document fields rather than metadata.
# "facts" holds ground truth for tests and is never indexed.
CORE_KEYS = {"doc_id", "kind", "title", "path", "created_at", "acl",
             "facts"}


# region: document-dataclass
@dataclass
class Document:
    """One source file, plus its naively extracted text."""

    doc_id: str
    kind: str
    title: str
    path: Path
    created_at: str | None
    acl: list[str] = field(default_factory=lambda: ["everyone"])
    metadata: dict = field(default_factory=dict)
    text: str = ""
    content_hash: str = ""
# endregion: document-dataclass


# region: load-manifest
def load_manifest(corpus_dir: Path | None = None) -> list[dict]:
    """Read manifest.jsonl: one JSON object per document."""
    path = Path(corpus_dir or config.CORPUS_DIR) / "manifest.jsonl"
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
# endregion: load-manifest


# region: iter-documents
def iter_documents(corpus_dir: Path | None = None, *,
                   kinds: Collection[str] | None = None,
                   doc_ids: Collection[str] | None = None,
                   ) -> Iterator[Document]:
    """Yield documents with text from the naive extractors.

    Rows with `embedded_in` live inside another file (an email
    attachment). The naive pipeline cannot see them, so it skips
    them; chapter 6 learns to open attachments.
    """
    root = Path(corpus_dir or config.CORPUS_DIR)
    for row in load_manifest(root):
        if row.get("embedded_in"):
            continue
        if kinds is not None and row["kind"] not in kinds:
            continue
        if doc_ids is not None and row["doc_id"] not in doc_ids:
            continue
        path = root / row["path"]
        yield Document(
            doc_id=row["doc_id"], kind=row["kind"],
            title=row.get("title", ""), path=path,
            created_at=row.get("created_at"),
            acl=row.get("acl") or ["everyone"],
            metadata={k: v for k, v in row.items()
                      if k not in CORE_KEYS and v is not None},
            text=extract(path),
            content_hash=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
# endregion: iter-documents
