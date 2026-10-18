# Brazil adapter notes

## Basket eras and structural breaks

| Era | SIDRA table | Basket (POF) | Levels available |
|---|---|---|---|
| Dec 1979 → | 1737 | — | headline only, plus the index number (Dec 1993 = 100) |
| Jan 2012 – Dec 2019 | 1419 | 2008–2009 | general, 9 groups, subgroups, items, subitems |
| Jan 2020 → | 7060 | 2017–2018 | same |
| IPCA-15, Feb 2020 → | 7062 | 2017–2018 | same |

- Where tables overlap we keep the most detailed one, so 7060, then 1419, then 1737. A validation check
  confirms the overlapping headline values are identical. They were identical across all 509 values
  compared in Oct 2026.
- Series identity across eras uses IBGE's hierarchical code: group `1`, subgroup `11`, item
  `1101`, subitem `1101002`. The 9 group codes are the same in both baskets.
- 13 codes were renamed in Jan 2020 but kept their meaning. Examples: `9101008` "Telefone celular" became
  "Plano de telefonia móvel", `7201090` "Hotel" became "Hospedagem", and subgroup `72` "Recreação, fumo e
  fotografia" became "Recreação e fumo". We use the newest label.
- 65 subseries exist only in the 2012–2019 basket, and 58 only in the 2020 basket. At item level, only
  `7203` (Fotografia e filmagem) ends in Dec 2019. `first_period` and `last_period` on each series record this.
- Table 1419's metadata has no hierarchy levels, so levels are derived from the code length
  everywhere.
- IPCA-15 data in table 7062 starts in Feb 2020. Its 2020 year-to-date figures therefore can't be
  rebuilt from monthly values, since January is missing. The YTD check uses only the latest year.

## Weights

IBGE's "peso mensal" for month *t* is the weight that goes with month *t*'s change:
Σ weight_t × change_t / 100 over the 9 groups reproduces the headline within 0.0066 pp
(2012–2026). Using the previous month's weights misses by up to 0.04 pp.

## Source quirks

- **SGS errors arrive with HTTP 200**, either as an HTML error page or as a JSON `{"erro": ...}`
  body. Both are rejected so they get retried. The firewall blocks bursts of requests.
- **SGS 432 (Selic target)** has rows dated in the future, holding the value in force until the
  next meeting. We drop rows dated after the fetch day.
- **Focus (Olinda)** needs `%20` for spaces in `$filter`.
- **IBGE calendar API** shows `12:00:00` for 09:00 Brasília releases, so we read it as UTC.
- **SIDRA special values:** `-` means zero, and `..`/`...`/`X` mean missing.
