# Inflation Dashboard

A web dashboard that tracks consumer inflation from official sources: Brazil first, then the
United States, Colombia and the Eurozone. A Python pipeline fetches, validates and exports the
data. A static React app displays it. The full brief is in [SPEC.md](SPEC.md), and the working rules are in
[CLAUDE.md](CLAUDE.md).

> Status: Phase 0 (scaffold). The pipeline commands exist but don't fetch data yet. The web app
> renders **sample data** that is clearly labelled as such.

## Prerequisites

- [uv](https://docs.astral.sh/uv/). It installs and manages Python 3.12 for you (`uv python install 3.12`).
- Node.js 22 or newer (LTS) and npm.

## Pipeline (Python)

```sh
uv sync                    # create .venv and install dependencies
uv run inflation --help    # list commands
uv run inflation due       # releases past their scheduled time and not yet published
uv run pytest              # tests (never use the network)
uv run ruff format --check . && uv run ruff check .   # format + lint
uv run mypy                # type-check
```

Commands: `fetch`, `validate`, `compute`, `export`, `run`, `backfill` (each takes a country code,
e.g. `br`) and `due`. In Phase 0 all of them except `due` exit with "not implemented".

## Web app

```sh
cd web
npm install
npm run dev        # http://localhost:5173
npm run typecheck
npm test           # smoke tests (Vitest)
npm run build      # production build in web/dist
```

The Overview reads `web/public/sample/overview.json`. From Phase 1 on, the pipeline's export
goes to `web/public/data/`, which is gitignored and never committed to `main`.

## Configuration

- `config/countries.yaml` holds, for each country: target and band, timezone, default UI language, core set, chart
  start year and enabled flag.
- `config/calendars/<country>.csv` holds the release schedules.
- Secrets go in `.env` (see `.env.example` for the names) and never in code.

## Layout

```
config/              countries.yaml, release calendars
src/inflation/       pipeline: cli, models, config, calendar, metrics/, countries/<code>/
tests/               pytest; recorded API responses in tests/fixtures/<country>/
web/                 React + TypeScript + Vite app
docs/                sources, methodology, glossary
```

## Adding a country

1. Add an entry to `config/countries.yaml` and a calendar CSV.
2. Create `src/inflation/countries/<code>/` with an adapter that implements `CountryAdapter`
   (`src/inflation/countries/base.py`) and decorate it with `@register`.
3. Record real responses as fixtures and write a release-replay test.

Nothing country-specific belongs outside `countries/<code>/` and `config/`.
