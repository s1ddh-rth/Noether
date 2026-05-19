# noether-frontend

Next.js 14 (App Router) operator UI — `add-frontend-dashboard`.

- `/dashboard` — live tag tiles + anomaly feed (phase 2)
- `/chat` — operator chat backed by `services/agent` (phase 3)

A thin BFF (route handlers under `app/api/*`) keeps secrets server-side:
tag/anomaly data is read straight from TimescaleDB via `pg`; chat is
proxied to the agent service.

## Dev

```bash
pnpm install          # uses .npmrc node-linker=hoisted (Next + pnpm)
pnpm dev              # http://localhost:3000
pnpm lint             # next lint (+ prettier config)
pnpm format:check
pnpm build            # standalone output
```

## Env vars

| Var                                   | Default                                    | Used by                   |
| ------------------------------------- | ------------------------------------------ | ------------------------- |
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD` | `timescaledb`/`5432`/`noether`/`noether`/— | BFF tag + anomaly queries |
| `AGENT_URL`                           | `http://agent:8100`                        | chat proxy (phase 3)      |
| `AGENT_API_KEY`                       | —                                          | chat proxy auth (phase 3) |

## Air-gap

No outbound requests at runtime. Fonts are **self-hosted** via
`next/font/local` from the committed `app/fonts/GeistVF.woff` +
`GeistMonoVF.woff` (no `next/font/google`, no `fonts.googleapis`/CDN
`<script>`). `next build` inlines them; the standalone server serves
everything same-origin. The BFF only calls in-cluster services
(Timescale, the agent). Verified by the air-gap grep in CI / review.

## Testing

- `pnpm test` / `pnpm test:coverage` — Vitest (jsdom), ≥70 % gate on
  `components/**`.
- `pnpm e2e` — Playwright smoke against a running compose `core`
  stack (`BASE_URL`, default `http://localhost:3001`).

## Docker

`Dockerfile` builds the Next standalone output into a small image. In
compose it's the `frontend` service (host `:3001`, profiles `core` +
`agent`). Helm: `services.frontend.enabled` (on by default; pair with
`ingress.enabled=true` for external access).
