# Inflation Dashboard

A web dashboard that tracks consumer inflation from official sources: Brazil first, then the
United States, Colombia and the Eurozone. A Python pipeline fetches, validates and exports the
data. A static React app displays it. The full brief is in [SPEC.md](SPEC.md), and the working
rules are in [CLAUDE.md](CLAUDE.md).

> Status: Phase 1 (Brazil), run manually. Public hosting and automatic updates come in Phase 2.

## Prerequisites

- [uv](https://docs.astral.sh/uv/). It installs and manages Python 3.12 for you (`uv python install 3.12`).
- Node.js 22 or newer (LTS) and npm.
- Optional: the US Census Bureau's X-13ARIMA-SEATS for seasonal adjustment. Install it with
  `uv run python scripts/install_x13.py`, which puts it in `tools/x13/`. Without it, the momentum
  charts say that seasonally adjusted rates are unavailable.

## See the dashboard locally

```sh
uv sync
uv run inflation backfill br     # first time: download all history, validate, export (~10 min)
cd web && npm install && npm run dev   # then open http://localhost:5173
```

After that, `uv run inflation run br` refreshes the last ~13 months, validates and re-exports.
It takes well under a minute.

## Pipeline (Python)

| Command | What it does |
|---|---|
| `inflation fetch br [--full]` | Download raw responses into `raw/br/`, saved unchanged |
| `inflation validate br` | Normalize the raw files and run every check; print the report |
| `inflation compute br` | Validate and compute all metrics without writing anything |
| `inflation export br` | Validate, store (`data/br/`) and write the web JSON (`web/public/data/`) |
| `inflation run br` | Fetch recent data, then export. Nothing is written if a check fails |
| `inflation backfill br` | Same as `run`, but downloads all history |
| `inflation calendar br` | Rewrite `config/calendars/br.csv` from IBGE's release calendar |
| `inflation due` | List releases past their scheduled time and not yet published |

```sh
uv run pytest              # tests (never use the network; recorded fixtures in tests/fixtures/)
uv run ruff format --check . && uv run ruff check .   # format + lint
uv run mypy                # type-check
```

`raw/`, `data/` and `web/public/data/` are generated and gitignored. They are never committed to `main`.

## Web app

```sh
cd web
npm run dev        # http://localhost:5173 (reads web/public/data/)
npm run typecheck
npm test           # page smoke tests with sample fixtures (Vitest)
npm run build      # production build in web/dist
```

## Configuration

- `config/countries.yaml` holds, per country:
  - target and band, timezone and default UI language;
  - the core set, chart start year and enabled flag;
  - which series play which role on the page;
  - the country's color palette.
- `config/calendars/<country>.csv` holds the release schedules.
- Secrets go in `.env` (see `.env.example` for the names) and never in code.

## Documentation

- [docs/sources.md](docs/sources.md): every endpoint and series code, with the date it was verified.
- [docs/methodology.md](docs/methodology.md): formulas, validation checks and tolerances.
- [docs/glossary.md](docs/glossary.md): plain-language definitions.

## Layout

```
config/              countries.yaml, release calendars
src/inflation/       pipeline: cli, pipeline, models, store, validate, export, metrics/, countries/<code>/
tests/               pytest; recorded API responses in tests/fixtures/<country>/
web/                 React + TypeScript + Vite app (ECharts)
docs/                sources, methodology, glossary
scripts/             helper scripts (X-13 installer)
```

## Adding a country

1. Add an entry to `config/countries.yaml` (including its palette) and run or write its calendar CSV.
2. Create `src/inflation/countries/<code>/` with an adapter that implements `CountryAdapter`
   (`src/inflation/countries/base.py`), decorate it with `@register`, and import the package in
   `src/inflation/pipeline.py`.
3. Verify every endpoint live and record it in `docs/sources.md`.
4. Record real responses as fixtures and write a release-replay test.

Nothing country-specific belongs outside `countries/<code>/` and `config/`.
