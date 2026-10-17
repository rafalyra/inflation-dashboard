# Inflation Dashboard — Project Spec

Working name: **Inflation Dashboard** (rename freely). Owner: Rafael.
Spec version: 0.1 · 17 Oct 2026

This document is the brief for building the project with Claude Code. Read it together with `CLAUDE.md`, which has the working rules. Build **phase by phase** (section 9). Each phase ends with a stop for review.

---

## 1. What we are building

A web dashboard that tracks consumer inflation in four economies, added in this order:

1. **Brazil** — IPCA and IPCA-15 (IBGE), with the central bank's target and the market's expectations (BCB).
2. **United States** — CPI (BLS) and PCE (BEA).
3. **Colombia** — IPC (DANE) and the central bank's target (Banco de la República).
4. **Eurozone** — HICP flash and final estimates (Eurostat) and the ECB target.

The dashboard has three core properties:

- **Fast.** Each country refreshes on its own, within minutes of the official release. Release times come from a calendar, so the system knows when to look.
- **Correct.** No number is published unless the pipeline reproduces the official release. If a check fails, nothing is published and the last good version stays online.
- **Explanatory.** For every release it answers six questions:
  - What happened?
  - Was it more or less than expected?
  - How far is it from the central bank's target?
  - What drove it?
  - Is the trend speeding up or slowing down?
  - What happens to the 12-month rate next month?

The owner wants to **learn** how inflation analysis works while building this. So explanations are a feature: each metric has a plain-language definition on the site.

An **AI chat assistant** comes later (Phase 6). It answers questions about the data, using only the project's own numbers.

### Non-goals

- No paywalled data. That means no scraping Bloomberg or Reuters consensus, and no copying content from bank research reports.
- No copying code, text or visual design from other projects. Build from official data sources and documented open-source libraries only.
- No forecasting model in v1. We show expectations published by others; we don't produce our own.

---

## 2. Guiding principles

1. **Official numbers first.** Every displayed value traces back to a source series, a reference period and a release. A methodology page shows that trail.
2. **Validation gates publishing.** Fetch, then normalize, then validate. Only data that passes validation moves on to metrics, export and deploy.
3. **Country-agnostic core, country adapters at the edge.**
   - Each country's quirks live only in its adapter: API formats, codes, language and structural breaks.
   - Everything after normalization works the same for every country: storage, validation framework, metrics, export and frontend.
4. **Each calculation exists in exactly one place.** Metrics are computed in Python, and the frontend only displays them.
5. **Honest about gaps.** If there is no expectation for a release, the UI says so. If a series is short, or a method is approximate (for example US contributions), the UI labels it.
6. **Readable over clever.** The owner is learning, so prefer explicit, well-named steps over abstractions. Docstrings should connect the code to the economics, for example why a formula has the shape it does.

---

## 3. Concepts used throughout (also the seed for the site's "Learn" page)

| Term | Meaning |
|---|---|
| MoM | Month-over-month % change in the price index. |
| 12-month (YoY) | % change versus the same month a year earlier. This is the headline number in the news. |
| YTD | Accumulated change since December of the previous year. |
| NSA / SA | Not seasonally adjusted / seasonally adjusted. SA is needed to read MoM as a trend. |
| SAAR | Seasonally adjusted annualized rate, e.g. 3-month SAAR = ((I_t / I_{t-3})^4 − 1), using an SA index. It shows turning points before the 12-month rate does. |
| Core | A measure that strips out volatile items to show the underlying trend. Each country defines it differently. |
| Contribution (pp) | How many percentage points of the headline change came from a component, roughly weight × change. Contributions add up to the headline. |
| Diffusion | Share of items whose prices rose in the month (by count or by weight). |
| Target band | The central bank's target and tolerance interval. |
| Surprise | Actual minus expected, in pp. |
| Base effect | The 12-month rate next month depends on which month leaves the 12-month window. If the new monthly print is above the one dropping out, the 12-month rate rises. |
| Real policy rate (ex-ante) | (1 + policy rate) / (1 + expected inflation over the next 12 months) − 1. |
| Vintage | The value as first published at a given release, before any revision. |
| Flash / final | A preliminary estimate followed by the definitive one (Eurozone HICP). |

