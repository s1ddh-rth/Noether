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
- [x] 3.4 `app/api/chat/route.ts` proxies `POST` to `${AGENT_URL}/chat`
      injecting `X-API-Key` server-side (never reaches the browser);
      validates body; clean 502 when the agent is down; passes the
      agent JSON through (SSE-ready — comment explains the swap when
      the agent gains streaming).

## 4. Dashboard page

- [x] 4.1 `useLatestTags` SWR hook — `/api/tags/latest`, 1 s
      `refreshInterval` (`lib/hooks.ts`).
- [x] 4.2 `useRecentAnomalies` SWR hook — `/api/anomalies/recent`,
      5 s. (Plus `useTagRange` at 15 s for sparklines so 52 tiles
      don't hammer the BFF at 1 s.)
- [x] 4.3 `<TagTile>` — tag id, value (3 dp), Recharts sparkline
      from the 5-min range; presentational (`now` injectable for tests).
- [x] 4.4 `<AnomalyPanel>` — latest 20, newest first, time/score/
      tags; empty + error states.
- [x] 4.5 Stale indicator: sample age > 30 s → `data-stale="true"`
      + visible "stale" badge + danger border (spec scenario).

## 5. Chat page

- [x] 5.1 Per-tab `session_id` — `sessionStorage` + `crypto.randomUUID`
      on first load.
- [x] 5.2 Message list (user/assistant bubbles), input + Send form,
      busy/thinking + error states, autoscroll.
- [x] 5.3 JSON request/response. The agent is JSON-only today (its
      router defers SSE); the BFF + client are structured so streaming
      slots in without a client rewrite. Spec's SSE scenario is
      explicitly conditional ("WHEN the agent supports SSE").
- [x] 5.4 Citations rendered as a footer list under the answer.
- [x] 5.5 `<VegaChart>` — dynamically imports `vega-embed` (keeps it
      out of the initial bundle; `/chat` is 1.96 kB), renders agent
      `vega_spec`.
- [x] 5.6 `<ErrorBoundary>` wraps `<VegaChart>`; VegaChart itself
      validates the spec + try/catches embed → fallback message +
      `<details>` raw spec (spec "malformed spec is contained").

## 6. Tests

- [x] 6.1 Vitest: `<TagTile>` — value to 3 dp, sparkline svg present,
      fresh vs stale (`data-stale`/badge). 4 tests, `vitest.config.ts`
      + jsdom + `@testing-library`. (CI vitest job lands in phase 4.)
- [x] 6.2 Vitest: `<VegaChart>` — valid spec renders the container
      (embed mocked), embed-reject → fallback + `<details>` raw spec,
      non-object spec → fallback without calling embed. 3 tests
      (7 total in the suite, all pass).
- [x] 6.3 Playwright smoke (`e2e/smoke.spec.ts`, `playwright.config.ts`)
      against compose `core`: dashboard renders ≥1 tile + the anomaly
      panel; nav → `/chat`, a turn echoes + resolves to a reply or the
      graceful error (agent isn't in `core` → no LLM in CI; non-crash
      is the invariant). New CI `frontend-e2e` job (path-filtered,
      fork-guarded).
- [x] 6.4 Vitest v8 coverage gated ≥70% on `components/**`
      (`thresholds` in `vitest.config.ts`); current 98 % lines /
      82 % branches / 100 % funcs across 5 suites / 15 tests. New CI
      `frontend` job runs `test:coverage` + lint + tsc + build.

## 7. Air-gap

- [x] 7.1 No external CDN/font/script: `next/font/local` only
      (committed `app/fonts/*.woff`), no `next/font/google`, no CDN
      `<script>`. Verified by the air-gap grep in prior-phase reviews.
- [x] 7.2 `services/frontend/README.md` "Air-gap" section documents
      the self-hosted font bundle + same-origin serving.

## 8. Docs

- [x] 8.1 `services/frontend/README.md`: dev run, build, env vars,
      testing, air-gap, Docker/Helm.
- [x] 8.2 "Frontend (add-frontend-dashboard — live)" section added to
      `docs/architecture.md` (routes, BFF, air-gap, SSE-readiness).
- [x] 8.3 Recorded-demo/hero-media remains the post-v0.1 follow-up
      already noted in the top-level README roadmap (CI can't produce
      a video — same call as the M4 release pass; no dead link).
