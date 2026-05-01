"""POST /chat — operator question → orchestrator → answer + citations.

JSON mode is shipped here; SSE streaming lands in a follow-up commit
(it requires re-shaping the orchestrator to yield intermediate events).

The compiled LangGraph instance lives on `app.state.graph` and is
exposed via a `Depends`-able getter so tests can override it without
spinning up Ollama / Neo4j / Qdrant.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from noether_svc_agent.metrics import CHAT_LATENCY_MS, CHATS_TOTAL, TOOL_CALLS_TOTAL

router = APIRouter(tags=["chat"])
log = structlog.get_logger(__name__)


# --- request / response models -------------------------------------------------


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[str]
    vega_spec: dict[str, Any] | None = None
    selected_tools: list[str]
    facts_written: int


# --- dependency wiring --------------------------------------------------------


def get_graph(request: Request) -> Any:
    """Resolve the compiled orchestrator graph from app state.

    Tests override this via `app.dependency_overrides[get_graph]`.
    The runtime app puts a compiled graph here in its lifespan.
    """
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Agent orchestrator not initialised. Check Ollama / Neo4j / Qdrant "
                "connectivity in the service logs."
            ),
        )
    return graph


def _check_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None),
) -> None:
    expected = request.app.state.settings.api_key
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid X-API-Key header",
        )


# --- endpoint ----------------------------------------------------------------


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(_check_api_key)],
)
async def chat(req: ChatRequest, graph: Any = Depends(get_graph)) -> ChatResponse:
    log.info("chat.request", session_id=req.session_id, question_len=len(req.question))
    started = time.perf_counter()
    try:
        final = await graph.ainvoke(
            {
                "session_id": req.session_id,
                "question": req.question,
            }
        )
    except Exception:
        CHATS_TOTAL.labels(status="error").inc()
        CHAT_LATENCY_MS.observe((time.perf_counter() - started) * 1000.0)
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    CHATS_TOTAL.labels(status="ok").inc()
    CHAT_LATENCY_MS.observe(elapsed_ms)

    selected_tools = list(final.get("selected_tools") or [])
    for tool_name in selected_tools:
        TOOL_CALLS_TOTAL.labels(tool=tool_name).inc()

    response = ChatResponse(
        session_id=req.session_id,
        answer=final.get("answer", ""),
        citations=list(final.get("citations") or []),
        vega_spec=final.get("vega_spec"),
        selected_tools=selected_tools,
        facts_written=int(final.get("facts_written", 0)),
    )
    log.info(
        "chat.response",
        session_id=req.session_id,
        selected_tools=response.selected_tools,
        n_citations=len(response.citations),
        has_chart=response.vega_spec is not None,
        facts_written=response.facts_written,
        latency_ms=round(elapsed_ms, 1),
    )
    return response
