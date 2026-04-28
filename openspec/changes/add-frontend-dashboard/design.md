## Context

The frontend is intentionally minimal: it has to make the demo legible,
not be a product. Two routes carry the weight: a dashboard with live
tags + alerts, and a chat that talks to `services/agent`.

Polling is the explicit choice (SPEC section 9 forbids websockets at v0.1).
With ~50 tags at 1 Hz the BFF does cheap aggregations and the browser
re-renders strips on a 1-second cadence.

## Goals / Non-Goals

**Goals:**
- App Router project structure, server components by default.
- 1-second polling SWR hooks for tag data; 5-second for alerts.
- Single shared Tailwind theme; no UI library beyond Tailwind primitives.
- Recharts for fixed dashboard plots; Vega-Lite for agent-emitted plots.
- Chat surface supports both JSON and SSE responses from the agent.
- Cleanly themed dark-mode-by-default layout (industrial dashboards
  default dark — but no toggle UI at v0.1).

**Non-Goals (per SPEC section 9):**
- Websockets, real-time push.
- Responsive/mobile layout beyond Tailwind defaults.
- Authentication beyond the inference API key.
- A component library beyond Tailwind primitives.

## Decisions

- **Framework:** Next.js 14 App Router, server components default,
  client components for chart canvases and the chat input.
- **Data layer:** SWR for client-side polling. BFF API routes under
  `app/api/*` keep secrets server-side.
- **Charts:** Recharts for the fixed dashboard plots (line, sparkline,
  small multiples). Vega-Lite for agent-generated charts (renderer
  isolated to `<VegaChart spec={...} />`).
- **Chat:** SSE streaming when the agent supports it; JSON fallback.
  Citations rendered as a footer list; vega specs render inline.
- **Styling:** Tailwind only. No `shadcn/ui` for v0.1 to keep
  dependency surface minimal — flagged for v0.2 if needed.
- **State:** local component state only; no Redux/Zustand at v0.1.

## Risks / Trade-offs

- Polling is not the most modern UX choice. Acceptable: SPEC section 9
  explicitly takes this trade-off.
- No UI library means more handwritten markup. Acceptable at v0.1
  scale (two routes).
- Vega-Lite specs from the agent could be malformed; the renderer
  catches and shows a fallback "could not render chart" with the raw
  spec in a `<details>`.
- SPEC section 11: scope creep. We resist adding theming, settings panels,
  or playground routes at v0.1.
