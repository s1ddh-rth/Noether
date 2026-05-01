"""Selects a Provider implementation from `AgentSettings.llm_backend`.

Cloud providers (OpenAI / Anthropic / Gemini) are stubbed — the actual
SDK adapters land once the optional dependency extras are populated.
Until then, requesting a cloud backend raises a clear NotImplementedError
with the install hint, so misconfigured deploys fail fast at boot.
"""

from __future__ import annotations

from noether_svc_agent.config import AgentSettings
from noether_svc_agent.providers.ollama import OllamaProvider
from noether_svc_agent.providers.types import Provider


def make_provider(settings: AgentSettings) -> Provider:
    backend = settings.llm_backend
    if backend == "ollama":
        return OllamaProvider()
    if backend in {"openai", "anthropic", "gemini"}:
        raise NotImplementedError(
            f"{backend!r} provider not yet wired. Install the relevant extra "
            f"(noether-svc-agent[{backend}]) and the adapter will land in a "
            f"follow-up commit. For now, set LLM_BACKEND=ollama."
        )
    # Settings validation would have caught this — kept for type-narrowing
    # so mypy treats the function as exhaustive.
    raise ValueError(f"unknown LLM_BACKEND: {backend!r}")
