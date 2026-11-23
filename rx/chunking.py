"""The baseline chunker: fixed-size windows of tokens with overlap."""
from __future__ import annotations

import re
from dataclasses import dataclass

from rx import config
from rx.textutil import TOKENS_PER_WORD


# region: chunk-dataclass
@dataclass(frozen=True)
class Chunk:
    """A slice of one document's text, with character offsets."""

    doc_id: str
    idx: int     # position of the chunk within its document
    text: str
    start: int   # offset of the first character in the document
    end: int     # offset one past the last character

    @property
    def chunk_id(self) -> str:
        return f"{self.doc_id}#{self.idx}"
# endregion: chunk-dataclass


# region: fixed-chunks
WORD_RE = re.compile(r"\S+")


def fixed_chunks(doc_id: str, text: str,
                 size: int = config.CHUNK_SIZE,
                 overlap: int = config.CHUNK_OVERLAP) -> list[Chunk]:
    """Cut text into windows of about `size` tokens.

    Neighboring windows share about `overlap` tokens. Tokens are
    approximated as whitespace words x 1.3 (see textutil), so a
    256-token window holds 196 words. Window edges ignore sentences,
    sections and tables on purpose: this is the baseline.
    """
    if not 0 <= overlap < size:
        raise ValueError("need 0 <= overlap < size")
    spans = [m.span() for m in WORD_RE.finditer(text)]       # <1>
    per_chunk = max(1, int(size / TOKENS_PER_WORD))          # <2>
    step = max(1, per_chunk - int(overlap / TOKENS_PER_WORD))
    chunks: list[Chunk] = []
    for first in range(0, len(spans), step):
        window = spans[first:first + per_chunk]
        start, end = window[0][0], window[-1][1]
        chunks.append(
            Chunk(doc_id, len(chunks), text[start:end], start, end))  # <3>
        if first + per_chunk >= len(spans):                  # <4>
            break
    return chunks
# endregion: fixed-chunks
