# Contributing

Noether is being built milestone-by-milestone per `SPEC.md §8`. We follow a
spec-first workflow.

## Before writing code

1. Read `SPEC.md` and `CLAUDE.md`.
2. Open or pick up an OpenSpec change proposal under `openspec/changes/`. If
   the work isn't covered by an existing proposal, run `openspec new change <slug>`
   (or use the `/opsx:propose` slash command in Claude Code) and wait for
   approval before starting on the implementation.
3. One branch per proposal: `change/<slug>`.

## Code

- Python 3.11, formatted with `black` (line length 100), linted with `ruff`,
  type-checked with `mypy --strict`.
- TypeScript with Prettier + ESLint; `tsconfig.json` strict mode.
- No `print()` in production code — use `structlog`.
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.

## Tests

- Pytest for Python; ≥70% coverage on new code in `libs/` and `services/`.
- Vitest for the Next.js frontend.
- Integration tests use `docker compose up -d` with healthchecks.
- No tests, no merge.

## Pull requests

- Green CI is required.
- Update docs in the same PR as the behaviour change.
- If the PR touches a model, include eval results in the description.
