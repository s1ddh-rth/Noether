# CLAUDE.md — Working Conventions for Noether

This file tells Claude Code how to work in this repo. It is derived from
**SPEC.md §7** and is the operational counterpart to the spec.

## Sources of truth, in order

1. **SPEC.md** — canonical project specification. Scope, stack, milestones,
   conventions, definition of done. If anything here conflicts with SPEC.md,
   SPEC.md wins.
2. **openspec/** — per-change proposals, designs, tasks, and capability specs.
   Generated and managed via the `openspec` CLI. Project-wide context for new
   proposals lives in `openspec/config.yaml`.
3. **This file** — day-to-day conventions for Claude Code.

## Operating posture

- **Spec-first.** Propose changes via OpenSpec before implementing. One change
  proposal per scoped unit of work. Await human approval before writing code.
- **Boring tech wins.** The stack in SPEC §5 is locked. Do not introduce a new
  top-level dependency without an OpenSpec change proposal that justifies it.
- **Library discipline.** Use OSS, do not reimplement. PyOD for AD, Nixtla for
  forecasting, Graphiti for memory, RAGAS for eval. If you find yourself
  writing >30 lines of "core algorithm," stop and check whether a library does it.
- **Air-gap and cost rules are non-negotiable.** Default config must run with
  zero paid services and zero outbound network calls (`LLM_BACKEND=ollama`,
  `OFFLINE_MODE=1`).
- **One milestone at a time.** Do not skip ahead in SPEC §8.

## Code style

### Python
- Black (line length 100), Ruff for linting, mypy strict on new code.
- `structlog` for structured JSON logs. **No `print()` in production code.**
- No bare `except:` — always specify exception types.
- Errors that cross service boundaries are typed Pydantic models.
- All config via `pydantic-settings` `BaseSettings`. `.env.example` committed,
  `.env` gitignored.

### TypeScript
- Prettier, ESLint (Next.js defaults), strict mode in `tsconfig.json`.

### Pre-commit hooks
Run via `pre-commit`: black, ruff, mypy, prettier, eslint, end-of-file-fixer,
trailing-whitespace.

## Project structure

```
noether/
├── SPEC.md                    # canonical spec
├── CLAUDE.md                  # this file
├── README.md                  # public-facing
├── pyproject.toml             # uv-managed
├── docker-compose.yml         # dev stack
├── charts/noether/            # Helm chart
├── services/
│   ├── ingest/                # pyTEP replayer
│   ├── inference/             # FastAPI: forecast, anomaly, explain
│   ├── agent/                 # LangGraph orchestrator
│   └── frontend/              # Next.js
├── libs/
│   ├── forecasting/           # shared forecast logic
│   ├── anomaly/               # shared AD logic
│   ├── rag/                   # ingestion, chunking, retrieval
│   └── memory/                # Graphiti wrapper
├── eval/
│   ├── forecast_harness.py
│   ├── anomaly_harness.py
│   └── rag_ragas.py
├── data/                      # DVC-tracked, not committed
├── notebooks/                 # exploratory only — not part of the runtime
├── openspec/                  # change proposals + capability specs
└── docs/
    ├── architecture.md
    ├── benchmarks.md
    └── deployment.md
```

## Tooling

- **Package manager:** `uv`. Lockfile committed. Add deps via `uv add` only
  after the relevant change proposal is approved.
- **OpenSpec:** install once with `npm i -g @fission-ai/openspec`. Use
  `/opsx:propose` (or `openspec new change <name>`) to start a change.
  Validate with `openspec validate <name>`.

## Testing

- **Pytest** for Python; minimum **70% coverage** on new code in `libs/` and
  `services/`.
- **Vitest** for the Next.js frontend.
- **Integration tests** use `docker compose up -d` with health-checked services.
- **No tests, no merge.**

## Commits and branches

- **Conventional Commits**: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- **One branch per OpenSpec change proposal**: `change/<proposal-slug>`.
- **PRs require:** green CI, updated docs if behaviour changes, eval results in
  the PR description if a model is touched.

## Configuration

- `pydantic-settings` `BaseSettings` for all config.
- `.env.example` committed, `.env` gitignored.
- One Helm `values.yaml` plus `values.dev.yaml` and `values.airgapped.yaml` overlays.

## Observability

- `structlog` JSON output everywhere.
- Every FastAPI endpoint emits `request_id`, `latency_ms`, `status`.
- Prometheus exporters from every service. Grafana dashboards in `charts/`.

## Security

- **No API keys in code, ever.**
- **No PII in commits.**
- Air-gapped mode must work without any external DNS lookups
  (`OFFLINE_MODE=1` enforces this).
- API key on the inference endpoints is the only auth in v0.1.

## Documentation

- Every service has a `README.md`: purpose, endpoints, env vars, how to run,
  how to test.
- Architecture diagrams kept as `.mermaid` source in `/docs`, rendered to SVG in CI.
- The top-level `README.md` is rewritten only via PR — not touched casually.

## OpenSpec workflow

1. **Propose** — `openspec new change <kebab-name>` (or `/opsx:propose`).
   Creates `openspec/changes/<name>/` with `proposal.md`, `design.md`,
   `tasks.md`, and `specs/<capability>/spec.md` deltas.
2. **Validate** — `openspec validate <name>` before requesting review.
3. **Wait for approval.** Do not implement until the human signs off.
4. **Implement** on a branch named `change/<name>`. Mark `tasks.md` items as
   work proceeds.
5. **Archive** — `openspec archive <name>` when shipped; the deltas merge into
   `openspec/specs/`.

## What's out of scope (SPEC §9 — do not propose)

- Real OPC UA / SCADA / DCS connectors
- Custom physics-informed neural networks (PINNs)
- Fine-tuned domain LLMs
- Cloud-managed K8s (EKS/GKE)
- Multi-tenant deployments
- Auth beyond an API key on inference endpoints
- Mobile/responsive frontend beyond Tailwind defaults
- Real-time websocket streaming to the frontend (poll-based is fine)
- Custom embedding model training
- Anything requiring a paid API key in default mode

## When in doubt

Optimise for **clarity** and **shippability**, not cleverness. If something in
SPEC.md is ambiguous, **ask** before assuming.
