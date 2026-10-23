"""Is this month unusual for the time of year? (docs/methodology.md §Seasonality)

Many prices follow the calendar: school fees jump in February, clothing falls in the sales,
food moves with harvests. So a monthly change is best judged against the same calendar
month in "normal" years (the baseline, from config). We summarize each calendar month by
its median and its middle half (25th to 75th percentile) over the baseline years.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

MONTHS = [f"{m:02d}" for m in range(1, 13)]


def _in_years(mom_pct: pd.Series, years: list[int]) -> pd.Series:
    return mom_pct[mom_pct.index.str[:4].astype(int).isin(years)]


def monthly_stats(mom_pct: pd.Series, years: list[int]) -> pd.DataFrame:
    """Median, quartiles and count of the monthly change for each calendar month."""
    base = _in_years(mom_pct.dropna(), years)
    grouped = base.groupby(base.index.str[5:])
    stats = pd.DataFrame(
        {
            "median_pct": grouped.median(),
            "q25_pct": grouped.quantile(0.25),
            "q75_pct": grouped.quantile(0.75),
            "n": grouped.size(),
        }
    )
    return stats.reindex(MONTHS)


def latest_vs_pattern(mom_pct: pd.Series, period: str, stats: pd.DataFrame) -> dict[str, Any]:
    """The latest change next to its calendar month's baseline median and middle half."""
    month = period[5:]
    row = stats.loc[month]
    value = float(mom_pct[period])
    median = None if pd.isna(row["median_pct"]) else float(row["median_pct"])
    return {
        "period": period,
        "value_pct": value,
        "median_pct": median,
        "q25_pct": None if pd.isna(row["q25_pct"]) else float(row["q25_pct"]),
        "q75_pct": None if pd.isna(row["q75_pct"]) else float(row["q75_pct"]),
        "n_years": int(row["n"]) if not pd.isna(row["n"]) else 0,
        "deviation_pp": None if median is None else value - median,
    }


def profile(
    mom_pct: pd.Series, year: int, previous_years: int, stats: pd.DataFrame
) -> dict[str, Any]:
    """Jan–Dec changes for `year` and the years just before it, beside the baseline band."""

    def year_values(y: int) -> list[float | None]:
        return [
            float(mom_pct[f"{y}-{m}"])
            if f"{y}-{m}" in mom_pct.index and pd.notna(mom_pct[f"{y}-{m}"])
            else None
            for m in MONTHS
        ]

    return {
        "year": year,
        "current": year_values(year),
        "previous": {str(y): year_values(y) for y in range(year - previous_years, year)},
        "median_pct": [None if pd.isna(v) else float(v) for v in stats["median_pct"]],
        "q25_pct": [None if pd.isna(v) else float(v) for v in stats["q25_pct"]],
        "q75_pct": [None if pd.isna(v) else float(v) for v in stats["q75_pct"]],
    }


def weighted_deviation(
    mom_pct: pd.DataFrame, weight_pct: pd.DataFrame, period: str, years: list[int]
) -> pd.Series:
    """For each component (column): (this month's change − its baseline median for this
    calendar month) × its weight / 100, in pp.

    It shows which components pushed the headline away from a normal month for this time of
    year. Components without baseline history for this month (e.g. new items) are left out.
    """
    month = period[5:]
    base = mom_pct[mom_pct.index.str[5:] == month]
    base = base[base.index.str[:4].astype(int).isin(years)]
    median = base.median()
    deviation = (mom_pct.loc[period] - median) * weight_pct.loc[period] / 100
    return deviation.dropna()
