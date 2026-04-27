## 1. Scaffolding

- [ ] 1.1 `npx create-next-app@14 services/frontend --ts --tailwind
      --app --no-src --no-eslint`
- [ ] 1.2 Re-enable ESLint with Next defaults; add Prettier config
- [ ] 1.3 `pnpm` workspace integration; pin Node 20+
- [ ] 1.4 Add `Dockerfile` (standalone output) and compose entry

## 2. Theme and shell

- [ ] 2.1 Tailwind base + dark default; minimal layout in `app/layout.tsx`
- [ ] 2.2 Global header with route nav (`/dashboard`, `/chat`)
- [ ] 2.3 Bundle a self-hosted variable font (no Google Fonts)

## 3. BFF API routes

- [ ] 3.1 `app/api/tags/latest/route.ts` → backend storage query
- [ ] 3.2 `app/api/tags/[tag]/range/route.ts` for sparklines
- [ ] 3.3 `app/api/anomalies/recent/route.ts` → latest 20 alerts
- [ ] 3.4 `app/api/chat/route.ts` proxies to `services/agent` (JSON + SSE)

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
