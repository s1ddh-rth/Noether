"""Anomaly tool — calls services/inference `/anomaly` and `/explain`.

`/anomaly` returns the rank-normalised ensemble score + per-detector
breakdown for a given window. `/explain` returns per-tag SHAP-blended
contributions for a stored alert. The tool exposes both via the
`include_explain` flag so the orchestrator can decide whether the user
needs the why or just the what.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field

from noether_svc_agent.tools.types import ToolResult


class AnomalyToolInput(BaseModel):
    tags: list[str] = Field(min_length=1)
    start: str  # ISO-8601 UTC
    end: str  # ISO-8601 UTC
    alert_id: str | None = None  # if set + include_explain, also fetches /explain
    include_explain: bool = False


class AnomalyTool:
    name: str = "anomaly"
    description: str = (
        "Score a tag window with the anomaly ensemble and optionally "
        "retrieve the per-tag SHAP explanation for a stored alert id."
    )
    input_model = AnomalyToolInput

    def __init__(
        self,
        base_url: str,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._key = api_key
        self._client = client
        self._owns_client = client is None
        self._timeout = timeout_s

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def run(self, input: AnomalyToolInput) -> ToolResult:
        client = await self._get_client()
        score_resp = await client.post(
            f"{self._base}/anomaly",
            json={"tags": input.tags, "start": input.start, "end": input.end},
            headers={"X-API-Key": self._key},
        )
        score_resp.raise_for_status()
        score: dict[str, Any] = score_resp.json()

        explain: dict[str, Any] | None = None
        if input.include_explain and input.alert_id is not None:
            ex_resp = await client.post(
                f"{self._base}/explain",
                json={"alert_id": input.alert_id},
                headers={"X-API-Key": self._key},
            )
            ex_resp.raise_for_status()
            explain = ex_resp.json()

        flag = "ALERT" if score["alert"] else "ok"
        summary = f"Anomaly score {score['score']:.3f} ({flag})"
        if explain is not None:
            top = explain.get("contributions", [])[:3]
            if top:
                summary += "; top contributors: " + ", ".join(
                    f"{c['tag']}={c['contribution']:.3f}" for c in top
                )

        data: dict[str, Any] = {"score": score}
        if explain is not None:
            data["explain"] = explain

        return ToolResult(summary=summary, data=data)

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None
