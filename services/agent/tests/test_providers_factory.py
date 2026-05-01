"""Factory routes `LLM_BACKEND` to the right Provider impl."""

from __future__ import annotations

import pytest
from noether_svc_agent.config import AgentSettings
from noether_svc_agent.providers import OllamaProvider, make_provider


def test_returns_ollama_provider_by_default() -> None:
    settings = AgentSettings(LLM_BACKEND="ollama")
    p = make_provider(settings)
    assert isinstance(p, OllamaProvider)


@pytest.mark.parametrize("backend", ["openai", "anthropic", "gemini"])
def test_cloud_backends_raise_until_wired(backend: str) -> None:
    settings = AgentSettings(LLM_BACKEND=backend)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError, match=backend):
        make_provider(settings)
