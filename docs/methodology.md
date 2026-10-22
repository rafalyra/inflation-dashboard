# Methodology

Each metric is implemented once, in `src/inflation/metrics/`. Its formula and the reasoning
behind it are written down here. The web app only displays the results.

## Conventions

- Names end in `_pct` for percent changes and `_pp` for percentage-point contributions or differences.
- Percent and pp values are shown with 2 decimals. The decimal separator follows the UI language.
- Reference periods are calendar months written `YYYY-MM`. Timestamps are stored in UTC.
- When an input is missing (no survey, too little history for seasonal adjustment), the export
  says so (`null` plus a reason) and the page shows that. Nothing is estimated to fill a gap.

## Changes (`metrics/changes.py`)

Monthly rates compound. Two months of +1% is a 2.01% rise, not 2%.

- **12-month change:** (1 + m₁/100)(1 + m₂/100)…(1 + m₁₂/100) − 1, over the latest 12 months.
- **Year to date:** the same product from January to the latest month.
- **From an index:** I_t / I_{t−k} − 1. This is the most precise method when the agency publishes an
  index number, because it avoids compounding rounded monthly rates.

The published 12-month and year-to-date rates are always displayed as published. These formulas
are used for validation, and for series that only exist as monthly rates (the BCB core measures).

## Core measures (`metrics/cores.py`)

Each core measure removes volatility differently: by excluding items (EX0–EX3, EX-FE), by trimming
the extremes of the price-change distribution (MS, MA, P55), or by reweighting by volatility (DP).

- The page shows the **average of a configured set**. The default is EX0, EX3, MS, DP and P55
  (`config/countries.yaml`).
- It also shows the **range (min–max)** across that set. A narrow range means the measures agree.
- 12-month core rates are compounded from the BCB's monthly series. The average uses only months
  where every member exists.

## Contributions (`metrics/contributions.py`)

**Monthly.** A component's contribution, in pp, is its weight × its change / 100. A group with a
20% weight whose prices rose 1% added 0.20 pp to the headline.

IBGE's "peso mensal" for month t is the weight that goes with month t's change. Using it, the 9
groups reproduce the headline within 0.0066 pp across 2012–2026. Using the previous month's
weights misses by up to 0.04 pp.

**Over 12 months.** Summing 12 monthly contributions does not give the 12-month rate, because of
compounding. The exact decomposition follows from the identity

    Y = Π(1 + h_s) − 1 = Σ_s h_s · Π_{k<s}(1 + h_k)

So component i's share of the 12-month rate is Σ_s c_{i,s} · Π_{k<s}(1 + h_k): each month's
contribution, scaled by how much prices had already risen earlier in the window.

- These shares add up exactly to Y when the monthly contributions add up to the headline.
- The small difference left by IBGE's rounding is shown separately as "rounding", not hidden.
- For readability, the stacked chart keeps at most 8 series. The smallest groups (by latest weight)
  are summed into "Other", and the page names which groups those are.

**Top movers.** These are the 5 largest positive and the 5 largest negative item-level (IBGE level
3) contributions in the latest month.

## Momentum (`metrics/momentum.py`, `metrics/seasonal.py`)

The 12-month rate turns slowly. Annualizing a shorter, seasonally adjusted window shows turning
points earlier:

    SAAR_k = (I_t / I_{t−k})^(12/k) − 1, on a seasonally adjusted index, for k = 3 and 6

**Seasonal adjustment** uses the US Census Bureau's X-13ARIMA-SEATS. The program is called directly,
with this setup:
- a log transform, because seasonal effects on prices are proportional;
- automatic ARIMA model selection;
- automatic outlier detection, so one-off shocks don't distort the seasonal factors.

Seasonal factors are estimated from 10 years of history before the chart start. The latest 12
adjusted values are revised as new months arrive, and the page labels them as revisable.
`scripts/install_x13.py` installs the program. Without it, the page says that seasonally adjusted
rates are unavailable.

**Same month in past years.** This compares this month's change with the same calendar month in the
previous 10 years (median and range), so seasonal months are compared like with like.

## Target (`metrics/target.py`)

- **Status:** above, inside or below the tolerance band. The band edges count as inside.
- **Distance:** 12-month rate − target, in pp.
- **Months outside the band:** consecutive months, ending with the latest, outside the band.
  Brazil's continuous target counts as missed at 6 (`config/countries.yaml`).

## Base effects (`metrics/base_effects.py`)

The 12-month window moves forward one month at a time:

    1 + Y_{t+1} = (1 + Y_t) · (1 + m_{t+1}) / (1 + m_{t−11})

The page lists the month that leaves the window at each of the next three releases. It also shows the 12-month
rate implied for next month if the new print equals the latest expectation.

## Real interest rate (`metrics/real_rate.py`)

    ex-ante real rate = (1 + policy rate) / (1 + expected inflation over the next 12 months) − 1

- The expectation is the smoothed 12-month-ahead Focus median, the same one the BCB uses.
- The history chart pairs the policy rate at each month end with the latest survey of that month.

## Surprise (`metrics/surprise.py`)

Surprise = actual − expected, in pp.

- **Brazil.** The "expected" value is the median of the BCB Focus survey, using the forecasts
  submitted over the last 30 days (`baseCalculo = 0`, the figure in the published report).
  - We take the latest survey dated **before** the release day.
  - The 5-day median is shown as a secondary figure.
  - Focus has no IPCA-15 survey, so the IPCA-15 card says that no expectation exists.

## Validation: how we know our numbers match the official ones

Nothing is stored or published unless every check passes. The generic checks run for every
country:

- the data follows the schema: known units, valid months, no duplicates, UTC timestamps;
- every series is in the catalog;
- headline and group series have no missing months;
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
| SGS copy matches IBGE | The BCB's copies of the monthly and 12-month IPCA (SGS 433, 13522) match SIDRA exactly | 0 of 381 months differ |
| SGS series are current | Cores, diffusion, free and administered prices reach the latest IPCA month | — |
| Tables agree on overlap | Tables 7060/1419 and the long-run table 1737 publish identical headline values | 0 (485 values) |

The 12-month check is applied to the latest month only. Chaining rounded monthly prints works
well at today's inflation rates, but drifts by up to 0.14 pp in the early-1990s hyperinflation,
when monthly rates were tens of percent. That's a property of rounding, not of the data.

## Chart colors

Each country's page palette and chart order live in `config/countries.yaml`.

- **Chart series** reuse a categorical palette that was already checked for color-blind safety.
  For Brazil it is reordered so that blue, green and gold lead.
- **The order was checked by computation** (the dataviz palette validator) in light and dark mode,
  against each mode's surface color:
  - the lightness band and chroma floor;
  - separation between neighboring colors as seen with each kind of color blindness;
  - separation with normal color vision.
  The weakest neighboring pair is aqua against red, at ΔE 6.5–6.9. It is only used in the stacked
  chart, which adds 2px gaps between segments, a legend and a table view.
- **Every chart has a "Show table" view,** because some light-mode hues are below 3:1 contrast
  against the background.
