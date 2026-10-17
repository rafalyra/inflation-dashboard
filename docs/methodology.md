# Methodology

Each metric is implemented once, in `src/inflation/metrics/`. Its formula and the reasoning
behind it are written down here. The web app only displays the results.

No metrics implemented yet. They arrive in Phase 1.

## Conventions

- Names end in `_pct` for percent changes and `_pp` for percentage-point contributions or differences.
- Percent and pp values are shown with 2 decimals. The decimal separator follows the UI language.
- Reference periods are calendar months written `YYYY-MM`. Timestamps are stored in UTC.
