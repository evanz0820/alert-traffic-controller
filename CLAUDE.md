# CLAUDE.md — Alert Traffic Controller (ATC)

## Purpose
Portfolio project. A gateway ("controller") that sits in front of a retail bank's
independent alert producers (balance, transaction, fraud, payment, statement,
marketing) and decides, per customer, **what** to send, **when**, and on **which
channel**. Inspired by LinkedIn's 2018 "Air Traffic Controller" post. The bank is the
fictional **Northgate Bank**; all data is synthetic (seed 42).

Headline claim the app must prove: alert volume drops sharply, customer fatigue drops,
and **zero critical alerts are ever suppressed or delayed**.

## NON-NEGOTIABLE RULE
**Critical alerts (fraud suspected, card locked, login from new device) are never
suppressed, delayed, capped, batched, or rerouted away from a channel.** They are sent
immediately on every channel (see docs/PLAN.md §5). Any change touching the rules
engine must keep `tests/property/test_critical_guarantee.py` green. Never weaken,
skip, or `xfail` that test. If a feature seems to require touching critical
delivery, stop and ask.

## Stack
- Backend: Python 3.12 (uv), FastAPI, Pydantic v2, SQLModel on SQLite, pytest +
  hypothesis, ruff, mypy (strict on `atc.engine`)
- Frontend: React 18 + TypeScript + Vite, Tailwind CSS, shadcn/ui, Recharts (+ Sankey),
  Framer Motion, lucide-react, TanStack Query + Table, ESLint + Prettier
- Tooling: Makefile, Docker Compose (optional), GitHub Actions CI, Claude Code hooks

## Folder map
```
api/index.py      Vercel Python function: exposes the FastAPI app for /api/*
vercel.json       Vercel build, static output, function bundle, rewrites
requirements.txt  runtime deps for the Vercel function (keep in sync with backend/pyproject)
backend/
  data/atc.db     committed read-only snapshot (dataset + baseline + default run)
  src/atc/
    engine/       pure rules pipeline (no I/O, no DB, mypy strict)
      rules/      one module per rule, shared Rule protocol
    simulator/    synthetic customers, accounts, events (seeded)
    directory/    account type -> customer service phone mapping
    db/           SQLModel tables, session, repositories
    analytics/    summary, flows (Sankey), timeseries, timelines (from in-memory rows)
    api/          FastAPI app + routers, all under /api
    snapshot.py   build-time: writes backend/data/atc.db (`make seed`)
    simulation.py runtime: POST /simulate, computed in memory, never stored
    config.py     loads/validates rules.yaml
  tests/          unit/, property/, integration/
frontend/
  src/
    app/          router, providers, layout shell
    components/   ui/ (shadcn), brand/, charts/, shared
    features/     overview, tower, rules-lab, customers, alert-log, about
    lib/          api client, query hooks, formatters, tokens
rules.yaml        single source of rule config (dashboard edits write here)
docs/PLAN.md      approved plan: data model, API contract, pipeline, wireframes
```

## Commands
| Task | Command |
|---|---|
| Install everything | `make setup` |
| Run API + web | `make dev` (API :8000, web :5173, docs at :8000/docs) |
| Rebuild read-only snapshot | `make seed` (writes `backend/data/atc.db`; commit it) |
| All tests | `make test` |
| Lint + format check + types | `make lint` |
| Screenshots (Playwright) | `make screenshots` (needs `make dev`) |
| A11y + interaction QA | `make qa` (needs `make dev`) |
| Backend only | `cd backend && uv run pytest` / `uv run ruff check` / `uv run mypy` |
| Frontend only | `cd frontend && npm run dev` / `npm run typecheck` / `npm run lint` |

## Conventions
- The deployed app is read-only: never write to disk at runtime. Stored runs come from the
  snapshot; simulations are returned, not saved. Rebuild and commit the snapshot after
  changing the engine, simulator or rules.yaml (a test fails if it is stale).
- Engine rules are pure: `apply(request, decision, ctx) -> decision`. No clocks, no
  randomness, no DB inside `atc.engine`. Time and state come in through arguments.
- All times stored in UTC (`datetime` with tz). Convert to the customer's zone only
  inside rules or the UI. Use `zoneinfo` and never fixed offsets.
- Every decision records `decided_by_rule` and a plain-English `reason`.
- Config comes only from `rules.yaml` → `RulesConfig` (Pydantic). No magic numbers in rules.
- Python: ruff defaults + isort, type hints everywhere, snake_case.
- TS: strict mode, function components, feature folders, no `any`. Colors come only from
  design tokens (CSS variables), never hex values in components.
- Red is reserved for critical alerts in the UI.
- Commit after each stage (conventional commit messages).

## Gotchas
- The repo may live in an iCloud-synced folder that marks `.venv` hidden, so Python skips
  the editable-install `.pth`. The Makefile exports `PYTHONPATH=src`; do the same when
  running backend commands by hand.
- shadcn's generated components target React 19. On React 18, any component that Radix
  passes a ref to (via `asChild` or a portal) must use `forwardRef` (see `button.tsx`,
  `sheet.tsx`, `dialog.tsx`), and `CommandDialog` children must be wrapped in `<Command>`.
- `with_overrides` deep-merges, but `PUT /config` and `rules.yaml` replace maps wholesale;
  validators therefore require complete maps.
