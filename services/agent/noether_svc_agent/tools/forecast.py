"""Forecast tool — calls services/inference `/forecast`.

The inference service owns the actual ensemble/PatchTST/LGBM dispatch;
the tool just shapes the request and translates the response into a
`ToolResult` the synthesiser can compose with.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field

from noether_svc_agent.tools.types import ToolResult


class ForecastTagPoint(BaseModel):
    ts: str  # ISO-8601 (UTC) — the inference API parses it
    value: float


class ForecastToolInput(BaseModel):
    tag: str = Field(min_length=1)
    history: list[ForecastTagPoint] = Field(min_length=1)


class ForecastTool:
    name: str = "forecast"
    description: str = (
        "Predict the next 30 minutes for a tag given recent history. "
        "Returns a point estimate plus a 95% prediction band."
    )

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

    async def run(self, input: ForecastToolInput) -> ToolResult:
        client = await self._get_client()
        resp = await client.post(
            f"{self._base}/forecast",
            json={
                "tag": input.tag,
                "history": [p.model_dump() for p in input.history],
            },
            headers={"X-API-Key": self._key},
        )
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()

        return ToolResult(
            summary=(
                f"{input.tag} forecast at horizon {body['horizon_min']} min: "
                f"{body['point']:.3f} (95% PI [{body['lower']:.3f}, {body['upper']:.3f}], "
                f"model={body['model_kind']})."
            ),
            data={
                "tag": body["tag"],
                "horizon_min": body["horizon_min"],
                "point": body["point"],
                "lower": body["lower"],
                "upper": body["upper"],
                "model_kind": body["model_kind"],
                "model_version": body["model_version"],
            },
        )

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None
