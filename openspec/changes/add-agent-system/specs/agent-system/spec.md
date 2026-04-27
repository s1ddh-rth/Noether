## ADDED Requirements

### Requirement: Chat endpoint
The agent service SHALL expose `POST /chat` accepting `{ "session_id":
str, "message": str }` and returning `{ "answer": str, "citations":
[{"doc_id": str, "chunk_idx": int}], "vega_spec": dict | null,
"trace_id": str }`. It SHALL stream tokens via server-sent events when
the request `Accept` header includes `text/event-stream`, otherwise
return a single JSON response.

#### Scenario: Plain JSON answer
- **WHEN** a client posts `{"session_id": "demo", "message": "what is
  the latest value of FT-101?"}` with `Accept: application/json`
- **THEN** the response status is 200
- **AND** the body contains `answer` (non-empty), `citations` (possibly
  empty list), `vega_spec` (null), `trace_id` (uuid)

#### Scenario: Streaming answer
- **WHEN** the same call is made with `Accept: text/event-stream`
- **THEN** the response is a stream of `data:` events
- **AND** the final event payload has the same JSON shape as the
  non-streaming response

### Requirement: Router selects a minimal toolset
The router SHALL select between zero and three tools per turn from the
set {SQL, RAG, MultimodalRAG, Forecast, Anomaly, Viz}. The selection
SHALL be returned as part of the trace.

#### Scenario: Anomaly + RAG fan-out
- **WHEN** the message is "Why did anomaly fire on FT-101 yesterday at
  14:23?"
- **THEN** the router selects at least {Anomaly, RAG}
- **AND** does not select Forecast or Viz unless the synthesiser
  requests Viz downstream

### Requirement: Tools return typed ToolResult
Every sub-agent tool SHALL return a `ToolResult { summary: str, data:
dict | None, citations: list[str], vega_spec: dict | None }`. The
synthesiser SHALL only consume `ToolResult`s — never raw service
responses.

#### Scenario: Tool result shape
- **WHEN** the SQL tool runs against the latest-value query for FT-101
- **THEN** its return type-checks as `ToolResult`
- **AND** `summary` mentions FT-101 and the numeric value

### Requirement: Cross-session memory via Graphiti
The agent SHALL persist extracted facts to Graphiti at the end of every
turn, scoped by `session_id`, and SHALL retrieve relevant memories at
turn start. Memory size SHALL be bounded to the most recent 200 facts
per session.

#### Scenario: Memory persists across turns
- **WHEN** turn 1 in session `demo` establishes that FT-101 alarmed at
  14:23 yesterday and turn 2 asks "and what was its trend before that?"
- **THEN** the router includes the prior fact in the prompt context for
  turn 2 (visible in trace)

### Requirement: Dual-mode LLM backend
The agent SHALL select between Ollama (default) and cloud providers via
the `LLM_BACKEND` env var (values: `ollama`, `openai`, `anthropic`,
`gemini`). With `LLM_BACKEND=ollama` and `OFFLINE_MODE=1`, the agent
SHALL operate without any outbound network calls beyond local services.

#### Scenario: Air-gapped Ollama mode
- **WHEN** the agent service starts with `LLM_BACKEND=ollama` and
  `OFFLINE_MODE=1`
- **THEN** `/chat` answers a basic question within 30 seconds of
  container start
- **AND** no DNS lookups occur beyond Ollama, Neo4j, Postgres, Qdrant,
  and the inference service

### Requirement: Demo question end-to-end
The agent SHALL answer the Milestone-3 demo query "Why did anomaly fire
on FT-101 yesterday at 14:23?" with: a non-empty answer that names
contributing tags, at least one citation with `doc_id`, and a
non-null `vega_spec` showing the relevant time window.

#### Scenario: Demo query
- **WHEN** the corpus is indexed, an alert exists for FT-101 at the
  cited time, and the message is the demo query
- **THEN** the response contains all three of: contributing tags in
  `answer`, at least one citation, a non-null `vega_spec`
