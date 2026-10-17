# CLAUDE.md — working rules for this repo

**Current phase: 0 (scaffold), then 1 (Brazil).** The owner updates this line as phases close.

The full brief is in `SPEC.md`. Read it before starting any phase, and re-read the section for the phase you're on.

## How we work

- **One phase at a time.**
  - Start a phase with a short plan: files you'll create, data sources you'll touch, open questions. Wait for approval.
  - End a phase with a summary: what was built, how to run it, what was verified, what's left. Then stop.
- **Ask before you guess.** Stop and ask when:
  - a methodology choice is ambiguous
  - a source has changed format or disagrees with another source
  - something the work needs isn't covered by SPEC.md
- Keep the owner learning. When you implement an economic concept (contributions, SAAR, base effects…), explain it in two or three plain sentences in the phase summary.

## Data integrity (non-negotiable)

- Before writing code against any endpoint or series code, query it live and confirm what it returns. Record it in `docs/sources.md`: the URL pattern, the code, what it means, and the date you verified it.
- Never invent, estimate or hard-code data values in application code. Values come from sources, from fixtures (tests) or from config (targets, bands).
- Validation gates publishing. If any check fails, the pipeline stops before export and reports exactly what failed. Never weaken a check to make it pass; report the mismatch instead.
- Tests never call the network. Record real responses as fixtures under `tests/fixtures/<country>/`.

## Where things live

- Country-specific logic goes only in `src/inflation/countries/<code>/` and `config/`. Everything else is country-agnostic.
- Each metric is implemented once, in `src/inflation/metrics/`, and its formula is written down in `docs/methodology.md`. The web app displays numbers; it never computes metrics.
- Units are explicit in names: `_pct` for percent changes, `_pp` for percentage-point contributions or differences.
- Targets, bands, timezones, core sets, chart start years and release dates belong in `config/countries.yaml` or `config/calendars/`, never as literals in code.

## Code conventions

**Python**
- Python 3.12 and `uv`.
- `ruff` for formatting and linting.
- Type hints on public functions; `pytest` for tests.
- Prefer small modules and plain functions; use pydantic models for data shapes and config.
- When a formula or a data quirk isn't obvious, add a comment that ties it to the economics, or points to the relevant section of `docs/methodology.md`.

**Web**
- React, TypeScript and Vite, with ECharts for charts.
- Every user-facing string goes through i18n (`en`, `pt-BR`), including number formatting (decimal comma in Portuguese).
- Colors, spacing and type are CSS-variable design tokens, with light and dark themes.
- Mobile-first. Never use color as the only signal.

**Secrets**
- Secrets live in `.env` locally and in GitHub Actions secrets in CI.
- `.env.example` lists names only.
- Never print or log keys.

## Originality

- Write everything from scratch: code, text, visual design. Don't copy from other repositories, templates or websites.
- Don't base colors, fonts or layouts on any company's branding.
- Open-source libraries are fine. Official data must be credited on the Methodology page.

## Git

- Small commits with clear messages, and keep `main` green.
- Don't commit generated data, exported JSON or web builds to `main`. Canonical data goes to the `data` branch via automation (SPEC §4).