Units must be explicit everywhere. Variables and columns end in `_pct` for percent changes and `_pp` for percentage-point contributions or differences.

---

## 4. Architecture

```
official sources (IBGE, BCB, BLS, BEA, DANE, BanRep, Eurostat, ECB)
        │
        ▼  fetch        country adapter: raw responses saved as-is
        ▼  normalize    country adapter → common data model
        ▼  validate     generic checks + adapter's "answer key" checks  ──✗──► stop, report, keep last good site
        ▼  compute      country-agnostic metrics
        ▼  export       versioned JSON per country + overview + glossary
        ▼  build        static web app (reads JSON)
        ▼  deploy       static hosting
```

### 4.1 Stack (proposed — confirm in Phase 0)

- **Pipeline:** Python 3.12, `uv` for environments, `pandas`, `httpx`, `pydantic` (schemas and config), `pyarrow`, `typer` (CLI), `pytest`, `ruff`.
- **Seasonal adjustment** (only where the source doesn't publish SA):
  - Use X-13ARIMA-SEATS via statsmodels if the Census binary installs reliably in CI; otherwise use STL.
  - Document the choice, and flag the latest SA points as revisable.
- **Web:** React + TypeScript + Vite, with Apache ECharts for charts. It supports target-band shading, treemaps, heatmaps and good tooltips.
- **Hosting:** Cloudflare Pages, a static site with free hosting. Pages Functions will host the AI assistant endpoint later.
- **Automation:** GitHub Actions.
- **Storage:** an orphan `data` branch in the same repo, written only by the bot. It holds the canonical data, vintages and the publish log, partitioned by country and reference month so each release commits only a few small files. Generated JSON and the web build are **not** committed to `main`.

### 4.2 Repository layout

```
inflation-dashboard/
  CLAUDE.md                 working rules for Claude Code
  SPEC.md                   this file
  README.md                 how to run, deploy, add a country
  pyproject.toml
  .env.example              variable names only, no values
  config/
    countries.yaml          per country: timezone, currency, target, band, display names (en/pt-BR), color token, enabled flag
    calendars/              one CSV per country (see 4.4)
    expectations_manual.csv optional hand-entered consensus, with source
  src/inflation/
    cli.py                  `inflation fetch|validate|compute|export|run|due|backfill`
    models.py               pydantic models: Series, Observation, Release, Expectation, ValidationReport
    store.py                read/write canonical partitions and vintages
    calendar.py             which releases are due and not yet published
    validate.py             generic checks; calls the adapter's official checks
    metrics/                one module per family: changes, momentum, contributions, diffusion, target, base_effects, real_rate, surprise
    export.py               JSON for the web app (schema-versioned)
    countries/
      base.py               the adapter interface (4.5)
      br/                   adapter.py, catalog.csv, NOTES.md
      us/  co/  ea/         added in later phases
  tests/
    fixtures/<country>/     recorded API responses (tests never hit the network)
    test_metrics_*.py       hand-computed examples
    test_release_replay_*.py  replay a real release and assert the published numbers
  web/
    src/                    pages, components, i18n (en, pt-BR), design tokens
    public/data/            generated at build time (gitignored)
  docs/
    sources.md              every endpoint and series code, with the date it was verified
    methodology.md          formulas and choices, with reasoning
    glossary.md             plain-language definitions (feeds the Learn page and, later, the assistant)
  .github/workflows/
    ci.yml                  lint, type-check, tests on every push
    release-watch.yml       release-day detection and pipeline (4.6)
    deploy.yml              build web from the data branch and deploy
```

### 4.3 Common data model

**Series catalog** (one CSV per country, `countries/<code>/catalog.csv`):
`series_id` (e.g. `br.ipca.group.food`), `country`, `indicator` (IPCA, IPCA15, CPI, PCE, IPC, HICP), `concept` (headline, core, group, item, diffusion, policy_rate, fx, …), `parent_id`, `level`, `label_en`, `label_pt`, `source`, `source_code`, `unit`, `frequency`, `adjustment` (nsa / official_sa / own_sa).

**Observations** (canonical store):
`series_id`, `period` (YYYY-MM), `value`, `unit`, `release_id`, `fetched_at_utc`.

**Releases** (from the calendar plus detection):
`release_id`, `country`, `indicator`, `reference_period`, `scheduled_utc`, `detected_utc`, `status` (scheduled / published / failed).

**Expectations:**
`country`, `indicator`, `reference_period`, `measure` (mom_pct / yoy_pct / year_end_pct / next_12m_pct), `statistic` (median / mean), `value`, `n_respondents`, `source`, `survey_date`, `captured_at_utc`.

- Several sources can coexist for the same release. `countries.yaml` names the primary source shown on the card; the others appear in the tooltip.

**Vintages:** at each release, freeze the headline numbers as first published, so surprises and later revisions stay traceable.

### 4.4 Release calendar

One CSV per country in `config/calendars/`:
`release_id, indicator, reference_period, release_date, release_time_local, timezone, source_url`

- Seed each calendar from the official agency calendar.
- Warn on the site and in CI when a calendar has fewer than 60 days of future dates left.

### 4.5 Country adapter interface

Each adapter implements:

- `fetch(since)` — download the raw responses and save them unchanged.
- `normalize()` — turn the raw data into catalog series and observations, and handle structural breaks such as basket or classification changes.
- `latest_reference_period()` — the newest period actually available at the source. Used to detect whether a release has landed.
- `official_checks()` — the "answer key": values the agency itself published for the latest release, which validation compares against.
- `fetch_expectations()` and `fetch_context()` — expectations, policy rate and FX.

Nothing country-specific may exist outside `countries/<code>/` and `config/`.

### 4.6 Release-day automation

`release-watch.yml` runs on a schedule every 5 minutes, but only inside UTC windows that cover the release times. The windows are configurable; initially they are roughly 09:00–15:00 UTC and 22:00–24:00 UTC on weekdays. On each run:

1. Run `inflation due`: list releases that are past their scheduled time, not yet published, and less than 12 hours old. If there are none, exit within seconds.
2. For each due release, check `latest_reference_period()`. If the new period hasn't appeared yet, exit; the next run retries.
3. If it has appeared, fetch, normalize, validate, compute and export for that country. Then commit the new partitions to the `data` branch and trigger `deploy.yml`.
4. If validation fails, publish nothing. Open a GitHub issue containing the validation report, and keep the previous site online.

Notes:

- GitHub's scheduled runs can start several minutes late, which is acceptable for v1.
- Upgrade path for faster updates: a Cloudflare Worker cron fires at the exact release minute and calls the workflow's `workflow_dispatch`.
- Keep the repo public, or watch Actions minutes, because frequent short runs add up on private repos.

---

## 5. What the dashboard shows

The interface is bilingual from day one: English and Brazilian Portuguese, toggled in the header. All strings live in i18n files.

### 5.1 Overview (home)

- One card per enabled country, showing:
  - headline 12-month rate, MoM and core 12-month rate
  - a target status chip (inside band / above / below)
  - date of the last release
  - countdown to the next release
- A "latest releases" feed across countries.
- From two countries onward, a cross-country chart of headline 12-month rates, each with its own target band.

### 5.2 Country page (same skeleton for every country; country-specific panels where noted)

1. **Release snapshot**
   - Headline MoM and 12-month, plus core.
   - Actual vs expected (surprise in pp, with the expectation source).
   - Distance from target.
   - One factual sentence generated from a template, with no AI. Example: "Prices rose 0.82% in September; electricity contributed most."
2. **Drivers**
   - Contributions by group for the latest month (pp, sorted).
   - Top 5 items pushing up and top 5 holding down.
   - Stacked 12-month contributions by group over time.
3. **Underlying trend**
   - Core measures: Brazil shows the average of a configurable set plus its min–max range.
   - Services vs goods.
   - Diffusion.
   - Brazil only: free vs administered prices.
4. **Momentum**
   - 3-month and 6-month SAAR against the 12-month rate.
   - This month's MoM compared with the same calendar month in past years (median and range).
5. **Base effects**
   - The monthly prints that drop out of the 12-month window over the next 3 months.
   - The 12-month rate implied for next month if the new print equals the expectation.
6. **Policy and markets**
   - Policy rate and real ex-ante rate.
   - Inflation expectations (next 12 months and year-end).
   - The currency against the USD, with its 12-month change. Pass-through matters for Brazil and Colombia.
7. **History**
   - Headline and core 12-month rates since 2010, with the target band shaded.
   - Brazil: a counter of consecutive months outside the band (see 6.1).

### 5.3 Compare (from Phase 3)

- Headline and core 12-month rates, gap to target, and real policy rates, side by side.
- A caveats panel that explains why the indices aren't identical:
  - US CPI includes owners' equivalent rent; the HICP excludes owner-occupied housing.
  - Coverage differs between countries.
  - Core definitions differ.
  - Seasonal adjustment differs.

### 5.4 Learn

- Plain-language explanations of every concept in section 3.
- Each explanation is illustrated with a live example from the latest data, e.g. "this month, food contributed X pp…".
- A short "how to read an inflation release" walkthrough.

### 5.5 Methodology and sources

- For every country: sources, series codes, release times, last validation result and time, and known limitations.

### 5.6 Visual identity

- Original design. Don't base the palette or typography on any company's brand.
- Proposed direction (confirm with the owner):
  - Calm neutral background, one accent color per country, and a separate pair of colors for "above / below expectation".
  - IBM Plex Sans for text and IBM Plex Mono or tabular figures for numbers.
- Light and dark mode, defined as CSS-variable design tokens.
- Mobile-first layout; color is never the only signal.
- Numbers use 2 decimals for % and pp. The decimal separator follows the UI language (0.82 in English, 0,82 in Portuguese).

---

## 6. Country details

**Every series code and endpoint below is a starting point. Verify each one against the live source before coding against it, and record the verification in `docs/sources.md` with the date.**

### 6.1 Brazil (Phase 1)

**Release events (both from IBGE, 09:00 Brasília time):**
- **IPCA**, monthly, around the 10th of the following month.
- **IPCA-15**, the mid-month preview, around the 25th. Price collection runs from about the 16th of the previous month to the 15th of the reference month.

**Sources:**

- **IBGE SIDRA API** (`apisidra.ibge.gov.br/values/...`; metadata at `servicodados.ibge.gov.br/api/v3/agregados/{table}/metadados`)
  - IPCA from Jan 2020: table **7060**, which covers the general index, groups, subgroups, items and subitems. Variables: **63** monthly %, **69** YTD %, **2265** 12-month %, **66** monthly weight.
  - IPCA Jan 2012–Dec 2019 (previous basket): table **1419**, same structure.
  - Long-run general index: table **1737**.
  - IPCA-15 from 2020: table **7062**.
  - Handle the classification breaks of Jan 2012 and Jan 2020 explicitly. Map groups across baskets where possible, and mark items that start or end.
- **BCB SGS API** (`api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json`; paginate by date range if a request is capped)
  - **433** IPCA monthly %; **13522** IPCA 12-month %.
  - Core measures, per BCB Technical Note 57 (Dec 2025), which extended the series back to 1991. The current versions **keep the long-standing codes**:
    - **4466** MS (trimmed mean, smoothed)
    - **11427** EX0
    - **16121** EX1
    - **27838** EX2
    - **27839** EX3
    - **16122** DP
    - **28751** EX-FE
    - **11426** MA
    - **28750** P55
    - New series: **29683** EX3 services and **29684** EX3 industrial goods.
    - Do **not** use codes 29675–29682. They hold the old versions and are no longer updated.
  - **21379** diffusion index.
  - Free prices, administered prices, services, industrial goods and food at home: look up the current codes in SGS.
  - **432** Selic target. USD/BRL (PTAX): look up the code.
- **BCB Olinda OData — Expectativas** (Focus survey)
  - Monthly IPCA expectations (median, mean, respondents) by survey date and reference month; 12-month-ahead expectations; year-end expectations.
  - Check entity and field names via `$metadata`.
  - The "expected" value for a release is the latest Focus survey dated **before** the release timestamp.

**Target:**
- 3%, tolerance ±1.5 pp (band 1.5%–4.5%).
- **Continuous target since 2025:** the target counts as missed when 12-month IPCA stays outside the band for 6 consecutive months, and the BCB must then explain itself in an open letter.
- Show a counter of consecutive months outside the band, and the status.

**Brazil-specific panels:**
- The 9 groups, with labels in both languages:
  - Alimentação e bebidas / Food & beverages
  - Habitação / Housing
  - Artigos de residência / Household articles
  - Vestuário / Apparel
  - Transportes / Transport
  - Saúde e cuidados pessoais / Health & personal care
  - Despesas pessoais / Personal expenses
  - Educação / Education
  - Comunicação / Communication
- Free vs administered prices.
- Core average: configurable set, default EX0, EX3, MS, DP, P55. Confirm against current BCB usage.
- IPCA-15 shown as the preview for the month.

**Validation answer key (examples):**
- The 12-month rate computed from the chained monthly series matches variable 2265 within tolerance.
- The sum of weight × change over the 9 groups matches the headline MoM.
- SGS 433 equals the SIDRA headline.
- The latest period equals the calendar's expected reference period.
- Tolerance is set by published precision (2 decimals → 0.01 pp).

**Known anchors for release-replay tests** (from IBGE releases; confirm against the official tables):
- **IPCA Sep 2026** (released 9 Oct 2026):
  - +0.82% MoM, after −0.32% in Aug 2026; YTD 3.95%.
  - All 9 groups rose, and residential electricity was the main driver.
- **IPCA-15 Sep 2026:** +0.70% MoM, 12-month 4.47%.
- **IPCA Oct 2025:** +0.09%. This is the month that drops out of the window at the next release, which makes a useful base-effect example.

### 6.2 United States (Phase 3)

**Release events:**
- CPI from BLS at 08:30 ET; the schedule is on bls.gov and also published as an `.ics` feed.
- PCE from BEA, later in the month.

**Sources:**
- **BLS Public Data API v2.** It needs a free key that must be renewed yearly; it allows 50 series per request. Starting series IDs (verify):
  - All items: `CUSR0000SA0` (SA), `CUUR0000SA0` (NSA)
  - Core: `CUSR0000SA0L1E` (SA), `CUUR0000SA0L1E` (NSA)
  - Food `CUSR0000SAF1`, energy `CUSR0000SA0E`, shelter `CUSR0000SAH1`
  - Core goods `CUSR0000SACL1E`, core services `CUSR0000SASLE`
  - Services less rent of shelter `CUSR0000SASL2RS`. This is one common "supercore" proxy; definitions vary, so label it.
  - Weights: BLS relative importance tables. US contributions are an approximation; label them as such.
- **Convention:** headline MoM uses SA data; the 12-month rate uses NSA data. Both appear in the snapshot.
- **PCE:** BEA, or FRED (`PCEPI`, `PCEPILFE`). The Fed's 2% target is defined on **PCE**, not CPI. The US page shows the 2% line on the PCE chart, and the CPI chart notes this.
- **Policy:** fed funds target range (FRED `DFEDTARU` / `DFEDTARL`).
- **Expectations:** there is no free consensus.
  - Capture the Cleveland Fed inflation nowcast before each release.
  - Allow manual consensus entries with a source.
  - Market-based: FRED `T5YIE`, `T10YIE`, `T5YIFR`.
  - Survey: University of Michigan 1-year expectations.

**Live test:** October 2026 CPI, released 10 Nov 2026 at 08:30 ET.

### 6.3 Colombia (Phase 4)

**Why it's interesting now (context as of Oct 2026; verify before using):**
- 12-month inflation rose to **6.29%** in September 2026 (+0.37% MoM, YTD 5.74%), about double the 3% target.
- Banco de la República surprised the market with a 25 bp hike to **12.25%** on 30 Sep 2026.
- The peso rallied strongly in mid-2026. Reasons cited include high carry and optimism about the new government; President Abelardo de la Espriella took office on 7 Aug 2026.
- FX pass-through and policy-rate panels matter most here.

**Release:**
- DANE IPC, early in the following month. Recent releases have come out in the evening, Bogotá time; confirm the exact time on DANE's calendar.

**Sources (data access is the main risk; investigate first):**
- **DANE:** IPC by the 12 COICOP divisions, with weights, published in Excel annexes. Expect to parse spreadsheets. Look for machine-readable alternatives on datos.gov.co.
- **BanRep SUAMECA:**
  - Policy rate (series page 59).
  - TRM USD/COP (series page 1).
  - Core measures such as ex-food and ex-food-and-regulated items: verify what is available and how to download it programmatically.
- **BanRep's monthly survey of economic analysts:** expectations for monthly and 12-month inflation.

**Target:** 3% ±1 pp.

**Colombia-specific panel:**
- Exchange-rate pass-through: USD/COP 12-month change against goods inflation.
- A note on indexation: many prices are adjusted by the previous year's inflation, which makes inflation sticky.

**Anchors for release-replay tests:** Sep 2026 IPC, +0.37% MoM, 6.29% 12-month, YTD 5.74%.

### 6.4 Eurozone (Phase 5)

**Releases:** the HICP **flash** estimate comes at 11:00 CET, around the last working day of the reference month or just after. The **final** HICP follows about two weeks later.
- Treat these as two release events.
- Store the flash as a vintage and show any revision when the final arrives.

**Sources:**
- **Eurostat dissemination API** (JSON-stat). Verify the dataset codes for monthly and annual rates, weights and flash estimates.
- Main aggregates: energy; food, alcohol & tobacco; non-energy industrial goods; services.
- Core = HICP excluding energy, food, alcohol & tobacco.
- Optional breakdown for Germany, France, Italy and Spain.
- **ECB Data Portal API:** deposit facility rate, EUR/USD reference rate, the Survey of Professional Forecasters and the Consumer Expectations Survey.

**Target:** 2%, symmetric, over the medium term (no formal band; show the target line only).

---

## 7. Testing and quality

- **No network in tests.** Every adapter has recorded fixtures.
- **Metric unit tests** use small hand-computed cases:
  - 12-month rate from a monthly chain
  - SAAR
  - contributions summing to the headline
  - base-effect identity
  - consecutive-months-outside-band counter
  - real rate
- **Release-replay tests** per country use a frozen copy of a real release and assert that the published headline numbers come out (anchors in section 6).
- **Web:** type-check, plus a smoke test that each page renders with sample data.
- **CI** runs lint, type-check and tests on every push. Deploy only from a green `main`.

---

## 8. Configuration and secrets

- **`.env` locally and GitHub Actions secrets in CI.** `.env.example` lists names only:
  - `BLS_API_KEY`
  - `CLOUDFLARE_API_TOKEN`
  - `CLOUDFLARE_ACCOUNT_ID`
  - later: `ANTHROPIC_API_KEY`, `ASSISTANT_ENABLED`, assistant limits
- Keys never appear in code, logs or exported JSON.
- **`config/countries.yaml`** holds everything a human adjusts without touching code:
  - timezone, target and band
  - primary expectation source
  - default core set
  - chart start year
  - enabled flag

---

## 9. Phased plan

Each phase begins with a short plan from Claude Code, approved by the owner. Each phase ends with a summary:
- what was built
- how to run it
- what was verified
- what's left

Then **stop**.

### Phase 0 — Scaffold

- Repo, tooling, CLI skeleton, pydantic models, config loader, adapter interface.
- CI workflow.
- Empty web app with routing, i18n (en, pt-BR), design tokens, light/dark mode, and an Overview page that renders from a sample JSON.
- **Done when:** `uv run pytest` and `npm run build` pass, CI is green, and the README explains how to run both.

### Phase 1 — Brazil, end to end (run manually)

1. Verify the sources and write `docs/sources.md`.
2. Backfill history:
   - IPCA headline from 1995, groups and items from 2012
   - IPCA-15, cores, diffusion, free/administered
   - Focus expectations, Selic, USD/BRL
3. Normalize, including the basket breaks.
4. Validation with the Brazil answer key.
5. All metrics in section 5.2.
6. JSON export.
7. Web: Overview (Brazil only), Brazil page, Learn and Methodology, in both languages.
8. `docs/methodology.md` and `docs/glossary.md`.

**Done when:**
- The Sep 2026 IPCA and IPCA-15 replays pass.
- Contributions sum to the headline within tolerance.
- `inflation run br` rebuilds everything from scratch.
- The site runs locally.

### Phase 2 — Brazil automated and live

- Brazil calendar, `release-watch.yml`, the `data` branch, `deploy.yml` to Cloudflare Pages.
- Failure handling: a GitHub issue opens, and the last good site stays live.

**Done when:** a real release appears on the live site without anyone running anything.
- First chance: IPCA-15 for October, on 23 Oct 2026.
- Fallback test: IPCA for October, on 12 Nov 2026.

### Phase 3 — United States

- US adapter, CPI and PCE, Fed context, expectations as in section 6.2, and the US calendar.
- First version of the Compare page.

**Done when:** the US replay tests pass, and the 10 Nov 2026 CPI goes live automatically.

### Phase 4 — Colombia

- Investigate data access first, and report options to the owner before building.
- Then build the adapter, the Colombia-specific panels and the calendar.

### Phase 5 — Eurozone

- Flash and final releases, the vintage/revision display, ECB context, and the calendar.

### Phase 6 — AI chat assistant (the detailed design is agreed with the owner before starting)

**Goal:** a chat panel on the site that answers questions about any country and release ("what drove Brazil's September IPCA?", "is US core speeding up?"), in the user's language.

**Requirements:**
- **Architecture:**
  - A server-side endpoint on Cloudflare Pages Functions calls the Claude API through Anthropic's official SDK.
  - The API key lives only on the server.
  - The model ID comes from an environment variable, defaulting to `claude-sonnet-5-5`.
  - Check docs.claude.com for current SDK usage.
- **Grounded answers:**
  - The model reads data only through tools that query the exported JSON: release summaries, series lookup, contributions, expectations, glossary and methodology.
  - It never states a number that didn't come from a tool result in that conversation.
  - When data doesn't exist (for example, no expectation recorded), it says so.
- **UI link:** the assistant can open the relevant country page or section and highlight the series it is talking about.
- **Controls:**
  - per-IP rate limit
  - token cap per answer
  - a monthly spend ceiling
  - a kill switch (`ASSISTANT_ENABLED=false`) that hides the chat without affecting the dashboard
- **Evaluation:** a set of about 20 questions with known answers from the data, run before launch and after every prompt or tool change.

### Backlog (later)

- Release alerts by email or Telegram.
- A 12-month heatmap of components.
- A revision tracker.
- Shareable PNG cards for a release.
- Brazil breakdown by metro area.
- More countries.

---

## 10. Open decisions (defaults applied; the owner can change them)

| Decision | Default in this spec |
|---|---|
| Code and docs language | English |
| UI languages | English + Brazilian Portuguese; default language set in config |
| Delivery | Website only (no single offline file) |
| Hosting | Cloudflare Pages (alternatives: Vercel; GitHub Pages without the assistant) |
| Repo visibility | Public (keeps Actions minutes free) |
| Visual direction | Section 5.6 proposal |
| Owner's design and feature preferences | To be added before Phase 1 web work |
