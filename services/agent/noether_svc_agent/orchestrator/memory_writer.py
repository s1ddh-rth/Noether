"""Memory writer node — extracts facts from a turn and persists them.

The synthesiser produces the final answer; this node looks at the
question + answer + tool results, asks the LLM to pull out any facts
worth keeping across sessions, and writes them through the
`MemoryStore` Protocol.

Decoupled from any specific backend — in tests we use
`InMemoryStore`; in production this is the `GraphitiStore` (Neo4j).
The Protocol is the only contract.

Failure mode policy: the LLM occasionally returns malformed JSON.
Persisting *some* facts is better than persisting *none*, but
persisting bad data is worse than persisting nothing. So: parse
strictly, drop bad rows, log on parse failure, return the count
actually written. Never raise — memory write failure must not break
the chat turn.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from noether_memory import MemoryFact, MemoryStore

from noether_svc_agent.prompts import load_prompt
from noether_svc_agent.providers import Message, Provider
from noether_svc_agent.tools.types import ToolResult

logger = logging.getLogger(__name__)


class MemoryWriterNode:
    def __init__(self, provider: Provider, store: MemoryStore) -> None:
        self._provider = provider
        self._store = store
        self._prompt_template = load_prompt("memory_writer")

    async def write_turn(
        self,
        session_id: str,
        question: str,
        answer: str,
        tool_results: list[ToolResult],
    ) -> int:
        """Extract facts from this turn and persist them.

        Returns the number of facts actually persisted.
        """
        prompt = self._prompt_template.format(
            question=question,
            answer=answer,
            tool_results=self._format_tool_results(tool_results),
        )
        response = await self._provider.chat(
            [Message(role="user", content=prompt)],
            json_mode=True,
        )

        facts = self._parse_facts(response.content)
        if not facts:
            return 0
        try:
            self._store.write_facts(session_id, facts)
        except Exception:
            logger.warning("memory_writer.store_failed", exc_info=True)
            return 0
        return len(facts)

    def _parse_facts(self, raw: str) -> list[MemoryFact]:
        text = raw.strip()
        # Tolerate the same code-fence leakage the router does.
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("memory_writer.parse_failed", extra={"raw": raw[:200]})
            return []

        if not isinstance(obj, list):
            return []

        facts: list[MemoryFact] = []
        for entry in obj:
            if not isinstance(entry, dict):
                continue
            try:
                facts.append(
                    MemoryFact(
                        subject=str(entry["subject"]),
                        predicate=str(entry["predicate"]),
                        object=str(entry["object"]),
                    )
                )
            except (KeyError, ValueError):
                # Drop the bad row, keep the good ones.
                continue
        return facts

    def _format_tool_results(self, results: list[ToolResult]) -> str:
        if not results:
            return "(none)"
        rendered: list[dict[str, Any]] = []
        for r in results:
            payload: dict[str, Any] = {"summary": r.summary}
            if r.citations:
                payload["citations"] = r.citations
            rendered.append(payload)
        return json.dumps(rendered, default=str)
