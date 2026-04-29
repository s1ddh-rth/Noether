"""Recursive character chunker.

A 30-line analogue of LangChain's `RecursiveCharacterTextSplitter` that we
keep standalone to avoid pulling LangChain into `libs/rag` (it arrives
later via the agent service, but isolating the chunker keeps `libs/rag`
self-contained).

Sizes are in characters. The default (size=2000, overlap=200) approximates
~500 tokens with ~50 token overlap at 4 chars/token — the convention named
in the `add-rag-pipeline` proposal.
"""

from __future__ import annotations

from typing import Final

DEFAULT_SIZE: Final[int] = 2000
DEFAULT_OVERLAP: Final[int] = 200

_SEPARATORS: Final[tuple[str, ...]] = ("\n\n", "\n", ". ", " ")


def chunk_text(
    text: str,
    size: int = DEFAULT_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split `text` into chunks of at most `size` chars with `overlap` carry-over.

    Empty or whitespace-only input yields an empty list. Inputs already
    shorter than `size` are returned as a single chunk verbatim.
    """
    if not text.strip():
        return []
    if len(text) <= size:
        return [text]

    units = _atomic_split(text, size)
    chunks: list[str] = []
    cur = ""
    for unit in units:
        candidate = f"{cur} {unit}".strip() if cur else unit
        if len(candidate) <= size:
            cur = candidate
            continue
        if cur:
            chunks.append(cur)
        tail = cur[-overlap:] if cur and overlap > 0 else ""
        cur = f"{tail} {unit}".strip() if tail else unit
        # If even (tail + unit) busts size, hard-split it.
        if len(cur) > size:
            for piece in _hard_split(cur, size):
                chunks.append(piece)
            cur = ""
    if cur:
        chunks.append(cur)
    return chunks


def _atomic_split(text: str, size: int) -> list[str]:
    """Pick the highest-level separator that yields parts each <= size.

    Falls back to a hard size-bounded split if no separator gives small
    enough pieces.
    """
    for sep in _SEPARATORS:
        parts = [p for p in text.split(sep) if p]
        if len(parts) > 1 and all(len(p) <= size for p in parts):
            return parts
    return _hard_split(text, size)


def _hard_split(text: str, size: int) -> list[str]:
    """Last-resort fixed-window split for inputs that contain no usable separator."""
    return [text[i : i + size] for i in range(0, len(text), size)]
