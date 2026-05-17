"""Compose the orchestrator from `AgentSettings`.

Lives in its own module so the lifespan can call it cleanly and tests
can exercise individual builder steps without standing up the whole
graph. Each builder is failure-tolerant where the network is involved:

- Memory store: try Graphiti against `NEO4J_URI`; on any failure
  (DB unreachable, auth, schema init) fall back to `InMemoryStore`
  with a logged warning. The chat turn keeps working without
  cross-session persistence.
- RAG / multimodal-RAG retrievers: stubbed for v0.1. Loading
  BGE-base + OpenCLIP at the agent service costs ~1 GB of model
  weights and ~30 s of startup on a cold cache. The RAG corpus is
  also typically empty until the operator runs `ingest`, so the
  stub returns empty — the synthesiser then honestly says "no
  documentation hits". Wiring real retrievers is a tracked
  follow-up in `docs/architecture.md`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import httpx
from noether_memory import GraphitiStore, InMemoryStore, MemoryStore
from noether_storage import async_dsn  # type: ignore[import-untyped]
from noether_storage.config import StorageSettings  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from noether_svc_agent.config import AgentSettings
from noether_svc_agent.orchestrator import (
    FanOutNode,
    MemoryWriterNode,
    ParamExtractor,
    RouterNode,
    SynthesiserNode,
    build_graph,
)
from noether_svc_agent.providers import OllamaProvider, Provider
from noether_svc_agent.tools import (
    AgentTool,
    AnomalyTool,
    ForecastTool,
    MultimodalRagTool,
    RagTool,
    SqlTool,
    VizTool,
)

logger = logging.getLogger(__name__)


def build_provider(settings: AgentSettings) -> Provider:
    if settings.llm_backend != "ollama":
        raise NotImplementedError(
            f"{settings.llm_backend!r} provider not yet wired. Set LLM_BACKEND=ollama."
        )
    return OllamaProvider(host=settings.ollama_host, model=settings.ollama_model)


def build_engine(settings: AgentSettings) -> AsyncEngine:
    """AsyncEngine for the SQL tool. Re-uses libs/storage's DSN builder."""
    storage_settings = StorageSettings(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )
    return create_async_engine(async_dsn(storage_settings), pool_pre_ping=True)


def build_memory_store(settings: AgentSettings) -> MemoryStore:
    """GraphitiStore against Neo4j, falling back to InMemoryStore on any failure."""
    try:
        return GraphitiStore.connect(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
    except Exception:
        logger.warning(
            "factory.graphiti_unavailable_falling_back_to_in_memory",
            exc_info=True,
            extra={"neo4j_uri": settings.neo4j_uri},
        )
        return InMemoryStore()


def _stub_rag_retrieve(query: str, top_n: int) -> list[object]:
    """Stub for v0.1 — see module docstring."""
    return []


def build_tools(
    settings: AgentSettings,
    *,
    engine: AsyncEngine,
    inference_client: httpx.AsyncClient,
    rag_retrieve_fn: Callable[[str, int], list[object]] = _stub_rag_retrieve,
    mm_rag_retrieve_fn: Callable[[str, int], list[object]] = _stub_rag_retrieve,
) -> list[AgentTool]:
    """Build the six tool instances. Inference clients are injected so tests
    can substitute httpx.MockTransport without going through the network.

    The list is typed as `list[AgentTool]` (the runtime-checkable Protocol).
    Each concrete tool's `run(input: SpecificInput)` is contravariant against
    the Protocol's `run(input: BaseModel)`, which mypy strict mode flags —
    every entry is statically a Protocol-conforming AgentTool at runtime
    so we cast through `list[AgentTool]` via type-ignore.
    """
    tools: list[AgentTool] = [
        SqlTool(engine),  # type: ignore[list-item]
        RagTool(retrieve_fn=rag_retrieve_fn),  # type: ignore[list-item]
        MultimodalRagTool(retrieve_fn=mm_rag_retrieve_fn),  # type: ignore[list-item]
        ForecastTool(  # type: ignore[list-item]
            base_url=settings.inference_url,
            api_key=settings.inference_api_key,
            client=inference_client,
        ),
        AnomalyTool(  # type: ignore[list-item]
            base_url=settings.inference_url,
            api_key=settings.inference_api_key,
            client=inference_client,
        ),
        VizTool(),  # type: ignore[list-item]
    ]
    return tools


def build_orchestrator(
    settings: AgentSettings,
    *,
    engine: AsyncEngine,
    inference_client: httpx.AsyncClient,
    memory_store: MemoryStore,
    rag_retrieve_fn: Callable[[str, int], list[object]] = _stub_rag_retrieve,
    mm_rag_retrieve_fn: Callable[[str, int], list[object]] = _stub_rag_retrieve,
) -> object:
    """Build the compiled LangGraph from settings + injected resources.

    Returns the compiled graph (typed as `object` because LangGraph's
    compiled-graph generic varies across minor versions).
    """
    provider = build_provider(settings)
    tools = build_tools(
        settings,
        engine=engine,
        inference_client=inference_client,
        rag_retrieve_fn=rag_retrieve_fn,
        mm_rag_retrieve_fn=mm_rag_retrieve_fn,
    )
    router = RouterNode(provider=provider, tools=tools)
    fan_out = FanOutNode(tools=tools, param_extractor=ParamExtractor(provider=provider))
    synthesiser = SynthesiserNode(provider=provider)
    memory_writer = MemoryWriterNode(provider=provider, store=memory_store)
    return build_graph(
        router=router,
        fan_out=fan_out,
        synthesiser=synthesiser,
        memory_writer=memory_writer,
    )
