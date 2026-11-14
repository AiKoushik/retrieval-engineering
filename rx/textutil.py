"""Small text helpers: folding, tokens, stopwords, token counts."""
from __future__ import annotations

import functools
import os
import re
import unicodedata
from pathlib import Path

# region: fold
def fold(text: str) -> str:
    """Lowercase and strip accents: 'Café' -> 'cafe'."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(
        c for c in decomposed if not unicodedata.combining(c))
# endregion: fold


# region: tokenize
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Split folded text into word and code tokens.

    A code such as 'H-2291' stays whole ('h-2291') and also yields
    its parts ('h', '2291'), so both spellings can match. Decimals
    like '2.0' stay whole.
    """
    tokens: list[str] = []
    for tok in TOKEN_RE.findall(fold(text)):
        tokens.append(tok)
        if "-" in tok:
            tokens.extend(part for part in tok.split("-") if part)
    return tokens
# endregion: tokenize


# region: stopwords
STOPWORDS = frozenset("""
a an and are as at be been by can did do does for from had has have
he her his how i if in into is it its me my no not of on or our she
shall should so than that the their them then there these they this
those to us was we were what when where which who whom why will with
would you your
""".split())
# endregion: stopwords


# region: analyze
def stem(token: str) -> str:
    """Strip a plural ending. A deliberately tiny stemmer."""
    if len(token) > 3 and token.isalpha():
        if token.endswith("ies"):
            return token[:-3] + "y"
        if token.endswith("s") and not token.endswith("ss"):
            return token[:-1]
    return token


def analyze(text: str) -> list[str]:
    """Tokens for indexing: tokenize, drop stopwords, stem."""
    return [stem(t) for t in tokenize(text) if t not in STOPWORDS]
# endregion: analyze


# region: count-tokens
TOKENS_PER_WORD = 1.3


def count_tokens(text: str) -> int:
    """Approximate LLM tokens as whitespace words x 1.3.

    Subword tokenizers average roughly 1.2-1.4 tokens per English
    word; part codes and numbers cost more. The estimate is good
    enough for chunk sizes and context budgets, not for invoices.
    """
    return round(len(text.split()) * TOKENS_PER_WORD)
# endregion: count-tokens


# region: model-tokens
O200K_SHA256 = ("446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0"
                "cfb1a2d")


@functools.lru_cache(maxsize=1)
def _o200k():
    """OpenAI's o200k_base encoding through tiktoken (MIT).

    Reads data/tiktoken/o200k_base.tiktoken (or $RX_TIKTOKEN_DIR) when
    it is there; otherwise tiktoken downloads the file once and caches
    it. Either way the file is checked against the same SHA-256, so
    every machine counts the same tokens.
    """
    import tiktoken
    from tiktoken.load import load_tiktoken_bpe
    from tiktoken_ext import openai_public
    folder = Path(os.environ.get("RX_TIKTOKEN_DIR",
                                 Path(__file__).resolve().parents[1]
                                 / "data" / "tiktoken"))
    local = folder / "o200k_base.tiktoken"
    if local.exists():
        def load(url: str, expected_hash: str | None = None):
            return load_tiktoken_bpe(str(local), O200K_SHA256)
        openai_public.load_tiktoken_bpe = load
    return tiktoken.Encoding(**openai_public.o200k_base())


def model_tokens(text: str) -> int:
    """Count tokens with a real tokenizer (o200k_base), not a rule of thumb.

    Use it wherever a token count is printed or a prompt must fit a
    model's window: codes, numbers and export files cost far more
    tokens per word than prose, so words x 1.3 runs low on archives.
    """
    return len(_o200k().encode(text, disallowed_special=()))
# endregion: model-tokens


# region: split-sentences
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\[(])|\n\s*\n")


def split_sentences(text: str) -> list[str]:
    """Split on sentence ends and blank lines; keep it simple."""
    parts = (p.strip() for p in SENTENCE_RE.split(text))
    return [p for p in parts if p]
# endregion: split-sentences
