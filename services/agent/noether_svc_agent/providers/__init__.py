"""LLM provider abstraction.

A thin async wrapper exposing `chat(messages, json_mode) -> ChatResponse`.
Implementations:

- `MockProvider`   — deterministic stub for unit tests; records calls.
- `OllamaProvider` — local Ollama HTTP API; the air-gapped default.
- Cloud (OpenAI / Anthropic / Gemini) — selected by `LLM_BACKEND` and
  imported lazily in `factory.py`. Raises `NotImplementedError` until
  the optional SDK extra is installed and the adapter wired up.

Tool-calling support is intentionally NOT in this layer: LangGraph
handles tool dispatch at the graph level (task 5). Providers here only
need plain chat completion + a `json_mode` knob for strict-JSON outputs
the router relies on.
"""

from noether_svc_agent.providers.factory import make_provider
from noether_svc_agent.providers.mock import MockProvider
from noether_svc_agent.providers.ollama import OllamaProvider
from noether_svc_agent.providers.types import ChatResponse, Message, Provider, ProviderCall

__all__ = [
    "ChatResponse",
    "Message",
    "MockProvider",
    "OllamaProvider",
    "Provider",
    "ProviderCall",
    "make_provider",
]
