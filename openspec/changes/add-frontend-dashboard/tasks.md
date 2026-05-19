## 1. Scaffolding

- [x] 1.1 `create-next-app@14 services/frontend --ts --tailwind --app
      --no-src-dir --no-eslint --use-pnpm` (Next 14.2.35).
- [x] 1.2 ESLint re-enabled (`next/core-web-vitals` + `prettier`);
      Prettier config + ignore; `format`/`format:check` scripts.
      eslint-config-next pinned to 14.2.35 (matches Next 14).
- [x] 1.3 pnpm project (`.npmrc node-linker=hoisted` — required for
      Next + pnpm prerender of `/404`,`/500`); `engines.node >=20`.
      (Standalone JS app — not part of the uv/Python workspace.)
- [x] 1.4 `Dockerfile` (multi-stage, Next standalone runtime, non-root)
      + `.dockerignore`; compose `frontend` service (host `:3001`,
      profiles `core`+`agent`, Timescale healthcheck dep).

## 2. Theme and shell

- [x] 2.1 Tailwind + fixed dark palette in `globals.css`; minimal
      `app/layout.tsx` shell (header + centered main).
- [x] 2.2 `components/Header.tsx` — client nav with active-route
      highlight (`/dashboard`, `/chat`); `/` redirects to `/dashboard`.
- [x] 2.3 Self-hosted Geist variable fonts via `next/font/local`
      (bundled `app/fonts/*.woff`) — no Google Fonts / external fetch.

## 3. BFF API routes

- [x] 3.1 `app/api/tags/latest/route.ts` — `DISTINCT ON (tag)` newest
      sample per tag via the shared `pg` pool (`lib/db.ts`,
      `server-only`), `force-dynamic`, `no-store`.
- [x] 3.2 `app/api/tags/[tag]/range/route.ts` — last 5 min of a tag
      for sparklines; tag id validated against `^[A-Za-z0-9_]{1,64}$`.
- [x] 3.3 `app/api/anomalies/recent/route.ts` — latest 20
      `tag_anomalies` rows, newest first.
- [ ] 3.4 `app/api/chat/route.ts` proxies to `services/agent` (JSON;
      SSE-ready) — phase 3 (the chat page lands with it).

## 4. Dashboard page

- [ ] 4.1 SWR hook `useLatestTags` (1 s polling)
- [ ] 4.2 SWR hook `useRecentAnomalies` (5 s polling)
- [ ] 4.3 `<TagTile>` component with sparkline (Recharts)
- [ ] 4.4 `<AnomalyPanel>` listing alerts, newest first
- [ ] 4.5 Stale indicator (>30 s old)

## 5. Chat page

- [ ] 5.1 Per-tab `session_id` (sessionStorage)
- [ ] 5.2 Message list, input, send
- [ ] 5.3 SSE handler with JSON fallback
- [ ] 5.4 Citations footer rendering
- [ ] 5.5 `<VegaChart>` client component using `vega-embed`
- [ ] 5.6 Error boundary around `<VegaChart>`

## 6. Tests

- [ ] 6.1 Vitest: `<TagTile>` renders value, sparkline, stale state
- [ ] 6.2 Vitest: `<VegaChart>` renders valid spec, falls back on
      malformed
- [ ] 6.3 Playwright (smoke): dashboard loads against compose stack;
      chat turn returns an answer
- [ ] 6.4 Coverage >=70% on components in `services/frontend/`

## 7. Air-gap

- [ ] 7.1 No external CDN/font/script references in built output
- [ ] 7.2 Document local font bundle in `services/frontend/README.md`

## 8. Docs

- [ ] 8.1 `services/frontend/README.md`: dev run, build, env vars
- [ ] 8.2 Frontend section added to `docs/architecture.md`
- [ ] 8.3 Hero GIF capture step noted for the README finalisation pass
