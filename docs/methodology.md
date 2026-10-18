# Methodology

Each metric is implemented once, in `src/inflation/metrics/`. Its formula and the reasoning
behind it are written down here. The web app only displays the results.

## Conventions

- Names end in `_pct` for percent changes and `_pp` for percentage-point contributions or differences.
- Percent and pp values are shown with 2 decimals. The decimal separator follows the UI language.
- Reference periods are calendar months written `YYYY-MM`. Timestamps are stored in UTC.

## Validation: how we know our numbers match the official ones

Nothing is stored or published unless every check passes. The generic checks run for every
country:

- the data follows the schema: known units, valid months, no duplicates, UTC timestamps;
- every series is in the catalog;
- headline series have no missing months;
- expectations aren't dated after we captured them.

Each country then adds an "answer key" of checks against what its agency published.

### Tolerance

Agencies publish rates with 2 decimals, so a value we *derive* from other published values can
differ from the published one by rounding. The tolerance is **0.01 pp**, one unit in the last
published digit (SPEC §6.1). Two copies of the *same* published number, such as IBGE's figure and
the BCB's copy of it, must match exactly.

### Brazil answer key

| Check | What it means | Largest gap seen (Oct 2026 analysis) |
|---|---|---|
| Latest month equals the calendar | The newest IPCA / IPCA-15 month is the one the calendar says was last released | — |
| 12-month rate from chained months | (1+m₁)(1+m₂)…(1+m₁₂) − 1 over the 12 latest monthly prints equals the published 12-month rate | 0.0049 pp (IPCA), 0.0051 (IPCA-15), last 24 months |
| 12-month rate from the index | I_t / I_{t−12} − 1 using the index number equals the published 12-month rate | 0.0091 pp since 1995 |
| YTD from chained months | Same idea, from January to the latest month | within 0.01 |
| 9 groups add up to the headline | Σ weight × change / 100 over the 9 groups equals the headline monthly change | 0.0066 pp (IPCA 2012–2026), 0.0072 (IPCA-15) |
| Group weights sum to 100 | | 0.0003 |
| SGS copy matches IBGE | The BCB's copies of the monthly and 12-month IPCA (SGS 433, 13522) match SIDRA exactly | — |
| SGS series are current | Cores, diffusion, free and administered prices reach the latest IPCA month | — |
| Tables agree on overlap | Tables 7060/1419 and the long-run table 1737 publish identical headline values | 0 (509 values) |

The 12-month check is applied to the latest month only. Chaining rounded monthly prints works
well at today's inflation rates, but drifts by up to 0.14 pp in the early-1990s hyperinflation,
when monthly rates were tens of percent. That's a property of rounding, not of the data.

## Expectations

- **Brazil.** The "expected" value for a release is the median of the BCB Focus survey, using the forecasts
  submitted over the last 30 days (`baseCalculo = 0`, the figure in the published report). We take
  the latest survey dated before the release day. The 5-day median is shown as a secondary figure.
- **12-month-ahead expectations** use the smoothed series (`Suavizada = S`), as the BCB does for its
  ex-ante real rate.
