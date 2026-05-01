"""Prompt templates loaded from on-disk Markdown.

Stored as `.md` so prompts are diff-able like any other text and a
reviewer can see their full content in PR diffs without scanning a
giant Python string. Loaded eagerly at module import — small files,
read once, no fs-pressure concern.
"""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template by basename (no extension).

    Raises FileNotFoundError if the file is missing — better to fail
    boot than ship a service with prompts silently empty.
    """
    path = _PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


__all__ = ["load_prompt"]
