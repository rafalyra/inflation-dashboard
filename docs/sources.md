# Data sources

Every endpoint and series code the pipeline uses is listed here. Each entry is verified against the
live source before any code is written against it (see CLAUDE.md, "Data integrity").
**Status:** ✅ verified live · ⏳ not yet verified (code written to the documented format, but the
pipeline won't publish until it is verified).

## Brazil

### IBGE SIDRA: IPCA and IPCA-15

URL pattern: `https://apisidra.ibge.gov.br/values/t/{table}/n1/all/v/{variable}/p/{YYYYMM}-{YYYYMM}/c315/all`
Metadata: `https://servicodados.ibge.gov.br/api/v3/agregados/{table}/metadados`. This host was
unreachable on 2026-10-22, both from this machine and from GitHub's runners. The pipeline therefore
doesn't call it at fetch time: each table's first month is fixed in the adapter, from metadata read on
2026-10-17/18. The newest month is asked of the values API itself (`/p/last%201`).
Classification 315 = general index (category 7169), 9 groups, subgroups, items, subitems.

| Table | Covers | Variables | Status |
|---|---|---|---|
| 7060 | IPCA, Jan 2020 → (POF 2017–18 basket); 457 categories | 63 monthly %, 69 YTD %, 2265 12-month %, 66 monthly weight | ✅ 2026-10-17 |
| 1419 | IPCA, Jan 2012 – Dec 2019 (POF 2008–09 basket); 464 categories, metadata has no levels | 63, 69, 2265, 66 (same as 7060) | ✅ 2026-10-18 |
| 1737 | IPCA headline, Dec 1979 → | 2266 index (Dec 1993 = 100), 63, 2263 (3 m), 2264 (6 m), 69, 2265 | ✅ 2026-10-18 |
| 7062 | IPCA-15, Feb 2020 →; 447 categories | 355 monthly %, 356 YTD %, 1120 12-month %, 357 monthly weight | ✅ 2026-10-17 |

Group category ids are the same in tables 7060, 1419 and 7062: 7170 Food & beverages, 7445 Housing,
7486 Household articles, 7558 Apparel, 7625 Transport, 7660 Health & personal care, 7712 Personal
expenses, 7766 Education, 7786 Communication.

Response quirks: the first JSON element is a header row naming the columns. Special values follow
IBGE's conventions: `-` is a true zero, while `..`, `...` and `X` mean the value doesn't exist (items outside
their basket) or is suppressed.

### IBGE release calendar

`https://servicodados.ibge.gov.br/api/v3/calendario/{product}?de=MM-DD-YYYY&ate=MM-DD-YYYY&qtd=500`
(✅ 2026-10-18). Products: **9256** IPCA, **9260** IPCA-15. (9262 is "IPCA Especial", which we don't use.)
Times are listed as `12:00:00` for releases IBGE makes at 09:00 Brasília time, so we read them as UTC.
`inflation calendar br` rewrites `config/calendars/br.csv` from this API. The same
`servicodados` host failed from GitHub's runners on 2026-10-22, so for now the calendar is
refreshed locally and committed. Revisit this in Phase 2.

### BCB SGS: cores, context and the SGS copy of IPCA

URL pattern: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json&dataInicial=DD/MM/YYYY&dataFinal=DD/MM/YYYY`
(`/dados/ultimos/{n}` also works). Rows look like `{"data": "01/09/2026", "valor": "0.82"}`.

| Code | Meaning | Status |
|---|---|---|
| 433 | IPCA monthly % (copy of SIDRA) | ✅ 2026-10-17 (Sep 2026 = 0.82) |
| 13522 | IPCA 12-month % | ✅ 2026-10-17 (Sep 2026 = 4.58) |
| 4466 | Core MS, smoothed trimmed mean | ✅ 2026-10-17 |
| 11426 | Core MA, unsmoothed trimmed mean | ✅ 2026-10-17 |
| 11427 | Core EX0 (ex food at home and administered) | ✅ 2026-10-17 |
| 16121 | Core EX1 | ✅ 2026-10-17 (first request returned an HTML error, the retry worked) |
| 27838 | Core EX2 | ✅ 2026-10-17 |
| 27839 | Core EX3 | ✅ 2026-10-17 |
| 16122 | Core DP, double weighting | ✅ 2026-10-17 |
| 28751 | Core EX-FE | ✅ 2026-10-17 |
| 28750 | Core P55 | ✅ 2026-10-17 |
| 29683 | EX3 services (new, Technical Note 57) | ✅ 2026-10-17 |
| 29684 | EX3 industrial goods (new) | ✅ 2026-10-17 |
| 21379 | Diffusion index | ✅ 2026-10-17 (Sep 2026 = 54.91) |
| 432 | Selic target, daily (includes future-dated rows until the next meeting) | ✅ 2026-10-17 |
| 11428 | IPCA free prices ("itens livres") | ✅ 2026-10-22 (Sep 2026 = 0.55) |
| 4449 | IPCA administered prices ("preços monitorados – total") | ✅ 2026-10-22 (Sep 2026 = 1.59) |
| 10844 | IPCA services | ✅ 2026-10-22 (Sep 2026 = 0.61) |
| 1 | USD/BRL, free market, sell, daily | ✅ 2026-10-22 (22 Oct 2026 = 5.0383) |
| — | IPCA industrial goods | Not used. 27863 returns data but its metadata page was down on 2026-10-22, so its meaning is unconfirmed. The "services vs goods" panel uses the verified EX3 pair 29683/29684 instead. |

Food at home comes from SIDRA (subgroup 11, "Alimentação no domicílio"), so it needs no SGS code.

**Availability (2026-10-18 to 22):**
- After about 30 probe requests over two days, every SGS request from this machine started returning
  HTTP 200 with either an HTML "Requisição inválida" page or
  `{"erro":{"statusCode":500,"detail":"Internal error"}}`. Access came back by 2026-10-22.
- The client now treats both responses as failures. It throttles SGS to one request every 3 s and
  backs off for 20 s, 60 s, 180 s… between retries.
- From GitHub's runners (the manual "Source health" workflow, 2026-10-22), SGS, SIDRA and Focus all
  answered normally.

### BCB Olinda: Focus market expectations

Base: `https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/` (✅ 2026-10-18).
Filters must be percent-encoded with `%20` for spaces, because Olinda reads `+` literally.

| Entity | Use | Key fields |
|---|---|---|
| `ExpectativaMercadoMensais` | Expected IPCA for a month | `Indicador`, `Data` (survey date), `DataReferencia` (`MM/YYYY`), `Mediana`, `Media`, `numeroRespondentes`, `baseCalculo` |
| `ExpectativasMercadoInflacao12Meses` | IPCA over the next 12 months | same, plus `Suavizada` (`S`/`N`) |
| `ExpectativasMercadoAnuais` | IPCA for a calendar year | same, `DataReferencia` = `YYYY` |

`baseCalculo` 0 = forecasts from the last 30 days (the published Focus report's figure, our
primary); 1 = the last 5 business days. Monthly IPCA history starts in Jan 2000. The monthly
entity also has `IPCA Administrados`, `IPCA Livres`, `IPCA Serviços`, `IPCA Bens industrializados`
and `IPCA Alimentação no domicílio`. **There is no IPCA-15 expectation in Focus**, so the IPCA-15 card
will say none is available.

Check value: the last 30-day survey before the Sep 2026 IPCA release (dated 2026-10-08) has a
median of 0.60% from 136 respondents. The actual print was 0.82%.
