"""Router node: LLM-as-classifier with strict-JSON output.

Takes the operator's question and emits a list of tool names to fan out
to. Any names not in the registered tool set are filtered out, so a
hallucinated tool name from the LLM degrades to "skip that tool" rather
than crashing downstream.

If the LLM's response can't be parsed as valid JSON, we retry once with
a stricter "your previous response was not valid JSON, return ONLY a
JSON object" message. After two failures the router falls back to a
single safe default — `["sql"]` — so the rest of the pipeline still has
something to work with. (Better to answer narrowly than not at all.)
"""

from __future__ import annotations

import json

from noether_svc_agent.prompts import load_prompt
from noether_svc_agent.providers import Message, Provider
from noether_svc_agent.tools.types import AgentTool

DEFAULT_FALLBACK_TOOL = "sql"


class RouterNode:
    """Pick which tools to dispatch for a given question.

    Args:
        provider: any Provider impl (Ollama in prod, Mock in tests).
        tools:    the set of tool instances available — only their
                  `name`s are used for filtering router output.
        max_tools: cap on how many tools to dispatch in one turn.
                  Mirrors the design's "minimal toolset (1-3 tools) per
                  turn" rule that keeps fan-out cost bounded.
    """

    def __init__(
        self,
        provider: Provider,
        tools: list[AgentTool],
        *,
        max_tools: int = 3,
    ) -> None:
        self._provider = provider
        self._known_names = {t.name for t in tools}
        self._max_tools = max_tools
        self._prompt_template = load_prompt("router")

    async def select_tools(self, question: str) -> list[str]:
        """Return the tool names the orchestrator should fan out to."""
        prompt = self._prompt_template.format(question=question)
        messages = [Message(role="user", content=prompt)]

        response = await self._provider.chat(messages, json_mode=True)
        names = self._parse(response.content)

        if names is None:
            # One retry with a stricter system message before falling back.
            stricter = [
                Message(
                    role="system",
                    content=(
                        "Your previous response was not valid JSON. "
                        'Return ONLY a JSON object of the form {"tools": [...]} '
                        "with no surrounding text, code fences, or commentary."
                    ),
                ),
                Message(role="user", content=prompt),
            ]
            retry = await self._provider.chat(stricter, json_mode=True)
            names = self._parse(retry.content)

        if names is None:
            return [DEFAULT_FALLBACK_TOOL] if DEFAULT_FALLBACK_TOOL in self._known_names else []

        # Filter to known tools and cap.
        filtered = [n for n in names if n in self._known_names]
        return filtered[: self._max_tools]

    def _parse(self, raw: str) -> list[str] | None:
        """Parse the JSON reply; return None on any malformed input.

        Tolerates surrounding whitespace and the common ```json fences``` even
        though the prompt forbids them — local LLMs frequently leak fences.
        """
        text = raw.strip()
        if text.startswith("```"):
            # Strip code-fence markers (json, ```, etc.) — keep only the inner body.
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return None

        if not isinstance(obj, dict):
            return None
        tools = obj.get("tools")
        if not isinstance(tools, list):
            return None
        if not all(isinstance(t, str) for t in tools):
            return None
        return tools
