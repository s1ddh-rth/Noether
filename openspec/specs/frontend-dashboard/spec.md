# frontend-dashboard Specification

## Purpose
Provide the operator web UI: a Next.js 14 dashboard of live plant
tags + an anomaly feed, and a chat surface backed by the agent
service. A thin server-side BFF keeps all backend access (TimescaleDB,
the agent API key) off the browser; the build is air-gapped
(self-hosted fonts, no CDN) and polling-based (no websockets at v0.1).

## Requirements
### Requirement: Dashboard route renders live tags
The `/dashboard` route SHALL render a grid of tag tiles, each showing
the tag id, latest numeric value, units (when known), and a 5-minute
sparkline. Tile values SHALL refresh on a 1-second cadence using SWR
polling against the BFF endpoint `/api/tags/latest`.

#### Scenario: Initial render with live data
- **WHEN** the dashboard route is loaded with the backend stack running
- **THEN** within 3 seconds the page shows >= 50 tag tiles
- **AND** each tile shows a numeric value and a non-empty sparkline

#### Scenario: Stale-data indicator
- **WHEN** the BFF returns a tag whose latest sample is older than 30
  seconds
- **THEN** that tile renders with a `data-stale="true"` attribute and a
  visible "stale" badge

### Requirement: Anomaly feed
The `/dashboard` route SHALL render an "Anomalies" panel listing the
latest 20 alerts from `tag_anomalies`, newest first, with timestamp,
score, and contributing tags. The list SHALL refresh on a 5-second
cadence.

#### Scenario: New alert appears
- **WHEN** a new row is inserted into `tag_anomalies` with score 0.9
- **THEN** the alert appears at the top of the panel within 6 seconds

### Requirement: Chat route
The `/chat` route SHALL render a chat surface that posts user messages
to `/api/chat` (which proxies to `services/agent` `POST /chat`),
preserves a per-tab `session_id`, and renders the agent's `answer`,
`citations`, and `vega_spec` when present.

#### Scenario: Round-trip chat turn
- **WHEN** the user sends "what is the latest value of FT-101?"
- **THEN** within 10 seconds the conversation pane shows the agent's
  answer
- **AND** any returned `vega_spec` renders as a chart inline

#### Scenario: Streaming response
- **WHEN** the agent supports SSE and the user sends a message
- **THEN** the answer text streams character-by-character into the
  pane (incremental render)

### Requirement: Vega-Lite renderer
The frontend SHALL include a `VegaChart` client component that accepts
a Vega-Lite spec and renders it via `vega-embed`. Malformed specs SHALL
NOT crash the page; the component SHALL render a fallback message and
show the raw spec under a `<details>` element.

#### Scenario: Valid spec renders
- **WHEN** `<VegaChart spec={validLineSpec} />` is mounted
- **THEN** an SVG/Canvas chart appears

#### Scenario: Malformed spec is contained
- **WHEN** `<VegaChart spec={{ "not": "valid" }} />` is mounted
- **THEN** the page does not throw
- **AND** a fallback message and `<details>` element render in place
  of the chart

### Requirement: Air-gapped operation
The frontend SHALL operate without any outbound network calls. All
fonts, scripts, and assets SHALL be bundled or served from the same
origin. With `OFFLINE_MODE=1`, runtime SHALL not perform any external
network fetches (Google Fonts, CDNs, telemetry).

#### Scenario: Air-gapped load
- **WHEN** the browser opens the dashboard with all external DNS blocked
- **THEN** the page renders fully (no layout shift from missing fonts)
- **AND** DevTools network tab shows no requests to non-allowlisted hosts

