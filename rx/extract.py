"""Naive text extraction, the way most first RAG systems do it.

Kept naive on purpose: PDF running headers and footers stay in the
text, tables come out as cell soup, email attachments are reduced to
their file names, and OCR noise passes straight through. Later
chapters replace each of these with something better.
"""
from __future__ import annotations

from email import policy
from email.parser import BytesParser
from pathlib import Path

from pypdf import PdfReader


# region: extract-pdf
def extract_pdf(path: Path) -> str:
    """Concatenate the text layer of every page."""
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)
# endregion: extract-pdf


# region: extract-email
HEADERS = ("From", "To", "Date", "Subject")


def extract_email(path: Path) -> str:
    """Headers, the plain-text body, and attachment names only."""
    msg = BytesParser(policy=policy.default).parsebytes(
        path.read_bytes())
    lines = [f"{h}: {msg[h]}" for h in HEADERS if msg[h]]
    names = [part.get_filename() or "unnamed"
             for part in msg.iter_attachments()]
    if names:
        lines.append("Attachments: " + ", ".join(names))
    body = msg.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body is not None else ""
    return "\n".join(lines) + "\n\n" + text
# endregion: extract-email


# region: extract-dispatch
def extract_plain(path: Path) -> str:
    """Text, Markdown, CSV, WebVTT: read the file as it is."""
    return path.read_text(encoding="utf-8", errors="replace")


EXTRACTORS = {".pdf": extract_pdf, ".eml": extract_email}  # <1>


def extract(path: str | Path) -> str:
    """Pick an extractor by file suffix; Postgres rejects NUL bytes."""
    path = Path(path)
    reader = EXTRACTORS.get(path.suffix.lower(), extract_plain)  # <2>
    return reader(path).replace("\x00", "")                     # <3>
# endregion: extract-dispatch
