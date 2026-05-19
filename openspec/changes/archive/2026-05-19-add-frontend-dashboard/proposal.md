## Why

The frontend is what the hiring-manager audience actually sees in 90
seconds (SPEC section 2). It must surface live tags, anomaly alerts, and the
agent chat — minimally, cleanly, and within the boring-tech rule
(SPEC section 11). SPEC section 3 (6) and SPEC section 4 (component 7) name Next.js 14
+ Tailwind + Recharts, with Vega-Lite for agent-generated charts.

This change lands the frontend that the Milestone-3 demo question runs
against, plus the dashboard for Milestone 1 evidence.

## What Changes

- Add `services/frontend/` as a Next.js 14 App Router project with
  TypeScript + Tailwind + Recharts.
- Routes:
  - `/dashboard` — live tag display + anomaly feed
  - `/chat` — operator chat surface backed by the agent service
- Polling: 1-second poll against a backend BFF endpoint that aggregates
  latest values, recent alerts, and forecast strips — no websockets.
- Vega-Lite renderer for agent-generated charts.
- Containerise and add to `docker-compose.yml`.

## Capabilities

### New Capabilities
- `frontend-dashboard`: Render a live operator dashboard and a chat
  surface served by Next.js, polling backend services for tag values,
  anomalies, forecasts, and chat answers.

### Modified Capabilities
_None._

## Impact

- New code: `services/frontend/` (Next.js project), thin BFF route
  handlers under `services/frontend/app/api/` calling backend services.
- New deps: Next 14, React 18, TypeScript 5, Tailwind 3, Recharts,
  `vega-lite` + `vega-embed` for chart rendering, `swr` for polling.
- No new infra; same docker-compose network.
- Out of scope: real websocket streaming, mobile/responsive layout
  beyond Tailwind defaults, authentication beyond an inference API key
  (SPEC section 9).
