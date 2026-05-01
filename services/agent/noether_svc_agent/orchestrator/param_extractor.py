"""LLM-driven tool input extractor.

Given a question and a tool whose `input_model` is a Pydantic class,
the extractor asks the LLM to fill in JSON matching the schema, then
validates it. On parse / validation failure it returns None — the
fan-out node treats that as "skip this tool" rather than crashing the
whole turn.

This is one of the LLM calls in the per-turn budget (one call per
selected tool) — design.md caps fan-out at 3 tools to keep the total
under the p95 < 6 s budget on a local Ollama model.
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, ValidationError

from noether_svc_agent.prompts import load_prompt
from noether_svc_agent.providers import Message, Provider
from noether_svc_agent.tools.types import AgentTool

logger = logging.getLogger(__name__)


class ParamExtractor:
    def __init__(self, provider: Provider) -> None:
        self._provider = provider
        self._template = load_prompt("param_extractor")

    async def extract(self, tool: AgentTool, question: str) -> BaseModel | None:
        """Build a validated input model for `tool` from `question`.

        Returns None if the LLM's JSON can't be parsed or doesn't
        validate against `tool.input_model` — caller should skip this
        tool rather than guess.
        """
        schema = json.dumps(tool.input_model.model_json_schema(), indent=2)
        prompt = self._template.format(
            tool_name=tool.name,
            tool_description=tool.description,
            schema=schema,
            question=question,
        )
        response = await self._provider.chat(
            [Message(role="user", content=prompt)],
            json_mode=True,
        )

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "param_extractor.parse_failed",
                extra={"tool": tool.name, "raw": response.content[:200]},
            )
            return None

        try:
            return tool.input_model.model_validate(payload)
        except ValidationError:
            logger.warning(
                "param_extractor.validation_failed",
                extra={"tool": tool.name, "payload": payload},
            )
            return None
