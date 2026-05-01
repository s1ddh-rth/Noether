"""Fan-out node: dispatch the router-selected tools concurrently.

For each selected tool name, look it up in the registry, ask the
ParamExtractor for a validated input, then run the tool. Tools whose
input couldn't be extracted are skipped — they don't break the turn.

`asyncio.gather(..., return_exceptions=True)` ensures one tool's
failure (HTTP timeout, DB hiccup) doesn't take down siblings. Failed
tools log and drop out of the result list rather than propagating.
"""

from __future__ import annotations

import asyncio
import logging

from noether_svc_agent.orchestrator.param_extractor import ParamExtractor
from noether_svc_agent.tools.types import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class FanOutNode:
    def __init__(self, tools: list[AgentTool], param_extractor: ParamExtractor) -> None:
        self._registry: dict[str, AgentTool] = {t.name: t for t in tools}
        self._param_extractor = param_extractor

    async def run(self, question: str, selected_tools: list[str]) -> list[ToolResult]:
        async def _one(name: str) -> ToolResult | None:
            tool = self._registry.get(name)
            if tool is None:
                # Router shouldn't pick unknown tools (it filters), but be defensive.
                logger.warning("fan_out.unknown_tool", extra={"tool": name})
                return None

            tool_input = await self._param_extractor.extract(tool, question)
            if tool_input is None:
                logger.warning("fan_out.input_extraction_failed", extra={"tool": name})
                return None

            try:
                return await tool.run(tool_input)
            except Exception:
                logger.warning(
                    "fan_out.tool_failed",
                    exc_info=True,
                    extra={"tool": name},
                )
                return None

        coroutines = [_one(name) for name in selected_tools]
        outputs = await asyncio.gather(*coroutines)
        return [r for r in outputs if r is not None]
